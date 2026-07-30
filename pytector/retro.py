# -*- coding: utf-8 -*-
"""1991 mode: the program as it would have looked and read when it was written.

Two things change.

**The palette.** Turbo Pascal blue. Not an arbitrary retro choice: the original
Tensor.exe is a 16-bit MS-DOS binary that looks like Turbo Pascal output, with
overlays, so this is roughly what its author was looking at while writing it.

**The language.** French. Also not invented: the program's own output files are
French with English added afterwards.

    ++++  CALCUL DU  TENSEUR DES CONTRAINTES  ++++
    ++++    DETERMINATION OF STRESS TENSOR    ++++
     NUMERO  POIDS ...
           MOYENNE/MEAN
           ECART-/S.DEV
     APPLICATIONS ET AUTRES METHODES

and the programs in the suite are MESURE, DESSIN, DIAGRA, VISION, TRADUC.
Words marked ORIGINAL below are lifted from those files. The rest had no
counterpart in the archive and are translated here; they are marked ADDED so
nobody mistakes them for Angelier's own wording.
"""

# Turbo Pascal / Borland IDE, as close as a stylesheet gets
DESK = '#0000A8'        # the blue desktop
PANEL = '#A8A8A8'       # dialog grey
INK = '#000000'
HILITE = '#FFFF54'      # yellow
CYAN = '#00A8A8'
WHITE = '#FFFFFF'
SHADOW = '#545454'

#: A stack, not one name: a missing family is silently substituted by Qt,
#: and the substitute is proportional, which breaks the console look this
#: mode exists for. Windows face first; the rest are macOS and Linux.
MONO = ('"Consolas", "SF Mono", "Menlo", "DejaVu Sans Mono", '
        '"Courier New", monospace')       # a bitmap console face

#: the stereogram goes phosphor green on black, like the monitor it would have
#: been drawn on before it reached the plotter
PLOT_PEN = '#3BF23B'
PLOT_PAPER = '#000000'
#: a touch heavier with antialiasing off, so the stair steps are legible
PLOT_STROKE = 1.2

#: label -> (French, provenance)
VOCAB = {
    'SITE': ('SITE', 'ORIGINAL'),
    'NEW RECORD': ('NOUVELLE MESURE', 'ADDED, after the program MESURE'),
    'FAULT SLIPS': ('GLISSEMENTS DE FAILLES', 'ADDED, "failles" is ORIGINAL'),
    'BACK-TILT': ('BASCULEMENT', 'ADDED'),
    'RUNS FOUND': ('SITES TROUVES', 'ADDED'),
    'INVERT': ('CALCULER', 'ADDED, cf. CALCUL DU TENSEUR DES CONTRAINTES'),
    'Results': ('RESULTATS', 'ADDED'),
    'Open site': ('OUVRIR', 'ADDED'),
    'Scan folder': ('EXPLORER', 'ADDED'),
    'Clear': ('EFFACER', 'ADDED'),
    'Delete': ('SUPPRIMER', 'ADDED'),
    'Save PNG': ('DESSIN PNG', 'DESSIN is ORIGINAL, the plotting program'),
    'Save HPGL': ('DESSIN HPGL', 'DESSIN is ORIGINAL'),
    'Save INFO1': ('INFO1', 'ORIGINAL'),
    'Save MOHR1': ('MOHR1', 'ORIGINAL'),
    'Fitted shear': ('CISAILLEMENT CALCULE', 'ADDED'),
    'archive LAMBDA': ('LAMBDA ARCHIVE', 'LAMBDA is ORIGINAL'),
    'observed': ('MESURE', 'ORIGINAL, the data-entry program'),
    'off': ('AUCUN', 'ADDED'),
}

#: result-strip wording
AXIS = 'AXE SIGMA'          # ORIGINAL had AXIS SIGMA; AXE is the French
RATIO = 'RAPPORT PHI'       # ORIGINAL: RATIO PHI
MEAN = 'MOYENNE'            # ORIGINAL
SDEV = 'ECART-TYPE'         # ORIGINAL prints ECART-
WEIGHT = 'POIDS'            # ORIGINAL
NUMBER = 'NUMERO'           # ORIGINAL

TITLE = 'pyTECTOR  —  CALCUL DU TENSEUR DES CONTRAINTES'

QSS = """
QMainWindow, QWidget {{
    background: {DESK};
    color: {WHITE};
    font-family: {MONO};
    font-size: 13px;
}}
/* A background on QWidget cascades into every QLabel, QCheckBox and
   QToolButton, so each one ends up carrying a blue rectangle. On the light
   theme that was invisible because it matched the panels; here it turns the
   text unreadable. Everything that only needs to paint text is forced
   transparent. */
QLabel, QCheckBox, QToolButton {{ background: transparent; }}

QToolBar {{
    background: {PANEL};
    border: 0;
    border-bottom: 2px solid {SHADOW};
    padding: 3px 6px;
    spacing: 2px;
}}
QToolBar QToolButton {{
    background: transparent;
    color: {INK};
    padding: 3px 9px;
    border: 0;
}}
QToolBar QToolButton:hover {{ background: {CYAN}; color: {INK}; }}
QToolBar QToolButton:disabled {{ color: {SHADOW}; }}
QToolBar QCheckBox {{ background: transparent; color: {INK}; }}
QToolBar QLabel {{ background: transparent; color: {INK}; }}
QToolBar::separator {{ background: {SHADOW}; width: 2px; margin: 3px 5px; }}

QPushButton#run {{
    background: {CYAN};
    color: {INK};
    border: 0;
    padding: 4px 16px;
    font-weight: 600;
}}
QPushButton#run:hover {{ background: {HILITE}; }}
QPushButton#run:disabled {{ background: {SHADOW}; color: {PANEL}; }}
QPushButton {{
    background: {PANEL}; color: {INK}; border: 0; padding: 3px 10px;
}}
QPushButton:hover {{ background: {CYAN}; }}

/* Dialogs are blue with a white border, so everything on them reads in white
   or yellow. Grey panels with black text would need a second set of label
   colours for the sidebar, which sits on blue. */
/* No border here: a stylesheet cannot draw a double line, so Panel paints the
   two nested rectangles itself. */
QFrame#panel {{
    background: {DESK};
    border: 0;
    border-radius: 0;
}}
QFrame#plotpanel {{
    background: {INK};
    border: 0;
    border-radius: 0;
}}

QLabel {{ color: {WHITE}; }}
QLabel#heading {{
    color: {HILITE};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0;
}}
QLabel#value, QLabel#axis {{
    color: {HILITE};
    font-family: {MONO};
    font-size: 16px;
}}
QLabel#secondary {{ color: {CYAN}; font-size: 11px; }}
QLabel#legend, QLabel#count {{ color: {CYAN}; font-size: 11px; }}
QLabel#state {{
    color: {INK}; background: {HILITE};
    font-family: {MONO}; font-size: 11px; font-weight: 600;
    padding: 2px 8px; border: 0;
}}
QLabel#context {{
    color: {WHITE}; font-family: {MONO}; font-size: 12px;
    font-weight: 600; padding: 2px 4px;
}}
QLabel#stale {{
    color: {WHITE}; background: #A80000;
    font-family: {MONO}; font-size: 11px; font-weight: 600;
    padding: 2px 8px; border: 0;
}}
QLabel#sitename {{ color: {HILITE}; }}

QLineEdit {{
    background: {INK}; color: {HILITE}; border: 1px solid {SHADOW};
    border-radius: 0; padding: 2px 4px;
    selection-background-color: {CYAN}; selection-color: {INK};
}}
QLineEdit:focus {{ border: 1px solid {HILITE}; }}
QLineEdit#seg {{ font-family: {MONO}; font-size: 15px; }}
/* Disabled fields were yellow-on-black turning to near-black-on-black. Grey on
   grey reads as switched off while staying legible, which is what a DOS
   dialog did with an inactive control. */
QLineEdit:disabled {{
    background: {SHADOW}; color: {PANEL}; border: 1px solid {SHADOW};
}}
QComboBox:disabled, QSpinBox:disabled {{
    background: {SHADOW}; color: {PANEL};
}}

QComboBox, QSpinBox {{
    background: {PANEL}; color: {INK}; border: 0;
    border-radius: 0; padding: 2px 4px;
}}
QCheckBox {{ color: {INK}; spacing: 4px; padding: 2px; }}
QToolBar QCheckBox {{ color: {INK}; }}

QTableWidget, QListWidget {{
    background: {INK}; color: {CYAN}; border: 1px solid {SHADOW};
    border-radius: 0; gridline-color: {SHADOW};
    font-family: {MONO}; font-size: 12px;
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background: {CYAN}; color: {INK};
}}
QHeaderView::section {{
    background: {PANEL}; color: {INK}; border: 0;
    border-bottom: 1px solid {SHADOW}; padding: 2px 4px; font-size: 11px;
}}

QTabWidget::pane {{
    background: {PANEL}; border: 2px solid {WHITE}; border-radius: 0; top: -1px;
}}
QTabBar::tab {{
    background: {SHADOW}; color: {WHITE}; border: 0;
    padding: 5px 18px; min-width: 72px;
}}
QTabBar::tab:selected {{ background: {PANEL}; color: {INK}; }}

QPlainTextEdit {{ background: {INK}; color: {CYAN}; border: 0; }}
QPlainTextEdit#report {{
    font-family: {MONO}; font-size: 13px; padding: 6px 10px;
    color: {HILITE};
}}

QStatusBar {{ background: {PANEL}; color: {INK}; border: 0; }}
QProgressBar {{
    background: {INK}; border: 1px solid {SHADOW}; border-radius: 0; height: 6px;
}}
QProgressBar::chunk {{ background: {HILITE}; border-radius: 0; }}
QSplitter::handle {{ background: {DESK}; }}
QScrollBar:vertical {{ background: {SHADOW}; width: 12px; border: 0; }}
QScrollBar::handle:vertical {{ background: {PANEL}; border-radius: 0; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{ background: {HILITE}; color: {INK}; border: 1px solid {INK};
            padding: 3px 6px; }}
""".format(DESK=DESK, PANEL=PANEL, INK=INK, HILITE=HILITE, CYAN=CYAN,
           WHITE=WHITE, SHADOW=SHADOW, MONO=MONO)


def translate(text):
    """French for a label, or the text unchanged when there is no entry."""
    hit = VOCAB.get(text)
    return hit[0] if hit else text


def provenance():
    """Which words are Angelier's and which are ours. Used by the About box so
    the distinction is visible rather than buried in a comment."""
    orig, added = [], []
    for en, (fr, note) in sorted(VOCAB.items()):
        (orig if note.startswith('ORIGINAL') else added).append((en, fr, note))
    return orig, added
