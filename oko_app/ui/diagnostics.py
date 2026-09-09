"""Diagnostics panel — automated test routines for БОД components."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
    QScrollArea,
    QMessageBox,
)

from ..core.serial_worker import SerialWorker
from ..core.commands import (
    CMD_TEST_HW,
    CMD_TEST_ON,
    CMD_TEST_OFF,
    CMD_LED_ALL,
    build_command_string,
)
from ..core.constants import VIBRO_MIN, VIBRO_MAX, SPK_MIN, SPK_MAX


class TestResultCard(QFrame):

    def __init__(self, name: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(60)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)

        self._name = QLabel(name)
        self._name.setAccessibleName("Название теста: {}".format(name))
        self._name.setStyleSheet("font-size: 13px; font-weight: 600;")
        self._name.setFixedWidth(180)
        layout.addWidget(self._name)

        self._status = QLabel("Ожидание")
        self._status.setAccessibleName("Статус теста: {}".format(name))
        self._status.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(self._status)

        layout.addStretch()

        self._result = QLabel("—")
        self._result.setAccessibleName("Результат теста: {}".format(name))
        self._result.setStyleSheet("color: #8b949e; font-size: 12px;")
        self._result.setMinimumWidth(150)
        layout.addWidget(self._result)

    def set_running(self) -> None:
        self._status.setText("Выполняется...")
        self._status.setStyleSheet("color: #ffbb33; font-size: 12px; font-weight: 500;")

    def set_pass(self, detail: str = "OK") -> None:
        self._status.setText("OK")
        self._status.setStyleSheet("color: #44ff88; font-size: 12px; font-weight: 500;")
        self._result.setText(detail)
        self._result.setStyleSheet("color: #44ff88; font-size: 12px;")

    def set_fail(self, detail: str = "Ошибка") -> None:
        self._status.setText("Ошибка")
        self._status.setStyleSheet("color: #ff5555; font-size: 12px; font-weight: 500;")
        self._result.setText(detail)
        self._result.setStyleSheet("color: #ff5555; font-size: 12px;")

    def reset(self) -> None:
        self._status.setText("Ожидание")
        self._status.setStyleSheet("color: #8b949e; font-size: 12px;")
        self._result.setText("—")
        self._result.setStyleSheet("color: #8b949e; font-size: 12px;")


class Diagnostics(QWidget):

    def __init__(self, worker: SerialWorker, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Диагностика")
        header.setAccessibleName("Экран диагностики")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #e6edf3;")
        main_layout.addWidget(header)

        quick_card = QFrame()
        quick_card.setObjectName("card")
        quick_layout = QVBoxLayout(quick_card)
        quick_layout.setSpacing(10)

        quick_title = QLabel("Быстрые тесты")
        quick_title.setObjectName("cardTitle")
        quick_layout.addWidget(quick_title)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        self._btn_hw_test = QPushButton("Тест аппаратуры")
        self._btn_hw_test.setMinimumHeight(36)
        self._btn_hw_test.setToolTip("Запустить проверку аппаратуры")
        self._btn_hw_test.clicked.connect(self._test_hw)
        btn_row.addWidget(self._btn_hw_test)

        self._btn_led_test = QPushButton("Тест LED")
        self._btn_led_test.setMinimumHeight(36)
        self._btn_led_test.clicked.connect(self._test_led)
        btn_row.addWidget(self._btn_led_test)

        self._btn_led_off = QPushButton("LED OFF")
        self._btn_led_off.setMinimumHeight(36)
        self._btn_led_off.clicked.connect(self._led_off)
        btn_row.addWidget(self._btn_led_off)

        self._btn_debug_mode = QPushButton("TEST ON")
        self._btn_debug_mode.setMinimumHeight(36)
        self._btn_debug_mode.clicked.connect(self._toggle_debug)
        btn_row.addWidget(self._btn_debug_mode)

        self._btn_debug_off = QPushButton("TEST OFF")
        self._btn_debug_off.setMinimumHeight(36)
        self._btn_debug_off.clicked.connect(self._disable_debug)
        btn_row.addWidget(self._btn_debug_off)

        btn_row.addStretch()
        quick_layout.addLayout(btn_row)
        main_layout.addWidget(quick_card)

        spk_card = QFrame()
        spk_card.setObjectName("card")
        spk_layout = QVBoxLayout(spk_card)
        spk_layout.setSpacing(10)

        spk_title = QLabel("Тест динамика (звуки 0–13 по руководству, разд. 6.4)")
        spk_title.setObjectName("cardTitle")
        spk_layout.addWidget(spk_title)

        spk_hint = QLabel("0 — тихий бип, 5 — «Тревога». SPK B — короткий тест-бип.")
        spk_hint.setStyleSheet("color: #8b949e; font-size: 11px;")
        spk_layout.addWidget(spk_hint)

        spk_row1 = QHBoxLayout()
        spk_row1.setSpacing(6)
        for i in range(7):
            btn = QPushButton(str(i))
            btn.setMinimumSize(44, 36)
            btn.clicked.connect(lambda _, n=i: self._spk_test(n))
            spk_row1.addWidget(btn)
        spk_row1.addStretch()
        spk_layout.addLayout(spk_row1)

        spk_row2 = QHBoxLayout()
        spk_row2.setSpacing(6)
        for i in range(7, 14):
            btn = QPushButton(str(i))
            btn.setMinimumSize(44, 36)
            btn.clicked.connect(lambda _, n=i: self._spk_test(n))
            spk_row2.addWidget(btn)
        self._btn_spk_b = QPushButton("SPK B")
        self._btn_spk_b.setToolTip("Короткий тест-бип (для диагностики из руководства)")
        self._btn_spk_b.clicked.connect(lambda: self._send_raw("SPK B"))
        spk_row2.addWidget(self._btn_spk_b)
        spk_row2.addStretch()
        spk_layout.addLayout(spk_row2)
        main_layout.addWidget(spk_card)

        out_card = QFrame()
        out_card.setObjectName("card")
        out_layout = QVBoxLayout(out_card)
        out_layout.setSpacing(10)

        out_title = QLabel("Триггеры на регистратор")
        out_title.setObjectName("cardTitle")
        out_layout.addWidget(out_title)

        out_row = QHBoxLayout()
        out_row.setSpacing(6)
        for ch in ("1", "2", "4", "8"):
            btn = QPushButton("OUT {}".format(ch))
            btn.clicked.connect(lambda _, c=ch: self._out_test(c))
            out_row.addWidget(btn)
        out_row.addStretch()
        out_layout.addLayout(out_row)
        main_layout.addWidget(out_card)

        sensor_card = QFrame()
        sensor_card.setObjectName("card")
        sensor_layout = QVBoxLayout(sensor_card)
        sensor_layout.setSpacing(10)

        sensor_title = QLabel("Симуляция событий датчиков")
        sensor_title.setObjectName("cardTitle")
        sensor_layout.addWidget(sensor_title)

        sensor_row = QHBoxLayout()
        sensor_row.setSpacing(6)
        for label, cmd in [
            ("Закрыть глаза", "EYES_1"),
            ("Отвернуться", "FACE_4"),
            ("Телефон у уха", "PHONE5"),
            ("Курение", "SMOKE6"),
        ]:
            btn = QPushButton(label)
            btn.clicked.connect(lambda _, c=cmd: self._send_raw(c))
            sensor_row.addWidget(btn)
        sensor_row.addStretch()
        sensor_layout.addLayout(sensor_row)
        main_layout.addWidget(sensor_card)

        results_card = QFrame()
        results_card.setObjectName("card")
        results_layout = QVBoxLayout(results_card)
        results_layout.setSpacing(6)

        results_title = QLabel("Результаты компонентов")
        results_title.setObjectName("cardTitle")
        results_layout.addWidget(results_title)

        self._test_button = TestResultCard("Кнопка")
        self._test_speaker = TestResultCard("Динамик / Вибромотор")
        self._test_gps = TestResultCard("GPS модуль")
        self._test_gsm = TestResultCard("GSM модуль")
        self._test_sensors = TestResultCard("Оптические датчики")

        for card in (self._test_button, self._test_speaker, self._test_gps,
                     self._test_gsm, self._test_sensors):
            results_layout.addWidget(card)

        main_layout.addWidget(results_card)

        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)

        log_title = QLabel("Лог диагностики")
        log_title.setObjectName("cardTitle")
        log_layout.addWidget(log_title)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumHeight(180)
        log_layout.addWidget(self._log)

        main_layout.addWidget(log_card)
        main_layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _connect_signals(self) -> None:
        self._worker.hw_test_result.connect(self._on_hw_result)
        self._worker.button_event.connect(self._on_button_event)
        self._worker.sensor_event.connect(self._on_sensor_event)
        self._worker.gps_data.connect(self._on_gps_data)
        self._worker.gsm_data.connect(self._on_gsm_data)
        self._worker.data_received.connect(self._on_raw_data)
        self._worker.command_completed.connect(self._on_cmd_done)
        self._worker.command_failed.connect(self._on_cmd_done)
        self._worker.command_cancelled.connect(self._on_cmd_cancelled)
        self._hw_active_id = 0

    def _test_hw(self) -> None:
        if not self._worker.is_connected:
            self._log_append("! Нет подключения")
            return
        self._log_append("-> TEST HW")
        for card in (self._test_button, self._test_speaker, self._test_gps,
                     self._test_gsm, self._test_sensors):
            card.reset()
        self._test_speaker.set_running()
        self._btn_hw_test.setEnabled(False)
        self._hw_active_id = self._worker.queue_command(
            build_command_string(CMD_TEST_HW), "line", 20000, 0, owner="diag"
        )

    @pyqtSlot(int, str, str)
    def _on_cmd_done(self, request_id: int, command: str, response: str) -> None:
        if request_id == self._hw_active_id:
            self._hw_active_id = 0
            self._btn_hw_test.setEnabled(True)

    @pyqtSlot(int, str)
    def _on_cmd_cancelled(self, request_id: int, command: str) -> None:
        if request_id == self._hw_active_id:
            self._hw_active_id = 0
            self._btn_hw_test.setEnabled(True)

    def _test_led(self) -> None:
        self._log_append("-> LED ALL 1000 500 #")
        self._worker.send_command("LED ALL 1000 500 #")

    def _led_off(self) -> None:
        self._log_append("-> LED ALL 0 0 #")
        self._worker.send_command("LED ALL 0 0 #")

    def _toggle_debug(self) -> None:
        self._log_append("-> TEST ON")
        self._worker.send_command(build_command_string(CMD_TEST_ON), owner="diag")

    def _disable_debug(self) -> None:
        self._log_append("-> TEST OFF")
        self._worker.send_command(build_command_string(CMD_TEST_OFF), owner="diag")

    def _spk_test(self, num: int) -> None:
        self._log_append("-> SPK P {}".format(num))
        self._worker.send_command("SPK P {}".format(num))

    def _out_test(self, channel: str) -> None:
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Отправить OUT {} на регистратор?".format(channel),
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._log_append("-> OUT {}".format(channel))
        self._worker.send_command("OUT {}".format(channel), owner="diag")

    def _send_raw(self, cmd: str) -> None:
        self._log_append("-> {}".format(cmd))
        self._worker.send_command(cmd)

    @pyqtSlot(dict)
    def _on_hw_result(self, data: dict) -> None:
        vibro = data.get("vibro", 0)
        spk1 = data.get("spk1", 0)
        spk2 = data.get("spk2", 0)
        gpsant = data.get("gpsant", 0)
        ftg = data.get("ftg", 0)

        vibro_ok = VIBRO_MIN <= vibro <= VIBRO_MAX
        spk_ok = SPK_MIN <= spk1 <= SPK_MAX and SPK_MIN <= spk2 <= SPK_MAX

        if vibro_ok and spk_ok:
            self._test_speaker.set_pass("VIBRO={} SPK={}/{}".format(vibro, spk1, spk2))
        else:
            self._test_speaker.set_fail("VIBRO={} SPK={}/{}".format(vibro, spk1, spk2))

        if gpsant == 0:
            self._test_gps.set_pass("GPSANT={}".format(gpsant))
        else:
            self._test_gps.set_fail("GPSANT={} (ожид. 0)".format(gpsant))

        if ftg == 0:
            self._test_sensors.set_pass("FTG={}".format(ftg))
        else:
            self._test_sensors.set_fail("FTG={} (ожид. 0)".format(ftg))

        self._log_append("TEST HW: VIBRO={}, SPK={}/{}, GPSANT={}, FTG={}".format(
            vibro, spk1, spk2, gpsant, ftg))

    @pyqtSlot(int)
    def _on_button_event(self, count: int) -> None:
        self._test_button.set_pass("Нажатий: {}".format(count))
        self._log_append("Кнопка нажата {} раз".format(count))

    @pyqtSlot(str)
    def _on_sensor_event(self, line: str) -> None:
        self._log_append("Датчик: {}".format(line))

    @pyqtSlot(dict)
    def _on_gps_data(self, data: dict) -> None:
        self._test_gps.set_pass("Lat={} Lng={}".format(
            data.get("lat", "?"), data.get("lng", "?")))

    @pyqtSlot(dict)
    def _on_gsm_data(self, data: dict) -> None:
        signal = data.get("signal", 0)
        if signal >= 14:
            self._test_gsm.set_pass("Signal={} Errors={}".format(
                signal, data.get("errors", 0)))
        else:
            self._test_gsm.set_fail("Signal={} (мин. 14)".format(signal))

    @pyqtSlot(str)
    def _on_raw_data(self, line: str) -> None:
        if any(kw in line for kw in ("DEBUG", "TST:", "Button")):
            self._log_append("< {}".format(line))

    def _log_append(self, text: str) -> None:
        self._log.append(text)
        sb = self._log.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())
