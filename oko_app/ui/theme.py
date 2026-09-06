"""Futuristic dark theme for OKO Device Manager.

Dark background with cyan/teal neon accents, subtle glows,
and rounded corners. Not overly sci-fi — professional with a tech edge.
"""

# ── Color palette ───────────────────────────────────────────────────────────
BG_PRIMARY = "#0d1117"       # Main background — very dark blue-gray
BG_SECONDARY = "#161b22"     # Panel/card background
BG_TERTIARY = "#21262d"      # Input fields, hover states
BORDER = "#30363d"           # Subtle borders
BORDER_ACCENT = "#00d4aa"    # Cyan/teal accent for focus states

TEXT_PRIMARY = "#e6edf3"     # Main text — bright white
TEXT_SECONDARY = "#a0aab4"   # Dimmed text — labels, hints (improved contrast ~5.8:1)
TEXT_ACCENT = "#00d4aa"      # Accent text — teal/cyan

ACCENT = "#00d4aa"           # Primary accent — teal
ACCENT_HOVER = "#00f0c0"     # Lighter on hover
ACCENT_DIM = "#00d4aa33"     # Accent with transparency

LED_POWER = "#ff4444"        # Red — power indicator
LED_GPS = "#ffbb33"          # Yellow — GPS/GLONASS
LED_GSM = "#4488ff"          # Blue — GSM/SIM
LED_OPTICS = "#44ff88"       # Green — optical sensors
LED_OFF = "#333333"          # Off state

DANGER = "#ff5555"
WARNING = "#ffbb33"
SUCCESS = "#44ff88"

# ── QSS Stylesheet ──────────────────────────────────────────────────────────

MAIN_STYLESHEET = f"""
/* ── Global ─────────────────────────────────────────────────────────────── */
QWidget {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    font-family: 'Segoe UI', 'SF Pro Display', 'Helvetica Neue', sans-serif;
    font-size: 13px;
}}

/* ── Main Window ────────────────────────────────────────────────────────── */
QMainWindow {{
    background-color: {BG_PRIMARY};
}}

/* ── Sidebar ────────────────────────────────────────────────────────────── */
#sidebar {{
    background-color: {BG_SECONDARY};
    border-right: 1px solid {BORDER};
    min-width: 220px;
    max-width: 300px;
}}

#sidebar QPushButton {{
    background-color: transparent;
    color: {TEXT_SECONDARY};
    border: none;
    border-left: 3px solid transparent;
    padding: 14px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}

#sidebar QPushButton:hover {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
}}

#sidebar QPushButton[active="true"] {{
    background-color: {ACCENT_DIM};
    color: {TEXT_ACCENT};
    border-left: 3px solid {ACCENT};
    font-weight: 600;
}}

#sidebarTitle {{
    color: {TEXT_ACCENT};
    font-size: 16px;
    font-weight: 700;
    padding: 20px 16px 8px 16px;
    letter-spacing: 1px;
}}

#sidebarSubtitle {{
    color: {TEXT_SECONDARY};
    font-size: 10px;
    padding: 0 16px 16px 16px;
    letter-spacing: 0.5px;
}}

/* ── Cards / Panels ────────────────────────────────────────────────────── */
#card {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 20px;
}}

#cardTitle {{
    color: {TEXT_PRIMARY};
    font-size: 16px;
    font-weight: 600;
    padding-bottom: 8px;
}}

/* ── Buttons ────────────────────────────────────────────────────────────── */
QPushButton {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 20px;
    font-weight: 500;
    min-height: 20px;
}}

QPushButton:hover {{
    background-color: {BORDER};
    border-color: {BORDER_ACCENT};
}}

QPushButton:pressed {{
    background-color: #00d4aa55;
}}

QPushButton:disabled {{
    background-color: {BG_PRIMARY};
    color: {TEXT_SECONDARY};
    border-color: {BORDER};
}}

#primaryButton {{
    background-color: {ACCENT};
    color: {BG_PRIMARY};
    border: none;
    font-weight: 600;
}}

#primaryButton:hover {{
    background-color: {ACCENT_HOVER};
}}

#dangerButton {{
    background-color: transparent;
    color: {DANGER};
    border: 1px solid {DANGER};
}}

#dangerButton:hover {{
    background-color: {DANGER};
    color: white;
}}

/* ── Inputs ─────────────────────────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    selection-background-color: {ACCENT_DIM};
    min-height: 20px;
}}

QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:on {{
    border-color: {ACCENT};
}}

QComboBox::drop-down {{
    border: none;
    width: 30px;
}}

QComboBox QAbstractItemView {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    selection-background-color: {ACCENT_DIM};
    padding: 4px;
}}

/* ── Labels ─────────────────────────────────────────────────────────────── */
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

#labelSecondary {{
    color: {TEXT_SECONDARY};
    font-size: 11px;
}}

#labelAccent {{
    color: {TEXT_ACCENT};
    font-weight: 600;
}}

/* ── Text Edit / Log ────────────────────────────────────────────────────── */
QTextEdit {{
    background-color: {BG_PRIMARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 10px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Consolas', monospace;
    font-size: 12px;
    selection-background-color: {ACCENT_DIM};
}}

/* ── Group Box ──────────────────────────────────────────────────────────── */
QGroupBox {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 10px;
    margin-top: 14px;
    padding: 16px 12px 12px 12px;
    font-weight: 600;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 10px;
    color: {TEXT_ACCENT};
}}

/* ── Scroll Bar ─────────────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
    min-height: 30px;
}}

QScrollBar::handle:vertical:hover {{
    background: {ACCENT};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 8px;
}}

QScrollBar::handle:horizontal {{
    background: {BORDER};
    border-radius: 4px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {ACCENT};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ── Tab Widget ─────────────────────────────────────────────────────────── */
QTabWidget::pane {{
    background-color: {BG_SECONDARY};
    border: 1px solid {BORDER};
    border-radius: 8px;
}}

QTabBar::tab {{
    background-color: {BG_TERTIARY};
    color: {TEXT_SECONDARY};
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 8px 16px;
    margin-right: 2px;
}}

QTabBar::tab:selected {{
    background-color: {BG_SECONDARY};
    color: {TEXT_ACCENT};
    border-color: {ACCENT};
    border-bottom-color: {BG_SECONDARY};
}}

QTabBar::tab:hover {{
    color: {TEXT_PRIMARY};
}}

/* ── Splitter ───────────────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {BORDER};
    width: 1px;
}}

/* ── Status Indicator ───────────────────────────────────────────────────── */
#statusDot {{
    border-radius: 6px;
    min-width: 12px;
    max-width: 12px;
    min-height: 12px;
    max-height: 12px;
}}

#statusConnected {{
    background-color: {SUCCESS};
    border: 2px solid {SUCCESS};
}}

#statusDisconnected {{
    background-color: {DANGER};
    border: 2px solid {DANGER};
}}

/* ── LED Indicator ──────────────────────────────────────────────────────── */
#ledIndicator {{
    border-radius: 10px;
    min-width: 20px;
    max-width: 20px;
    min-height: 20px;
    max-height: 20px;
    border: 2px solid rgba(255,255,255,0.1);
}}

/* ── Tooltips ───────────────────────────────────────────────────────────── */
QToolTip {{
    background-color: {BG_TERTIARY};
    color: {TEXT_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 6px 10px;
    font-size: 12px;
}}

/* ── Progress Bar ───────────────────────────────────────────────────────── */
QProgressBar {{
    background-color: {BG_TERTIARY};
    border: 1px solid {BORDER};
    border-radius: 6px;
    text-align: center;
    color: {TEXT_PRIMARY};
    height: 20px;
}}

QProgressBar::chunk {{
    background-color: {ACCENT};
    border-radius: 5px;
}}
"""
