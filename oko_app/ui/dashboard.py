"""Dashboard — device status overview with LED indicators."""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSlot, QTimer, QMetaObject
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QScrollArea,
    QProgressBar,
)

from ..core.serial_worker import SerialWorker
from ..core.commands import (
    CMD_VER, CMD_SERIAL, CMD_DEBUG_ONLY_POS, CMD_DEBUG_ONLY_GSM,
    build_command_string,
)
from .theme import LED_OFF, LED_POWER, LED_GPS, LED_GSM, LED_OPTICS


AUTO_SCAN_COMMANDS = (
    (CMD_VER, "ver", 30000, 1),
    (CMD_SERIAL, "serial", 10000, 1),
    (CMD_DEBUG_ONLY_POS, "pos", 30000, 1),
    ("SET", "set", 60000, 1),
)


class LedIndicator(QFrame):

    def __init__(self, color: str, label: str, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._color_off = LED_OFF
        self._color_on = color
        self._is_on = False
        self._blink_enabled = False

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        self._led = QFrame()
        self._led.setFixedSize(24, 24)
        self._led.setStyleSheet(self._led_style(self._color_off))
        layout.addWidget(self._led, alignment=Qt.AlignCenter)

        self._label = QLabel(label)
        self._label.setAlignment(Qt.AlignCenter)
        self._label.setStyleSheet("color: #8b949e; font-size: 10px;")
        layout.addWidget(self._label)

    def _led_style(self, color: str) -> str:
        return (
            "background-color: {};".format(color)
            + "border-radius: 12px;"
            + "border: 2px solid rgba(255,255,255,0.08);"
        )

    def set_on(self, on: bool) -> None:
        self._is_on = on
        color = self._color_on if on else self._color_off
        self._led.setStyleSheet(self._led_style(color))

    @pyqtSlot()
    def _turn_off(self) -> None:
        """Slot for turning off LED (called via QMetaObject.invokeMethod)."""
        self.set_on(False)

    def set_blink(self) -> None:
        if self._blink_enabled:
            self.set_on(not self._is_on)

    def enable_blink(self, enabled: bool) -> None:
        self._blink_enabled = enabled
        if not enabled:
            self.set_on(False)


class InfoRow(QWidget):

    def __init__(self, label: str, value: str = "\u2014", parent: QWidget = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)

        self._label = QLabel(label)
        self._label.setStyleSheet("color: #8b949e; font-size: 12px;")
        self._label.setMinimumWidth(140)
        self._label.setMaximumWidth(220)
        self._label.setWordWrap(False)
        layout.addWidget(self._label)

        self._value = QLabel(value)
        self._value.setStyleSheet("color: #e6edf3; font-size: 12px; font-weight: 500;")
        self._value.setWordWrap(True)
        layout.addWidget(self._value, stretch=1)

    def set_value(self, text: str) -> None:
        self._value.setText(str(text))

    def set_value_color(self, color: str) -> None:
        self._value.setStyleSheet(
            "color: {}; font-size: 12px; font-weight: 500;".format(color)
        )


class Dashboard(QWidget):

    def __init__(self, worker: SerialWorker, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._setup_ui()
        self._connect_signals()
        # No timer needed - LEDs react to real device events

    def _setup_ui(self) -> None:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        header = QLabel("Обзор устройства")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #e6edf3;")
        main_layout.addWidget(header)

        # ── LED Indicators ──
        indicators_card = QFrame()
        indicators_card.setObjectName("card")
        indicators_layout = QVBoxLayout(indicators_card)

        ind_title = QLabel("Индикаторы БОД")
        ind_title.setObjectName("cardTitle")
        indicators_layout.addWidget(ind_title)

        leds_row = QHBoxLayout()
        leds_row.setSpacing(24)
        leds_row.setAlignment(Qt.AlignCenter)

        self._led_power = LedIndicator(LED_POWER, "Питание")
        self._led_gps = LedIndicator(LED_GPS, "GPS/ГЛОНАСС")
        self._led_gsm = LedIndicator(LED_GSM, "GSM/Связь")
        self._led_optics_l = LedIndicator(LED_OPTICS, "Датчик L")
        self._led_optics_r = LedIndicator(LED_OPTICS, "Датчик R")

        for led in (self._led_power, self._led_gps, self._led_gsm,
                     self._led_optics_l, self._led_optics_r):
            leds_row.addWidget(led)

        indicators_layout.addLayout(leds_row)
        main_layout.addWidget(indicators_card)

        # ── Device Info ──
        info_card = QFrame()
        info_card.setObjectName("card")
        info_layout = QVBoxLayout(info_card)

        info_title = QLabel("Информация об устройстве")
        info_title.setObjectName("cardTitle")
        info_layout.addWidget(info_title)

        self._info_firmware = InfoRow("Версия прошивки")
        self._info_build = InfoRow("Дата сборки")
        self._info_serial = InfoRow("Серийный номер")
        self._info_gsm_signal = InfoRow("Уровень GSM сигнала")
        self._info_mqtt = InfoRow("Статус MQTT")
        self._info_gps_lat = InfoRow("Широта (Lat)")
        self._info_gps_lng = InfoRow("Долгота (Lng)")
        self._info_gps_vel = InfoRow("Скорость")
        self._scan_status = QLabel("")
        self._scan_status.setStyleSheet("color: #ffbb33; font-size: 11px;")
        self._scan_status.hide()
        self._btn_skip_scan = QPushButton("Пропустить этап")
        self._btn_skip_scan.hide()
        self._btn_skip_scan.clicked.connect(self._skip_scan_step)

        for row in (self._info_firmware, self._info_build, self._info_serial,
                    self._info_gsm_signal, self._info_mqtt,
                    self._info_gps_lat, self._info_gps_lng, self._info_gps_vel):
            info_layout.addWidget(row)

        main_layout.addWidget(info_card)
        
        # Scan progress bar
        self._scan_progress = QProgressBar()
        self._scan_progress.setFixedHeight(24)
        self._scan_progress.setValue(0)
        self._scan_progress.setFormat("Сканирование... %p%")
        self._scan_progress.setStyleSheet("""
            QProgressBar {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 8px;
                text-align: center;
                color: #e6edf3;
                font-size: 11px;
            }
            QProgressBar::chunk {
                background-color: #00d4aa;
                border-radius: 6px;
            }
        """)
        self._scan_progress.hide()
        main_layout.addWidget(self._scan_progress)
        
        scan_row = QHBoxLayout()
        scan_row.addWidget(self._scan_status, stretch=1)
        scan_row.addWidget(self._btn_skip_scan)
        main_layout.addLayout(scan_row)

        # ── Settings (from SET command) ──
        settings_card = QFrame()
        settings_card.setObjectName("card")
        settings_layout = QVBoxLayout(settings_card)

        settings_title = QLabel("Настройки устройства")
        settings_title.setObjectName("cardTitle")
        settings_layout.addWidget(settings_title)

        self._set_spk_vol = InfoRow("Громкость (SpkVol)")
        self._set_gsm_apn = InfoRow("GSM APN")
        self._set_gsm_user = InfoRow("GSM User")
        self._set_gsm_pwd = InfoRow("GSM Password")
        self._set_mqtt_url = InfoRow("MQTT URL")
        self._set_reg = InfoRow("Регистратор (REG)")
        self._set_gps = InfoRow("GPS/ГЛОНАСС режим")

        for row in (self._set_spk_vol, self._set_gsm_apn, self._set_gsm_user,
                    self._set_gsm_pwd, self._set_mqtt_url, self._set_reg, self._set_gps):
            settings_layout.addWidget(row)

        main_layout.addWidget(settings_card)

        # ── Quick Actions ──
        actions_card = QFrame()
        actions_card.setObjectName("card")
        actions_layout = QVBoxLayout(actions_card)

        actions_title = QLabel("Быстрые действия")
        actions_title.setObjectName("cardTitle")
        actions_layout.addWidget(actions_title)

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)

        self._btn_query_ver = QPushButton("Запрос версии")
        self._btn_query_ver.clicked.connect(lambda: self._send(CMD_VER))

        self._btn_query_serial = QPushButton("Запрос серийного номера")
        self._btn_query_serial.clicked.connect(lambda: self._send(CMD_SERIAL))

        self._btn_restart = QPushButton("Перезагрузка (RST)")
        self._btn_restart.setObjectName("dangerButton")
        self._btn_restart.clicked.connect(lambda: self._send_cmd_string("RST"))

        for btn in (self._btn_query_ver, self._btn_query_serial, self._btn_restart):
            buttons_row.addWidget(btn)

        actions_layout.addLayout(buttons_row)
        main_layout.addWidget(actions_card)
        main_layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _connect_signals(self) -> None:
        self._worker.version_info.connect(self._on_version)
        self._worker.serial_number.connect(self._on_serial)
        self._worker.gps_data.connect(self._on_gps)
        self._worker.gsm_data.connect(self._on_gsm)
        self._worker.settings_data.connect(self._on_settings)
        self._worker.connected.connect(self._on_device_connected)
        self._worker.disconnected.connect(self._on_device_disconnected)
        self._worker.command_completed.connect(self._on_scan_command_completed)
        self._worker.command_failed.connect(self._on_scan_command_failed)
        self._worker.command_cancelled.connect(self._on_scan_command_cancelled)
        self._scan_generation = 0
        self._scan_index = 0
        self._expected_scan_id = 0
        self._scan_ok = 0
        self._scan_fail = 0
        self._scan_countdown = QTimer(self)
        self._scan_countdown.timeout.connect(self._update_scan_countdown)
        self._scan_deadline = 0

    @pyqtSlot(str)
    def _on_device_connected(self, port: str) -> None:
        self._scan_generation += 1
        generation = self._scan_generation
        # Power LED: solid on when connected
        self._led_power.set_on(True)
        # Other LEDs off initially
        self._led_gps.set_on(False)
        self._led_gsm.set_on(False)
        self._led_optics_l.set_on(False)
        self._led_optics_r.set_on(False)

        self._scan_index = 0
        self._scan_ok = 0
        self._scan_fail = 0
        self._expected_scan_id = 0
        
        # Show progress bar
        self._scan_progress.show()
        self._scan_progress.setMaximum(len(AUTO_SCAN_COMMANDS))
        self._scan_progress.setValue(0)
        
        self._scan_status.show()
        self._btn_skip_scan.show()
        self._queue_next_scan(generation)

    def _update_scan_status(self, text: str) -> None:
        total = len(AUTO_SCAN_COMMANDS)
        done = min(self._scan_index + 1, total)
        self._scan_status.setText("Этап {}/{} · {}".format(done, total, text))
        # Update progress bar
        if self._scan_progress.isVisible():
            percent = int((done / total) * 100)
            self._scan_progress.setValue(percent)
            self._scan_progress.setFormat("Этап {} из {} · {}".format(done, total, text))

    def _skip_scan_step(self) -> None:
        if self._expected_scan_id:
            self._worker.cancel_request(self._expected_scan_id)
        self._scan_countdown.stop()
        self._scan_fail += 1
        self._scan_index += 1
        self._expected_scan_id = 0
        self._queue_next_scan(self._scan_generation)

    def _finish_scan_report(self) -> None:
        self._scan_countdown.stop()
        self._btn_skip_scan.hide()
        total = len(AUTO_SCAN_COMMANDS)
        self._scan_status.setText(
            "Сканирование завершено: {}/{} · ошибок: {}".format(
                self._scan_ok, total, self._scan_fail
            )
        )
        # Complete progress bar
        self._scan_progress.setValue(total)
        self._scan_progress.setFormat("✓ Завершено")
        QTimer.singleShot(4000, self._scan_progress.hide)
        QTimer.singleShot(4000, self._scan_status.hide)

    def _queue_next_scan(self, generation: int) -> None:
        if generation != self._scan_generation or not self._worker.is_connected:
            return
        if self._scan_index >= len(AUTO_SCAN_COMMANDS):
            self._finish_scan_report()
            return
        command, response_kind, timeout_ms, retries = AUTO_SCAN_COMMANDS[self._scan_index]
        text = command if isinstance(command, str) else build_command_string(command)
        self._update_scan_status("Запрос: {}".format(text))
        if response_kind == "gsm":
            self._scan_deadline = timeout_ms // 1000
            self._scan_countdown.start(1000)
            self._update_scan_countdown()
        self._expected_scan_id = self._worker.queue_command(
            text, response_kind, timeout_ms, retries, owner="scan"
        )

    def _update_scan_countdown(self) -> None:
        if self._scan_deadline > 0 and self._worker.is_connected:
            self._update_scan_status("Ожидание GSM ответа: {} с".format(self._scan_deadline))
            self._scan_deadline -= 1
        else:
            self._scan_countdown.stop()

    @pyqtSlot(int, str, str)
    def _on_scan_command_completed(self, request_id: int, command: str, response: str) -> None:
        if request_id != self._expected_scan_id:
            return
        if self._scan_index >= len(AUTO_SCAN_COMMANDS):
            return
        self._expected_scan_id = 0
        self._scan_countdown.stop()
        self._scan_ok += 1
        self._scan_index += 1
        self._queue_next_scan(self._scan_generation)

    @pyqtSlot(int, str, str)
    def _on_scan_command_failed(self, request_id: int, command: str, reason: str) -> None:
        if request_id != self._expected_scan_id:
            return
        if self._scan_index >= len(AUTO_SCAN_COMMANDS):
            return
        self._expected_scan_id = 0
        self._scan_countdown.stop()
        self._scan_fail += 1
        self._update_scan_status("Нет ответа: {}".format(command))
        self._scan_index += 1
        self._queue_next_scan(self._scan_generation)

    @pyqtSlot(int, str)
    def _on_scan_command_cancelled(self, request_id: int, command: str) -> None:
        if request_id != self._expected_scan_id:
            return
        self._expected_scan_id = 0
        self._scan_countdown.stop()

    @pyqtSlot()
    def _on_device_disconnected(self) -> None:
        self._scan_generation += 1
        self._expected_scan_id = 0
        self._scan_countdown.stop()
        self._scan_status.hide()
        self._btn_skip_scan.hide()
        self._scan_progress.hide()
        # All LEDs off
        self._led_power.set_on(False)
        self._led_gps.set_on(False)
        self._led_gsm.set_on(False)
        self._led_optics_l.set_on(False)
        self._led_optics_r.set_on(False)

        dash_fields = [
            self._info_firmware, self._info_build, self._info_serial,
            self._info_gsm_signal, self._info_mqtt,
            self._info_gps_lat, self._info_gps_lng, self._info_gps_vel,
        ]
        for f in dash_fields:
            f.set_value("\u2014")
            f.set_value_color("#e6edf3")

        set_fields = [
            self._set_spk_vol, self._set_gsm_apn, self._set_gsm_user,
            self._set_gsm_pwd, self._set_mqtt_url, self._set_reg, self._set_gps,
        ]
        for f in set_fields:
            f.set_value("\u2014")
            f.set_value_color("#e6edf3")

    @pyqtSlot(str, str)
    def _on_version(self, version: str, build_date: str) -> None:
        self._info_firmware.set_value(version)
        self._info_firmware.set_value_color("#00d4aa")
        self._info_build.set_value(build_date)

    @pyqtSlot(str)
    def _on_serial(self, serial_num: str) -> None:
        self._info_serial.set_value(serial_num)
        self._info_serial.set_value_color("#00d4aa")

    @pyqtSlot(dict)
    def _on_gps(self, data: dict) -> None:
        self._info_gps_lat.set_value(data.get("lat", "\u2014"))
        self._info_gps_lng.set_value(data.get("lng", "\u2014"))
        self._info_gps_vel.set_value("{} км/ч".format(data.get("vel", "\u2014")))
        # GPS LED: blink on GPS data received
        self._led_gps.set_on(True)
        QMetaObject.invokeMethod(self._led_gps, "_turn_off", 
                                Qt.QueuedConnection)

    @pyqtSlot(dict)
    def _on_gsm(self, data: dict) -> None:
        signal = data.get("signal", 0)
        self._info_gsm_signal.set_value("{}/31".format(signal))
        color = "#44ff88" if signal >= 14 else "#ffbb33" if signal > 0 else "#ff5555"
        self._info_gsm_signal.set_value_color(color)
        mqtt = data.get("mqtt_status", "\u2014")
        self._info_mqtt.set_value(mqtt if mqtt else "\u2014")
        # GSM LED: blink on GSM data received
        self._led_gsm.set_on(True)
        QMetaObject.invokeMethod(self._led_gsm, "_turn_off",
                                Qt.QueuedConnection)

    @pyqtSlot(dict)
    def _on_settings(self, data: dict) -> None:
        """Update settings display. Reset fields not in data to '—'."""
        all_fields = {
            "SpkVol": self._set_spk_vol,
            "GSM_APN": self._set_gsm_apn,
            "GSM_USER": self._set_gsm_user,
            "GSM_PWD": self._set_gsm_pwd,
            "MQTT_URL": self._set_mqtt_url,
            "REG": self._set_reg,
            "Gps": self._set_gps,
            "GPS": self._set_gps,
        }
        for key, field_widget in all_fields.items():
            if key in data:
                field_widget.set_value(data[key])
                field_widget.set_value_color("#00d4aa")
            else:
                field_widget.set_value("\u2014")
                field_widget.set_value_color("#e6edf3")

    def _send(self, cmd) -> None:
        if self._worker.is_connected:
            self._worker.send_command(build_command_string(cmd))

    def _send_cmd_string(self, text: str) -> None:
        if self._worker.is_connected:
            self._worker.send_command(text)
