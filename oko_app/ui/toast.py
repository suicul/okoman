"""Toast notification widget for OKO БОД Manager."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QPropertyAnimation, QRect
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QGraphicsOpacityEffect


class Toast(QFrame):
    """Brief notification widget that fades in/out."""

    def __init__(
        self,
        message: str,
        toast_type: str = "info",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("toast")
        self.setFixedHeight(48)
        self.setFixedWidth(400)

        # Set color based on type
        colors = {
            "success": ("#44ff88", "#0d3320"),
            "error": ("#ff5555", "#3d1515"),
            "warning": ("#ffbb33", "#3d2e0a"),
            "info": ("#4488ff", "#0a1e3d"),
        }
        text_color, bg_color = colors.get(toast_type, colors["info"])

        self.setStyleSheet(f"""
            Toast {{
                background-color: {bg_color};
                border: 1px solid {text_color};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(0)

        self._label = QLabel(message)
        self._label.setStyleSheet(
            f"color: {text_color}; font-size: 13px; font-weight: 500;"
        )
        layout.addWidget(self._label)

        # Opacity effect for fade animation
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._opacity_effect)

        self._opacity = 0.0
        self._opacity_effect.setOpacity(self._opacity)

        # Auto-hide timer
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._on_hide_timeout)

    def show_event(self, duration_ms: int = 3000) -> None:
        """Show toast with fade in/out animation."""
        self.show()

        # Fade in
        self._animate_opacity(0.0, 1.0, 200)

        # Schedule fade out
        self._hide_timer.start(duration_ms)

    @pyqtSlot()
    def _on_hide_timeout(self) -> None:
        """Fade out and hide."""
        self._animate_opacity(1.0, 0.0, 300, self.close)

    def _animate_opacity(
        self,
        from_val: float,
        to_val: float,
        duration: int,
        callback=None,
    ) -> None:
        """Animate opacity change."""
        self._animation = QPropertyAnimation(self, b"windowOpacity")
        self._animation.setStartValue(from_val)
        self._animation.setEndValue(to_val)
        self._animation.setDuration(duration)
        if callback:
            self._animation.finished.connect(callback)
        self._animation.start()


class ToastNotifier:
    """Singleton-like toast notifier for the main window."""

    def __init__(self, parent: QWidget) -> None:
        self._parent = parent
        self._current_toast: Toast | None = None
        self._toast_queue: list[dict] = []

    @pyqtSlot(str, str)
    def show(self, message: str, toast_type: str = "info") -> None:
        """Show a toast notification."""
        if self._current_toast and self._current_toast.isVisible():
            # Queue this toast
            self._toast_queue.append({"message": message, "type": toast_type})
            return

        # Hide current toast if any
        if self._current_toast:
            self._current_toast.close()

        # Create and show new toast
        self._current_toast = Toast(message, toast_type, self._parent)

        # Position at top center of parent
        parent_rect = self._parent.geometry()
        x = parent_rect.center().x() - self._current_toast.width() // 2
        y = parent_rect.top() + 80  # Offset from top
        self._current_toast.move(x, y)

        self._current_toast.show_event()

        # Connect close event to process queue
        self._current_toast.destroyed.connect(self._on_toast_closed)

    @pyqtSlot()
    def _on_toast_closed(self) -> None:
        """Process queued toasts when current one closes."""
        if self._toast_queue:
            next_toast = self._toast_queue.pop(0)
            self.show(next_toast["message"], next_toast["type"])
        self._current_toast = None
