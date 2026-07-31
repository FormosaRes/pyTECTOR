# -*- coding: utf-8 -*-
"""The survey window: many runs at once, rather than one site at a time.

The main window answers "what is the stress at this site". A study asks what a
whole set of sites says, and until now that question could only be reached from
the command line, through make_survey.py. This is the same work with the two
things that actually need judgement made visible and editable:

  which phase a run belongs to     nothing here guesses it, ever
  where the site is                typed in, or loaded from a CSV

Everything else follows from those two. Assign phases, and the roses redraw;
add coordinates, and the map export fills in.

Nothing in the scanned folders is read for anything but its recorded output,
and nothing there is ever written to. Exports go where the user points them.
"""
import csv
import io
import os

from PyQt5 import QtCore, QtGui, QtWidgets

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

from . import mappanel, rose, survey

#: The working data folder, beside the program. Old-format TENSOR runs get
#: dropped into DATA_DIR, one folder per station, and the two side files sit
#: next to it. The whole tree is gitignored: it is field data.
PY_DATA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'py_data')
DATA_DIR = os.path.join(PY_DATA, '古應力資料')
COORD_FILE = os.path.join(PY_DATA, 'coordinates.csv')
PHASE_FILE = os.path.join(PY_DATA, 'phases.csv')

#: table layout: (record key, heading, editable)
COLUMNS = [
    ('site', 'station', False),
    ('stage', 'phase', True),
    ('type', 'type', True),
    ('n', 'n', False),
    ('solution_from', 'solution', False),
    ('phi', 'Phi', False),
    ('ANG', 'ANG', False),
    ('RUP', 'RUP', False),
    ('s1', 'sigma1', False),
    ('s2', 'sigma2', False),
    ('s3', 'sigma3', False),
    ('longitude', 'lon', True),
    ('latitude', 'lat', True),
    ('run_id', 'run', False),
]

#: what may be typed into the type column. Blank is allowed and means "not
#: decided", which is different from any of the three.
TYPES = ['', 'normal', 'thrust', 'strike-slip']

#: What belongs in each editable column, shown on hover.
#:
#: These four were tinted for a while so they would not look like the twelve
#: read-only ones. On a table that already stripes its rows the extra colour
#: turned the whole grid muddy, and it was worse than the problem it solved.
#: The heading carries a pencil instead, which marks the column without
#: touching any of the cells.
EDIT_HINT = {
    'stage': 'Which deformation phase. Yours to decide; nothing here guesses '
             'it. Any label will do, and it groups the roses and the map.',
    'type': 'normal, thrust or strike-slip, or blank for undecided. It '
            'decides which axis the phase is read through.',
    'longitude': 'Decimal degrees, east positive.',
    'latitude': 'Decimal degrees, north positive.',
}


def _axis_text(rec, i):
    t, p = rec.get('s%d_trend' % i), rec.get('s%d_plunge' % i)
    t, p = survey._num(t), survey._num(p)
    if t is None or p is None:
        return ''
    return '%03.0f/%02.0f' % (t, p)


class Scanner(QtCore.QThread):
    """Walk the tree off the interface thread; a deep archive takes seconds."""
    done = QtCore.pyqtSignal(object, object)

    def __init__(self, root, method, parent=None):
        super(Scanner, self).__init__(parent)
        self.root, self.method = root, method

    def run(self):
        try:
            recs = survey.collect(self.root, method=self.method)
            self.done.emit(recs, None)
        except Exception as exc:                        # pragma: no cover
            self.done.emit([], str(exc))


class SurveyWindow(QtWidgets.QDialog):
    """Non-modal, so the main window stays usable behind it."""

    def __init__(self, parent=None):
        super(SurveyWindow, self).__init__(parent)
        self.setWindowTitle('pyTECTOR  -  survey')
        self.setWindowFlags(self.windowFlags()
                            | QtCore.Qt.WindowMinMaxButtonsHint)
        self.resize(1320, 880)
        self.main = parent
        self.recs = []
        self.root = DATA_DIR if os.path.isdir(DATA_DIR) else ''
        self.scanner = None
        self._filling = False        # table writes during a refill are not edits
        self._build()
        if self.root:
            self.lbl_root.setText(self.root)
            self.btn_scan.setEnabled(True)
            self.scan()

    # ------------------------------------------------------------ layout --
    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(6)
        b = QtWidgets.QPushButton('Folder...')
        b.setToolTip('A folder holding TENSOR run folders, at any depth')
        b.clicked.connect(self.choose_folder)
        top.addWidget(b)
        self.lbl_root = QtWidgets.QLabel('no folder chosen')
        self.lbl_root.setObjectName('legend')
        top.addWidget(self.lbl_root, 1)

        self.cmb_method = QtWidgets.QComboBox()
        self.cmb_method.addItems(['auto', 'invdir', 'psidir', '03'])
        self.cmb_method.setToolTip(
            'Which recorded solution to take when a run has more than one.\n'
            'auto prefers the block the run itself was left showing.')
        self.cmb_method.setFixedWidth(90)
        top.addWidget(self.cmb_method)

        self.btn_scan = QtWidgets.QPushButton('Scan')
        self.btn_scan.clicked.connect(self.scan)
        self.btn_scan.setEnabled(False)
        top.addWidget(self.btn_scan)
        lay.addLayout(top)

        self.lbl_head = QtWidgets.QLabel('')
        self.lbl_head.setObjectName('context')
        lay.addWidget(self.lbl_head)

        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)

        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        # a pencil on the four headings that can be typed into, rather than
        # colouring the cells themselves
        self.table.setHorizontalHeaderLabels(
            [(c[1] + '  ✎') if c[2] else c[1] for c in COLUMNS])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        # A single click on an already-selected cell starts editing. The
        # default needs a double click, and with the editable columns looking
        # exactly like the read-only ones there was nothing to suggest they
        # could be edited at all.
        self.table.setEditTriggers(
            QtWidgets.QTableWidget.DoubleClicked
            | QtWidgets.QTableWidget.SelectedClicked
            | QtWidgets.QTableWidget.EditKeyPressed
            | QtWidgets.QTableWidget.AnyKeyPressed)
        self.table.itemChanged.connect(self._edited)
        # Double-click a row to open that run in the main window. This is
        # where the old "Scan folder" button's job belongs: it opened a folder
        # only to show a bare list of paths, and this list already has the
        # numbers next to each one.
        self.table.itemDoubleClicked.connect(self._open_run)
        split.addWidget(self.table)

        tabs = QtWidgets.QTabWidget()
        self.fig = Figure(figsize=(9, 3.6))
        self.canvas = Canvas(self.fig)
        tabs.addTab(self.canvas, 'Roses')
        self.summary = QtWidgets.QTableWidget(0, 8)
        self.summary.setHorizontalHeaderLabels(
            ['phase', 'sites', 'read', 'why', 'usable', 'too steep',
             'mean', 'R'])
        self.summary.verticalHeader().setVisible(False)
        self.summary.setEditTriggers(QtWidgets.QTableWidget.NoEditTriggers)
        tabs.addTab(self.summary, 'By phase')
        split.addWidget(tabs)
        split.setSizes([520, 330])

        # Table and roses on the left, the map on the right. A stress
        # direction is a spatial claim and a column of azimuths cannot be read
        # as one; side by side, editing a phase moves both at once.
        self.map = mappanel.MapPanel(self)
        outer = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        outer.addWidget(split)
        outer.addWidget(self.map)
        outer.setStretchFactor(0, 3)
        outer.setStretchFactor(1, 2)
        outer.setSizes([820, 560])
        lay.addWidget(outer, 1)

        bot = QtWidgets.QHBoxLayout()
        bot.setSpacing(6)
        # Two buttons rather than five. Load used to be three, one per kind of
        # file, which made the user classify the CSV before opening it when
        # its own header already says what it is. Save used to be two, and
        # nobody writes the phases back without the coordinates.
        for text, tip, slot in (
                ('Load...',
                 'Any CSV keyed on the station: phases, coordinates, or whole '
                 'determinations that have no run folder behind them. Which '
                 'it is comes from its own column names.', self.load_csv),
                ('Save...',
                 'Write the phase, type and coordinate columns back out as '
                 'phases.csv and coordinates.csv, where the next scan picks '
                 'them up by itself.', self.save_edits)):
            b = QtWidgets.QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bot.addWidget(b)
        bot.addStretch(1)
        # Its own button as well as being part of Export all. The printed
        # table is the thing most often wanted on its own, and having it come
        # out only as one file among nine meant it could not be found.
        self.btn_table = QtWidgets.QPushButton('Table for a paper...')
        self.btn_table.setToolTip(
            'The solution table in the layout journals in this field print: '
            'site, stage, N, D and P for each axis, the ratio, ANG, RUP and '
            'Q. LaTeX, Word or Markdown.')
        self.btn_table.clicked.connect(self.export_table)
        self.btn_table.setEnabled(False)
        bot.addWidget(self.btn_table)

        self.btn_export = QtWidgets.QPushButton('Export all...')
        self.btn_export.setToolTip(
            'Table, fault data, map points as CSV and GeoJSON, and a rose '
            'per phase, into a folder you choose.')
        self.btn_export.clicked.connect(self.export)
        self.btn_export.setEnabled(False)
        bot.addWidget(self.btn_export)
        lay.addLayout(bot)

    # ------------------------------------------------------------- scan --
    def choose_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Folder of TENSOR runs', self.root or os.path.expanduser('~'))
        if not d:
            return
        self.root = d
        self.lbl_root.setText(d)
        self.btn_scan.setEnabled(True)
        self.scan()

    def scan(self):
        if not self.root:
            return
        self.btn_scan.setEnabled(False)
        self.lbl_head.setText('scanning %s ...' % self.root)
        self.scanner = Scanner(self.root, self.cmb_method.currentText(), self)
        self.scanner.done.connect(self._scanned)
        self.scanner.start()

    def _scanned(self, recs, err):
        self.btn_scan.setEnabled(True)
        if err:
            self.lbl_head.setText('scan failed: %s' % err)
            return
        # keep whatever the user had already decided, keyed on the run
        old = {r['run_id']: r for r in self.recs}
        for r in recs:
            prev = old.get(r['run_id'])
            if prev:
                for k in ('stage', 'type', 'longitude', 'latitude'):
                    if prev.get(k, '') != '':
                        r[k] = prev[k]
            r.setdefault('type', '')
        # a rescan rebuilds the list from the folder; imported rows have no
        # folder to be rebuilt from, so they are carried across by hand
        self.recs = recs + list(getattr(self, 'imported', []))

        # Pick up the side files without being asked. Typing a phase for every
        # station is the expensive part of this window, and having to remember
        # to reload it after every scan is how it gets lost.
        picked = []
        for path, fn, what in ((PHASE_FILE, self._apply_phases, 'phases'),
                               (COORD_FILE, survey.attach_coords,
                                'coordinates')):
            if os.path.exists(path):
                try:
                    fn(self.recs, path)
                    picked.append(what)
                except Exception as exc:
                    print('could not read %s: %s' % (path, exc))
        self._picked = picked
        self.refresh()

    @staticmethod
    def _apply_phases(recs, path):
        """phases.csv carries the type column too, which attach_stages does not."""
        survey._attach(recs, path, ['stage', 'type'], 'phases')

    # ------------------------------------------------------------ table --
    def refresh(self):
        self._filling = True
        try:
            self.table.setSortingEnabled(False)
            self.table.setRowCount(len(self.recs))
            for row, rec in enumerate(self.recs):
                for col, (key, _head, editable) in enumerate(COLUMNS):
                    if key in ('s1', 's2', 's3'):
                        text = _axis_text(rec, int(key[1]))
                    else:
                        v = rec.get(key, '')
                        text = '' if v is None else str(v)
                    it = QtWidgets.QTableWidgetItem(text)
                    if editable:
                        it.setToolTip(EDIT_HINT[key])
                    else:
                        it.setFlags(it.flags() & ~QtCore.Qt.ItemIsEditable)
                    if col == 0:
                        it.setData(QtCore.Qt.UserRole, rec['run_id'])
                    self.table.setItem(row, col, it)
            self.table.resizeColumnsToContents()
            self.table.setSortingEnabled(True)
        finally:
            self._filling = False

        none_sol = sum(1 for r in self.recs
                       if r.get('solution_from') == 'none')
        staged = sum(1 for r in self.recs if str(r.get('stage', '')).strip())
        placed = sum(1 for r in self.recs
                     if survey._num(r.get('longitude')) is not None)
        bits = ['%d run(s)' % len(self.recs),
                '%d assigned to a phase' % staged,
                '%d with coordinates' % placed]
        if none_sol:
            bits.append('%d carry no recorded solution' % none_sol)
        picked = getattr(self, '_picked', None)
        if picked:
            bits.append('%s read from py_data' % ' and '.join(picked))
        self.lbl_head.setText(',  '.join(bits))
        self.btn_export.setEnabled(bool(self.recs))
        self.btn_table.setEnabled(bool(self.recs))
        self.redraw()
        self.map.set_records(self.recs)

    def _open_run(self, item):
        """Load the double-clicked run into the main window.

        Only on a read-only column: double-clicking an editable one opens the
        editor, which is what the user meant by double-clicking it.
        """
        if COLUMNS[item.column()][2]:
            return
        run_id = self.table.item(item.row(), 0).data(QtCore.Qt.UserRole)
        rec = next((r for r in self.recs if r['run_id'] == run_id), None)
        if rec is None:
            return
        if not rec.get('folder'):
            QtWidgets.QMessageBox.information(
                self, 'pyTECTOR',
                '%s was imported from a table. There is no run behind it to '
                'open.' % rec.get('site', ''))
            return
        path = os.path.join(rec['folder'], rec['file_name'])
        if not os.path.exists(path):
            QtWidgets.QMessageBox.warning(
                self, 'pyTECTOR', 'The data file has gone:\n\n%s' % path)
            return
        main = self.main
        if main is None or not hasattr(main, '_load'):
            return
        main._load(path)
        main.show()
        main.raise_()
        main.activateWindow()

    def _edited(self, item):
        if self._filling:
            return
        row, col = item.row(), item.column()
        key = COLUMNS[col][0]
        run_id = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        text = item.text().strip()

        # A coordinate has to be a number in range. Without this a slipped
        # key put a station in the Atlantic and took the whole view with it,
        # and the only clue was that the map had gone blank.
        if key in ('longitude', 'latitude') and text:
            v = survey._num(text)
            limit = 180.0 if key == 'longitude' else 90.0
            if v is None or abs(v) > limit:
                QtWidgets.QMessageBox.warning(
                    self, 'pyTECTOR',
                    '%r is not a %s.\n\nDecimal degrees, between -%g and %g.'
                    % (text, key, limit, limit))
                self.refresh()
                return

        for rec in self.recs:
            if rec['run_id'] == run_id:
                rec[key] = text
                break
        if key in ('stage', 'type'):
            self.redraw()
            self.refresh_counts()
            self.map.redraw()
        elif key in ('longitude', 'latitude'):
            # a station that has just been given a position must appear, and
            # the view has to grow to include it
            self.refresh_counts()
            self.map.redraw(refit=True, refetch=True)

    def refresh_counts(self):
        staged = sum(1 for r in self.recs if str(r.get('stage', '')).strip())
        placed = sum(1 for r in self.recs
                     if survey._num(r.get('longitude')) is not None)
        self.lbl_head.setText('%d run(s),  %d assigned to a phase,  '
                              '%d with coordinates'
                              % (len(self.recs), staged, placed))

    # ------------------------------------------------------------ roses --
    def _phases(self):
        """{phase: [records]}, in a stable order, unassigned last."""
        from collections import OrderedDict
        by = {}
        for r in self.recs:
            by.setdefault(str(r.get('stage', '')).strip() or '(unassigned)',
                          []).append(r)
        keys = sorted(by, key=lambda s: (s == '(unassigned)', s))
        return OrderedDict((k, by[k]) for k in keys)

    def _axes_of(self, items):
        out = {}
        for i in (1, 2, 3):
            pairs = []
            for r in items:
                t = survey._num(r.get('s%d_trend' % i))
                p = survey._num(r.get('s%d_plunge' % i))
                if t is not None and p is not None:
                    pairs.append((t, p))
            out['sigma%d' % i] = pairs
        return out

    def redraw(self):
        self.fig.clear()
        phases = [(k, v) for k, v in self._phases().items()
                  if k != '(unassigned)']
        if not phases:
            ax = self.fig.add_subplot(111)
            ax.axis('off')
            ax.text(0.5, 0.5, 'Assign a phase to some runs and the roses '
                              'appear here.\nNothing here guesses which phase '
                              'a run belongs to.',
                    ha='center', va='center', fontsize=10, color='#7A776F')
            self.canvas.draw_idle()
            self.summary.setRowCount(0)
            return

        n = len(phases)
        self.summary.setRowCount(n)
        for i, (name, items) in enumerate(phases):
            groups = self._axes_of(items)
            label, why = rose.axis_for_regime(
                [r.get('type') for r in items], groups)
            ax = self.fig.add_subplot(1, n, i + 1, projection='polar')
            st = rose.plot_rose(ax, groups.get(label) or [],
                                title='%s  %s' % (name, label or ''),
                                emphasis=True)
            trends, dropped = rose.shallow_only(groups.get(label) or [])
            for col, text in enumerate((
                    name, str(len(items)), label or '-', why,
                    str(len(trends)), str(dropped),
                    '-' if not st else '%03.0f' % st['mean'],
                    '-' if not st else '%.2f' % st['R'])):
                self.summary.setItem(i, col,
                                     QtWidgets.QTableWidgetItem(text))
        self.summary.resizeColumnsToContents()
        self.fig.tight_layout(rect=(0, 0.02, 1, 0.98))
        self.canvas.draw_idle()

    # ------------------------------------------------------- side files --
    def _need_recs(self):
        if self.recs:
            return True
        QtWidgets.QMessageBox.information(self, 'pyTECTOR',
                                          'Scan a folder first.')
        return False

    def load_csv(self):
        """One opener for all three kinds, told apart by their own headers.

        A file that carries stress axes is a set of determinations and is
        imported as such. Otherwise whatever columns it has are applied to the
        runs already listed: phase and type, coordinates, or both, since one
        file often holds both and there was no reason to make that two trips.
        """
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'CSV keyed on the station', PY_DATA,
            'CSV (*.csv);;All (*)')
        if not p:
            return
        try:
            with io.open(p, encoding='utf-8-sig', newline='') as fh:
                head = next(csv.reader(
                    l for l in fh if not l.lstrip().startswith('#')), [])
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTECTOR',
                                          'Could not read it:\n\n%s' % exc)
            return
        cols = {(c or '').strip().lower() for c in head}

        if cols & {'s1_trend', 's2_trend', 's3_trend'}:
            self._import_solutions(p)
            return
        if not self._need_recs():
            return

        did = []
        if cols & {'stage', 'phase', 'type', 'regime'}:
            survey._attach(self.recs, p, ['stage', 'type'], 'phases')
            did.append('phases')
        if cols & {'longitude', 'lon', 'latitude', 'lat'}:
            survey.attach_coords(self.recs, p)
            did.append('coordinates')
        if not did:
            QtWidgets.QMessageBox.information(
                self, 'pyTECTOR',
                'Nothing in that file is recognised.\n\nExpected a station '
                'column plus at least one of: stage, type, longitude, '
                'latitude, or the s1/s2/s3 trend and plunge columns of a full '
                'determination.\n\nIts columns: %s'
                % ', '.join(sorted(c for c in cols if c)))
            return
        self.refresh()
        self.lbl_head.setText('%s read from %s'
                              % (' and '.join(did), os.path.basename(p)))

    def _import_solutions(self, p):
        """Add determinations that have no run behind them.

        Kept apart from the scanned records rather than merged into them: a
        rescan rebuilds the list from the folder, and anything imported would
        vanish with it if it were not held separately.
        """
        try:
            rows = survey.read_solutions(p)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTECTOR',
                                          'Could not read that file:\n\n%s'
                                          % exc)
            return
        if not rows:
            QtWidgets.QMessageBox.information(
                self, 'pyTECTOR',
                'No rows in that file had a site name.')
            return
        have = {r['run_id'] for r in self.recs}
        self.imported = [r for r in getattr(self, 'imported', [])
                         if r['run_id'] not in {x['run_id'] for x in rows}]
        self.imported += [r for r in rows if r['run_id'] not in have]
        self.recs = [r for r in self.recs
                     if r.get('solution_from') != 'imported'] + self.imported
        self.refresh()

    def save_edits(self):
        """Write the four typed-in columns back out, both files together.

        Typing a phase for every station is the expensive part of this window
        and it is the one thing that cannot be recomputed. It goes back to
        py_data, which is exactly where the next scan looks, so saving once
        means it returns by itself.

        Both files rather than one at a time: nobody writes the phases back
        without the coordinates, and asking twice for one action is how a
        button row grows to seven.
        """
        if not self._need_recs():
            return
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Write phases.csv and coordinates.csv into', PY_DATA)
        if not d:
            return
        wrote = []

        n = 0
        with io.open(os.path.join(d, 'phases.csv'), 'w', encoding='utf-8',
                     newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['site', 'stage', 'type'])
            for r in self.recs:
                if (str(r.get('stage', '')).strip()
                        or str(r.get('type', '')).strip()):
                    w.writerow([r.get('site', ''), r.get('stage', ''),
                                r.get('type', '')])
                    n += 1
        wrote.append('phases.csv (%d)' % n)

        n = 0
        with io.open(os.path.join(d, 'coordinates.csv'), 'w',
                     encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['site', 'longitude', 'latitude'])
            for r in self.recs:
                if survey._num(r.get('longitude')) is not None:
                    w.writerow([r.get('site', ''), r.get('longitude', ''),
                                r.get('latitude', '')])
                    n += 1
        wrote.append('coordinates.csv (%d)' % n)
        self.lbl_head.setText('%s written to %s' % (' and '.join(wrote), d))

    #: file dialog filter -> the extension write_publication_table produces
    TABLE_KINDS = [
        ('Word, keeps the merged header (*.html)', 'html'),
        ('LaTeX, booktabs (*.tex)', 'tex'),
        ('Markdown (*.md)', 'md'),
    ]

    def export_table(self):
        """Write just the printed table, in whichever of the three is wanted.

        All three are always generated, because they cost nothing and the one
        that is needed changes with where the table is going; the chooser only
        decides which name the user is asked for and which is reported back.
        """
        if not self._need_recs():
            return
        p, chosen = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Table for a paper',
            os.path.join(PY_DATA, 'table_publication.html'),
            ';;'.join(k[0] for k in self.TABLE_KINDS))
        if not p:
            return
        want = dict(self.TABLE_KINDS).get(chosen, 'html')
        outdir = os.path.dirname(p) or '.'
        try:
            n = survey.write_publication_table(
                self.recs, outdir,
                caption='Results of palaeostress determination')
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTECTOR',
                                          'Could not write it:\n\n%s' % exc)
            return
        # write_publication_table names its own files; if the user typed
        # something else, put the chosen format under that name too
        made = os.path.join(outdir, 'table_publication.%s' % want)
        if os.path.normcase(os.path.abspath(p)) != \
                os.path.normcase(os.path.abspath(made)):
            import shutil
            shutil.copyfile(made, p)
        self.lbl_head.setText(
            '%d row(s) written to %s  (.tex, .html and .md all in %s)'
            % (n, os.path.basename(p), outdir))

    def export(self):
        if not self._need_recs():
            return
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Write the survey into', self.root)
        if not d:
            return
        try:
            survey.write_all(self.recs, d)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTECTOR',
                                          'Export failed:\n%s' % exc)
            return
        self.lbl_head.setText('written to %s' % d)
