# -*- coding: utf-8 -*-
"""About box.

Four jobs, one per tab.

Credit the method and its author properly. Say what the program does and, more
usefully, what it does NOT claim: the criterion is biased, so neither run is
"the true stress", and INVDIR is not rotation equivariant, so a change across a
back-tilt is partly the parametrisation. Both belong somewhere a user will
actually meet them rather than only in a README.

Record how the drawing style and the file format were established, because
"measured off the plotter files" is the difference between this and a guess.

And make the provenance of 1991 mode's French visible: which words are
Angelier's own, taken from the program's output files, and which this program
made up.
"""
from PyQt5 import QtCore, QtGui, QtWidgets

from . import __version__, retro, splash

CREDIT = """\
pyTECTOR {ver}

A Python reconstruction of TENSOR 5.45 (jan91) by Jacques Angelier,
Tectonique Quantitative, Universite Pierre et Marie Curie, Paris.

Written from the published method, not by disassembling the original
16-bit DOS binary. No code was taken from it. Everything the papers
do not state was measured off the files the original program wrote.

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

Maintainer  Chi-Hsiu Pang
Repository  github.com/FormosaRes/pyTECTOR
Licence     MIT. The method is Angelier's; the opening drawing is his
            published figure and is not distributed with the code.

Requires numpy, scipy, matplotlib, PyQt5.
"""

METHOD = """\
THE CRITERION

  sigma = T n                                          eq 3
  tau   = sigma - (n.sigma) n                          eq 4-5
  upsilon^2 = lambda^2 + |tau|^2 - 2 lambda (s.sigma)   eq A1
  minimise  S4 = sum upsilon^2                         eq 13

  RUP = 100 |upsilon| / (sqrt(3)/2),  0 to 200 per cent
  ANG = angle between s and tau,      0 to 180 degrees

The tensor is normalised so the SUM OF SQUARED EIGENVALUES is 3/2
(eq A16), not so that sigma1 - sigma3 is fixed. The two agree only
at Phi = 0.5, and the criterion is not scale invariant, so the
difference changes the answer.


WHAT THIS PROGRAM DOES NOT CLAIM

1. Neither run is "the true stress".

   upsilon asks for two things at once: that the predicted shear
   points along the observed slip, AND that its magnitude is near
   lambda. Fed perfect Bott data with no noise at all it still
   misses the true tensor by about 4 degrees, because it favours
   orientations that load the faults heavily. An angle-only
   criterion recovers the same data to 0.00 degrees.

   So INVDIR is an approximate solution of a biased criterion and
   S4MIN is the exact solution of the same biased criterion. This
   is also why TectonicsFP and similar programs disagree with
   Angelier's numbers: it is not a bug in either.

2. INVDIR is not rotation equivariant. S4MIN is.

   S4 is rotation invariant, so its exact minimum turns with the
   data: back-tilting cannot change S4MIN's Phi or S4, and the
   whole content of a tilt test is where the axes end up.

   INVDIR does not behave that way. Equation (14) pins the tensor
   DIAGONAL to cos(psi), cos(psi + 2pi/3), cos(psi + 4pi/3) in the
   GEOGRAPHIC frame, and that four-parameter family is a different
   family once the data are turned.

   Measured on the original program itself, over the fourteen
   back-tilt pairs in the reference archive:

       carried through the rotation   vs   re-inverted
         sigma1   median 10.4 deg,  max 66.4
         sigma2   median 24.3 deg,  max 88.7
         sigma3   median 23.6 deg,  max 87.5

   The largest values sit where Phi is near 0 or 1 and two axes are
   near degenerate, but not all of them: site 0214-5, thirteen
   faults, Phi 0.46 to 0.72, still moves sigma1 by 19.8 degrees.

   In practice: read the Andersonian test off S4MIN, where the axes
   provably only rotate, and keep INVDIR for continuity with the
   older runs. The back-tilt window prints both and the separation
   between them.

3. Restoring a surface to horizontal is not automatically right.

   That assumes the faults predate the tilting. If they moved
   during it, full restoration over-rotates them into a tensor that
   never existed. Use the tilt test.


REPRODUCING A SPECIFIC HISTORICAL RUN

Tick "archive LAMBDA". lambda is re-derived from scratch by
default, and where the pass-1 surface is nearly flat that can land
a degree away with a WORSE fit than the original. Adopting the
LAMBDA the site's own INFO1 records puts the run back on the branch
the original was on: on L12 that is 1.02 degrees off and S4 +0.0137
against 0.31 degrees off and S4 -0.0028.
"""

SOURCES = """\
HOW THE DRAWING STYLE WAS ESTABLISHED

Every run folder holds an HPGL file: plain-text plotter vector
commands. It is not a description of what the program drew, it IS
what the program drew, stroke by stroke. So none of the style below
was inferred from figure captions.

  projection   EQUAL AREA (Schmidt). Decided by test, not by
               assumption: a great circle is a true circular arc
               under stereographic and is not under equal area.
               Circle-fit residuals 0.0044 / 0.0062 / 0.0010
               against an equal-area prediction of 0.0040 / 0.0055
               / 0.0007. Stereographic would give zero.

  stars        sigma1 five-pointed, sigma2 four-pointed and set
               diagonally, sigma3 three-pointed. Size is NOT
               constant:
                   size = 0.1004 + 0.0928 (0.5 - Phi) lambda_i
               fitted over 63 stars on 21 plots, rms 0.00063. At
               Phi = 0.5 all three are equal, so the size order
               flips either side of it.

  striae       a SHEAR COUPLE, not one arrow: a filled dot with two
               parallel shafts, each offset 0.024 to its own side,
               so the symbol reads as a Z. Heads follow the
               confidence code: S none, P one barb per end, C a
               two-segment slender head. Which side the offset and
               barbs sit is sign(slip . strike), right on all 89
               samples; reading it off the movement letter is right
               on only 83.

  arrows       outside the circle, inward along sigma1 and outward
               along sigma3, omitted for an axis plunging over 45.

  frame        NOT symmetric about the centre of the stereogram.
               All 93 archive files: x -1.2527 to 1.2547, y -1.3047
               to 1.4585 in units of the primitive radius, captions
               left aligned at fixed columns.

HPGL export replays the same drawing code that draws the screen,
into a recorder standing in for a matplotlib Axes, so the file
carries exactly what the figure carries.


THE FILE FORMAT

Decoded by cross-checking the data file, MOHR1, INFO1 and
Mesure_key.txt; verified on 35 records from two sites.

  [0:2]    first digit  striae confidence, 1=C 2=P 3=S
           second digit which end of the strike line the rake was
                        measured from
  [2:5]    TRUE dip azimuth, quadrant letter already resolved
  [5:7]    dip
  [7:10]   RAKE, from the strike end at (dip azimuth - 90)
  [47:61]  echo of what was typed

  The movement direction is RAKE + 180. Using the stored value
  directly swaps sigma1 and sigma3.

  On a site where every plane dips 85-89 degrees, sin(plunge) =
  sin(rake) sin(dip) makes rake and plunge agree within a degree,
  so [7:10] looks like a plunge. It is not.

  The 03 result line is fixed width, trend 5 characters and plunge
  4, with no separators. Splitting it on whitespace gives garbage.
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

The palette is Turbo Pascal blue, which is not an arbitrary retro
choice either: Tensor.exe is a 16-bit MS-DOS binary that looks like
Turbo Pascal output, with overlays, so that is roughly what its
author was looking at while writing it.

Nothing about the inversion changes in 1991 mode.
"""


class About(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(About, self).__init__(parent)
        self.setWindowTitle('About pyTECTOR')
        self.resize(760, 680)
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
        for text, title, wrap in (
                (CREDIT.format(ver=__version__), 'Credit', True),
                (METHOD, 'Method and its limits', False),
                (SOURCES, 'How it was established', False),
                (self._vocab_text(), '1991 mode', False)):
            box = QtWidgets.QPlainTextEdit(text)
            box.setReadOnly(True)
            box.setObjectName('report')
            if not wrap:
                box.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
            tabs.addTab(box, title)
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
