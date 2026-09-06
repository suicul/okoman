"""Terminal — raw serial command interface."""

from __future__ import annotations

import time

from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QTextEdit,
    QComboBox,
)

from ..core.serial_worker import SerialWorker
from ..core.commands import ALL_COMMANDS


class Terminal(QWidget):

    def __init__(self, worker: SerialWorker, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._history = []
        self._history_idx = -1
        self._last_line = ""
        self._last_time = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Терминал")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #e6edf3;")
        main_layout.addWidget(header)

        output_card = QFrame()
        output_card.setObjectName("card")
        output_layout = QVBoxLayout(output_card)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setMinimumHeight(300)
        output_layout.addWidget(self._output)

        main_layout.addWidget(output_card, stretch=1)

        helper_card = QFrame()
        helper_card.setObjectName("card")
        helper_layout = QVBoxLayout(helper_card)
        helper_layout.setSpacing(10)

        helper_title = QLabel("Быстрая команда")
        helper_title.setObjectName("cardTitle")
        helper_layout.addWidget(helper_title)

        cmd_row = QHBoxLayout()
        cmd_row.setSpacing(8)

        self._combo_commands = QComboBox()
        self._combo_commands.setMinimumWidth(300)
        for cmd in ALL_COMMANDS:
            self._combo_commands.addItem(
                "{} -- {}".format(cmd.syntax, cmd.description), cmd.syntax
            )
        cmd_row.addWidget(self._combo_commands)

        self._param_input = QLineEdit()
        self._param_input.setPlaceholderText("Параметр (если нужен)")
        self._param_input.setMinimumWidth(200)
        cmd_row.addWidget(self._param_input)

        self._btn_send_helper = QPushButton("Отправить")
        self._btn_send_helper.setObjectName("primaryButton")
        self._btn_send_helper.clicked.connect(self._send_helper_command)
        cmd_row.addWidget(self._btn_send_helper)

        cmd_row.addStretch()
        helper_layout.addLayout(cmd_row)

        self._syntax_label = QLabel("")
        self._syntax_label.setObjectName("labelSecondary")
        helper_layout.addWidget(self._syntax_label)

        self._combo_commands.currentTextChanged.connect(self._on_command_selected)

        main_layout.addWidget(helper_card)

        input_card = QFrame()
        input_card.setObjectName("card")
        input_layout = QHBoxLayout(input_card)
        input_layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("Введите команду и нажмите Enter...")
        self._input.returnPressed.connect(self._send_raw)
        input_layout.addWidget(self._input)

        self._btn_send = QPushButton("Отправить")
        self._btn_send.setObjectName("primaryButton")
        self._btn_send.clicked.connect(self._send_raw)
        input_layout.addWidget(self._btn_send)

        self._btn_clear = QPushButton("Очистить")
        self._btn_clear.clicked.connect(self._clear_output)
        input_layout.addWidget(self._btn_clear)

        main_layout.addWidget(input_card)

    def _connect_signals(self) -> None:
        self._worker.data_received.connect(self._on_data)
        self._worker.error.connect(self._on_error)
        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)

    @pyqtSlot(str)
    def _on_connected(self, port: str = "") -> None:
        self._append_line("--- Подключено ---", "#44ff88")

    @pyqtSlot()
    def _on_disconnected(self) -> None:
        self._append_line("--- Отключено ---", "#ff5555")

    def _send_raw(self) -> None:
        text = self._input.text().strip()
        if not text:
            return
        if not self._worker.is_connected:
            self._append_line("! Нет подключения", "#ff5555")
            return
        self._worker.send_command(text)
        self._append_line(">> {}".format(text), "#00d4aa")
        self._history.append(text)
        self._history_idx = len(self._history)
        self._input.clear()

    def _send_helper_command(self) -> None:
        syntax = self._combo_commands.currentData()
        if not syntax:
            return
        param = self._param_input.text().strip()
        full_cmd = "{} {}".format(syntax, param).strip() if param else syntax
        if not self._worker.is_connected:
            self._append_line("! Нет подключения", "#ff5555")
            return
        self._worker.send_command(full_cmd)
        self._append_line(">> {}".format(full_cmd), "#00d4aa")
        self._history.append(full_cmd)
        self._param_input.clear()

    def _on_command_selected(self, text: str) -> None:
        syntax = self._combo_commands.currentData()
        if syntax:
            self._syntax_label.setText("Синтаксис: {}".format(syntax))

    def _clear_output(self) -> None:
        self._output.clear()

    @pyqtSlot(str)
    def _on_data(self, line: str) -> None:
        # Filter empty lines and duplicates
        current_time = time.time()
        stripped = line.strip()
        
        if not stripped:
            return
        
        # Skip if same line as previous (within 0.1s)
        if stripped == self._last_line and (current_time - self._last_time) < 0.1:
            return
        
        self._last_line = stripped
        self._last_time = current_time
        self._append_line("<< {}".format(line), "#e6edf3")

    @pyqtSlot(str)
    def _on_error(self, msg: str) -> None:
        self._append_line("!! {}".format(msg), "#ff5555")

    def _append_line(self, text: str, color: str = "#e6edf3") -> None:
        escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self._output.append(
            '<span style="color: {};">{}</span>'.format(color, escaped)
        )
        sb = self._output.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
