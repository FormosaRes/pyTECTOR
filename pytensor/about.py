# -*- coding: utf-8 -*-
"""About box.

Two jobs. Credit the method and its author properly, and make the provenance of
1991 mode's French visible rather than buried in a source comment: which words
are Angelier's own, taken from the program's output files, and which ones this
program made up.
"""
from PyQt5 import QtCore, QtGui, QtWidgets

from . import __version__, retro, splash

CREDIT = """\
pyTENSOR {ver}

A Python reconstruction of TENSOR 5.45 (jan91) by Jacques Angelier,
Tectonique Quantitative, Universite Pierre et Marie Curie, Paris.

Written from the published method, not by disassembling the original
16-bit DOS binary. Every drawing constant was measured off the HPGL
plot files the original program wrote.

  Angelier, J. (1990) Inversion of field data in fault tectonics to
    obtain the regional stress - III. A new rapid direct inversion
    method by analytical means. Geophys. J. Int. 103, 363-376.
  Angelier, J. (1984) Tectonic analysis of fault slip data sets.
    J. Geophys. Res. 89(B7), 5835-5848.
  Angelier, J. (1994) Fault slip analysis and palaeostress
    reconstruction. In: Hancock (ed.) Continental Deformation, ch. 4.

The opening drawing is Angelier's own block diagram of the Taiwan
arc-continent collision. He used earthquake focal mechanisms from
near Yuli as the worked example of applying this method to
seismological data (1994, fig. 4.44).
"""

NOTE = """\
1991 mode puts the interface into French. That is not a costume: the
program's own output files are French with English added afterwards.

    ++++  CALCUL DU  TENSEUR DES CONTRAINTES  ++++
    ++++    DETERMINATION OF STRESS TENSOR    ++++
     NUMERO  POIDS ...
           MOYENNE/MEAN
           ECART-/S.DEV

and the programs in the suite are MESURE, DESSIN, DIAGRA, VISION,
TRADUC. Words below marked ORIGINAL come from those files. The rest
had no counterpart in the archive and were translated here.
"""


class About(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(About, self).__init__(parent)
        self.setWindowTitle('About pyTENSOR')
        self.resize(720, 620)
        lay = QtWidgets.QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 12)
        lay.setSpacing(8)

        p = splash.image_path()
        if p:
            pm = QtGui.QPixmap(p)
            if not pm.isNull():
                lab = QtWidgets.QLabel()
                lab.setPixmap(pm.scaledToWidth(
                    360, QtCore.Qt.SmoothTransformation))
                lab.setAlignment(QtCore.Qt.AlignCenter)
                lay.addWidget(lab)

        tabs = QtWidgets.QTabWidget()

        credit = QtWidgets.QPlainTextEdit(CREDIT.format(ver=__version__))
        credit.setReadOnly(True)
        credit.setObjectName('report')
        tabs.addTab(credit, 'Credit')

        vocab = QtWidgets.QPlainTextEdit(self._vocab_text())
        vocab.setReadOnly(True)
        vocab.setObjectName('report')
        vocab.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        tabs.addTab(vocab, '1991 mode')

        lay.addWidget(tabs, 1)

        row = QtWidgets.QHBoxLayout()
        row.addStretch(1)
        b = QtWidgets.QPushButton('Close')
        b.clicked.connect(self.accept)
        row.addWidget(b)
        lay.addLayout(row)

    @staticmethod
    def _vocab_text():
        orig, added = retro.provenance()
        out = [NOTE, '']
        out.append("ANGELIER'S OWN WORDS  (%d)" % len(orig))
        for en, fr, note in orig:
            out.append('   %-18s %-26s %s' % (en, fr, note))
        out.append('')
        out.append('TRANSLATED HERE  (%d)' % len(added))
        for en, fr, note in added:
            out.append('   %-18s %-26s %s' % (en, fr, note))
        out.append('')
        out.append('Result strip: AXIS SIGMA -> AXE SIGMA, RATIO PHI ->')
        out.append('RAPPORT PHI. Both come straight from INFO1.')
        return '\n'.join(out)
