"""Connection panel — auto-scan, auto-connect, filtered ports.

Supports USB (serial) and WiFi (TCP) connections.
"""

from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSlot, QTimer
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QFrame,
    QMessageBox,
    QSpinBox,
    QGroupBox,
    QRadioButton,
    QButtonGroup,
    QLineEdit,
)

from ..core.serial_worker import SerialWorker, PortInfo
from ..core.permissions import check_serial_permissions, try_apply_fix
from ..transport import TcpTransport, TransportType


class ConnectionPanel(QWidget):

    def __init__(self, worker: SerialWorker, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._auto_connecting = False
        self._transport_type = TransportType.SERIAL  # Default to USB
        self._tcp_worker = TcpTransport(self)
        self._setup_ui()
        self._connect_signals()
        self._scan_ports()

        self._scan_timer = QTimer(self)
        self._scan_timer.timeout.connect(self._on_scan_tick)
        self._scan_timer.start(3000)

        self._worker.update_known_ports()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        status_row = QHBoxLayout()
        status_row.setSpacing(6)

        self._dot = QFrame()
        self._dot.setFixedSize(10, 10)
        self._dot.setStyleSheet("background-color: #ff5555; border-radius: 5px;")
        status_row.addWidget(self._dot)

        self._status_label = QLabel("Не подключено")
        self._status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        status_row.addWidget(self._status_label)
        status_row.addStretch()

        layout.addLayout(status_row)

        # ── Transport type selector ──────────────────────────────────────
        transport_group = QGroupBox("Тип подключения")
        transport_layout = QHBoxLayout(transport_group)
        transport_layout.setSpacing(12)
        transport_layout.setContentsMargins(8, 4, 8, 4)

        self._radio_usb = QRadioButton("USB")
        self._radio_wifi = QRadioButton("WiFi")
        self._radio_usb.setChecked(True)

        self._transport_group = QButtonGroup(self)
        self._transport_group.addButton(self._radio_usb, 0)
        self._transport_group.addButton(self._radio_wifi, 1)

        self._radio_usb.toggled.connect(self._on_transport_changed)
        self._radio_wifi.toggled.connect(self._on_transport_changed)

        transport_layout.addWidget(self._radio_usb)
        transport_layout.addWidget(self._radio_wifi)
        transport_layout.addStretch()

        layout.addWidget(transport_group)

        # ── Serial port selector ─────────────────────────────────────────
        self._port_selector = QWidget()
        port_layout = QVBoxLayout(self._port_selector)
        port_layout.setContentsMargins(0, 0, 0, 0)
        port_layout.setSpacing(4)

        self._port_combo = QComboBox()
        self._port_combo.setPlaceholderText("COM порт...")
        self._port_combo.setStyleSheet("font-size: 11px;")
        port_layout.addWidget(self._port_combo)

        layout.addWidget(self._port_selector)

        # ── WiFi address selector ────────────────────────────────────────
        self._wifi_selector = QWidget()
        wifi_layout = QVBoxLayout(self._wifi_selector)
        wifi_layout.setContentsMargins(0, 0, 0, 0)
        wifi_layout.setSpacing(4)

        wifi_row1 = QHBoxLayout()
        self._wifi_address = QLineEdit()
        self._wifi_address.setPlaceholderText("IP-адрес устройства")
        self._wifi_address.setText("192.168.1.100")
        self._wifi_address.setStyleSheet("font-size: 11px;")
        wifi_row1.addWidget(self._wifi_address)

        self._wifi_port_spin = QSpinBox()
        self._wifi_port_spin.setRange(1, 65535)
        self._wifi_port_spin.setValue(20000)
        self._wifi_port_spin.setFixedWidth(70)
        self._wifi_port_spin.setSuffix(" :port")
        self._wifi_port_spin.setStyleSheet("font-size: 11px;")
        wifi_row1.addWidget(self._wifi_port_spin)

        wifi_layout.addLayout(wifi_row1)

        layout.addWidget(self._wifi_selector)

        # ── Connection buttons ───────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(4)

        self._refresh_btn = QPushButton("\u27f3")
        self._refresh_btn.setFixedSize(28, 28)
        self._refresh_btn.setToolTip("Обновить")
        self._refresh_btn.clicked.connect(self._scan_ports)
        btn_row.addWidget(self._refresh_btn)

        self._connect_btn = QPushButton("Подключить")
        self._connect_btn.setObjectName("primaryButton")
        self._connect_btn.clicked.connect(self._toggle_connection)
        btn_row.addWidget(self._connect_btn)

        layout.addLayout(btn_row)

        self._auto_label = QLabel("")
        self._auto_label.setStyleSheet("color: #ffbb33; font-size: 10px;")
        self._auto_label.hide()
        layout.addWidget(self._auto_label)

        self._device_info = QLabel("")
        self._device_info.setStyleSheet("color: #00d4aa; font-size: 11px;")
        self._device_info.setWordWrap(True)
        self._device_info.hide()
        layout.addWidget(self._device_info)

        # Initially show serial, hide WiFi
        self._wifi_selector.hide()

    def _connect_signals(self) -> None:
        self._worker.connected.connect(self._on_connected)
        self._worker.disconnected.connect(self._on_disconnected)
        self._worker.connection_failed.connect(self._on_failed)
        self._worker.version_info.connect(self._on_version)
        self._worker.permission_error.connect(self._on_permission_error)

        # WiFi signals
        self._tcp_worker.connected.connect(self._on_tcp_connected)
        self._tcp_worker.disconnected.connect(self._on_tcp_disconnected)
        self._tcp_worker.error.connect(self._on_tcp_error)

    def _on_transport_changed(self) -> None:
        """Switch between USB and WiFi transport."""
        if self._transport_group.checkedId() == 0:
            self._transport_type = TransportType.SERIAL
            self._port_selector.show()
            self._wifi_selector.hide()
            self._scan_ports()
        else:
            self._transport_type = TransportType.TCP
            self._port_selector.hide()
            self._wifi_selector.show()
            self._wifi_address.setFocus()

    @pyqtSlot()
    def _scan_ports(self) -> None:
        current = self._port_combo.currentText()
        self._port_combo.blockSignals(True)
        self._port_combo.clear()

        try:
            ports = SerialWorker.scan_ports()
            usb_ports = [p for p in ports if p.is_usb]
            other_ports = [p for p in ports if not p.is_usb]

            for p in usb_ports:
                label = "{} ({})".format(p.device, p.description[:30])
                self._port_combo.addItem(label, p.device)

            if other_ports and len(usb_ports) < 5:
                for p in other_ports:
                    self._port_combo.addItem(p.device, p.device)

            if not self._port_combo.count():
                self._port_combo.setPlaceholderText("Нет портов")
        except Exception:
            self._port_combo.setPlaceholderText("Ошибка сканирования")

        if current:
            for i in range(self._port_combo.count()):
                if self._port_combo.itemData(i) == current:
                    self._port_combo.setCurrentIndex(i)
                    break

        self._port_combo.blockSignals(False)

    def _on_scan_tick(self) -> None:
        if self._worker.is_connected or self._auto_connecting:
            return

        new_ports = self._worker.get_new_ports()
        usb_new = [p for p in new_ports if self._is_usb_port(p)]

        if usb_new:
            self._auto_label.show()
            self._auto_label.setText("Найдено: {}".format(usb_new[0]))
            self._try_auto_connect(usb_new[0])
        else:
            current = set(self._worker.available_ports())
            combo_ports = set()
            for i in range(self._port_combo.count()):
                d = self._port_combo.itemData(i)
                if d:
                    combo_ports.add(d)
            if current != combo_ports:
                self._scan_ports()

    def _is_usb_port(self, port_name: str) -> bool:
        for p in SerialWorker.scan_ports():
            if p.device == port_name and p.is_usb:
                return True
        return False

    def _try_auto_connect(self, port: str) -> None:
        if self._auto_connecting or self._worker.is_connected:
            return
        self._auto_connecting = True
        self._status_label.setText("Авто-подключение...")
        self._status_label.setStyleSheet("color: #ffbb33; font-size: 11px;")
        self._auto_label.setText("Попытка: {}".format(port))

        self._worker.connection_failed.connect(self._on_auto_failed)
        self._worker.connected.connect(self._on_auto_connected)
        self._worker.connect_to(port)

    @pyqtSlot(str)
    def _on_auto_connected(self, port: str) -> None:
        self._auto_connecting = False
        try:
            self._worker.connection_failed.disconnect(self._on_auto_failed)
            self._worker.connected.disconnect(self._on_auto_connected)
        except TypeError:
            pass
        self._auto_label.hide()

    @pyqtSlot(str)
    def _on_auto_failed(self, reason: str) -> None:
        self._auto_connecting = False
        try:
            self._worker.connection_failed.disconnect(self._on_auto_failed)
            self._worker.connected.disconnect(self._on_auto_connected)
        except TypeError:
            pass
        self._auto_label.setText("Не ОКО устройство, ожидание...")
        QTimer.singleShot(2000, lambda: self._auto_label.hide())
        self._status_label.setText("Не подключено")
        self._status_label.setStyleSheet("color: #8b949e; font-size: 11px;")

    @pyqtSlot()
    def _toggle_connection(self) -> None:
        if self._worker.is_connected:
            self._worker.disconnect()
        elif self._transport_type == TransportType.TCP:
            self._connect_wifi()
        else:
            port = self._port_combo.currentData()
            if not port:
                port = self._port_combo.currentText()
            if not port:
                return
            self._connect_btn.setEnabled(False)
            self._connect_btn.setText("...")
            self._status_label.setText("Подключение...")
            self._status_label.setStyleSheet("color: #ffbb33; font-size: 11px;")
            self._worker.connect_to(port)

    def _connect_wifi(self) -> None:
        """Connect via WiFi (TCP)."""
        address = self._wifi_address.text().strip()
        if not address:
            self._status_label.setText("Введите IP-адрес")
            self._status_label.setStyleSheet("color: #ff5555; font-size: 11px;")
            return

        port = self._wifi_port_spin.value()
        self._connect_btn.setEnabled(False)
        self._connect_btn.setText("...")
        self._status_label.setText("Подключение по WiFi...")
        self._status_label.setStyleSheet("color: #ffbb33; font-size: 11px;")

        self._tcp_worker.connect(address, port)

    @pyqtSlot(str)
    def _on_connected(self, port: str) -> None:
        self._dot.setStyleSheet("background-color: #44ff88; border-radius: 5px;")
        self._status_label.setText("Подключено")
        self._status_label.setStyleSheet("color: #44ff88; font-size: 11px;")
        self._connect_btn.setText("Откл.")
        self._connect_btn.setObjectName("dangerButton")
        self._connect_btn.setStyleSheet("")
        self._connect_btn.setEnabled(True)
        self._port_combo.setEnabled(False)
        self._device_info.show()
        self._device_info.setText("...")

    @pyqtSlot()
    def _on_disconnected(self) -> None:
        self._dot.setStyleSheet("background-color: #ff5555; border-radius: 5px;")
        self._status_label.setText("Не подключено")
        self._status_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        self._connect_btn.setText("Подключить")
        self._connect_btn.setObjectName("primaryButton")
        self._connect_btn.setStyleSheet("")
        self._connect_btn.setEnabled(True)
        self._port_combo.setEnabled(True)
        self._device_info.hide()

    @pyqtSlot(str)
    def _on_failed(self, reason: str) -> None:
        self._on_disconnected()
        self._status_label.setText("Ошибка")
        self._status_label.setStyleSheet("color: #ff5555; font-size: 11px;")

    @pyqtSlot(str, str)
    def _on_permission_error(self, message: str, fix_cmd: str) -> None:
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("Нет прав доступа")
        msg.setText(message)
        if fix_cmd:
            msg.setInformativeText("Исправить автоматически?\nКоманда: {}".format(fix_cmd))
            msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg.button(QMessageBox.Yes).setText("Исправить")
            msg.button(QMessageBox.No).setText("Отмена")
            if msg.exec_() == QMessageBox.Yes:
                ok, output = try_apply_fix(check_serial_permissions())
                if ok:
                    QMessageBox.information(self, "Готово", output)
                else:
                    QMessageBox.warning(self, "Ошибка", output)
        else:
            msg.exec_()

    @pyqtSlot(str, str)
    def _on_version(self, version: str, build_date: str) -> None:
        self._device_info.setText("v{} | {}".format(version, build_date))

    # ── WiFi handlers ─────────────────────────────────────────────────────

    @pyqtSlot(str)
    def _on_tcp_connected(self, address: str) -> None:
        self._dot.setStyleSheet("background-color: #44ff88; border-radius: 5px;")
        self._status_label.setText("Подключено по WiFi")
        self._status_label.setStyleSheet("color: #44ff88; font-size: 11px;")
        self._connect_btn.setText("Откл.")
        self._connect_btn.setObjectName("dangerButton")
        self._connect_btn.setStyleSheet("")
        self._connect_btn.setEnabled(True)
        self._port_combo.setEnabled(False)
        self._device_info.show()
        self._device_info.setText("WiFi: {}".format(address))

    @pyqtSlot()
    def _on_tcp_disconnected(self) -> None:
        self._on_disconnected()

    @pyqtSlot(str)
    def _on_tcp_error(self, message: str) -> None:
        self._on_disconnected()
        self._status_label.setText("Ошибка WiFi")
        self._status_label.setStyleSheet("color: #ff5555; font-size: 11px;")
        self._connect_btn.setEnabled(True)
        self._connect_btn.setText("Подключить")
        self._connect_btn.setObjectName("primaryButton")
        self._connect_btn.setStyleSheet("")
