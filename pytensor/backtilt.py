# -*- coding: utf-8 -*-
"""Back-tilting, in a window of its own.

It used to live in the main sidebar, where two problems came with it. The
stereogram silently changed meaning depending on a selector several inches
away, and the measured stress axes vanished the moment a rotation was applied,
so there was nothing to compare the restored axes against. Both are fixed by
giving back-tilting its own window: measured on the left, restored on the
right, always both, always labelled, and the measured axes carried through the
rotation are drawn on the restored diagram as open rings.

The two things this window is for:

**Where did the axes go.** The ring is the measured answer carried through the
rotation. The star is the answer obtained by re-inverting the rotated data.
For S4MIN they coincide exactly, because S4 is rotation invariant. For INVDIR
they do not, and that gap is a property of Angelier's method, not of the
geology. See plot.plot_carried_axes.

**Whether the rotation is defensible.** Restoring a bedding surface to
horizontal is only right if the faults predate the tilting. If they moved
during it, full restoration over-rotates them. So the window reports the
Andersonian misfit before and after rather than assuming that flat bedding is
the answer, and the tilt test sweeps partial restorations.
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

from . import core, entry, invdir, modern, plot, rotate, tensorfile, tilt, tiltui

DEG = '°'
PHI = 'Φ'

#: key, display name, one-line description
METHODS = (('A', 'INVDIR', 'as TENSOR 5.45 runs it'),
           ('B', 'S4MIN', 'exact minimum of the same criterion'))


def _run(key, n, s, n_pass):
    if key == 'A':
        r = invdir.run(n, s, n_pass=n_pass)
    else:
        r = modern.run(n, s, n_starts=400)
    out = core.summary(r['T'], n, s)
    out['T'] = r['T']
    return out


class Solver(QtCore.QThread):
    """Both states in one background run, so the pair on screen always comes
    from the same data and the same settings."""
    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)

    def __init__(self, n, s, rn, rs, keys, n_pass, parent=None):
        super(Solver, self).__init__(parent)
        self.n, self.s, self.rn, self.rs = n, s, rn, rs
        self.keys, self.n_pass = keys, n_pass

    def run(self):
        try:
            out = {}
            for k in self.keys:
                out['raw_' + k] = _run(k, self.n, self.s, self.n_pass)
                out['rot_' + k] = _run(k, self.rn, self.rs, self.n_pass)
            self.done.emit(out)
        except Exception:
            import traceback
            self.failed.emit(traceback.format_exc())


def carried(result, trend, plunge, angle):
    """The measured axes put through the same rotation as the data. Not an
    inversion: just the three unit vectors, turned."""
    out = {}
    for key in ('sigma1', 'sigma2', 'sigma3'):
        v = core.vec_from_trend_plunge(*result[key])
        v = rotate.rotate_vectors(np.atleast_2d(v), trend, plunge, angle)[0]
        out[key] = core.trend_plunge(v)
    out['phi'] = result['phi']
    out['eigenvalues'] = result.get('eigenvalues')
    return out


def separation(a, b):
    """Angle between the corresponding axes of two solutions, in degrees."""
    out = []
    for key in ('sigma1', 'sigma2', 'sigma3'):
        u = core.vec_from_trend_plunge(*a[key])
        v = core.vec_from_trend_plunge(*b[key])
        out.append(float(np.degrees(np.arccos(min(abs(float(u @ v)), 1.0)))))
    return out


class BackTiltWindow(QtWidgets.QDialog):
    """Non-modal, so the fault table stays usable behind it."""

    def __init__(self, parent=None):
        super(BackTiltWindow, self).__init__(parent)
        self.setWindowTitle('pyTENSOR  -  back-tilt')
        self.setWindowFlags(self.windowFlags()
                            | QtCore.Qt.WindowMinMaxButtonsHint)
        self.resize(1240, 900)
        self.main = parent
        self.results = {}
        self.rot = None
        self.worker = None
        self._build()
        self.reload()

    # ------------------------------------------------------------ layout --
    def _build(self):
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(6)

        self.lbl_head = QtWidgets.QLabel('')
        self.lbl_head.setObjectName('context')
        lay.addWidget(self.lbl_head)

        box = QtWidgets.QFrame()
        box.setObjectName('panel')
        bv = QtWidgets.QVBoxLayout(box)
        bv.setContentsMargins(10, 8, 10, 8)
        bv.setSpacing(4)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        self.cmb_src = QtWidgets.QComboBox()
        self.cmb_src.addItems(['restore the reference surface to horizontal',
                               'rotation axis   trend / plunge / angle'])
        self.cmb_src.setFixedWidth(300)
        self.cmb_src.currentIndexChanged.connect(self._changed)
        row.addWidget(self.cmb_src)

        self.fields = []
        for hint, tip in (('020', 'axis trend'), ('00', 'axis plunge'),
                          ('-20', 'rotation angle, right-hand rule')):
            e = QtWidgets.QLineEdit()
            e.setObjectName('seg')
            e.setFixedWidth(58)
            e.setAlignment(QtCore.Qt.AlignCenter)
            e.setPlaceholderText(hint)
            e.setToolTip(tip)
            e.textEdited.connect(lambda _t: self._changed())
            self.fields.append(e)
            row.addWidget(e)

        lab = QtWidgets.QLabel('   restore')
        lab.setObjectName('legend')
        row.addWidget(lab)
        self.sp_frac = QtWidgets.QSpinBox()
        self.sp_frac.setRange(0, 125)
        self.sp_frac.setSuffix(' %')
        self.sp_frac.setValue(100)
        self.sp_frac.setToolTip(
            'Partial restoration. Below 100 per cent the faults are treated as '
            'having moved part way through the tilting.')
        self.sp_frac.valueChanged.connect(lambda _v: self._changed())
        row.addWidget(self.sp_frac)
        row.addStretch(1)
        bv.addLayout(row)

        self.lbl_rot = QtWidgets.QLabel('')
        self.lbl_rot.setObjectName('legend')
        self.lbl_rot.setWordWrap(True)
        bv.addWidget(self.lbl_rot)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        self.cb_a = QtWidgets.QCheckBox('INVDIR')
        self.cb_a.setChecked(True)
        self.cb_b = QtWidgets.QCheckBox('S4MIN')
        self.cb_b.setChecked(True)
        for c in (self.cb_a, self.cb_b):
            c.toggled.connect(lambda _v: self._draw())
            row.addWidget(c)
        self.cb_carry = QtWidgets.QCheckBox('carried axes')
        self.cb_carry.setChecked(True)
        self.cb_carry.setToolTip(
            'Draw the measured axes put through the same rotation, as open '
            'rings, so you can see where they went.')
        self.cb_carry.toggled.connect(lambda _v: self._draw())
        row.addWidget(self.cb_carry)
        row.addStretch(1)

        self.btn_run = QtWidgets.QPushButton('Invert both')
        self.btn_run.setObjectName('run')
        self.btn_run.clicked.connect(self.invert)
        row.addWidget(self.btn_run)
        self.btn_tilt = QtWidgets.QPushButton('Tilt test')
        self.btn_tilt.setToolTip(
            'Invert at every restoration from 0 to 125 per cent, so faulting '
            'that happened during the tilting shows up as a best answer short '
            'of flat.')
        self.btn_tilt.clicked.connect(self.tilt_test)
        row.addWidget(self.btn_tilt)
        b = QtWidgets.QPushButton('Reload data')
        b.setToolTip('Pick up any edits made in the main window.')
        b.clicked.connect(self.reload)
        row.addWidget(b)
        b = QtWidgets.QPushButton('Save PNG')
        b.clicked.connect(self.save_png)
        row.addWidget(b)
        bv.addLayout(row)
        lay.addWidget(box)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(5)
        self.progress.hide()
        lay.addWidget(self.progress)

        self.fig = Figure(figsize=(11, 5.6), facecolor='white')
        self.canvas = Canvas(self.fig)
        holder = QtWidgets.QFrame()
        holder.setObjectName('plotpanel')
        hv = QtWidgets.QVBoxLayout(holder)
        hv.setContentsMargins(4, 4, 4, 4)
        hv.addWidget(self.canvas)
        lay.addWidget(holder, 1)

        self.txt = QtWidgets.QPlainTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setObjectName('report')
        self.txt.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.txt.setFixedHeight(168)
        lay.addWidget(self.txt)

    # -------------------------------------------------------------- data --
    def reload(self):
        """Take a copy of the main window's data. A copy, not a live view: the
        pair on screen must keep describing the numbers underneath it even if
        the table is edited while this window is open."""
        m = self.main
        self.records = [dict(r) for r in m.active] if m else []
        self.planes = [dict(p) for p in m.planes] if m else []
        self.site_name = getattr(m, 'site_name', '01') if m else '01'
        self.n_pass = m.sp_pass.value() if m else 1
        try:
            self.decl = float(m.ed_decl.text().strip())
        except (AttributeError, ValueError):
            self.decl = plot.MAGNETIC_OFFSET
        self.results = {}
        self._changed()

    @property
    def ref_plane(self):
        for p in self.planes:
            if p.get('ref'):
                return (p['dipaz'], p['dip'])
        return None

    @property
    def n_s(self):
        return entry.records_to_arrays(self.records)

    @property
    def certainty(self):
        return [r.get('confidence', 'C') for r in self.records]

    @property
    def sides(self):
        if not self.records:
            return np.zeros(0)
        return plot.strike_slip_sign(
            [r['dipaz'] for r in self.records],
            [r['dip'] for r in self.records],
            [r['rake'] + tensorfile.RAKE_OFFSET for r in self.records])

    def reference_now(self, rotated):
        if not self.planes:
            return None
        out = []
        for p in self.planes:
            az, dp = p['dipaz'], p['dip']
            if rotated and self.rot:
                v = core.normal_from_dipaz(az, dp)
                v = rotate.rotate_vectors(np.atleast_2d(v), *self.rot)[0]
                az, dp = plot.reference_from_vectors(v)
            out.append((az, dp, p.get('ref', False)))
        return out

    # --------------------------------------------------------- rotation --
    def _changed(self, *_a):
        """Work out the rotation from whichever source is selected.

        The angle is the user's call. There is no analytical solution for it:
        it is found by trying values and looking at the result, which is why
        the archive folders are named after what was tried. This only makes
        trying quick, and keeps the rotation in force visible.
        """
        axis_mode = self.cmb_src.currentIndex() == 1
        vals = []
        for e in self.fields:
            e.setEnabled(axis_mode)
            txt = e.text().strip()
            try:
                vals.append(float(txt) if txt else None)
            except ValueError:
                vals.append(None)

        frac = self.sp_frac.value() / 100.0
        self.rot, note = None, ''
        if axis_mode:
            if all(v is not None for v in vals):
                self.rot = (vals[0], vals[1], vals[2] * frac)
                note = 'right-hand rule about the axis'
            else:
                note = 'fill trend, plunge and angle'
        else:
            ref = self.ref_plane
            if ref is None:
                note = ('mark a reference surface in the main window, then '
                        'press Reload data')
            else:
                t, p, a = rotate.restores_to_horizontal(*ref)
                self.rot = (t, p, a * frac)
                note = ('reference surface  dip az %03.0f / %02.0f'
                        % (ref[0], ref[1]))

        if self.rot is None:
            self.lbl_rot.setText(note)
        else:
            t, p, a = self.rot
            extra = '' if frac == 1.0 else '   %d %% of the full restoration' \
                                           % self.sp_frac.value()
            self.lbl_rot.setText('axis %03.0f / %02.0f   angle %+.1f%s%s   %s'
                                 % (t, p, a, DEG, extra, note))
        n = len(self.records)
        self.lbl_head.setText(
            'SITE %s     %d fault%s     %s'
            % (self.site_name, n, '' if n == 1 else 's',
               'no rotation set' if self.rot is None
               else rotate.describe(*self.rot)))
        ok = bool(self.rot) and n >= 4
        self.btn_run.setEnabled(ok)
        self.btn_tilt.setEnabled(ok)
        self.results = {}
        self._draw()

    # -------------------------------------------------------- inversion --
    def keys(self):
        return [k for k, c in (('A', self.cb_a), ('B', self.cb_b))
                if c.isChecked()]

    def invert(self):
        if not self.rot or len(self.records) < 4:
            return
        keys = self.keys()
        if not keys:
            return
        n, s = self.n_s
        rn, rs = rotate.rotate_site(n, s, *self.rot)
        self.btn_run.setEnabled(False)
        self.progress.show()
        self.worker = Solver(n, s, rn, rs, keys, self.n_pass, self)
        self.worker.done.connect(self._finished)
        self.worker.failed.connect(self._failed)
        self.worker.start()

    def _failed(self, msg):
        self.btn_run.setEnabled(True)
        self.progress.hide()
        QtWidgets.QMessageBox.critical(self, 'pyTENSOR', msg)

    def _finished(self, out):
        self.btn_run.setEnabled(True)
        self.progress.hide()
        self.results = out
        self._draw()
        self.txt.setPlainText(self.summary())

    def tilt_test(self):
        if not self.rot or len(self.records) < 4:
            return
        n, s = self.n_s
        # the sweep needs the whole rotation, not the fraction already applied
        full = self.rot
        if self.sp_frac.value():
            full = (self.rot[0], self.rot[1],
                    self.rot[2] * 100.0 / self.sp_frac.value())
        dlg = tiltui.TiltDialog(n, s, full, self.n_pass, self)
        dlg.adopt.connect(self._adopt)
        dlg.exec_()

    def _adopt(self, trend, plunge, angle):
        self.cmb_src.setCurrentIndex(1)
        self.sp_frac.setValue(100)
        for e, v in zip(self.fields, (trend, plunge, angle)):
            e.setText('%.4g' % v)
        self._changed()

    # ----------------------------------------------------------- reading --
    def summary(self):
        """The numbers behind the two diagrams, and what they do and do not
        show. Written out rather than left to be inferred from the plots."""
        if not self.results or not self.rot:
            return ''
        t, p, a = self.rot
        L = ['ROTATION   axis %03.0f / %02.0f   angle %+.1f deg   %s'
             % (t, p, a, rotate.describe(t, p, a)), '']
        L.append('%-22s %-9s %-9s %-9s %-7s %-6s %-8s %s'
                 % ('', 'sigma1', 'sigma2', 'sigma3', 'Phi', 'ANG',
                    'S4', 'Andersonian misfit'))
        for k, name, _d in METHODS:
            raw, rot = self.results.get('raw_' + k), self.results.get('rot_' + k)
            if not (raw and rot):
                continue
            for lab, r in (('as measured', raw), ('restored', rot)):
                m, regime, _ax = tilt.andersonian(r)
                L.append('%-22s %-9s %-9s %-9s %-7.3f %-6.1f %-8.4f %.1f  %s'
                         % ('%s  %s' % (name, lab),
                            '%03.0f/%02.0f' % r['sigma1'],
                            '%03.0f/%02.0f' % r['sigma2'],
                            '%03.0f/%02.0f' % r['sigma3'],
                            r['phi'], r['ANG_mean'], r['S4'], m, regime))
            m0 = tilt.andersonian(raw)[0]
            m1 = tilt.andersonian(rot)[0]
            sep = separation(carried(raw, *self.rot), rot)
            L.append('%-22s carried vs re-inverted   %.1f  %.1f  %.1f deg'
                     % ('', sep[0], sep[1], sep[2]))
            if m1 > m0 + 2:
                L.append('%-22s the axes moved AWAY from horizontal and '
                         'vertical: this rotation is not supported' % '')
            L.append('')

        L.append('The ring is the measured answer carried through the '
                 'rotation; the star is the answer from re-inverting the')
        L.append('rotated data. For S4MIN they coincide, because S4 is '
                 'rotation invariant, so its Phi and S4 cannot change and')
        L.append('the whole content of the test is where the axes now sit. '
                 'For INVDIR they do not coincide: Angelier ties the')
        L.append('tensor diagonal to the geographic frame, so re-inverting '
                 'turned data searches a different family. That gap is')
        L.append('method, not geology. Median on the 14 archive back-tilt '
                 'pairs: 10 deg on sigma1, about 24 on sigma2 and sigma3.')
        return '\n'.join(L)

    # ----------------------------------------------------------- drawing --
    def _draw(self, annotate=False):
        self.fig.clear()
        n, s = self.n_s
        if not len(n):
            ax = self.fig.add_subplot(111)
            ax.set_facecolor(plot.PAPER)
            ax.axis('off')
            ax.text(0.5, 0.5, 'no fault slips in the main window',
                    ha='center', va='center', fontsize=12,
                    color='#7A776F' if plot.PEN == 'k' else plot.PEN)
            self.canvas.draw()
            return

        rn, rs = ((n, s) if self.rot is None
                  else rotate.rotate_site(n, s, *self.rot))
        keys = [k for k in self.keys() if ('raw_' + k) in self.results] \
            or [None]
        rows = len(keys)
        conf, sides = self.certainty, self.sides
        tag = '' if self.rot is None else '  %03.0f/%02.0f %+.0f' % self.rot
        title_colour = '#1E1E1C' if plot.PEN == 'k' else plot.PEN

        def cell(i, title, sub):
            ax = self.fig.add_subplot(rows, 2, i)
            ax.set_facecolor(plot.PAPER)
            if not annotate:
                ax.set_title('%s\n%s' % (title, sub), fontsize=11,
                             fontweight='600', color=title_colour, pad=6,
                             linespacing=1.4)
            return ax

        for j, k in enumerate(keys):
            name = dict((m[0], m[1]) for m in METHODS).get(k, '')
            raw = self.results.get('raw_%s' % k) if k else None
            rot = self.results.get('rot_%s' % k) if k else None

            ax = cell(2 * j + 1, 'AS MEASURED' + ('   ' + name if name else ''),
                      'no rotation applied')
            plot.plot_site(ax, n, s, raw, certainty=conf, sides=sides,
                           site_code=self.site_name,
                           reference=self.reference_now(False),
                           declination=self.decl,
                           header='AS MEASURED  no rotation')
            if annotate and raw:
                plot.annotate_result(ax, raw, n_data=len(self.records))

            ax = cell(2 * j + 2, 'BACK-TILTED' + ('   ' + name if name else ''),
                      tag.strip() or 'no rotation set')
            plot.plot_site(ax, rn, rs, rot, certainty=conf, sides=sides,
                           site_code=self.site_name,
                           reference=self.reference_now(True),
                           declination=self.decl,
                           header='BACK-TILTED' + tag)
            if raw and self.rot and self.cb_carry.isChecked():
                plot.plot_carried_axes(ax, carried(raw, *self.rot), rot)
            if annotate and rot:
                plot.annotate_result(ax, rot, n_data=len(self.records))

        self.fig.subplots_adjust(left=0.02, right=0.98,
                                 top=0.99 if annotate else 0.90,
                                 bottom=0.10 if annotate else 0.04,
                                 wspace=0.02, hspace=0.28)
        self.canvas.draw()

    def save_png(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save figure', '%s backtilt.png' % self.site_name,
            'PNG (*.png)')
        if not fn:
            return
        self._draw(annotate=True)
        self.fig.savefig(fn, dpi=300, facecolor=plot.PAPER,
                         bbox_inches='tight')
        self._draw()

    def set_palette(self):
        """Follow the main window into and out of 1991 mode."""
        self.fig.set_facecolor(plot.PAPER)
        self._draw()
