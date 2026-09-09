"""Live monitor — real-time sensor data visualization and event log."""

from __future__ import annotations

from datetime import datetime

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
)

from ..core.serial_worker import SerialWorker
from ..core.commands import (
    CMD_DEBUG_ONLY_POS,
    CMD_DEBUG_ONLY_GSM,
    CMD_DEBUG_ONLY_FTG,
    CMD_DEBUG_ON_PWR,
    CMD_PWR_TM,
    build_command_string,
)
from ..core.constants import GSM_GOOD_SIGNAL


class StatCard(QFrame):
    """A small stat card with label and value."""

    def __init__(
        self, label: str, value: str = "—", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumHeight(100)
        self.setMaximumHeight(120)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self._label = QLabel(label)
        self._label.setAccessibleName("Показатель: {}".format(label))
        self._label.setStyleSheet("color: #a0aab4; font-size: 12px; font-weight: 500;")
        self._label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._label)

        self._value = QLabel(value)
        self._value.setAccessibleName("Значение: {}".format(label))
        self._value.setStyleSheet(
            "color: #00d4aa; font-size: 24px; font-weight: 700;"
        )
        self._value.setAlignment(Qt.AlignCenter)
        self._value.setWordWrap(False)
        self._value.setMinimumHeight(40)
        layout.addWidget(self._value, stretch=1)

        self._unit = QLabel("")
        self._unit.setStyleSheet("color: #a0aab4; font-size: 11px;")
        self._unit.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._unit)

    def set_value(self, text: str, color: str = "#00d4aa") -> None:
        self._value.setText(text)
        self._value.setStyleSheet(
            f"color: {color}; font-size: 22px; font-weight: 700;"
        )

    def set_unit(self, unit: str) -> None:
        self._unit.setText(unit)


class LiveMonitor(QWidget):
    """Real-time monitoring page."""

    def __init__(self, worker: SerialWorker, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._event_count = 0
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 24, 24, 24)

        # Header with refresh controls
        header_row = QHBoxLayout()
        header = QLabel("Мониторинг в реальном времени")
        header.setAccessibleName("Экран мониторинга в реальном времени")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #e6edf3;")
        header_row.addWidget(header)

        header_row.addStretch()

        self._btn_refresh_gps = QPushButton("GPS")
        self._btn_refresh_gps.setMinimumHeight(36)
        self._btn_refresh_gps.clicked.connect(self._query_gps)
        header_row.addWidget(self._btn_refresh_gps)

        self._btn_refresh_gsm = QPushButton("GSM")
        self._btn_refresh_gsm.setMinimumHeight(36)
        self._btn_refresh_gsm.clicked.connect(self._query_gsm)
        header_row.addWidget(self._btn_refresh_gsm)

        self._btn_refresh_sensors = QPushButton("Датчики")
        self._btn_refresh_sensors.setMinimumHeight(36)
        self._btn_refresh_sensors.clicked.connect(self._query_sensors)
        header_row.addWidget(self._btn_refresh_sensors)

        self._btn_refresh_pwr = QPushButton("Питание")
        self._btn_refresh_pwr.setMinimumHeight(36)
        self._btn_refresh_pwr.clicked.connect(self._query_power)
        header_row.addWidget(self._btn_refresh_pwr)

        main_layout.addLayout(header_row)

        # ── Stat cards ───────────────────────────────────────────────────────
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)

        self._stat_lat = StatCard("Широта", "—")
        self._stat_lng = StatCard("Долгота", "—")
        self._stat_vel = StatCard("Скорость", "0")
        self._stat_vel.set_unit("км/ч")
        self._stat_gsm = StatCard("GSM Сигнал", "0")
        self._stat_gsm.set_unit("из 31")

        for card in (self._stat_lat, self._stat_lng, self._stat_vel, self._stat_gsm):
            cards_row.addWidget(card)

        main_layout.addLayout(cards_row)

        # ── Second row of cards ──────────────────────────────────────────────
        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(12)

        self._stat_events = StatCard("События", "0")
        self._stat_events.set_unit("всего")
        self._stat_errors = StatCard("Ошибки GSM", "0")

        for card in (self._stat_events, self._stat_errors):
            cards_row2.addWidget(card)

        cards_row2.addStretch()
        main_layout.addLayout(cards_row2)

        # ── Event log ────────────────────────────────────────────────────────
        log_card = QFrame()
        log_card.setObjectName("card")
        log_layout = QVBoxLayout(log_card)

        log_header = QHBoxLayout()
        log_title = QLabel("Журнал событий")
        log_title.setObjectName("cardTitle")
        log_header.addWidget(log_title)

        log_header.addStretch()

        self._btn_clear_log = QPushButton("Очистить")
        self._btn_clear_log.setMinimumHeight(36)
        self._btn_clear_log.setAccessibleName("Очистить журнал событий")
        self._btn_clear_log.clicked.connect(self._clear_log)
        log_header.addWidget(self._btn_clear_log)

        log_layout.addLayout(log_header)

        self._event_log = QTextEdit()
        self._event_log.setReadOnly(True)
        self._event_log.setMinimumHeight(250)
        log_layout.addWidget(self._event_log)

        main_layout.addWidget(log_card, stretch=1)

    def _connect_signals(self) -> None:
        self._worker.gps_data.connect(self._on_gps)
        self._worker.gsm_data.connect(self._on_gsm)
        self._worker.hw_test_result.connect(self._on_hw)
        self._worker.sensor_event.connect(self._on_sensor_event)
        self._worker.data_received.connect(self._on_any_data)
        self._worker.power_telemetry.connect(self._on_power)

    # ── Query actions ────────────────────────────────────────────────────────

    def _query_gps(self) -> None:
        self._worker.send_command(build_command_string(CMD_DEBUG_ONLY_POS))

    def _query_gsm(self) -> None:
        self._worker.send_command(build_command_string(CMD_DEBUG_ONLY_GSM))

    def _query_sensors(self) -> None:
        self._worker.send_command(build_command_string(CMD_DEBUG_ONLY_FTG))

    def _query_power(self) -> None:
        self._worker.send_command(build_command_string(CMD_PWR_TM, "15"))

    # ── Response handlers ────────────────────────────────────────────────────

    @pyqtSlot(dict)
    def _on_gps(self, data: dict) -> None:
        lat = data.get("lat", "—")
        lng = data.get("lng", "—")
        vel = data.get("vel", "0")
        self._stat_lat.set_value(lat)
        self._stat_lng.set_value(lng)
        self._stat_vel.set_value(vel, "#00d4aa")
        self._log_event(f"GPS: Lat={lat}, Lng={lng}, Vel={vel} км/ч")

    @pyqtSlot(dict)
    def _on_gsm(self, data: dict) -> None:
        signal = data.get("signal", 0)
        errors = data.get("errors", 0)
        color = "#44ff88" if signal >= GSM_GOOD_SIGNAL else "#ffbb33" if signal > 0 else "#ff5555"
        self._stat_gsm.set_value(str(signal), color)
        self._stat_errors.set_value(str(errors), "#ff5555" if errors > 0 else "#44ff88")
        self._log_event(f"GSM: Signal={signal}, Errors={errors}")

    @pyqtSlot(dict)
    def _on_hw(self, data: dict) -> None:
        vibro = data.get("vibro", 0)
        spk = data.get("spk1", 0)
        self._log_event(f"HW Test: VIBRO={vibro}, SPK={spk}")

    @pyqtSlot(str)
    def _on_sensor_event(self, line: str) -> None:
        self._event_count += 1
        self._stat_events.set_value(str(self._event_count), "#00d4aa")
        self._log_event(f"SENSOR: {line}")

    @pyqtSlot(str)
    def _on_power(self, line: str) -> None:
        self._log_event(f"PWR: {line}")

    @pyqtSlot(str)
    def _on_any_data(self, line: str) -> None:
        # Log interesting lines but not everything
        # NOTE: _event_count is only updated in _on_sensor_event to avoid double counting
        if any(kw in line for kw in ("EYES", "FACE", "PHONE", "SMOKE", "CAL_")):
            self._log_event(f"EVENT: {line}")

    def _log_event(self, text: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._event_log.append(
            f'<span style="color: #8b949e;">[{timestamp}]</span> '
            f'<span style="color: #e6edf3;">{self._escape(text)}</span>'
        )
        scrollbar = self._event_log.verticalScrollBar()
        if scrollbar:
            scrollbar.setValue(scrollbar.maximum())

    def _clear_log(self) -> None:
        self._event_log.clear()
        self._event_count = 0
        self._stat_events.set_value("0")

    @staticmethod
    def _escape(text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
