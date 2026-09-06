"""Calibration wizard — step-by-step optical sensor calibration."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QStackedWidget,
    QSizePolicy,
    QProgressBar,
)

from ..core.serial_worker import SerialWorker
from ..core.commands import (
    CMD_TEST_ON,
    CMD_EYES,
    build_command_string,
)


class StepIndicator(QWidget):
    """Horizontal step indicator showing progress through calibration."""

    def __init__(self, steps: list[str], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps = steps
        self._current = 0
        self._labels: list[QLabel] = []

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        for i, step_name in enumerate(steps):
            # Step number
            num = QLabel(str(i + 1))
            num.setFixedSize(28, 28)
            num.setAlignment(Qt.AlignmentFlag.AlignCenter)
            num.setStyleSheet(
                "background-color: #21262d; color: #8b949e; "
                "border-radius: 14px; font-size: 12px; font-weight: 600;"
            )
            layout.addWidget(num)
            self._labels.append(num)

            # Step name
            name = QLabel(step_name)
            name.setStyleSheet("color: #8b949e; font-size: 11px; padding: 0 8px;")
            name.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(name)

            # Connector line (except after last)
            if i < len(steps) - 1:
                line = QLabel()
                line.setFixedHeight(2)
                line.setStyleSheet("background-color: #30363d;")
                line.setSizePolicy(
                    QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
                )
                layout.addWidget(line)

    def set_current(self, index: int) -> None:
        self._current = index
        for i, label in enumerate(self._labels):
            if i < index:
                label.setStyleSheet(
                    "background-color: #00d4aa; color: #0d1117; "
                    "border-radius: 14px; font-size: 12px; font-weight: 600;"
                )
            elif i == index:
                label.setStyleSheet(
                    "background-color: #00d4aa33; color: #00d4aa; "
                    "border-radius: 14px; font-size: 12px; font-weight: 600; "
                    "border: 2px solid #00d4aa;"
                )
            else:
                label.setStyleSheet(
                    "background-color: #21262d; color: #8b949e; "
                    "border-radius: 14px; font-size: 12px; font-weight: 600;"
                )


class Calibration(QWidget):
    """Optical sensor calibration wizard."""

    def __init__(self, worker: SerialWorker, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._step = 0
        self._calibration_active = False
        self._cal_timeout = 30  # 30 seconds timeout
        self._cal_timer = QTimer(self)
        self._cal_timer.setSingleShot(True)
        self._cal_timer.timeout.connect(self._on_calibration_timeout)
        # Countdown timer for progress updates
        self._countdown_timer = QTimer(self)
        self._countdown_timer.timeout.connect(self._update_countdown)
        self._remaining_time = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Header
        header = QLabel("Калибровка датчиков")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #e6edf3;")
        main_layout.addWidget(header)

        # Step indicator
        self._steps = StepIndicator(
            ["Подготовка", "Усадка", "Калибровка", "Проверка"]
        )
        main_layout.addWidget(self._steps)

        # Content stack
        self._stack = QStackedWidget()

        # Step 0: Preparation
        self._stack.addWidget(self._make_step_preparation())
        # Step 1: Seating
        self._stack.addWidget(self._make_step_seating())
        # Step 2: Calibration
        self._stack.addWidget(self._make_step_calibration())
        # Step 3: Verification
        self._stack.addWidget(self._make_step_verification())

        main_layout.addWidget(self._stack)

        # Navigation buttons
        nav_row = QHBoxLayout()
        nav_row.setSpacing(12)

        self._btn_prev = QPushButton("← Назад")
        self._btn_prev.clicked.connect(self._prev_step)
        nav_row.addWidget(self._btn_prev)

        nav_row.addStretch()

        self._btn_next = QPushButton("Далее →")
        self._btn_next.setObjectName("primaryButton")
        self._btn_next.clicked.connect(self._next_step)
        nav_row.addWidget(self._btn_next)

        main_layout.addLayout(nav_row)

        self._update_nav()

    def _make_step_preparation(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        title = QLabel("Подготовка к калибровке")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        card_layout.addWidget(title)

        instructions = [
            "1. Убедитесь, что устройство подключено и питание подано (24V).",
            "2. Проверьте, что оптические датчики не заклеены и не прикрыты.",
            "3. Датчики должны быть направлены на зону контроля (лобовое стекло).",
            "4. Водительское кресло должно быть пустым.",
            "5. Убедитесь, что на камерах нет загрязнений.",
        ]
        for inst in instructions:
            label = QLabel(inst)
            label.setStyleSheet("color: #8b949e; font-size: 13px; padding: 4px 0;")
            card_layout.addWidget(label)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return w

    def _make_step_seating(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        title = QLabel("Усадка водителя")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        card_layout.addWidget(title)

        instructions = [
            "1. Попросите водителя сесть в кресло.",
            "2. Водитель должен смотреть прямо перед собой.",
            "3. Голова должна находиться в обычном положении.",
            "4. Датчики должны быть на уровне глаз водителя.",
            "5. Отрегулируйте положение датчиков при необходимости.",
        ]
        for inst in instructions:
            label = QLabel(inst)
            label.setStyleSheet("color: #8b949e; font-size: 13px; padding: 4px 0;")
            card_layout.addWidget(label)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return w

    def _make_step_calibration(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        title = QLabel("Процесс калибровки")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        card_layout.addWidget(title)

        desc = QLabel(
            "Нажмите кнопку «Начать калибровку». "
            "Водитель должен смотреть прямо перед собой 10 секунд."
        )
        desc.setStyleSheet("color: #8b949e; font-size: 13px;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        card_layout.addSpacing(16)

        self._btn_start_cal = QPushButton("Начать калибровку")
        self._btn_start_cal.setObjectName("primaryButton")
        self._btn_start_cal.setFixedWidth(220)
        self._btn_start_cal.clicked.connect(self._start_calibration)
        card_layout.addWidget(self._btn_start_cal)

        # Progress bar
        self._cal_progress = QProgressBar()
        self._cal_progress.setFixedHeight(30)
        self._cal_progress.setFixedWidth(300)
        self._cal_progress.setValue(0)
        self._cal_progress.setTextVisible(True)
        self._cal_progress.setFormat("%p% - %m:%s")
        self._cal_progress.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
                text-align: center;
                color: #e6edf3;
            }
            QProgressBar::chunk {
                background-color: #00d4aa;
                border-radius: 6px;
            }
        """)
        self._cal_progress.hide()
        card_layout.addWidget(self._cal_progress, alignment=Qt.AlignCenter)

        # Status with countdown
        self._cal_status = QLabel("")
        self._cal_status.setStyleSheet("font-size: 14px; font-weight: 500;")
        self._cal_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self._cal_status)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return w

    def _make_step_verification(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setSpacing(16)

        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)

        title = QLabel("Проверка результата")
        title.setStyleSheet("font-size: 16px; font-weight: 600; color: #e6edf3;")
        card_layout.addWidget(title)

        self._result_label = QLabel("Калибровка ещё не выполнялась.")
        self._result_label.setStyleSheet("color: #8b949e; font-size: 13px;")
        self._result_label.setWordWrap(True)
        card_layout.addWidget(self._result_label)

        card_layout.addSpacing(16)

        desc = QLabel(
            "Для проверки корректности калибровки:\n"
            "• Закройте глаза — должен появиться сигнал «Не вижу ваши глаза».\n"
            "• Отвернитесь — «Не вижу ваше лицо».\n"
            "• Поднесите телефон к уху — «Не отвлекайтесь на телефон»."
        )
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        desc.setWordWrap(True)
        card_layout.addWidget(desc)

        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        return w

    def _connect_signals(self) -> None:
        self._worker.data_received.connect(self._on_data)

    def _update_nav(self) -> None:
        self._btn_prev.setEnabled(self._step > 0)
        is_last = self._step >= 3
        self._btn_next.setText("Завершить" if is_last else "Далее →")

    @pyqtSlot()
    def _prev_step(self) -> None:
        if self._step > 0:
            self._step -= 1
            self._stack.setCurrentIndex(self._step)
            self._steps.set_current(self._step)
            self._update_nav()

    @pyqtSlot()
    def _next_step(self) -> None:
        if self._step < 3:
            self._step += 1
            self._stack.setCurrentIndex(self._step)
            self._steps.set_current(self._step)
            self._update_nav()

    @pyqtSlot()
    def _start_calibration(self) -> None:
        self._calibration_active = True
        self._remaining_time = self._cal_timeout
        
        # Show progress bar
        self._cal_progress.show()
        self._cal_progress.setMaximum(self._cal_timeout)
        self._cal_progress.setValue(0)
        self._countdown_timer.start(1000)  # Update every second
        
        self._cal_status.setText("⏳ Калибровка выполняется... Смотрите прямо перед собой.")
        self._cal_status.setStyleSheet("color: #ffbb33; font-size: 14px; font-weight: 500;")
        self._btn_start_cal.setEnabled(False)

        # Start timeout timer
        self._cal_timer.start(self._cal_timeout * 1000)

        # Send calibration commands using CommandDef
        if self._worker.is_connected:
            self._worker.send_command(build_command_string(CMD_TEST_ON))
            QTimer.singleShot(500, lambda: self._worker.send_command(
                build_command_string(CMD_EYES, "1")
            ))

    @pyqtSlot()
    def _update_countdown(self) -> None:
        """Update progress bar and status with countdown."""
        self._remaining_time -= 1
        if self._remaining_time < 0:
            self._remaining_time = 0
        
        self._cal_progress.setValue(self._cal_timeout - self._remaining_time)
        
        minutes = self._remaining_time // 60
        seconds = self._remaining_time % 60
        self._cal_status.setText(
            "⏳ Калибровка... {}:{:02d} осталось".format(minutes, seconds)
        )

    @pyqtSlot()
    def _on_calibration_timeout(self) -> None:
        """Handle calibration timeout."""
        self._calibration_active = False
        self._countdown_timer.stop()
        self._cal_progress.hide()
        self._cal_status.setText("⏱ Таймаут калибровки. Попробуйте снова.")
        self._cal_status.setStyleSheet("color: #ff5555; font-size: 14px; font-weight: 500;")
        self._btn_start_cal.setEnabled(True)

    @pyqtSlot(str)
    def _on_data(self, line: str) -> None:
        if not self._calibration_active:
            return

        # Stop timeout timer on any response
        self._cal_timer.stop()

        if "CAL_OK" in line or "успешно завершена" in line.lower():
            self._calibration_active = False
            self._countdown_timer.stop()
            self._cal_progress.hide()
            self._cal_status.setText("✓ Калибровка успешно завершена!")
            self._cal_status.setStyleSheet(
                "color: #44ff88; font-size: 14px; font-weight: 500;"
            )
            self._result_label.setText("Калибровка прошла успешно. Датчики настроены.")
            self._result_label.setStyleSheet("color: #44ff88; font-size: 13px;")
            self._btn_start_cal.setEnabled(True)

        elif "CAL_ER" in line or "ошибка" in line.lower():
            self._calibration_active = False
            self._countdown_timer.stop()
            self._cal_progress.hide()
            self._cal_status.setText("✗ Ошибка калибровки. Попробуйте снова.")
            self._cal_status.setStyleSheet(
                "color: #ff5555; font-size: 14px; font-weight: 500;"
            )
            self._btn_start_cal.setEnabled(True)
