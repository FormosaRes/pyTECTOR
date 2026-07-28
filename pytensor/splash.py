# -*- coding: utf-8 -*-
"""Opening screen.

The drawing is Angelier's own block diagram of the Taiwan arc-continent
collision, signed J.A. in the lower right. That signature is the way in to
1991 mode: click it.

Nothing here is required for the program to work. If the image is missing the
splash simply does not appear.
"""
import os

from PyQt5 import QtCore, QtGui, QtWidgets

IMAGE = 'Taiwan Tectonic Map.jpg'

#: where J.A. signed it, in pixels of the 600 x 394 original
SIGNATURE = QtCore.QRect(532, 218, 30, 24)
NATIVE = QtCore.QSize(600, 394)


def image_path(root=None):
    root = root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    p = os.path.join(root, IMAGE)
    return p if os.path.exists(p) else None


class Splash(QtWidgets.QDialog):
    """Frameless opening screen. Emits signature_clicked when J.A. is hit."""
    signature_clicked = QtCore.pyqtSignal()

    #: it closes itself after this long, so not clicking never blocks startup
    DWELL_MS = 4000

    def __init__(self, parent=None, scale=1.25, dwell_ms=None):
        super(Splash, self).__init__(parent)
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.Dialog)
        self.setModal(True)
        self.scale = scale
        self._pm = None
        p = image_path()
        if p:
            pm = QtGui.QPixmap(p)
            if not pm.isNull():
                self._pm = pm.scaled(
                    NATIVE * scale, QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation)

        w = self._pm.width() if self._pm else int(NATIVE.width() * scale)
        h = (self._pm.height() if self._pm else int(NATIVE.height() * scale))
        self.setFixedSize(w, h + 78)
        self.setStyleSheet('QDialog { background: #F4F1E8;'
                           ' border: 1px solid #B9B2A0; }')

        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self.canvas = QtWidgets.QLabel()
        self.canvas.setAlignment(QtCore.Qt.AlignCenter)
        if self._pm:
            self.canvas.setPixmap(self._pm)
        self.canvas.setCursor(QtCore.Qt.ArrowCursor)
        self.canvas.setMouseTracking(True)
        self.canvas.installEventFilter(self)
        lay.addWidget(self.canvas)

        foot = QtWidgets.QWidget()
        fl = QtWidgets.QVBoxLayout(foot)
        fl.setContentsMargins(16, 8, 16, 12)
        fl.setSpacing(2)
        t = QtWidgets.QLabel('pyTENSOR')
        t.setStyleSheet('font-size: 19px; font-weight: 600; color: #1E1E1C;')
        fl.addWidget(t)
        s = QtWidgets.QLabel(
            'palaeostress inversion after the method and the programs of '
            'Jacques Angelier')
        s.setStyleSheet('font-size: 11px; color: #6B665B;')
        fl.addWidget(s)
        hint = QtWidgets.QLabel('click anywhere to continue')
        hint.setStyleSheet('font-size: 10px; color: #A9A59C;')
        fl.addWidget(hint)
        lay.addWidget(foot)

        # never leave the user staring at a screen that will not go away
        QtCore.QTimer.singleShot(
            self.DWELL_MS if dwell_ms is None else dwell_ms, self.accept)

    # ------------------------------------------------------------------
    def _sig_rect(self):
        """The signature hotspot in widget coordinates."""
        if not self._pm:
            return QtCore.QRect()
        k = self._pm.width() / float(NATIVE.width())
        off_x = (self.canvas.width() - self._pm.width()) // 2
        off_y = (self.canvas.height() - self._pm.height()) // 2
        return QtCore.QRect(int(SIGNATURE.x() * k) + off_x,
                            int(SIGNATURE.y() * k) + off_y,
                            int(SIGNATURE.width() * k),
                            int(SIGNATURE.height() * k))

    def eventFilter(self, obj, ev):
        if obj is not self.canvas:
            return False
        if ev.type() == QtCore.QEvent.MouseMove:
            over = self._sig_rect().contains(ev.pos())
            self.canvas.setCursor(QtCore.Qt.PointingHandCursor if over
                                  else QtCore.Qt.ArrowCursor)
            return False
        if ev.type() == QtCore.QEvent.MouseButtonRelease:
            if self._sig_rect().contains(ev.pos()):
                self.signature_clicked.emit()
            self.accept()
            return True
        return False

    def mouseReleaseEvent(self, _ev):
        self.accept()

    def keyPressEvent(self, _ev):
        self.accept()
