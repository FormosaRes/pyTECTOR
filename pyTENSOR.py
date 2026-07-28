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

from pytensor import (about, core, entry, invdir, modern, plot, report, retro,
                      rotate, splash, tensorfile, tilt, tiltui)
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
                 raw=None, parent=None):
        super(Worker, self).__init__(parent)
        self.n, self.s = n, s
        #: the data BEFORE back-tilting, when a rotation is in force. Both are
        #: inverted so the two can be compared and the axes checked against
        #: horizontal and vertical.
        self.raw = raw
        self.do_a, self.do_b, self.n_pass = do_a, do_b, n_pass
        self.lam_printed = lam_printed

    def run(self):
        try:
            out = {}
            if self.raw is not None:
                rn, rs = self.raw
                T0 = invdir.run(rn, rs, n_pass=self.n_pass)['T']
                res0 = core.summary(T0, rn, rs)
                res0['T'] = T0
                out['RAW'] = res0
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


# ------------------------------------------------------------------ panel --
class Panel(QtWidgets.QFrame):
    """A framed panel that paints a DOS double-line border in 1991 mode.

    Two nested rectangles a few pixels apart, which is what a terminal drew
    when it printed the box characters. Qt stylesheets cannot express a double
    border, so the retro stylesheet drops the border entirely and this paints
    it instead.
    """
    GAP = 3

    def __init__(self, name='panel', parent=None):
        super(Panel, self).__init__(parent)
        self.setObjectName(name)
        self.retro = False

    def set_retro(self, on):
        self.retro = bool(on)
        self.update()

    def paintEvent(self, ev):
        super(Panel, self).paintEvent(ev)
        if not self.retro:
            return
        p = QtGui.QPainter(self)
        pen = QtGui.QPen(QtGui.QColor(retro.WHITE))
        pen.setWidth(1)
        p.setPen(pen)
        r = self.rect().adjusted(0, 0, -1, -1)
        p.drawRect(r)
        p.drawRect(r.adjusted(self.GAP, self.GAP, -self.GAP, -self.GAP))
        p.end()


# ----------------------------------------------------------- result widget --
class ResultStrip(Panel):
    """One row of results. Principal axes and the shape ratio go at full size;
    only n and S4 are allowed to be small and grey."""

    #: (axis labels, ratio label). The French is Angelier's own wording from
    #: INFO1: 'AXIS SIGMA 1' and 'RATIO PHI' become 'AXE SIGMA 1' and
    #: 'RAPPORT PHI'.
    WORDS = {False: (('σ₁', 'σ₂', 'σ₃'), 'Φ'),
             True: (('AXE SIGMA 1', 'AXE SIGMA 2', 'AXE SIGMA 3'),
                    'RAPPORT PHI')}

    def __init__(self, title, parent=None):
        super(ResultStrip, self).__init__('panel', parent)
        self.words = ResultStrip.WORDS[False]
        self._last = None
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

    def set_language(self, retro_on):
        """Switch between the symbols and Angelier's own French wording."""
        self.words = ResultStrip.WORDS[bool(retro_on)]
        if self._last is None:
            self.clear()
        else:
            self.show_result(*self._last)

    def clear(self):
        syms, phi = self.words
        for lab, sym in zip(self.axis_labels, syms):
            lab.setText('%s  -' % sym)
        self.phi.setText('%s -' % phi)
        self.ang.setText('ANG -')
        self.rup.setText('RUP -')
        self.small.setText('')
        self._last = None

    def show_result(self, r, n_data=None):
        self._last = (r, n_data)
        syms, phi_lab = self.words
        for lab, sym, key in zip(self.axis_labels, syms, AXES):
            tr, pl = r[key]
            lab.setText('%s %03d/%02d' % (sym, int(round(tr)) % 360,
                                          int(round(pl))))
        self.phi.setText('%s %.3f' % (phi_lab, r['phi']))
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
        self.planes = []
        self._loading = False
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
        lab = QtWidgets.QLabel('  decl ')
        lab.setStyleSheet('color:%s;' % MUTED)
        lab.setToolTip('magnetic declination')
        tb.addWidget(lab)
        self.ed_decl = QtWidgets.QLineEdit()
        self.ed_decl.setObjectName('seg')
        self.ed_decl.setFixedWidth(52)
        self.ed_decl.setAlignment(QtCore.Qt.AlignCenter)
        self.ed_decl.setMaxLength(6)
        self.ed_decl.setText('%.2f' % plot.MAGNETIC_OFFSET)
        self.ed_decl.setToolTip(
            'Where the M mark is drawn, in degrees east of geographic north. '
            'The archive draws it at a fixed 1.95. This moves the mark only; '
            'it does NOT rotate the data, so results never change behind your '
            'back.')
        self.ed_decl.textEdited.connect(lambda _t: self._draw())
        tb.addWidget(self.ed_decl)

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
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                             QtWidgets.QSizePolicy.Preferred)
        tb.addWidget(spacer)
        # only appears once 1991 mode is on, so it is a way back rather than a
        # spoiler sitting in the toolbar from the start
        self.act_1991 = tb.addAction('MODE 1991  ×')
        self.act_1991.setToolTip('back to the normal interface')
        self.act_1991.setVisible(False)
        self.act_1991.triggered.connect(lambda: self.toggle_1991(False))
        tb.addAction('About').triggered.connect(self.show_about)

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
        v.addWidget(heading('reference planes'))
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(3)
        self.cmb_ptype = QtWidgets.QComboBox()
        self.cmb_ptype.addItems(['plane', 'pole'])
        self.cmb_ptype.setFixedWidth(64)
        self.cmb_ptype.currentIndexChanged.connect(self._ptype_changed)
        row.addWidget(self.cmb_ptype)
        self.pl_fields = []
        for _ in range(2):
            e = QtWidgets.QLineEdit()
            e.setObjectName('seg')
            e.setFixedWidth(54)
            e.setMaxLength(4)
            e.setAlignment(QtCore.Qt.AlignCenter)
            e.returnPressed.connect(self.add_plane)
            self.pl_fields.append(e)
            row.addWidget(e)
        b = QtWidgets.QPushButton('Add')
        b.clicked.connect(self.add_plane)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)

        self.list_planes = QtWidgets.QListWidget()
        self.list_planes.setMaximumHeight(84)
        self.list_planes.setToolTip(
            'Double-click a surface to make it the back-tilt reference. '
            'It is then drawn with a longer dash.')
        self.list_planes.itemDoubleClicked.connect(self._star_plane)
        v.addWidget(self.list_planes)
        self._ptype_changed()

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(3)
        b = QtWidgets.QPushButton('Set as reference')
        b.clicked.connect(lambda: self._star_plane(
            self.list_planes.currentItem()))
        row.addWidget(b)
        b = QtWidgets.QPushButton('Remove')
        b.clicked.connect(self.remove_plane)
        row.addWidget(b)
        row.addStretch(1)
        v.addLayout(row)

        v.addSpacing(6)
        v.addWidget(heading('back-tilt'))
        self.cmb_bt = QtWidgets.QComboBox()
        self.cmb_bt.addItems(['off',
                              'restore the reference surface',
                              'rotation axis   trend / plunge / angle'])
        self.cmb_bt.currentIndexChanged.connect(self._bt_changed)
        v.addWidget(self.cmb_bt)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(3)
        self.bt_fields = []
        for hint in ('020', '00', '-20'):
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

        self.btn_tilt = QtWidgets.QPushButton('Tilt test')
        self.btn_tilt.setEnabled(False)
        self.btn_tilt.setToolTip(
            'Invert at every partial restoration from 0 to 125 per cent and '
            'plot both diagnostics, so syn-tilt faulting shows up as a best '
            'answer short of full restoration.')
        self.btn_tilt.clicked.connect(self.tilt_test)
        v.addWidget(self.btn_tilt)

        v.addSpacing(6)
        v.addWidget(heading('fault slips'))
        self.tbl = QtWidgets.QTableWidget(0, 7)
        self.tbl.setHorizontalHeaderLabels(
            ['#', 'use', 'type', 'as typed', 'strike', 'dip', 'rake'])
        self.tbl.verticalHeader().hide()
        self.tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.tbl.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        # 'as typed' absorbs the slack. Stretching the LAST column instead
        # pushes rake off the right edge as soon as the sidebar is narrow.
        hh = self.tbl.horizontalHeader()
        hh.setStretchLastSection(False)
        for i, wd in enumerate((22, 28, 32, 60, 40, 38, 36)):
            self.tbl.setColumnWidth(i, wd)
            hh.setSectionResizeMode(i, QtWidgets.QHeaderView.Fixed)
        hh.setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        hh.setMinimumSectionSize(20)
        self.tbl.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.tbl.verticalHeader().setDefaultSectionSize(19)
        self.tbl.itemChanged.connect(self._use_changed)
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

        return w

    def _workspace(self):
        split = QtWidgets.QSplitter(QtCore.Qt.Vertical)
        split.setChildrenCollapsible(False)

        holder = Panel('plotpanel')
        self.plot_holder = holder
        hv = QtWidgets.QVBoxLayout(holder)
        hv.setContentsMargins(4, 4, 4, 4)
        hv.setSpacing(4)

        # What is on screen must never be in doubt. One bar, always present:
        # what the data are on the left, which state is drawn on the right.
        bar = QtWidgets.QHBoxLayout()
        bar.setSpacing(8)
        bar.setContentsMargins(6, 3, 6, 1)
        self.lbl_context = QtWidgets.QLabel('')
        self.lbl_context.setObjectName('context')
        bar.addWidget(self.lbl_context)
        bar.addStretch(1)
        self.lbl_stale = QtWidgets.QLabel('')
        self.lbl_stale.setObjectName('stale')
        self.lbl_stale.hide()
        bar.addWidget(self.lbl_stale)
        self.cmb_view = QtWidgets.QComboBox()
        self.cmb_view.addItems(['AS MEASURED', 'BACK-TILTED', 'BOTH'])
        self.cmb_view.setToolTip(
            'Which data the stereogram shows. Back-tilted data and measured '
            'data are never drawn without saying which is which.')
        self.cmb_view.currentIndexChanged.connect(lambda _i: self._draw())
        bar.addWidget(self.cmb_view)
        self.lbl_state = QtWidgets.QLabel('')
        self.lbl_state.setObjectName('state')
        bar.addWidget(self.lbl_state)
        hv.addLayout(bar)

        self.fig = Figure(figsize=(11, 5.4), facecolor='white')
        self.canvas = Canvas(self.fig)
        hv.addWidget(self.canvas, 1)
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

    # -------------------------------------------------- reference planes --
    def _ptype_changed(self, *_a):
        """Planes are entered as strike and dip with a quadrant, the same
        convention as the fault records. Poles as trend and plunge."""
        plane = self.cmb_ptype.currentText() == 'plane'
        hints = ('122', '87W') if plane else ('045', '12')
        tips = (('strike, 000 to 360', 'dip and its quadrant, e.g. 87W')
                if plane else ('pole trend', 'pole plunge'))
        for e, h, t in zip(self.pl_fields, hints, tips):
            e.setPlaceholderText(h)
            e.setToolTip(t)

    def add_plane(self):
        """A surface, given as strike and dip or by its pole. Any number may
        be entered; one of them can drive the back-tilt."""
        txt = [e.text().strip() for e in self.pl_fields]
        if not all(txt):
            return
        kind = self.cmb_ptype.currentText()
        try:
            if kind == 'plane':
                if not txt[0].isdigit():
                    raise entry.RecordError('strike: "%s"' % txt[0])
                strike = int(txt[0]) % 360
                dip, quad = entry._split_num_quad(txt[1], 'dip')
                if not 0 <= dip <= 90:
                    raise entry.RecordError('dip must be 0-90')
                dipaz = entry.dip_azimuth(strike, quad)
                a, b = float(strike), txt[1].upper()
            else:                               # a pole names its own plane
                trend, plunge = float(txt[0]) % 360.0, float(txt[1])
                if not 0 <= plunge <= 90:
                    raise entry.RecordError('plunge must be 0-90')
                dipaz, dip = (trend + 180.0) % 360.0, 90.0 - plunge
                a, b = trend, plunge
        except (entry.RecordError, ValueError) as exc:
            QtWidgets.QMessageBox.warning(self, 'pyTENSOR', str(exc))
            return

        self.planes.append(dict(kind=kind, a=a, b=b, dipaz=dipaz, dip=dip,
                                ref=not any(p['ref'] for p in self.planes)))
        for e in self.pl_fields:
            e.clear()
        self.pl_fields[0].setFocus()
        self._refresh_planes()

    def remove_plane(self):
        i = self.list_planes.currentRow()
        if 0 <= i < len(self.planes):
            was_ref = self.planes[i]['ref']
            del self.planes[i]
            if was_ref and self.planes:
                self.planes[0]['ref'] = True
            self._refresh_planes()

    def _star_plane(self, item):
        if item is None:
            return
        i = self.list_planes.row(item)
        for k, p in enumerate(self.planes):
            p['ref'] = (k == i)
        self._refresh_planes()

    def _refresh_planes(self):
        self.list_planes.clear()
        for p in self.planes:
            mark = '*' if p['ref'] else ' '
            if p['kind'] == 'plane':
                shown = '%03.0f %s' % (p['a'], p['b'])
            else:
                shown = '%03.0f / %02.0f' % (p['a'], p['b'])
            self.list_planes.addItem(
                '%s %-5s %-9s   dip az %03.0f / %02.0f'
                % (mark, p['kind'], shown, p['dipaz'], p['dip']))
        self._bt_changed()

    def ref_plane(self):
        """The surface marked as the back-tilt reference, if any."""
        for p in self.planes:
            if p['ref']:
                return (p['dipaz'], p['dip'])
        return None

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
        use_axis = (mode == 2)
        vals = []
        for e, lab in zip(self.bt_fields,
                          ('axis trend', 'axis plunge', 'angle')):
            e.setEnabled(use_axis)
            e.setToolTip(lab)
            txt = e.text().strip()
            try:
                vals.append(float(txt) if txt else None)
            except ValueError:
                vals.append(None)

        self.rot = None
        note = ''
        ref = self.ref_plane()
        if mode == 1:
            if ref is None:
                note = 'add a surface above and mark it as the reference'
            else:
                self.rot = rotate.restores_to_horizontal(*ref)
                note = 'restores the starred surface to horizontal'
        elif use_axis and all(v is not None for v in vals):
            self.rot = (vals[0], vals[1], vals[2])
            note = 'right-hand rule about the axis'

        if self.rot is None:
            self.lbl_bt.setText('off' if mode == 0
                                else note or 'fill the fields to rotate')
        else:
            t, p, a = self.rot
            self.lbl_bt.setText(
                'axis %03.0f / %02.0f, angle %+.0f%s   %s\n%s'
                % (t, p, a, DEG, note, rotate.describe(t, p, a)))
        if hasattr(self, 'btn_tilt'):
            self.btn_tilt.setEnabled(bool(self.rot)
                                     and len(self.records) >= 4)
        self.results = {}
        for s in (self.strip_a, self.strip_b):
            s.clear()
        self.lbl_diff.setText('')
        self.txt_info.clear()
        self.txt_mohr.clear()
        self._draw()

    def tilt_test(self):
        if not self.rot or len(self.records) < 4:
            return
        n, s = self.n_s_raw
        dlg = tiltui.TiltDialog(n, s, self.rot, self.sp_pass.value(), self)
        dlg.adopt.connect(self._adopt_rotation)
        dlg.exec_()

    def _adopt_rotation(self, trend, plunge, angle):
        """Switch the panel to the explicit axis so the chosen partial
        restoration is what is applied, and is visible."""
        self.cmb_bt.setCurrentIndex(3)
        for e, val in zip(self.bt_fields, (trend, plunge, angle)):
            e.setText('%.4g' % val)
        self._bt_changed()
        self.status.showMessage('back-tilt set to %+.1f deg about %03.0f/%02.0f'
                                % (angle, trend, plunge))

    # -------------------------------------------------------------- data --
    @property
    def active(self):
        """The faults with their switch on. Everything downstream, the
        inversion and the plots, uses only these; an excluded datum stays in
        the table greyed out so the decision is visible and reversible."""
        return [r for r in self.records if r.get('use', True)]

    @property
    def n_s(self):
        """Fault normals and slips, back-tilted if a rotation is in force."""
        n, s = entry.records_to_arrays(self.active)
        if getattr(self, 'rot', None) and len(n):
            n, s = rotate.rotate_site(n, s, *self.rot)
        return n, s

    @property
    def n_s_raw(self):
        """The same data as measured, whatever rotation is in force."""
        return entry.records_to_arrays(self.active)

    def reference_now(self, rotated):
        """Every entered surface, optionally carried through the rotation so a
        correct restoration is visible as the dashed circle flattening."""
        if not self.planes:
            return None
        out = []
        for p in self.planes:
            az, dp = p['dipaz'], p['dip']
            if rotated and self.rot:
                nv = core.normal_from_dipaz(az, dp)
                nv = rotate.rotate_vectors(np.atleast_2d(nv), *self.rot)[0]
                az, dp = plot.reference_from_vectors(nv)
            out.append((az, dp, p['ref']))
        return out

    @property
    def confidence(self):
        return [r.get('confidence', 'C') for r in self.active]

    @property
    def sides(self):
        """Which side the barb sits on, from the strike-slip component."""
        act = self.active
        if not act:
            return np.zeros(0)
        return plot.strike_slip_sign(
            [r['dipaz'] for r in act], [r['dip'] for r in act],
            [r['rake'] + tensorfile.RAKE_OFFSET for r in act])

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

    @staticmethod
    def quadrant(dipaz):
        """The single letter the field notation uses for the dip direction."""
        a = float(dipaz) % 360.0
        if a < 45 or a >= 315:
            return 'N'
        if a < 135:
            return 'E'
        if a < 225:
            return 'S'
        return 'W'

    def _use_changed(self, item):
        if self._loading or item.column() != 1:
            return
        i = item.row()
        if 0 <= i < len(self.records):
            on = item.checkState() == QtCore.Qt.Checked
            if self.records[i].get('use', True) != on:
                self.records[i]['use'] = on
                self.results = {}
                self._refresh()

    def _refresh(self):
        self._loading = True
        self.tbl.setRowCount(len(self.records))
        for i, r in enumerate(self.records):
            # the entry convention here is strike and dip, not dip azimuth
            strike = (r['dipaz'] - 90.0) % 360.0
            vals = ['%d' % (i + 1), None, r.get('sense') or r.get('code', ''),
                    r.get('tail', ''), '%03.0f' % strike,
                    '%02d%s' % (r['dip'], self.quadrant(r['dipaz'])),
                    '%.0f' % r['rake']]
            for j, val in enumerate(vals):
                if j == 1:
                    it = QtWidgets.QTableWidgetItem()
                    it.setFlags(QtCore.Qt.ItemIsUserCheckable
                                | QtCore.Qt.ItemIsEnabled
                                | QtCore.Qt.ItemIsSelectable)
                    it.setCheckState(QtCore.Qt.Checked
                                     if r.get('use', True)
                                     else QtCore.Qt.Unchecked)
                else:
                    it = QtWidgets.QTableWidgetItem(str(val))
                    if j in (0, 4, 5, 6):
                        it.setTextAlignment(QtCore.Qt.AlignRight
                                            | QtCore.Qt.AlignVCenter)
                    if not r.get('use', True):
                        it.setForeground(QtGui.QBrush(QtGui.QColor('#A9A59C')))
                self.tbl.setItem(i, j, it)
        self._loading = False
        used = len(self.active)
        total = len(self.records)
        self.lbl_count.setText('%d fault%s' % (used, '' if used == 1 else 's')
                               + ('' if used == total
                                  else '   %d excluded' % (total - used)))
        if hasattr(self, 'btn_tilt'):
            self.btn_tilt.setEnabled(bool(self.rot) and used >= 4)
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
        """Find every run under a folder and offer them in a picker, rather
        than parking a list in the sidebar that is empty most of the time."""
        d = QtWidgets.QFileDialog.getExistingDirectory(
            self, 'Folder containing TENSOR runs')
        if not d:
            return
        found = tensorfile.discover(d)
        if not found:
            QtWidgets.QMessageBox.information(
                self, 'pyTENSOR', 'No TENSOR runs found under that folder.')
            return
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle('%d runs found' % len(found))
        dlg.resize(560, 460)
        lay = QtWidgets.QVBoxLayout(dlg)
        lst = QtWidgets.QListWidget()
        for p in found:
            it = QtWidgets.QListWidgetItem(
                os.path.relpath(p, d).replace('\\', '/'))
            it.setData(QtCore.Qt.UserRole, p)
            lst.addItem(it)
        lst.setCurrentRow(0)
        lst.itemDoubleClicked.connect(lambda _i: dlg.accept())
        lay.addWidget(lst)
        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        ok = QtWidgets.QPushButton('Open')
        ok.clicked.connect(dlg.accept)
        row.addWidget(ok)
        no = QtWidgets.QPushButton('Cancel')
        no.clicked.connect(dlg.reject)
        row.addWidget(no)
        lay.addLayout(row)
        if dlg.exec_() and lst.currentItem():
            self._load(lst.currentItem().data(QtCore.Qt.UserRole))

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
        if len(self.active) < 4:
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
                             lam_printed=lam,
                             raw=self.n_s_raw if self.rot else None)
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
        self._result_print = self._fingerprint()
        self.lbl_diff.setText(self._difference() + self._tilt_note())
        self._write_reports()
        self.status.showMessage('done')
        self._draw()

    def _tilt_note(self):
        """Did the axes actually come back towards horizontal and vertical?

        Restoring the reference surface to horizontal is only correct if the
        faults predate the tilting. If they formed during it, part of the tilt
        post-dates them and full restoration over-rotates. So report the
        Andersonian misfit before and after rather than assuming.
        """
        raw = self.results.get('RAW')
        new = self.results.get('A') or self.results.get('B')
        if not (raw and new and self.rot):
            return ''
        m0, r0, _ = tilt.andersonian(raw)
        m1, r1, _ = tilt.andersonian(new)
        txt = ('\nBACK-TILT   as measured  σ₁ %03d/%02d  Φ %.3f  ANG %.1f°  '
               'Andersonian %.1f° (%s)'
               % (raw['sigma1'][0], raw['sigma1'][1], raw['phi'],
                  raw['ANG_mean'], m0, r0))
        txt += ('\n            restored     σ₁ %03d/%02d  Φ %.3f  ANG %.1f°  '
                'Andersonian %.1f° (%s)'
                % (new['sigma1'][0], new['sigma1'][1], new['phi'],
                   new['ANG_mean'], m1, r1))
        if m1 > m0 + 2:
            txt += ('\n            the axes moved AWAY from horizontal and '
                    'vertical, so this rotation is not supported. Run the '
                    'tilt test.')
        return txt

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
                       n_data=len(self.active),
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
            report.mohr1_text(r, len(self.active), method=kw['method'],
                              site=kw['site']))

    # ------------------------------------------------------------ context --
    def _fingerprint(self):
        """Everything a result depends on. If this changes after an inversion,
        what is on screen no longer describes the current data."""
        return (tuple((r['dipaz'], r['dip'], round(r['rake'], 3),
                       bool(r.get('use', True))) for r in self.records),
                self.rot, self.sp_pass.value(),
                self.cb_a.isChecked(), self.cb_b.isChecked(),
                self.cb_lam.isChecked() if self.cb_lam.isEnabled() else None)

    def _update_context(self):
        """The one line that says what the data are, always visible."""
        used, total = len(self.active), len(self.records)
        bits = ['SITE %s' % (self.site_name or '01')]
        bits.append('%d fault%s' % (used, '' if used == 1 else 's'))
        if used != total:
            bits.append('%d excluded' % (total - used))
        if self.planes:
            bits.append('%d reference surface%s'
                        % (len(self.planes),
                           '' if len(self.planes) == 1 else 's'))
        self.lbl_context.setText('     '.join(bits))

        stale = (bool(self.results)
                 and self._fingerprint() != getattr(self, '_result_print',
                                                    None))
        self.lbl_stale.setVisible(stale)
        if stale:
            self.lbl_stale.setText('data changed since this result   '
                                   'press INVERT')
        return stale

    # ------------------------------------------------------------ drawing --
    def _draw(self, annotate=False):
        """annotate=False on screen: the result strips already carry the
        numbers at full size, so printing them on the figure as well would
        duplicate them and crowd the footer. Exported figures stand alone, so
        they do get the numbers."""
        self.fig.clear()
        stale = self._update_context()
        n, s = self.n_s
        conf, sides = self.confidence, self.sides
        keys = [k for k in ('A', 'B') if k in self.results]
        want_fit = bool(keys) and self.cb_fit.isChecked()

        if not len(n):
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(plot.PAPER)
            ax.axis('off')
            ax.text(0.5, 0.55, 'no fault slips yet',
                    ha='center', va='center', fontsize=13,
                    color='#7A776F' if plot.PEN == 'k' else plot.PEN)
            ax.text(0.5, 0.44,
                    'type one on the left, for example   CS - 122 - 87W - 124',
                    ha='center', va='center', fontsize=10,
                    color='#A9A59C' if plot.PEN == 'k' else plot.PEN)
            self.canvas.draw()
            return

        # Which state is on screen. With no rotation there is only one, and
        # the selector is forced to it so the label can never lie.
        if not self.rot:
            self.cmb_view.setEnabled(False)
            self.cmb_view.setCurrentIndex(0)
            view = 0
            self.lbl_state.setText('')
        else:
            self.cmb_view.setEnabled(True)
            view = self.cmb_view.currentIndex()
            t, p, a = self.rot
            self.lbl_state.setText('rotation in force:  axis %03.0f / %02.0f'
                                   '   angle %+.1f%s' % (t, p, a, DEG))
        raw_avail = 'RAW' in self.results

        show_raw = bool(self.rot) and view in (0, 2) and raw_avail
        show_rot = (not self.rot) or view in (1, 2)
        if self.rot and view == 0 and not raw_avail:
            show_raw, show_rot = False, True   # nothing measured yet, be clear

        panels = max((1 if show_raw else 0)
                     + (len(keys) if show_rot else 0)
                     + (1 if (want_fit and show_rot) else 0), 1)
        col = [0]
        title_colour = '#1E1E1C' if plot.PEN == 'k' else plot.PEN

        def cell(title=None, sub=None):
            """A panel. On screen it gets a plain title above the frame so
            there is no hunting in the footer for what you are looking at;
            exported figures keep Angelier's layout and omit it."""
            col[0] += 1
            ax = self.fig.add_subplot(1, panels, col[0])
            ax.set_facecolor(plot.PAPER)
            if title and not annotate:
                ax.set_title(title + ('\n' + sub if sub else ''),
                             fontsize=11, fontweight='600',
                             color=title_colour, pad=8, linespacing=1.5)
            return ax

        rot_tag = ''
        if self.rot:
            t, p, a = self.rot
            rot_tag = '  %03.0f/%02.0f %+.0f' % (t, p, a)
        try:
            decl = float(self.ed_decl.text().strip())
        except ValueError:
            decl = plot.MAGNETIC_OFFSET

        if not keys:
            show_rotated = bool(self.rot) and view != 0
            ax = cell('BACK-TILTED' if show_rotated
                      else ('AS MEASURED' if self.rot else 'OBSERVED DATA'),
                      sub=(rot_tag.strip() if show_rotated
                           else ('rotation not applied here' if self.rot
                                 else 'not yet inverted')))
            plot.plot_site(
                ax, n if show_rotated else self.n_s_raw[0],
                s if show_rotated else self.n_s_raw[1],
                None, certainty=conf, sides=sides,
                site_code=self.plot_name if show_rotated else self.site_name,
                reference=self.reference_now(show_rotated),
                declination=decl,
                header=('BACK-TILTED' + rot_tag) if show_rotated
                else ('AS MEASURED  no rotation' if self.rot
                      else (retro.translate('observed')
                            if getattr(self, 'retro', False) else 'observed')))
        else:
            if show_raw:
                rn, rs = self.n_s_raw
                ax = cell('AS MEASURED', 'no rotation applied')
                plot.plot_site(ax, rn, rs, self.results['RAW'],
                               certainty=conf, sides=sides,
                               site_code=self.site_name,
                               reference=self.reference_now(False),
                               header='AS MEASURED  no rotation', declination=decl)
                if annotate:
                    plot.annotate_result(ax, self.results['RAW'],
                                         n_data=len(self.active))
            if show_rot:
                for k in keys:
                    ax = cell(('BACK-TILTED  ' + NAME[k]) if self.rot
                              else NAME[k],
                              (rot_tag.strip() if self.rot
                               else MODES[0 if k == 'A' else 1][3]))
                    r = self.results[k]
                    plot.plot_site(ax, n, s, r, certainty=conf, sides=sides,
                                   site_code=self.plot_name,
                                   reference=self.reference_now(True),
                                   declination=decl,
                                   header=(('BACK-TILTED' + rot_tag + '   '
                                            + NAME[k]) if self.rot
                                           else NAME[k]))
                    if annotate:
                        plot.annotate_result(ax, r, n_data=len(self.active))
                if want_fit:
                    ax = cell('FITTED SHEAR',
                              'what the solution predicts on these planes')
                    plot.plot_fitted(ax, n, self.results[keys[0]]['T'],
                                     site_code=self.plot_name,
                                     header='fitted shear', declination=decl)
        if stale:
            # unmistakable, because acting on an out-of-date stereogram is the
            # kind of mistake that survives all the way into a figure
            self.fig.text(0.5, 0.5, 'OUT OF DATE', ha='center', va='center',
                          fontsize=42, color='#C0392B', alpha=0.16,
                          rotation=18, zorder=50)
        self.fig.subplots_adjust(left=0.01, right=0.99,
                                 top=0.99 if annotate else 0.88,
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
            text = report.mohr1_text(r, len(self.active),
                                     method=kw['method'], site=kw['site'])
        with open(fn, 'w', newline='\n', encoding='ascii',
                  errors='replace') as fh:
            fh.write(text)
        self.status.showMessage('saved ' + fn)

    def show_about(self):
        about.About(self).exec_()

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

        # phosphor green on black, and hard aliased edges so the lines read as
        # pixels rather than as smooth strokes
        if self.retro:
            plot.set_palette(retro.PLOT_PEN, retro.PLOT_PAPER,
                             aa=False, stroke=retro.PLOT_STROKE)
            self.fig.set_facecolor(retro.PLOT_PAPER)
        else:
            plot.set_palette()
            self.fig.set_facecolor('white')

        for strip in (self.strip_ar, self.strip_a, self.strip_b):
            strip.set_language(self.retro)
        for pan in self.findChildren(Panel):
            pan.set_retro(self.retro)

        self.act_1991.setVisible(self.retro)

        for w in self.findChildren(QtWidgets.QLabel):
            if w.objectName() == 'heading':
                base = w.property('en') or w.text()
                w.setProperty('en', base)
                w.setText(retro.translate(base) if self.retro else base)
        for act in self.findChildren(QtWidgets.QAction):
            if act is self.act_1991:
                continue          # its label is the way out, leave it alone
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

    retro_wanted = {'on': False}
    if splash.image_path():
        sp = splash.Splash()
        sp.signature_clicked.connect(
            lambda: retro_wanted.__setitem__('on', True))
        sp.exec_()          # dismisses on a click, a key, or its own timer

    w.show()
    if retro_wanted['on']:
        w.toggle_1991(True)
    w.entry.focus()
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
