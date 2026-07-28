# -*- coding: utf-8 -*-
"""pyTENSOR desktop interface.

Run it yourself:   pyTENSOR.bat        (or  python pyTENSOR.py)

Never launched from an automated shell: a QApplication started there pops a Qt
platform-plugin error box and exits.

The layout follows Angelier's own chain, Mesure -> Tensor -> Dessin:

    left    type records, watch them land on the stereogram
    centre  the stereograms, which are the deliverable
    bottom  the numbers, at a size you can actually read

Record format, four fields:

    CS - 122 - 87W - 124
    |    |     |     |
    |    |     |     +-- pitch + quadrant (62N), or a bare trend (124)
    |    |     +-------- dip + quadrant
    |    +-------------- strike
    +------------------- confidence C/P/S  +  movement I/N/S/D
"""
import os
import sys
import traceback

os.environ.setdefault('QT_AUTO_SCREEN_SCALE_FACTOR', '1')

import numpy as np
from PyQt5 import QtCore, QtGui, QtWidgets

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

from pytensor import (core, entry, invdir, modern, plot, report, retro,
                      rotate, splash, tensorfile)
from pytensor.ui_style import QSS, MUTED

AXES = ('sigma1', 'sigma2', 'sigma3')
SYM = ('σ₁', 'σ₂', 'σ₃')
PHI = 'Φ'
DEG = '°'

#: The two runs, named after what they are rather than by a letter that would
#: imply one is the better one. INVDIR is Angelier's own name for the method;
#: S4MIN says only that it is the exact minimum of the same S4. Both inherit
#: the criterion's built-in bias, so neither is "the true stress".
#:   key, display name, 4-character code for INFO1, one-line description
MODES = (
    ('A', 'INVDIR', 'INVD', 'as TENSOR 5.45 runs it'),
    ('B', 'S4MIN', 'S4MN', 'exact minimum of the same criterion'),
)
NAME = {k: nm for k, nm, _c, _d in MODES}
CODE = {k: c for k, _nm, c, _d in MODES}


def heading(text):
    lab = QtWidgets.QLabel(text.upper())
    lab.setObjectName('heading')
    return lab


# ------------------------------------------------------------------ worker --
class Worker(QtCore.QThread):
    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, n, s, do_a, do_b, n_pass, lam_printed=None,
                 parent=None):
        super(Worker, self).__init__(parent)
        self.n, self.s = n, s
        self.do_a, self.do_b, self.n_pass = do_a, do_b, n_pass
        self.lam_printed = lam_printed

    def run(self):
        try:
            out = {}
            if self.do_a:
                r = invdir.run(self.n, self.s, n_pass=self.n_pass,
                               lam_printed=self.lam_printed)
                res = core.summary(r['T'], self.n, self.s)
                res['T'] = r['T']
                res['lambda_trace'] = r['lambda_trace']
                # the pre-PSIDIR solution, so INFO1 can print both blocks
                res['invdir_summary'] = core.summary(r['T_invdir'],
                                                     self.n, self.s)
                out['A'] = res
            if self.do_b:
                r = modern.run(self.n, self.s, n_starts=400)
                res = core.summary(r['T'], self.n, self.s)
                res['T'] = r['T']
                out['B'] = res
            self.done.emit(out)
        except Exception:
            self.failed.emit(traceback.format_exc())


# ------------------------------------------------------------ entry widget --
class EntryRow(QtWidgets.QWidget):
    """Four segmented fields with auto-advance. Enter commits."""
    submitted = QtCore.pyqtSignal(object)

    WIDTHS = (2, 3, 4, 4)
    HINTS = ('CS', '122', '87W', '124')
    TIPS = ('confidence C / P / S  then movement I / N / S / D',
            'strike, 000 to 360',
            'dip and its quadrant, e.g. 87W',
            'pitch and quadrant e.g. 62N, or a bare trend e.g. 124')

    def __init__(self, parent=None):
        super(EntryRow, self).__init__(parent)
        lay = QtWidgets.QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(3)
        self.fields = []
        for i, (w, hint, tip) in enumerate(zip(self.WIDTHS, self.HINTS,
                                               self.TIPS)):
            e = QtWidgets.QLineEdit()
            e.setObjectName('seg')
            e.setMaxLength(w)
            e.setAlignment(QtCore.Qt.AlignCenter)
            e.setFixedWidth(15 * w + 20)
            e.setPlaceholderText(hint)
            e.setToolTip(tip)
            e.textEdited.connect(self._advance)
            e.returnPressed.connect(self.commit)
            e.installEventFilter(self)
            self.fields.append(e)
            lay.addWidget(e)
            if i < len(self.WIDTHS) - 1:
                d = QtWidgets.QLabel('-')
                d.setStyleSheet('color:%s;' % MUTED)
                lay.addWidget(d)
        lay.addStretch(1)

    def eventFilter(self, obj, ev):
        # backspace in an empty field walks back one field
        if (ev.type() == QtCore.QEvent.KeyPress
                and ev.key() == QtCore.Qt.Key_Backspace
                and isinstance(obj, QtWidgets.QLineEdit)
                and not obj.text()):
            i = self.fields.index(obj)
            if i > 0:
                self.fields[i - 1].setFocus()
                self.fields[i - 1].setCursorPosition(
                    len(self.fields[i - 1].text()))
                return True
        return False

    def _advance(self, _t):
        src = self.sender()
        i = self.fields.index(src)
        if len(src.text()) >= src.maxLength() and i < len(self.fields) - 1:
            self.fields[i + 1].setFocus()
            self.fields[i + 1].selectAll()

    def commit(self):
        vals = [e.text().strip() for e in self.fields]
        if not any(vals):
            return
        try:
            rec = entry.parse_record(*vals)
        except entry.RecordError as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTENSOR', str(exc))
            return
        self.submitted.emit(rec)
        for e in self.fields:
            e.clear()
        self.fields[0].setFocus()

    def focus(self):
        self.fields[0].setFocus()


# ----------------------------------------------------------- result widget --
class ResultStrip(QtWidgets.QFrame):
    """One row of results. Principal axes and the shape ratio go at full size;
    only n and S4 are allowed to be small and grey."""

    def __init__(self, title, parent=None):
        super(ResultStrip, self).__init__(parent)
        self.setObjectName('panel')
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(11, 8, 11, 9)
        lay.setSpacing(3)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(8)
        self.title = heading(title)
        top.addWidget(self.title)
        top.addStretch(1)
        self.small = QtWidgets.QLabel('')
        self.small.setObjectName('secondary')
        top.addWidget(self.small)
        lay.addLayout(top)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(18)
        self.axis_labels = []
        for sym in SYM:
            lab = QtWidgets.QLabel('%s  -' % sym)
            lab.setObjectName('axis')
            self.axis_labels.append(lab)
            row.addWidget(lab)
        row.addSpacing(6)
        self.phi = QtWidgets.QLabel('%s -' % PHI)
        self.phi.setObjectName('value')
        row.addWidget(self.phi)
        self.ang = QtWidgets.QLabel('ANG -')
        self.ang.setObjectName('value')
        row.addWidget(self.ang)
        self.rup = QtWidgets.QLabel('RUP -')
        self.rup.setObjectName('value')
        row.addWidget(self.rup)
        row.addStretch(1)
        lay.addLayout(row)

    def clear(self):
        for lab, sym in zip(self.axis_labels, SYM):
            lab.setText('%s  -' % sym)
        self.phi.setText('%s -' % PHI)
        self.ang.setText('ANG -')
        self.rup.setText('RUP -')
        self.small.setText('')

    def show_result(self, r, n_data=None):
        for lab, sym, key in zip(self.axis_labels, SYM, AXES):
            tr, pl = r[key]
            lab.setText('%s %03d/%02d' % (sym, int(round(tr)) % 360,
                                          int(round(pl))))
        self.phi.setText('%s %.3f' % (PHI, r['phi']))
        if 'ANG_mean' in r:
            self.ang.setText('ANG %.1f%s' % (r['ANG_mean'], DEG))
            self.rup.setText('RUP %.0f%%' % r['RUP_mean'])
        bits = []
        if n_data is not None:
            bits.append('n %d' % n_data)
        if 'S4' in r:
            bits.append('S4 %.4f' % r['S4'])
        if 'n_rup1' in r:
            bits.append('RUP>75 %d' % r['n_rup1'])
        self.small.setText('     '.join(bits))


# ------------------------------------------------------------------- main ---
class Main(QtWidgets.QMainWindow):
    def __init__(self):
        super(Main, self).__init__()
        self.setWindowTitle('pyTENSOR')
        self.resize(1500, 950)
        self.records = []
        self.results = {}
        self.archive = None
        self.rot = None
        self.site_name = '01'
        self.site_code = '01'
        self.archive_lambda = None
        self._build()
        self._refresh()

    @property
    def plot_name(self):
        """Site label, carrying the rotation when one is applied, in the same
        form the archive folders use."""
        if self.rot:
            return '%s %s' % (self.site_name, rotate.describe(*self.rot))
        return self.site_name

    # ------------------------------------------------------------ layout --
    def _build(self):
        tb = self.addToolBar('main')
        tb.setMovable(False)
        tb.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        tb.addAction('Open site').triggered.connect(self.open_site)
        tb.addAction('Scan folder').triggered.connect(self.scan_folder)
        tb.addAction('Clear').triggered.connect(self.clear_all)
        tb.addSeparator()
        self.cb_a = QtWidgets.QCheckBox('INVDIR')
        self.cb_a.setChecked(True)
        self.cb_a.setToolTip(
            "Angelier's direct inversion exactly as TENSOR 5.45 runs it, "
            'including the lambda that stops before it converges. Use this to '
            'reproduce archive numbers.')
        self.cb_b = QtWidgets.QCheckBox('S4MIN')
        self.cb_b.setChecked(True)
        self.cb_b.setToolTip(
            'The exact minimum of the same S4, lambda held at sqrt(3)/2. '
            'Lower S4 on every archive site, but the criterion itself is '
            'biased, so this is not "the true stress" either.')
        tb.addWidget(self.cb_a)
        tb.addWidget(self.cb_b)
        self.cb_fit = QtWidgets.QCheckBox('Fitted shear')
        self.cb_fit.setChecked(False)
        self.cb_fit.setToolTip(
            'Extra panel: the same fault planes carrying the shear stress the '
            'solution predicts. Useful for spotting a datum whose observed '
            'slip runs against the solution; off by default.')
        self.cb_fit.toggled.connect(lambda _v: self._draw())
        tb.addWidget(self.cb_fit)
        lab = QtWidgets.QLabel('  INVDIR pass ')
        lab.setStyleSheet('color:%s;' % MUTED)
        tb.addWidget(lab)
        self.sp_pass = QtWidgets.QSpinBox()
        self.sp_pass.setRange(1, 8)
        self.sp_pass.setToolTip('the "(NO k)" printed in the original INFO1')
        tb.addWidget(self.sp_pass)
        self.cb_lam = QtWidgets.QCheckBox('archive LAMBDA')
        self.cb_lam.setEnabled(False)
        self.cb_lam.setToolTip(
            'Adopt the LAMBDA the site\'s own INFO1 records instead of '
            're-deriving it. Where the surface is flat, re-deriving can land a '
            'degree away with a worse fit; adopting the recorded value '
            'reproduces that historical run. Only available when the site '
            'came with an INFO1.')
        tb.addWidget(self.cb_lam)
        tb.addSeparator()
        self.btn_run = QtWidgets.QPushButton('INVERT')
        self.btn_run.setObjectName('run')
        self.btn_run.setShortcut('Ctrl+Return')
        self.btn_run.setToolTip('Ctrl+Enter')
        self.btn_run.clicked.connect(self.invert)
        tb.addWidget(self.btn_run)
        tb.addSeparator()
        tb.addAction('Save PNG').triggered.connect(self.save_png)
        tb.addAction('Save HPGL').triggered.connect(self.save_hpgl)
        tb.addAction('Save INFO1').triggered.connect(
            lambda: self._save_report('INFO1'))
        tb.addAction('Save MOHR1').triggered.connect(
            lambda: self._save_report('MOHR1'))

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.setChildrenCollapsible(False)
        self.setCentralWidget(split)
        split.addWidget(self._sidebar())
        split.addWidget(self._workspace())
        split.setStretchFactor(1, 1)
        split.setSizes([350, 1150])

        self.status = self.statusBar()
        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedWidth(120)
        self.progress.hide()
        self.status.addPermanentWidget(self.progress)
        self.status.showMessage('type a record, for example  CS 122 87W 124')

    def _sidebar(self):
        w = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(w)
        v.setContentsMargins(10, 10, 6, 10)
        v.setSpacing(3)                      # tight, no group gaps

        v.addWidget(heading('site'))
        self.ed_site = QtWidgets.QLineEdit(self.site_name)
        self.ed_site.textEdited.connect(self._rename)
        v.addWidget(self.ed_site)

        v.addSpacing(6)
        v.addWidget(heading('new record'))
        self.entry = EntryRow()
        self.entry.submitted.connect(self.add_record)
        v.addWidget(self.entry)
        leg = QtWidgets.QLabel(
            'C certain · P probable · S suppose\n'
            'I inverse · N normal · S senestral · D dextral')
        leg.setObjectName('legend')
        v.addWidget(leg)

        v.addSpacing(6)
        v.addWidget(heading('back-tilt'))
        self.cmb_bt = QtWidgets.QComboBox()
        self.cmb_bt.addItems(['off',
                              'reference plane   dip az / dip',
                              'reference plane by pole   trend / plunge',
                              'rotation axis   trend / plunge / angle'])
        self.cmb_bt.currentIndexChanged.connect(self._bt_changed)
        v.addWidget(self.cmb_bt)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(3)
        self.bt_fields = []
        for hint in ('212', '87', '-20'):
            e = QtWidgets.QLineEdit()
            e.setObjectName('seg')
            e.setFixedWidth(58)
            e.setAlignment(QtCore.Qt.AlignCenter)
            e.setPlaceholderText(hint)
            e.textEdited.connect(lambda _t: self._bt_changed())
            self.bt_fields.append(e)
            row.addWidget(e)
        row.addStretch(1)
        v.addLayout(row)

        self.lbl_bt = QtWidgets.QLabel('')
        self.lbl_bt.setObjectName('legend')
        self.lbl_bt.setWordWrap(True)
        v.addWidget(self.lbl_bt)

        v.addSpacing(6)
        v.addWidget(heading('fault slips'))
        self.tbl = QtWidgets.QTableWidget(0, 5)
        self.tbl.setHorizontalHeaderLabels(['', 'dip az', 'dip', 'rake',
                                            'typed'])
        self.tbl.verticalHeader().hide()
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.tbl.horizontalHeader().setStretchLastSection(True)
        for i, wd in enumerate((30, 48, 34, 42)):
            self.tbl.setColumnWidth(i, wd)
        self.tbl.verticalHeader().setDefaultSectionSize(19)
        v.addWidget(self.tbl, 1)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(3)
        self.lbl_count = QtWidgets.QLabel('0 faults')
        self.lbl_count.setObjectName('count')
        row.addWidget(self.lbl_count)
        row.addStretch(1)
        b = QtWidgets.QPushButton('Delete')
        b.setShortcut(QtGui.QKeySequence.Delete)
        b.clicked.connect(self.delete_selected)
        row.addWidget(b)
        v.addLayout(row)

        v.addSpacing(6)
        v.addWidget(heading('runs found'))
        self.list_sites = QtWidgets.QListWidget()
        self.list_sites.setMaximumHeight(130)
        self.list_sites.itemDoubleClicked.connect(
            lambda it: self._load(it.data(QtCore.Qt.UserRole)))
        v.addWidget(self.list_sites)
        return w

    def _workspace(self):
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        split.setChildrenCollapsible(False)

        holder = QtWidgets.QFrame()
        holder.setObjectName('plotpanel')
        hv = QtWidgets.QVBoxLayout(holder)
        hv.setContentsMargins(4, 4, 4, 4)
        self.fig = Figure(figsize=(11, 5.6), facecolor='white')
        self.canvas = Canvas(self.fig)
        hv.addWidget(self.canvas)
        split.addWidget(holder)

        self.tabs = QtWidgets.QTabWidget()

        page = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout(page)
        v.setContentsMargins(8, 8, 8, 8)
        v.setSpacing(4)
        self.strip_ar = ResultStrip('archive   what the old run recorded')
        self.strip_ar.hide()
        self.strip_a = ResultStrip('%s   %s' % (MODES[0][1], MODES[0][3]))
        self.strip_b = ResultStrip('%s   %s' % (MODES[1][1], MODES[1][3]))
        v.addWidget(self.strip_ar)
        v.addWidget(self.strip_a)
        v.addWidget(self.strip_b)
        self.lbl_diff = QtWidgets.QLabel('')
        self.lbl_diff.setObjectName('secondary')
        self.lbl_diff.setContentsMargins(12, 2, 0, 0)
        self.lbl_diff.setWordWrap(True)
        v.addWidget(self.lbl_diff)
        v.addStretch(1)
        self.tabs.addTab(page, 'Results')

        self.txt_info = QtWidgets.QPlainTextEdit()
        self.txt_mohr = QtWidgets.QPlainTextEdit()
        for t in (self.txt_info, self.txt_mohr):
            t.setReadOnly(True)
            t.setObjectName('report')          # picks up the monospace rule
            t.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.tabs.addTab(self.txt_info, 'INFO1')
        self.tabs.addTab(self.txt_mohr, 'MOHR1')
        split.addWidget(self.tabs)
        split.setStretchFactor(0, 3)
        split.setSizes([560, 330])
        return split

    # --------------------------------------------------------- back-tilt --
    def _bt_changed(self, *_a):
        """Read the back-tilt fields and work out the rotation.

        The reference surface and the ANGLE are the user's calls. There is no
        analytical solution for the angle: it is found by trying values and
        looking at the result, which is why the archive folders are named
        after what was tried. This panel only makes trying quick, and shows
        exactly which rotation is in force.
        """
        mode = self.cmb_bt.currentIndex()
        labels = {0: ('', '', ''),
                  1: ('dip azimuth', 'dip', ''),
                  2: ('pole trend', 'pole plunge', ''),
                  3: ('axis trend', 'axis plunge', 'angle')}[mode]
        vals = []
        for e, lab in zip(self.bt_fields, labels):
            e.setEnabled(bool(lab))
            e.setToolTip(lab)
            txt = e.text().strip()
            try:
                vals.append(float(txt) if txt else None)
            except ValueError:
                vals.append(None)

        self.rot = None
        note = ''
        if mode == 1 and vals[0] is not None and vals[1] is not None:
            self.rot = rotate.restores_to_horizontal(vals[0], vals[1])
            note = 'restores that plane to horizontal'
        elif mode == 2 and vals[0] is not None and vals[1] is not None:
            dipaz = (vals[0] + 180.0) % 360.0
            dip = 90.0 - vals[1]
            self.rot = rotate.restores_to_horizontal(dipaz, dip)
            note = 'pole implies a plane %03.0f/%02.0f' % (dipaz, dip)
        elif mode == 3 and all(v is not None for v in vals):
            self.rot = (vals[0], vals[1], vals[2])
            note = 'right-hand rule about the axis'

        if self.rot is None:
            self.lbl_bt.setText('off' if mode == 0
                                else 'fill the fields to apply a rotation')
        else:
            t, p, a = self.rot
            self.lbl_bt.setText(
                'axis %03.0f / %02.0f, angle %+.0f%s   %s\n%s'
                % (t, p, a, DEG, note, rotate.describe(t, p, a)))
        self.results = {}
        for s in (self.strip_a, self.strip_b):
            s.clear()
        self.lbl_diff.setText('')
        self.txt_info.clear()
        self.txt_mohr.clear()
        self._draw()

    # -------------------------------------------------------------- data --
    @property
    def n_s(self):
        """Fault normals and slips, back-tilted if a rotation is in force."""
        n, s = entry.records_to_arrays(self.records)
        if getattr(self, 'rot', None) and len(n):
            n, s = rotate.rotate_site(n, s, *self.rot)
        return n, s

    @property
    def confidence(self):
        return [r.get('confidence', 'C') for r in self.records]

    @property
    def sides(self):
        """Which side the barb sits on, from the strike-slip component."""
        if not self.records:
            return np.zeros(0)
        return plot.strike_slip_sign(
            [r['dipaz'] for r in self.records],
            [r['dip'] for r in self.records],
            [r['rake'] + tensorfile.RAKE_OFFSET for r in self.records])

    def _rename(self, txt):
        self.site_name = txt or '01'
        self._draw()

    def add_record(self, rec):
        rec['confidence'] = (rec.get('sense') or 'C')[0:1].upper()
        rec['code'] = rec.get('sense', '')
        self.records.append(rec)
        self.results = {}
        self._refresh()
        self.status.showMessage('%d fault slips' % len(self.records))

    def delete_selected(self):
        rows = sorted({i.row() for i in self.tbl.selectedIndexes()},
                      reverse=True)
        for r in rows:
            if 0 <= r < len(self.records):
                del self.records[r]
        if rows:
            self.results = {}
            self._refresh()

    def clear_all(self):
        self.records, self.results, self.archive = [], {}, None
        self.site_name = '01'
        self.ed_site.setText('01')
        self.strip_ar.hide()
        self._refresh()
        self.entry.focus()

    def _refresh(self):
        self.tbl.setRowCount(len(self.records))
        for i, r in enumerate(self.records):
            vals = (r.get('confidence', 'C'), r['dipaz'], r['dip'],
                    '%.0f' % r['rake'], r.get('tail', ''))
            for j, val in enumerate(vals):
                it = QtWidgets.QTableWidgetItem(str(val))
                if j:
                    it.setTextAlignment(QtCore.Qt.AlignRight
                                        | QtCore.Qt.AlignVCenter)
                self.tbl.setItem(i, j, it)
        self.lbl_count.setText('%d fault%s'
                               % (len(self.records),
                                  '' if len(self.records) == 1 else 's'))
        if not self.results:
            for s in (self.strip_a, self.strip_b):
                s.clear()
            self.lbl_diff.setText('')
            self.txt_info.clear()
            self.txt_mohr.clear()
        self._draw()

    # -------------------------------------------------------- file input ---
    def open_site(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open a TENSOR site file', '', 'All files (*)')
        if fn:
            self._load(fn)

    def scan_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Folder containing TENSOR runs')
        if not d:
            return
        found = tensorfile.discover(d)
        self.list_sites.clear()
        for p in found:
            it = QtWidgets.QListWidgetItem(
                os.path.relpath(p, d).replace('\\', '/'))
            it.setData(QtCore.Qt.UserRole, p)
            self.list_sites.addItem(it)
        self.status.showMessage('%d runs found' % len(found))
        if found:
            self._load(found[0])

    def _load(self, path):
        try:
            site = tensorfile.read_site(path)
        except Exception as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTENSOR', str(exc))
            return
        self.records = [dict(r) for r in site.records]
        self.site_name = site.name
        self.site_code = getattr(site, 'code', '01')
        self.ed_site.setText(site.name)
        self.results = {}
        self.archive = tensorfile.parse_result_line(site.result_line)
        if self.archive:
            self.strip_ar.show()
            self.strip_ar.show_result(self.archive, len(site))
        else:
            self.strip_ar.hide()
        self.archive_lambda = None
        self.cb_lam.setEnabled(False)
        self.cb_lam.setChecked(False)
        info = os.path.join(os.path.dirname(path), 'INFO1')
        if os.path.exists(info):
            d = tensorfile.read_info_lambda(info)
            if d.get('pass_no'):
                self.sp_pass.setValue(d['pass_no'])
            if d.get('lambda_invdir'):
                self.archive_lambda = d['lambda_invdir']
                self.cb_lam.setEnabled(True)
                self.cb_lam.setChecked(True)
                self.cb_lam.setText('archive LAMBDA %.2f'
                                    % self.archive_lambda)
        self._refresh()
        self.status.showMessage(path)

    # --------------------------------------------------------- inversion ---
    def invert(self):
        if len(self.records) < 4:
            QtWidgets.QMessageBox.information(
                self, 'pyTENSOR',
                'Four fault slips are the minimum: the reduced stress tensor '
                'has four unknowns.')
            return
        n, s = self.n_s
        self.btn_run.setEnabled(False)
        self.progress.show()
        self.status.showMessage('inverting')
        lam = (self.archive_lambda
               if self.cb_lam.isEnabled() and self.cb_lam.isChecked()
               else None)
        self.worker = Worker(n, s, self.cb_a.isChecked(),
                             self.cb_b.isChecked(), self.sp_pass.value(),
                             lam_printed=lam)
        self.worker.done.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _failed(self, msg):
        self.btn_run.setEnabled(True)
        self.progress.hide()
        self.status.showMessage('failed')
        QtWidgets.QMessageBox.critical(self, 'pyTENSOR', msg)

    def _finished(self, out):
        self.btn_run.setEnabled(True)
        self.progress.hide()
        self.results = out
        n = len(self.records)
        for tag, strip in (('A', self.strip_a), ('B', self.strip_b)):
            if tag in out:
                strip.show_result(out[tag], n)
            else:
                strip.clear()
        self.lbl_diff.setText(self._difference())
        self._write_reports()
        self.status.showMessage('done')
        self._draw()

    def _difference(self):
        a, b = self.results.get('A'), self.results.get('B')
        if not (a and b):
            return ''
        bits = []
        for sym, key in zip(SYM, AXES):
            va = core.vec_from_trend_plunge(*a[key])
            vb = core.vec_from_trend_plunge(*b[key])
            bits.append('%s %.1f%s'
                        % (sym, np.degrees(np.arccos(
                            min(abs(float(va @ vb)), 1.0))), DEG))
        txt = ('%s -> %s      ' % (NAME['A'], NAME['B']) + '   '.join(bits)
               + '      d%s %+.3f   dS4 %+.4f'
               % (PHI, b['phi'] - a['phi'], b['S4'] - a['S4']))
        if min(a['phi'], b['phi']) < 0.2 or max(a['phi'], b['phi']) > 0.8:
            txt += ('      -  at this %s one axis is near-degenerate, so '
                    'expect the disagreement to sit there' % PHI)
        return txt

    # ------------------------------------------------------------ reports --
    def _report_source(self):
        for tag in ('A', 'B'):
            if tag in self.results:
                return tag, self.results[tag]
        return None, None

    def _info_kwargs(self):
        """Everything info1_text needs, so the panel and the exported file
        stay in step."""
        tag, r = self._report_source()
        if r is None:
            return None, None
        trace = r.get('lambda_trace') or []
        return r, dict(site_file=self.plot_name, res=r,
                       n_data=len(self.records),
                       invdir=r.get('invdir_summary'),
                       lam_invdir=trace[-1]['lam_printed'] if trace else None,
                       pass_no=self.sp_pass.value(),
                       # the two-character code the file carries, not the file
                       # name: it goes into fixed-width fields
                       site=getattr(self, 'site_code', '01'),
                       method=CODE[tag])

    def _write_reports(self):
        r, kw = self._info_kwargs()
        if r is None:
            self.txt_info.clear()
            self.txt_mohr.clear()
            return
        # the panel shows the substance only; the banner and the file-handling
        # lines belong in the exported file, not on screen
        self.txt_info.setPlainText(report.info1_text(compact=True, **kw))
        self.txt_mohr.setPlainText(
            report.mohr1_text(r, len(self.records), method=kw['method'],
                              site=kw['site']))

    # ------------------------------------------------------------ drawing --
    def _draw(self, annotate=False):
        """annotate=False on screen: the result strips already carry the
        numbers at full size, so printing them on the figure as well would
        duplicate them and crowd the footer. Exported figures stand alone, so
        they do get the numbers."""
        self.fig.clear()
        n, s = self.n_s
        keys = [k for k in ('A', 'B') if k in self.results]
        conf, sides = self.confidence, self.sides
        want_fit = bool(keys) and self.cb_fit.isChecked()
        panels = max(len(keys) + (1 if want_fit else 0), 1)

        for ax in self.fig.get_axes():
            ax.set_facecolor(plot.PAPER)

        if not keys:
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(plot.PAPER)
            plot.plot_site(ax, n, s, None, certainty=conf, sides=sides,
                           site_code=self.plot_name,
                           header=retro.translate('observed')
                           if getattr(self, 'retro', False) else 'observed')
        else:
            for i, k in enumerate(keys):
                ax = self.fig.add_subplot(1, panels, i + 1)
                ax.set_facecolor(plot.PAPER)
                r = self.results[k]
                plot.plot_site(ax, n, s, r, certainty=conf, sides=sides,
                               site_code=self.plot_name, header=NAME[k])
                if annotate:
                    plot.annotate_result(ax, r, n_data=len(self.records))
            if want_fit:
                ax = self.fig.add_subplot(1, panels, panels)
                ax.set_facecolor(plot.PAPER)
                plot.plot_fitted(ax, n, self.results[keys[0]]['T'],
                                 site_code=self.plot_name,
                                 header='fitted shear')
        self.fig.subplots_adjust(left=0.01, right=0.99, top=0.99,
                                 bottom=0.14 if annotate else 0.06,
                                 wspace=0.02)
        self.canvas.draw()

    # ------------------------------------------------------------- export --
    def save_png(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save figure', '%s.png' % self.site_name, 'PNG (*.png)')
        if not fn:
            return
        self._draw(annotate=True)
        self.fig.savefig(fn, dpi=300, facecolor='white', bbox_inches='tight')
        self._draw()
        self.status.showMessage('saved ' + fn)

    def _save_report(self, which):
        r, kw = self._info_kwargs()
        if r is None:
            QtWidgets.QMessageBox.information(
                self, 'pyTENSOR', 'Run the inversion first.')
            return
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save ' + which, which, 'All files (*)')
        if not fn:
            return
        # the file gets the full layout, banner and all, so it drops straight
        # in beside the old runs
        if which == 'INFO1':
            text = report.info1_text(full_header=True, **kw)
        else:
            text = report.mohr1_text(r, len(self.records),
                                     method=kw['method'], site=kw['site'])
        with open(fn, 'w', newline='\n', encoding='ascii',
                  errors='replace') as fh:
            fh.write(text)
        self.status.showMessage('saved ' + fn)

    # -------------------------------------------------------- 1991 mode --
    def toggle_1991(self, on=None):
        """Turbo Pascal blue and Angelier's own French.

        Reached by clicking the J.A. signature on the opening screen. Purely
        cosmetic: nothing about the inversion changes.
        """
        self.retro = (not getattr(self, 'retro', False)) if on is None else on
        app = QtWidgets.QApplication.instance()
        app.setStyleSheet(retro.QSS if self.retro else QSS)
        self.setWindowTitle(retro.TITLE if self.retro else 'pyTENSOR')

        # phosphor green on black for the stereogram
        if self.retro:
            plot.set_palette(retro.PLOT_PEN, retro.PLOT_PAPER)
            self.fig.set_facecolor(retro.PLOT_PAPER)
        else:
            plot.set_palette()
            self.fig.set_facecolor('white')

        for w in self.findChildren(QtWidgets.QLabel):
            if w.objectName() == 'heading':
                base = w.property('en') or w.text()
                w.setProperty('en', base)
                w.setText(retro.translate(base) if self.retro else base)
        for act in self.findChildren(QtWidgets.QAction):
            base = act.property('en') or act.text()
            act.setProperty('en', base)
            act.setText(retro.translate(base) if self.retro else base)
        for cb in (self.cb_fit,):
            base = cb.property('en') or cb.text()
            cb.setProperty('en', base)
            cb.setText(retro.translate(base) if self.retro else base)
        self.btn_run.setText(retro.translate('INVERT') if self.retro
                             else 'INVERT')
        self.tabs.setTabText(0, retro.translate('Results') if self.retro
                             else 'Results')
        self.status.showMessage(
            'MODE 1991  —  ' + retro.TITLE if self.retro
            else 'type a record, for example  CS 122 87W 124')
        self._draw()

    def save_hpgl(self):
        from pytensor import hpgl
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save HPGL', '%s.hpgl' % self.site_name, 'HPGL (*.hpgl)')
        if not fn:
            return
        n, _s = self.n_s
        w = hpgl.Writer()
        t = np.linspace(0, 2 * np.pi, 721)
        w.polyline(np.cos(t), np.sin(t))
        for i in range(len(n)):
            for seg in plot.great_circle(n[i]):
                w.polyline(seg[:, 0], seg[:, 1])
        r = self.results.get('A') or self.results.get('B')
        if r:
            sizes = plot.star_sizes(r['phi'], r['eigenvalues'])
            for i, key in enumerate(AXES):
                v = core.vec_from_trend_plunge(*r[key])
                X, Y = plot.schmidt(v[None, :])
                px, py = plot.star_polygon(float(X[0]), float(Y[0]),
                                           plot.STAR_POINTS[i],
                                           float(sizes[i]),
                                           inner=plot.STAR_INNER[i],
                                           phase_deg=plot.STAR_PHASE[i])
                w.polyline(np.append(px, px[0]), np.append(py, py[0]))
        w.label(-1.25, -1.36, self.plot_name)
        w.label(0.80, -1.36, 'pyTENSOR')
        w.save(fn)
        self.status.showMessage('saved ' + fn)


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setStyleSheet(QSS)
    w = Main()

    sp = splash.Splash()
    retro_wanted = {'on': False}
    sp.signature_clicked.connect(lambda: retro_wanted.__setitem__('on', True))
    if splash.image_path():
        sp.exec_()

    w.show()
    if retro_wanted['on']:
        w.toggle_1991(True)
    w.entry.focus()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
