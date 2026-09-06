#!/usr/bin/env python3
"""Generate OKO app icon — an owl eye symbolizing vision/monitoring."""

from PyQt5.QtGui import QPainter, QColor, QFont, QFontMetrics, QPolygon
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QRect


def create_icon() -> None:
    """Create a 256x256 icon with an owl eye design."""
    app = QApplication([])

    # Create pixmap
    size = 256
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    # ── Background circle ─────────────────────────────────────────────
    bg_color = QColor(13, 17, 23)  # Dark blue-gray
    painter.setBrush(bg_color)
    painter.setPen(QColor(0, 212, 170))  # Teal accent
    painter.drawEllipse(16, 16, 224, 224)

    # ── Eye shape (almond) ────────────────────────────────────────────
    eye_color = QColor(0, 212, 170)  # Teal
    painter.setPen(eye_color)
    painter.setBrush(QColor(0, 180, 145))

    # Draw eye shape using bezier curve
    eye_rect = QRect(48, 76, 160, 104)
    painter.drawEllipse(eye_rect)

    # ── Iris ──────────────────────────────────────────────────────────
    iris_color = QColor(0, 160, 130)
    painter.setPen(iris_color)
    painter.setBrush(iris_color)
    painter.drawEllipse(88, 96, 80, 80)

    # ── Pupil ─────────────────────────────────────────────────────────
    pupil_color = QColor(13, 17, 23)
    painter.setPen(pupil_color)
    painter.setBrush(pupil_color)
    painter.drawEllipse(112, 120, 32, 32)

    # ── Eye highlight (catchlight) ────────────────────────────────────
    highlight_color = QColor(255, 255, 255, 180)
    painter.setPen(Qt.NoPen)
    painter.setBrush(highlight_color)
    painter.drawEllipse(120, 112, 12, 12)

    # ── Second highlight ──────────────────────────────────────────────
    painter.drawEllipse(104, 128, 6, 6)

    # ── Owl ears (top corners) ────────────────────────────────────────
    ear_color = QColor(22, 27, 34)
    painter.setPen(QColor(0, 212, 170, 100))
    painter.setBrush(ear_color)

    # Left ear
    painter.setBrush(QColor(22, 27, 34))
    painter.drawPolygon(QPolygon([32, 48, 56, 24, 72, 48]))
    # Right ear
    painter.drawPolygon(QPolygon([224, 48, 200, 24, 184, 48]))

    # ── OKO text ──────────────────────────────────────────────────────
    painter.setPen(QColor(0, 212, 170))
    font = QFont("Segoe UI", 28, QFont.Bold)
    painter.setFont(font)
    painter.drawText(
        QRect(0, 200, 256, 56),
        Qt.AlignCenter,
        "ОКО",
    )

    painter.end()

    # Save as PNG
    pixmap.save("oko_app/resources/icon.png", "PNG")
    print("Icon saved: oko_app/resources/icon.png")

    # Also save as ICO for Windows
    pixmap.save("oko_app/resources/icon.ico", "ICO")
    print("Icon saved: oko_app/resources/icon.ico")


if __name__ == "__main__":
    from PyQt5.QtGui import QPixmap
    create_icon()
