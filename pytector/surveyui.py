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

from PyQt5 import QtCore, QtWidgets

import matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

from . import rose, survey

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
        self.table.setHorizontalHeaderLabels([c[1] for c in COLUMNS])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QtWidgets.QTableWidget.SelectRows)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.itemChanged.connect(self._edited)
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
        lay.addWidget(split, 1)

        bot = QtWidgets.QHBoxLayout()
        bot.setSpacing(6)
        for text, tip, slot in (
                ('Load phases...',
                 'CSV of  run,stage . The key may be the run id, the station '
                 'or the folder name.', self.load_stages),
                ('Load coordinates...',
                 'CSV of  site,longitude,latitude , keyed the same way.',
                 self.load_coords),
                ('Save phases...',
                 'Write the phase and type columns to py_data/phases.csv, '
                 'where the next scan picks them up by itself.',
                 self.save_stages),
                ('Save coordinates...',
                 'Write the lon/lat columns to py_data/coordinates.csv, '
                 'read back the same way.', self.save_coords)):
            b = QtWidgets.QPushButton(text)
            b.setToolTip(tip)
            b.clicked.connect(slot)
            bot.addWidget(b)
        bot.addStretch(1)
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
        self.recs = recs

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
                    if not editable:
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
        self.redraw()

    def _edited(self, item):
        if self._filling:
            return
        row, col = item.row(), item.column()
        key = COLUMNS[col][0]
        run_id = self.table.item(row, 0).data(QtCore.Qt.UserRole)
        for rec in self.recs:
            if rec['run_id'] == run_id:
                rec[key] = item.text().strip()
                break
        if key in ('stage', 'type'):
            self.redraw()
            self.refresh_counts()

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

    def load_stages(self):
        if not self._need_recs():
            return
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'CSV of  run,stage', self.root, 'CSV (*.csv);;All (*)')
        if p:
            survey.attach_stages(self.recs, p)
            self.refresh()

    def load_coords(self):
        if not self._need_recs():
            return
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'CSV of  site,longitude,latitude', self.root,
            'CSV (*.csv);;All (*)')
        if p:
            survey.attach_coords(self.recs, p)
            self.refresh()

    def save_stages(self):
        """Write the phase and type columns out, so the judgement survives.

        Typing a phase for every run is the expensive part of this window and
        it is the one thing that cannot be recomputed. It goes to a file the
        moment the user asks, keyed on the station so a rescan can find it.
        """
        if not self._need_recs():
            return
        # Defaults to py_data/phases.csv, which is exactly where the next scan
        # looks: save once and the judgement comes back by itself.
        p, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save phases', PHASE_FILE, 'CSV (*.csv)')
        if not p:
            return
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(p, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['site', 'stage', 'type'])
            for r in self.recs:
                if str(r.get('stage', '')).strip() or str(r.get('type', '')).strip():
                    w.writerow([r.get('site', ''), r.get('stage', ''),
                                r.get('type', '')])
        self.lbl_head.setText('phases written to %s' % p)

    def save_coords(self):
        """Write the coordinate columns out, same idea as save_phases."""
        if not self._need_recs():
            return
        p, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save coordinates', COORD_FILE, 'CSV (*.csv)')
        if not p:
            return
        d = os.path.dirname(p)
        if d and not os.path.isdir(d):
            os.makedirs(d)
        with io.open(p, 'w', encoding='utf-8', newline='') as fh:
            w = csv.writer(fh)
            w.writerow(['site', 'longitude', 'latitude'])
            for r in self.recs:
                if survey._num(r.get('longitude')) is not None:
                    w.writerow([r.get('site', ''), r.get('longitude', ''),
                                r.get('latitude', '')])
        self.lbl_head.setText('coordinates written to %s' % p)

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
