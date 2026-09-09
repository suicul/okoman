"""Main window — sidebar navigation with stacked widget."""

from __future__ import annotations

import os
from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtGui import QIcon, QFont, QPixmap, QPainter, QColor
from PyQt5.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QSizePolicy,
    QSpacerItem,
)

from .. import __version__
from ..core.serial_worker import SerialWorker
from .connection_panel import ConnectionPanel
from .dashboard import Dashboard
from .diagnostics import Diagnostics
from .configuration import Configuration
from .calibration import Calibration
from .terminal import Terminal
from .live_monitor import LiveMonitor
from .toast import ToastNotifier


def _make_icon(char: str, color: str = "#8b949e") -> QIcon:
    """Create a simple text-based icon."""
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setPen(QColor(color))
    font = QFont("Segoe UI", 14, QFont.Bold)
    painter.setFont(font)
    painter.drawText(pixmap.rect(), Qt.AlignCenter, char)
    painter.end()
    return QIcon(pixmap)


class MainWindow(QMainWindow):
    """Main application window with sidebar and stacked pages."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("mainWindow")
        self.setWindowTitle("ОКО — Управление БОД v{}".format(__version__))
        # 860×560 — влезает в нетбучные 1024×600 полевых ноутбуков.
        self.setMinimumSize(860, 560)
        self.resize(1100, 700)

        self._worker = SerialWorker(self)
        self._current_page = 0
        self._dash = None
        self._config = None
        self._toast = ToastNotifier(self)

        # Load application icon
        self._icon = self._load_icon()
        if self._icon:
            self.setWindowIcon(self._icon)

        self._setup_ui()
        self._connect_pages()

    def _load_icon(self) -> QIcon:
        """Load application icon from resources."""
        # Try multiple fallback paths for icon
        candidates = [
            # Relative to this file (oko_app/ui/main_window.py)
            os.path.join(os.path.dirname(__file__), "..", "resources", "icon.png"),
            # Relative to project root
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "oko_icon.png"),
            # Relative to resources directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                         "oko_app", "resources", "icon.png"),
        ]
        
        for icon_path in candidates:
            icon_path = os.path.normpath(icon_path)
            if os.path.exists(icon_path):
                icon = QIcon(icon_path)
                if not icon.isNull():
                    return icon
        
        return QIcon()

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── Sidebar ──────────────────────────────────────────────────────────
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(208)
        sidebar.setMaximumWidth(208)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(12, 16, 12, 16)
        sidebar_layout.setSpacing(0)

        # Logo / Title - vertical layout for better appearance
        logo_card = QWidget()
        logo_card.setMinimumWidth(176)
        logo_card.setMaximumWidth(208)
        logo_layout = QVBoxLayout(logo_card)
        logo_layout.setContentsMargins(0, 12, 0, 12)
        logo_layout.setSpacing(4)
        logo_layout.setAlignment(Qt.AlignCenter)

        logo_card.setToolTip("ОКО БОД Manager")

        # App icon - use oko_icon.png from project root
        icon_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "oko_icon.png"
        )
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            if not icon.isNull():
                pixmap = icon.pixmap(80, 80)
                if not pixmap.isNull():
                    logo_label = QLabel()
                    logo_label.setObjectName("appLogo")
                    logo_label.setAccessibleName("Логотип ОКО БОД Manager")
                    logo_label.setToolTip("ОКО БОД Manager")
                    logo_label.setPixmap(pixmap.scaled(80, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                    logo_label.setFixedSize(80, 80)
                    logo_label.setAlignment(Qt.AlignCenter)
                    logo_layout.addWidget(logo_label)

        title = QLabel("ОКО")
        title.setObjectName("sidebarTitle")
        title.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(title)

        subtitle = QLabel("БОД Manager")
        subtitle.setObjectName("sidebarSubtitle")
        subtitle.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(subtitle)

        sidebar_layout.addWidget(logo_card)
        
        # Spacer after logo
        spacer = QSpacerItem(0, 20, QSizePolicy.Minimum, QSizePolicy.Expanding)
        sidebar_layout.addItem(spacer)

        # Connection panel inside sidebar
        conn_widget = QWidget()
        conn_layout = QVBoxLayout(conn_widget)
        conn_layout.setContentsMargins(0, 0, 0, 0)
        conn_layout.setSpacing(8)
        self._conn_panel = ConnectionPanel(self._worker)
        conn_layout.addWidget(self._conn_panel)
        sidebar_layout.addWidget(conn_widget)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("background-color: #30363d; max-height: 1px; margin: 12px 0;")
        sidebar_layout.addWidget(sep)

        # Navigation buttons
        self._nav_buttons = []
        pages = [
            ("01", "Обзор"),
            ("02", "Диагностика"),
            ("03", "Конфигурация"),
            ("04", "Калибровка"),
            ("05", "Мониторинг"),
            ("06", "Терминал"),
        ]

        for i, (icon_text, label) in enumerate(pages):
            btn = QPushButton("{}  {}".format(icon_text, label))
            btn.setObjectName("navBtn")
            btn.setMinimumHeight(40)
            btn.setToolTip(label)
            btn.setAccessibleName(label)
            btn.setCheckable(True)
            btn.clicked.connect(lambda _, idx=i: self._switch_page(idx))
            sidebar_layout.addWidget(btn)
            self._nav_buttons.append(btn)

        sidebar_layout.addStretch()

        # Author and version at bottom
        footer_card = QWidget()
        footer_layout = QVBoxLayout(footer_card)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        footer_layout.setSpacing(4)
        footer_layout.setAlignment(Qt.AlignCenter)

        author_label = QLabel("\u00a9 Гореловский И.А.")
        author_label.setObjectName("labelSecondary")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("color: #a0aab4; font-size: 11px; padding: 4px;")
        footer_layout.addWidget(author_label)

        version_label = QLabel("v{}".format(__version__))
        version_label.setObjectName("labelSecondary")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #a0aab4; font-size: 11px; padding: 4px;")
        footer_layout.addWidget(version_label)

        sidebar_layout.addWidget(footer_card)

        root_layout.addWidget(sidebar)

        # ── Content area ─────────────────────────────────────────────────────
        self._stack = QStackedWidget()
        self._dash = Dashboard(self._worker)
        self._config = Configuration(self._worker)
        self._stack.addWidget(self._dash)
        self._stack.addWidget(Diagnostics(self._worker))
        self._stack.addWidget(self._config)
        self._stack.addWidget(Calibration(self._worker))
        self._stack.addWidget(LiveMonitor(self._worker))
        self._stack.addWidget(Terminal(self._worker))

        root_layout.addWidget(self._stack, stretch=1)

        # Set initial page
        self._switch_page(0)
        
        # Connect toast after all pages are created
        self._connect_toast()

    def _switch_page(self, index: int) -> None:
        """Switch the stacked widget page and update sidebar state."""
        self._current_page = index
        self._stack.setCurrentIndex(index)

        for i, btn in enumerate(self._nav_buttons):
            is_active = i == index
            btn.setProperty("active", is_active)
            btn.setDown(is_active)
            # Force style refresh
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def _connect_pages(self) -> None:
        """Connect signals between pages for data sharing."""
        # Forward worker settings to Configuration
        self._worker.settings_data.connect(self._config.apply_settings)

    def _connect_toast(self) -> None:
        """Connect toast notification system."""
        # Override _show_toast in Configuration to emit through MainWindow
        original_show_toast = self._config._show_toast
        def wrapped_show_toast(message: str, toast_type: str = "info") -> None:
            original_show_toast(message, toast_type)
            self._show_toast(message, toast_type)
        self._config._show_toast = wrapped_show_toast

    @pyqtSlot(str, str)
    def _show_toast(self, message: str, toast_type: str = "info") -> None:
        """Wrapper for toast notification."""
        self._toast.show(message, toast_type)

    def closeEvent(self, event) -> None:
        """Clean up serial connection on close."""
        if self._worker.is_connected:
            self._worker.disconnect()
        event.accept()
