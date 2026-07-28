# -*- coding: utf-8 -*-
"""Stylesheet for the pyTENSOR desktop app.

Deliberately neutral: the stereograms are pure black and white in Angelier's
own style, so the interface stays out of their way. This is NOT the pyADR
chart palette (seaborn darkgrid / lavender); that belongs to Argon Pipeline
diagrams and must not leak in here.

House rules carried over from the pyADR UI work:
  * sidebar packs tight, spacing 3, no big gaps between groups
  * key numbers go full size on their own line; only secondary statistics
    (n, S4) are allowed to be small and grey
  * section headings carry no explanatory subtitle
  * QTabBar selected never gets font-weight bold (Qt clips the tab)
  * QFrame borders are scoped by objectName so nothing cascades
"""

INK = '#1E1E1C'
MUTED = '#7A776F'
FAINT = '#A9A59C'
BG = '#F6F5F2'
PANEL = '#FFFFFF'
LINE = '#DCD8D0'
ACCENT = '#23324A'
ACCENT_HI = '#31465F'
WARN = '#8A5A00'

FONT = 'Segoe UI'
MONO = 'Consolas'

QSS = """
QMainWindow, QWidget {{
    background: {BG};
    color: {INK};
    font-family: "{FONT}";
    font-size: 12px;
}}

QToolBar {{
    background: {PANEL};
    border: 0;
    border-bottom: 1px solid {LINE};
    padding: 5px 8px;
    spacing: 3px;
}}
QToolBar QToolButton {{
    padding: 5px 11px;
    border: 1px solid transparent;
    border-radius: 4px;
    color: {INK};
}}
QToolBar QToolButton:hover {{
    background: {BG};
    border: 1px solid {LINE};
}}
QToolBar QToolButton:pressed {{ background: {LINE}; }}
QToolBar QToolButton:disabled {{ color: {FAINT}; }}
QToolBar::separator {{
    background: {LINE};
    width: 1px;
    margin: 4px 7px;
}}

QPushButton#run {{
    background: {ACCENT};
    color: #FFFFFF;
    border: 0;
    border-radius: 4px;
    padding: 6px 20px;
    font-weight: 600;
}}
QPushButton#run:hover {{ background: {ACCENT_HI}; }}
QPushButton#run:disabled {{ background: {FAINT}; color: {PANEL}; }}

QPushButton {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
    padding: 5px 12px;
}}
QPushButton:hover {{ background: {BG}; }}
QPushButton:pressed {{ background: {LINE}; }}
QPushButton:disabled {{ color: {FAINT}; }}

QFrame#panel {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 5px;
}}
QFrame#plotpanel {{
    background: #FFFFFF;
    border: 1px solid {LINE};
    border-radius: 5px;
}}

QLabel#heading {{
    color: {MUTED};
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 1.1px;
    padding: 0 0 1px 1px;
}}
QLabel#value {{
    color: {INK};
    font-family: "{MONO}";
    font-size: 17px;
}}
QLabel#axis {{
    color: {INK};
    font-family: "{MONO}";
    font-size: 16px;
}}
QLabel#secondary {{
    color: {MUTED};
    font-family: "{MONO}";
    font-size: 11px;
}}
QLabel#legend {{ color: {MUTED}; font-size: 11px; }}
QLabel#count {{ color: {MUTED}; font-size: 11px; }}
QLabel#sitename {{ font-size: 15px; font-weight: 600; }}
QLabel#warn {{ color: {WARN}; font-size: 11px; }}

QLineEdit {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
    padding: 4px 6px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QLineEdit#seg {{
    font-family: "{MONO}";
    font-size: 15px;
    padding: 5px 2px;
}}

QTableWidget {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
    gridline-color: {BG};
    font-family: "{MONO}";
    font-size: 11px;
}}
QTableWidget::item {{ padding: 2px 4px; }}
QTableWidget::item:selected {{ background: {ACCENT}; color: #FFFFFF; }}
QHeaderView::section {{
    background: {BG};
    border: 0;
    border-bottom: 1px solid {LINE};
    padding: 4px 5px;
    color: {MUTED};
    font-size: 10px;
    font-weight: 600;
}}

QListWidget {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
    font-size: 11px;
}}
QListWidget::item {{ padding: 3px 5px; }}
QListWidget::item:selected {{ background: {ACCENT}; color: #FFFFFF; }}

QCheckBox {{ spacing: 5px; padding: 2px 4px; }}
QSpinBox {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 4px;
    padding: 3px 4px;
    min-width: 42px;
}}

QSplitter::handle {{ background: {LINE}; }}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical {{ height: 1px; }}

/* Tabs: generous hit area, and never bold on the selected tab. Qt does not
   re-measure the tab when the weight changes, so bold clips the label. */
QTabWidget::pane {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-radius: 5px;
    top: -1px;
}}
QTabBar::tab {{
    background: transparent;
    border: 1px solid transparent;
    border-bottom: 0;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 7px 18px;
    min-width: 72px;
    color: {MUTED};
}}
QTabBar::tab:hover {{ color: {INK}; }}
QTabBar::tab:selected {{
    background: {PANEL};
    border: 1px solid {LINE};
    border-bottom: 1px solid {PANEL};
    color: {INK};
}}

QPlainTextEdit {{
    background: {PANEL};
    border: 0;
    color: {INK};
    selection-background-color: {ACCENT};
}}
/* The report boxes must be monospace or the columns do not line up. A
   stylesheet beats a programmatic setFont, so the family has to be set HERE:
   the global "QMainWindow, QWidget" rule above would otherwise win and
   silently render the fixed-width tables in a proportional face. */
QPlainTextEdit#report {{
    font-family: "{MONO}", "Courier New", monospace;
    font-size: 12px;
    padding: 8px 12px;
}}

QStatusBar {{
    background: {PANEL};
    border-top: 1px solid {LINE};
    color: {MUTED};
}}
QStatusBar::item {{ border: 0; }}

QProgressBar {{
    background: {BG};
    border: 1px solid {LINE};
    border-radius: 3px;
    height: 5px;
    text-align: center;
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}

QScrollBar:vertical {{
    background: {BG}; width: 10px; margin: 0; border: 0;
}}
QScrollBar::handle:vertical {{
    background: {LINE}; border-radius: 5px; min-height: 24px;
}}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QToolTip {{
    background: {INK}; color: #FFFFFF; border: 0;
    padding: 4px 7px; border-radius: 3px;
}}
""".format(BG=BG, INK=INK, MUTED=MUTED, FAINT=FAINT, PANEL=PANEL, LINE=LINE,
           ACCENT=ACCENT, ACCENT_HI=ACCENT_HI, WARN=WARN, FONT=FONT, MONO=MONO)
