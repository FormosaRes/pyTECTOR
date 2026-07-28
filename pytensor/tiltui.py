# -*- coding: utf-8 -*-
"""The incremental restoration test, as a window.

Sweeps the rotation from nothing to more than full restoration, inverting at
each step, and draws both diagnostics against the fraction removed. The point
is to make the syn-tilt case visible: if the faults formed while the tilting
was happening, the best answer is at a partial restoration, and restoring the
whole amount is wrong.

Nothing here chooses the angle. It shows the curves and lets the user adopt a
fraction if they want to.
"""
import numpy as np
from PyQt5 import QtCore, QtWidgets

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as Canvas
from matplotlib.figure import Figure

from . import core, invdir, tilt

FIT_COLOUR = '#23324A'
AND_COLOUR = '#8A5A00'


class SweepWorker(QtCore.QThread):
    done = QtCore.pyqtSignal(object)
    failed = QtCore.pyqtSignal(str)
    step = QtCore.pyqtSignal(int, int)

    def __init__(self, n, s, rot, n_pass, steps=26, parent=None):
        super(SweepWorker, self).__init__(parent)
        self.n, self.s, self.rot, self.n_pass = n, s, rot, n_pass
        self.steps = steps

    def run(self):
        try:
            fr = np.linspace(0.0, 1.25, self.steps)
            done = [0]

            def runner(nn, ss):
                T = invdir.run(nn, ss, n_pass=self.n_pass)['T']
                done[0] += 1
                self.step.emit(done[0], len(fr))
                return T

            rows = tilt.sweep(self.n, self.s, self.rot[0], self.rot[1],
                              self.rot[2], runner, fractions=fr)
            self.done.emit(rows)
        except Exception as exc:
            self.failed.emit(str(exc))


class TiltDialog(QtWidgets.QDialog):
    #: emitted with an angle in degrees when the user adopts a restoration
    adopt = QtCore.pyqtSignal(float, float, float)

    def __init__(self, n, s, rot, n_pass=1, parent=None):
        super(TiltDialog, self).__init__(parent)
        self.setWindowTitle('Incremental restoration test')
        self.resize(880, 620)
        self.rot = rot
        self.rows = None

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(12, 12, 12, 10)
        lay.setSpacing(8)

        head = QtWidgets.QLabel(
            'Restoring the reference surface to horizontal is only right if '
            'the faults predate the tilting. If they formed during it, the '
            'best answer is at a partial restoration.')
        head.setWordWrap(True)
        head.setObjectName('legend')
        lay.addWidget(head)

        self.fig = Figure(figsize=(8, 3.6), facecolor='white')
        self.canvas = Canvas(self.fig)
        lay.addWidget(self.canvas, 1)

        self.txt = QtWidgets.QPlainTextEdit()
        self.txt.setReadOnly(True)
        self.txt.setObjectName('report')
        self.txt.setMaximumHeight(140)
        lay.addWidget(self.txt)

        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)
        self.bar = QtWidgets.QProgressBar()
        self.bar.setFixedWidth(180)
        row.addWidget(self.bar)
        row.addStretch(1)
        row.addWidget(QtWidgets.QLabel('adopt'))
        self.sp = QtWidgets.QSpinBox()
        self.sp.setRange(0, 125)
        self.sp.setSuffix(' %')
        self.sp.setValue(100)
        self.sp.setEnabled(False)
        row.addWidget(self.sp)
        self.btn_adopt = QtWidgets.QPushButton('Use this restoration')
        self.btn_adopt.setEnabled(False)
        self.btn_adopt.clicked.connect(self._adopt)
        row.addWidget(self.btn_adopt)
        b = QtWidgets.QPushButton('Close')
        b.clicked.connect(self.reject)
        row.addWidget(b)
        lay.addLayout(row)

        self.worker = SweepWorker(n, s, rot, n_pass)
        self.worker.step.connect(
            lambda i, k: (self.bar.setMaximum(k), self.bar.setValue(i)))
        self.worker.done.connect(self._finished)
        self.worker.failed.connect(
            lambda m: QtWidgets.QMessageBox.critical(self, 'pyTENSOR', m))
        self.worker.start()

    # ------------------------------------------------------------------
    def _finished(self, rows):
        self.rows = rows
        self.bar.setValue(self.bar.maximum())
        self.sp.setEnabled(True)
        self.btn_adopt.setEnabled(True)

        b_fit = tilt.best(rows, 'ANG')
        self.sp.setValue(int(round(100 * b_fit['fraction'])))
        self.txt.setPlainText('\n'.join(tilt.summarise(rows)))

        f = np.array([r['fraction'] for r in rows]) * 100
        self.fig.clear()
        ax = self.fig.add_subplot(111)
        ax.plot(f, [r['ANG'] for r in rows], 'o-', color=FIT_COLOUR,
                lw=1.6, ms=4, label='mean ANG, the fit')
        ax.plot(f, [r['andersonian'] for r in rows], 's-', color=AND_COLOUR,
                lw=1.6, ms=4,
                label='Andersonian misfit, 0 = one axis vertical')
        ax.axvline(100, color='0.7', lw=1.0, ls='--')
        ax.axvline(100 * b_fit['fraction'], color=FIT_COLOUR, lw=1.0, ls=':')
        ax.set_xlabel('per cent of the rotation removed')
        ax.set_ylabel('degrees')
        ax.legend(fontsize=9, frameon=False)
        ax.grid(alpha=0.25)
        for side in ('top', 'right'):
            ax.spines[side].set_visible(False)
        self.fig.tight_layout()
        self.canvas.draw()

    def _adopt(self):
        t, p, a = self.rot
        self.adopt.emit(t, p, a * self.sp.value() / 100.0)
        self.accept()
