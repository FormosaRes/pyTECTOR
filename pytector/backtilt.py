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

from . import (core, diagnose, entry, hpgl, invdir, modern, penrec, plot,
               rotate, tensorfile, tilt, tiltui)

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
    # only INVDIR has a PSIDIR stage, so only INVDIR can permute its axes
    out['permutation'] = r.get('permutation')
    out['psidir_flag'] = r.get('psidir_flag')
    out['phi_invdir'] = r['invdir']['phi'] if 'invdir' in r else None
    return out


class Solver(QtCore.QThread):
    """Runs a list of jobs off the GUI thread.

    Carries a generation number so that results from a superseded run can be
    dropped on arrival. Dragging the angle slider starts a new solve on every
    step, and without this an early slow one could land after a later fast one
    and leave the screen showing an angle the user has already moved past.
    """
    done = QtCore.pyqtSignal(object, int)
    failed = QtCore.pyqtSignal(str, int)

    def __init__(self, jobs, n_pass, gen, parent=None):
        super(Solver, self).__init__(parent)
        self.jobs, self.n_pass, self.gen = jobs, n_pass, gen

    def run(self):
        try:
            out = {}
            for slot, key, n, s in self.jobs:
                out[slot] = _run(key, n, s, self.n_pass)
            self.done.emit(out, self.gen)
        except Exception:
            import traceback
            self.failed.emit(traceback.format_exc(), self.gen)


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
        self.setWindowTitle('pyTECTOR  -  back-tilt')
        self.setWindowFlags(self.windowFlags()
                            | QtCore.Qt.WindowMinMaxButtonsHint)
        self.resize(1240, 900)
        self.main = parent
        self.results = {}
        self.rot = None
        self.worker = None
        self._gen = 0            # newest solve; older ones are discarded
        self._syncing = False    # slider <-> field, stop the echo
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(90)
        self._timer.timeout.connect(lambda: self._solve(live=True))
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

        # The angle is the one parameter with no analytical answer: it is found
        # by trying values and watching the axes move. A slider is the honest
        # control for that, and the axes have to keep up with it.
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        lab = QtWidgets.QLabel('angle')
        lab.setObjectName('legend')
        lab.setFixedWidth(38)
        row.addWidget(lab)
        self.sl_angle = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.sl_angle.setRange(-90, 90)
        self.sl_angle.setValue(0)
        self.sl_angle.setPageStep(5)
        self.sl_angle.setTickInterval(15)
        self.sl_angle.setTickPosition(QtWidgets.QSlider.TicksBelow)
        self.sl_angle.setToolTip(
            'Rotation angle, right-hand rule about the axis. Drag it: the '
            'stress axes are recomputed as you go.')
        self.sl_angle.valueChanged.connect(self._slider_moved)
        row.addWidget(self.sl_angle, 1)
        self.cb_live = QtWidgets.QCheckBox('recompute while dragging')
        self.cb_live.setChecked(True)
        self.cb_live.setToolTip(
            'Re-invert on every slider step. Turn off on very large data sets '
            'if the drag becomes uneven.')
        row.addWidget(self.cb_live)
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
            'Ring = the measured axis put through the same rotation, i.e. '
            'where it should be.\nStar = the answer from re-inverting the '
            'rotated data.\nThe arrow joins the pair and is labelled with the '
            'gap between them.')
        self.cb_carry.toggled.connect(lambda _v: self._draw())
        row.addWidget(self.cb_carry)
        self.cb_flag = QtWidgets.QCheckBox('flag data')
        self.cb_flag.setChecked(False)
        self.cb_flag.setToolTip(
            'Ring the faults that fit badly or that are holding the answer in '
            'place, and list them underneath. Leave-one-out, so "holding the '
            'answer" means the axes actually move without it.')
        self.cb_flag.toggled.connect(lambda _v: self._refresh_flags())
        row.addWidget(self.cb_flag)
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
        self.btn_hpgl = QtWidgets.QPushButton('Save HPGL')
        self.btn_hpgl.setToolTip(
            'Write the back-tilted stereogram as HPGL, the same pen-plotter '
            'vector format the original program produced.')
        self.btn_hpgl.clicked.connect(self.save_hpgl)
        row.addWidget(self.btn_hpgl)
        bv.addLayout(row)
        lay.addWidget(box)

        self.progress = QtWidgets.QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setFixedHeight(5)
        self.progress.hide()
        lay.addWidget(self.progress)

        # The rotated data themselves. The window was showing what the rotation
        # did to the ANSWER and never what it did to the DATA, so the numbers
        # that would go back into TENSOR were nowhere on screen.
        left = QtWidgets.QFrame()
        left.setObjectName('panel')
        lv = QtWidgets.QVBoxLayout(left)
        lv.setContentsMargins(8, 6, 8, 8)
        lv.setSpacing(4)
        lab = QtWidgets.QLabel('BACK-TILTED DATA')
        lab.setObjectName('heading')
        lv.addWidget(lab)
        self.lbl_data = QtWidgets.QLabel('')
        self.lbl_data.setObjectName('legend')
        self.lbl_data.setWordWrap(True)
        lv.addWidget(self.lbl_data)
        self.txt_data = QtWidgets.QPlainTextEdit()
        self.txt_data.setReadOnly(True)
        self.txt_data.setObjectName('report')
        self.txt_data.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        lv.addWidget(self.txt_data, 1)
        b = QtWidgets.QPushButton('Copy')
        b.setToolTip('Copy the back-tilted records to the clipboard, in the '
                     'four-field entry format, ready to paste into a new site.')
        b.clicked.connect(self._copy_data)
        lv.addWidget(b)

        self.fig = Figure(figsize=(11, 5.6), facecolor='white')
        self.canvas = Canvas(self.fig)
        self.canvas.mpl_connect('resize_event', self._on_resize)
        holder = QtWidgets.QFrame()
        holder.setObjectName('plotpanel')
        hv = QtWidgets.QVBoxLayout(holder)
        hv.setContentsMargins(4, 4, 4, 4)
        hv.addWidget(self.canvas)

        self.txt = QtWidgets.QPlainTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setObjectName('report')
        self.txt.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.txt.setFixedHeight(168)

        right = QtWidgets.QWidget()
        rv = QtWidgets.QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(6)
        rv.addWidget(holder, 1)
        rv.addWidget(self.txt)

        split = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        split.setChildrenCollapsible(False)
        split.addWidget(left)
        split.addWidget(right)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 940])
        lay.addWidget(split, 1)

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
        # The as-measured half does not depend on the rotation, and the main
        # window has usually just computed it. Adopt it rather than showing an
        # empty diagram and making the user press Invert to see an answer that
        # already exists.
        self.results = {}
        self._adopt_main_results()
        self._changed()

    def _adopt_main_results(self):
        """Take the main window's as-measured solution if we have none."""
        m = self.main
        got = False
        for k in ('A', 'B'):
            r = getattr(m, 'results', {}).get(k) if m else None
            if r is not None and ('raw_' + k) not in self.results:
                self.results['raw_' + k] = r
                got = True
        return got

    def showEvent(self, ev):
        """Shown again. Pick up anything new, but do NOT reload: this also
        fires when the window is restored from minimised, and a reload would
        throw away an inversion the user is in the middle of reading. A genuine
        reopen goes through the main window, which calls reload itself."""
        super(BackTiltWindow, self).showEvent(ev)
        if self._adopt_main_results():
            self._draw()
            self.txt.setPlainText(self.summary())
        self._sync_planes()

    def changeEvent(self, ev):
        """Brought back to the front: pick up reference surfaces added in the
        main window in the meantime.

        Only the surfaces, not the fault data, so an inversion already on
        screen is not thrown away just because the user clicked between
        windows. Marking a reference plane next door and finding this window
        still saying there is none was the whole of the problem.
        """
        super(BackTiltWindow, self).changeEvent(ev)
        if ev.type() == QtCore.QEvent.ActivationChange and self.isActiveWindow():
            self._sync_planes()

    def _sync_planes(self):
        m = self.main
        if m is None:
            return
        planes = [dict(p) for p in m.planes]
        if planes == self.planes:
            return
        self.planes = planes
        self._changed(live=self.cb_live.isChecked())

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
    def _slider_moved(self, value):
        """The slider owns the angle field; dragging it implies axis mode."""
        if self._syncing:
            return
        if self.cmb_src.currentIndex() != 1:
            self.cmb_src.setCurrentIndex(1)
        self._syncing = True
        self.fields[2].setText('%d' % value)
        self._syncing = False
        self._changed(live=True)

    def _changed(self, *_a, **kw):
        """Work out the rotation from whichever source is selected.

        The angle is the user's call. There is no analytical solution for it:
        it is found by trying values and looking at the result, which is why
        the archive folders are named after what was tried. This only makes
        trying quick, and keeps the rotation in force visible.
        """
        live = bool(kw.get('live'))
        axis_mode = self.cmb_src.currentIndex() == 1
        vals = []
        for e in self.fields:
            e.setEnabled(axis_mode)
            txt = e.text().strip()
            try:
                vals.append(float(txt) if txt else None)
            except ValueError:
                vals.append(None)

        self.sl_angle.setEnabled(axis_mode)
        if axis_mode and not self._syncing and vals[2] is not None:
            self._syncing = True
            self.sl_angle.setValue(int(round(max(-90.0, min(90.0, vals[2])))))
            self._syncing = False

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
                note = ('no reference surface: mark one in the main window '
                        '(it appears here as soon as you come back)')
            else:
                t, p, a = rotate.restores_to_horizontal(*ref)
                self.rot = (t, p, a * frac)
                # Say what the rotation actually does to the reference surface,
                # rather than asking anyone to take it on trust. At 100 per
                # cent the restored dip must read 00.
                v = core.normal_from_dipaz(ref[0], ref[1])
                v = rotate.rotate_vectors(np.atleast_2d(v), *self.rot)[0]
                raz, rdip = plot.reference_from_vectors(v)
                note = ('reference surface %03.0f/%02.0f  ->  %03.0f/%02.0f'
                        % (ref[0], ref[1], raz, rdip))
                if frac == 1.0:
                    note += ('  (flat)' if rdip < 0.5
                             else '  NOT FLAT - this is a bug, please report')

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
        # the as-measured half is invertible with no rotation set at all
        ok = bool(self.rot) and n >= 4
        self.btn_run.setEnabled(n >= 4)
        self.btn_tilt.setEnabled(ok)
        # the as-measured half does not depend on the rotation, so keep it:
        # that is what makes dragging cheap enough to do live
        self.results = dict((k, v) for k, v in self.results.items()
                            if k.startswith('raw_'))
        self._fill_data()
        self._draw()
        if live and ok and self.cb_live.isChecked():
            self._timer.start()

    # -------------------------------------------------------- inversion --
    def keys(self):
        return [k for k, c in (('A', self.cb_a), ('B', self.cb_b))
                if c.isChecked()]

    def invert(self):
        self._solve(live=False)

    def _solve(self, live=False):
        """Queue whatever is missing. Only the rotated half is ever recomputed
        on a drag; the as-measured half is solved once and kept."""
        if len(self.records) < 4:
            return
        keys = self.keys()
        if not keys:
            return
        n, s = self.n_s
        jobs = []
        for k in keys:
            if ('raw_' + k) not in self.results:
                jobs.append(('raw_' + k, k, n, s))
        if self.rot:
            rn, rs = rotate.rotate_site(n, s, *self.rot)
            for k in keys:
                jobs.append(('rot_' + k, k, rn, rs))
        if not jobs:
            return

        self._gen += 1
        if not live:
            self.btn_run.setEnabled(False)
            self.progress.show()
        w = Solver(jobs, self.n_pass, self._gen, self)
        w.done.connect(self._finished)
        w.failed.connect(self._failed)
        # hold a reference until it has actually stopped, or Qt may collect a
        # running thread out from under itself
        self._workers = [x for x in getattr(self, '_workers', [])
                         if x.isRunning()]
        self._workers.append(w)
        self.worker = w
        w.start()

    def _flags(self, which):
        """Per-datum diagnostics for one of the two states, cached.

        Leave-one-out, so it needs an inversion per datum. That is a few
        milliseconds each with INVDIR, but it is not free, so it is computed
        once per solution and kept.
        """
        if not self.cb_flag.isChecked():
            return None
        key = self.keys()
        if not key:
            return None
        res = self.results.get('%s_%s' % (which, key[0]))
        if res is None or len(self.records) < 5:
            return None
        cache = getattr(self, '_flag_cache', {})
        tag = (which, key[0], id(res))
        if tag not in cache:
            n, s = self.n_s
            if which == 'rot' and self.rot:
                n, s = rotate.rotate_site(n, s, *self.rot)
            solver = ((lambda a, b: invdir.run(a, b, n_pass=self.n_pass)['T'])
                      if key[0] == 'A'
                      else (lambda a, b: modern.run(a, b, n_starts=200)['T']))
            try:
                cache = dict(cache)
                cache[tag] = diagnose.combine(res, n, s, solver)
            except Exception:
                cache[tag] = []
            self._flag_cache = cache
        return cache.get(tag) or None

    def _disclosure(self, which, rows):
        """The with-and-without comparison for one of the two states."""
        key = self.keys()
        if not rows or not key or len(self.records) < 6:
            return None
        n, s = self.n_s
        if which == 'rot' and self.rot:
            n, s = rotate.rotate_site(n, s, *self.rot)
        solver = ((lambda a, b: invdir.run(a, b, n_pass=self.n_pass)['T'])
                  if key[0] == 'A'
                  else (lambda a, b: modern.run(a, b, n_starts=200)['T']))
        try:
            return diagnose.disclosure(rows, n, s, solver)
        except Exception:
            return None

    def _refresh_flags(self):
        self._flag_cache = {}
        self._draw()
        self.txt.setPlainText(self.summary())

    def _failed(self, msg, gen):
        if gen != self._gen:
            return
        self.btn_run.setEnabled(True)
        self.progress.hide()
        QtWidgets.QMessageBox.critical(self, 'pyTECTOR', msg)

    def _finished(self, out, gen):
        if gen != self._gen:
            return          # the slider has already moved past this one
        self.btn_run.setEnabled(True)
        self.progress.hide()
        self.results.update(out)
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
        if not self.results:
            return ''
        if not self.rot:
            # no rotation yet: still worth reading the measured answer
            L = ['NO ROTATION SET.  The as-measured solution only.', '']
            L.append('%-22s %-9s %-9s %-9s %-7s %-6s %-8s %s'
                     % ('', 'sigma1', 'sigma2', 'sigma3', 'Phi', 'ANG',
                        'S4', 'Andersonian misfit'))
            for k, name, _d in METHODS:
                r = self.results.get('raw_' + k)
                if not r:
                    continue
                m, regime, _ax = tilt.andersonian(r)
                L.append('%-22s %-9s %-9s %-9s %-7.3f %-6.1f %-8.4f %.1f  %s'
                         % ('%s  as measured' % name,
                            '%03.0f/%02.0f' % r['sigma1'],
                            '%03.0f/%02.0f' % r['sigma2'],
                            '%03.0f/%02.0f' % r['sigma3'],
                            r['phi'], r['ANG_mean'], r['S4'], m, regime))
            return '\n'.join(L)
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
            # PSIDIR relabels the frozen axes whenever its psi leaves the last
            # 60 degrees of the turn. TENSOR prints this on the PSIDIR line.
            for lab, r in (('as measured', raw), ('restored', rot)):
                if r.get('permutation'):
                    L.append('%-22s PSIDIR %s: sigma1/2/3 are NOT INVDIR\'s '
                             'labels (INVDIR Phi %.3f -> %.3f)'
                             % ('', lab, r.get('phi_invdir') or float('nan'),
                                r['phi']))
            L.append('')

        for which, lab in (('raw', 'AS MEASURED'), ('rot', 'BACK-TILTED')):
            rows = self._flags(which)
            if not rows:
                continue
            hot = [r for r in rows if r['flag']]
            L.append('DATA WORTH CHECKING, %s   (%d of %d flagged)'
                     % (lab, len(hot), len(rows)))
            L.append(diagnose.text_table(rows, limit=8))
            if len(hot) > 8:
                L.append('   ... and %d more' % (len(hot) - 8))
            L.append('')
            d = self._disclosure(which, rows)
            if d:
                L.append('IF THOSE WERE SET ASIDE, %s' % lab)
                L.append(diagnose.disclosure_text(d, rows))
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
        conf = self.certainty
        # Two separate things have to be redone for the restored panel.
        #
        # NOT canonicalised. See rotate.canonicalise: the archive settles it,
        # and the original kept the rotated slip vector as it came.
        # The side the barb sits on, which is orientation-dependent in its own
        # right and reverses for any datum whose slip passes through pure
        # dip-slip, about 20 per cent of archive data at the usual angles.
        sides = plot.strike_slip_sign_vectors(n, s)
        sides_rot = plot.strike_slip_sign_vectors(rn, rs)
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

            fraw = self._flags('raw') if k else None
            frot = self._flags('rot') if k else None
            ax = cell(2 * j + 1, 'AS MEASURED' + ('   ' + name if name else ''),
                      'no rotation applied')
            plot.plot_site(ax, n, s, raw, certainty=conf, sides=sides,
                           site_code=self.site_name,
                           reference=self.reference_now(False),
                           declination=self.decl,
                           mark=[d['plot_mark'] for d in fraw] if fraw else None,
                           header='AS MEASURED  no rotation')
            if annotate and raw:
                plot.annotate_result(ax, raw, n_data=len(self.records))

            ax = cell(2 * j + 2, 'BACK-TILTED' + ('   ' + name if name else ''),
                      tag.strip() or 'no rotation set')
            plot.plot_site(ax, rn, rs, rot, certainty=conf, sides=sides_rot,
                           site_code=self.site_name,
                           reference=self.reference_now(True),
                           declination=self.decl,
                           mark=[d['plot_mark'] for d in frot] if frot else None,
                           header='BACK-TILTED' + tag)
            if raw and self.rot and self.cb_carry.isChecked():
                plot.plot_carried_axes(ax, carried(raw, *self.rot), rot)
            # in axis mode the rotation is three numbers in a box and nothing
            # on the diagram; draw the axis so it can be checked by eye
            if self.rot and self.cmb_src.currentIndex() == 1:
                plot.plot_rotation_axis(ax, *self.rot)
            if annotate and rot:
                plot.annotate_result(ax, rot, n_data=len(self.records))

        if not annotate and self.rot and self.cb_carry.isChecked():
            # One line, in the same ink as the diagram. The coloured legend
            # that stood here was removed with the colours, but "what is the
            # dashed line" still needs an answer on the page.
            bits = ['○ measured axis carried through the rotation',
                    'dashed = its path to the ★ re-inverted answer']
            if self.cmb_src.currentIndex() == 1:
                bits.append('⊙ rotation axis, arrow = which way it turns')
            self.fig.text(0.02, 0.006, '     '.join(bits), fontsize=7.5,
                          va='bottom',
                          color='#1E1E1C' if plot.PEN == 'k' else plot.PEN)
        self.fig.subplots_adjust(left=0.02, right=0.98,
                                 top=0.99 if annotate else 0.90,
                                 bottom=0.06 if annotate else 0.045,
                                 wspace=0.02, hspace=0.28)
        # after the layout, because it measures the panels
        plot.fit_captions(self.fig)
        self.canvas.draw()

    def rotated_records(self):
        """The data as they are after the rotation, as dip azimuth / dip /
        rake, which is the form they go back into TENSOR in."""
        n, s = self.n_s
        if not len(n) or not self.rot:
            return []
        rn, rs = rotate.rotate_site(n, s, *self.rot)
        return rotate.as_records(rn, rs)

    def _fill_data(self):
        """Measured beside back-tilted, one line per fault."""
        recs = self.rotated_records()
        if not recs:
            self.txt_data.setPlainText('')
            self.lbl_data.setText('set a rotation to see the data it produces')
            return
        L = ['%-3s %-4s %-12s   %-12s' % ('n', 'code', 'as measured',
                                          'back-tilted'),
             '%-3s %-4s %-12s   %-12s' % ('', '', 'az / dip / rake',
                                          'az / dip / rake')]
        for i, (a, b) in enumerate(zip(self.records, recs)):
            code = '%s%s' % (a.get('confidence', 'C') or 'C',
                             a.get('sense', '') or '')
            L.append('%-3d %-4s %03d /%02d /%03d   %03d /%02d /%03d'
                     % (i + 1, code[:4], a['dipaz'], a['dip'],
                        round(a['rake']), b['dipaz'], b['dip'],
                        round(b['rake'])))
        self.txt_data.setPlainText('\n'.join(L))
        self.lbl_data.setText(
            'rake is stored with Angelier’s +180 convention, the same as '
            'in the site file. %s' % rotate.describe(*self.rot))

    def _copy_data(self):
        recs = self.rotated_records()
        if not recs:
            return
        out = []
        for a, b in zip(self.records, recs):
            out.append('%s%s %03d %02d %03d'
                       % (a.get('confidence', 'C') or 'C',
                          a.get('sense', '') or '', b['dipaz'], b['dip'],
                          round(b['rake'])))
        QtWidgets.QApplication.clipboard().setText('\n'.join(out))
        self.lbl_data.setText('%d records copied.' % len(out))

    def _on_resize(self, _ev):
        """The captions are sized to the panel, so they have to be resized
        with it. Only the text changes, so there is no need to redraw the
        stereograms."""
        plot.fit_captions(self.fig)

    #: where each panel's centre goes in plotter units. A stereogram with its
    #: frame is about 2.5 x 2.8 plot units, and the writer's scale is 2002
    #: units per plot unit, so 5600 across and 6200 down clears it.
    HPGL_PITCH = (5600, 6200)

    def save_hpgl(self):
        """Everything on screen as HPGL, in one file, laid out as on screen.

        It used to write the back-tilted panel alone, which threw away three
        quarters of what the window had just computed: the comparison IS the
        output here, so the file has to carry the pair, and both methods when
        both are shown.

        Replays plot_site through the pen recorder rather than keeping a second,
        shorter drawing routine, so each panel carries what the figure carries:
        striae, ticks, centre cross, N and M, frame, arrows, reference surfaces.
        The writer reads its origin at every call, so moving the origin between
        panels tiles them into one plot.
        """
        n, s = self.n_s
        if not len(n):
            return
        keys = [k for k in self.keys() if ('raw_' + k) in self.results]
        if not keys:
            QtWidgets.QMessageBox.information(
                self, 'pyTECTOR', 'Invert first: there is nothing to write.')
            return
        tag = rotate.describe(*self.rot) if self.rot else 'as measured'
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save HPGL', '%s %s.hpgl' % (self.site_name, tag),
            'HPGL (*.hpgl)')
        if not fn:
            return

        rn, rs = ((n, s) if not self.rot
                  else rotate.rotate_site(n, s, *self.rot))
        sides, sides_rot = (plot.strike_slip_sign_vectors(n, s),
                            plot.strike_slip_sign_vectors(rn, rs))
        rtag = ('' if not self.rot
                else '  %03.0f/%02.0f %+.0f' % self.rot)

        w = hpgl.Writer()
        x0, y0 = w.origin
        dx, dy = self.HPGL_PITCH
        panels = 0
        for row, k in enumerate(keys):
            name = dict((m[0], m[1]) for m in METHODS).get(k, '')
            for col, (nn, ss, sd, res, head) in enumerate((
                    (n, s, sides, self.results.get('raw_' + k),
                     'AS MEASURED  %s' % name),
                    (rn, rs, sides_rot, self.results.get('rot_' + k),
                     'BACK-TILTED  %s%s' % (name, rtag)))):
                rec = penrec.Recorder()
                plot.plot_site(rec, nn, ss, res, certainty=self.certainty,
                               sides=sd, site_code=self.site_name,
                               reference=self.reference_now(col == 1),
                               declination=self.decl, header=head)
                # top row first, so the sheet reads the way the window does
                w.origin = (x0 + col * dx, y0 + (len(keys) - 1 - row) * dy)
                rec.emit(w)
                panels += 1
        w.origin = (x0, y0)
        w.save(fn)
        QtWidgets.QMessageBox.information(
            self, 'pyTECTOR', 'saved %s\n%d panels' % (fn, panels))

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
