"""Configuration panel — parameter editor for БОД settings."""

from __future__ import annotations

import json
from typing import Optional

from PyQt5.QtCore import Qt, pyqtSlot
from PyQt5.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QGroupBox,
    QMessageBox,
    QScrollArea,
    QFileDialog,
)

from ..core.serial_worker import SerialWorker
from ..core.commands import (
    CMD_SET_GSM_APN,
    CMD_SET_GSM_USER,
    CMD_SET_GSM_PWD,
    CMD_SET_MQTT_URL,
    CMD_SET_SPK_VOL,
    CMD_SET_REG,
    CMD_SET_GPS,
    CMD_SET_AS,
    CMD_SET_NO_PARAM,
    build_command_string,
)
from ..core.validators import ConfigValidator


class ConfigField(QWidget):

    def __init__(
        self,
        label: str,
        placeholder: str = "",
        validator_type: str = "",
        parent: QWidget = None,
    ) -> None:
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self._label = QLabel(label)
        self._label.setStyleSheet("color: #8b949e; font-size: 11px; font-weight: 500;")
        layout.addWidget(self._label)

        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._validator_type = validator_type
        self._error_label = QLabel("")
        self._error_label.setStyleSheet("color: #ff5555; font-size: 10px;")
        self._error_label.hide()
        self._input.textChanged.connect(self._validate)
        layout.addWidget(self._input)
        layout.addWidget(self._error_label)

    def _validate(self) -> None:
        if not self._validator_type:
            self._error_label.hide()
            return

        value = self._input.text().strip()
        valid, msg = getattr(ConfigValidator, f"validate_{self._validator_type}")(value)

        if not valid:
            self._error_label.setText(msg)
            self._error_label.show()
            self._input.setStyleSheet(
                "border: 1px solid #ff5555; border-radius: 8px; "
                "padding: 8px 12px; background-color: #21262d; color: #e6edf3;"
            )
        else:
            self._error_label.hide()
            self._input.setStyleSheet("")

    def text(self) -> str:
        return self._input.text().strip()

    def set_text(self, value: str) -> None:
        self._input.setText(value)

    def is_valid(self) -> bool:
        if not self._validator_type:
            return True
        value = self._input.text().strip()
        valid, _ = getattr(ConfigValidator, f"validate_{self._validator_type}")(value)
        return valid

    def validate_and_show(self) -> bool:
        """Validate and show error if invalid. Returns True if valid."""
        self._validate()
        return not self._error_label.isVisible()


class Configuration(QWidget):

    def __init__(self, worker: SerialWorker, parent: QWidget = None) -> None:
        super().__init__(parent)
        self._worker = worker
        self._cfg_pending: set = set()
        self._setup_ui()
        self._worker.command_completed.connect(self._on_cfg_done)
        self._worker.command_failed.connect(self._on_cfg_done)
        self._worker.command_cancelled.connect(self._on_cfg_cancelled)

    @pyqtSlot(dict)
    def apply_settings(self, data: dict) -> None:
        """Apply settings from device to UI fields."""
        if "SpkVol" in data:
            self._spin_volume.setValue(float(data["SpkVol"]))
        if "GSM_APN" in data:
            self._field_apn.set_text(data["GSM_APN"])
        if "GSM_USER" in data:
            self._field_gsm_user.set_text(data["GSM_USER"])
        if "GSM_PWD" in data:
            self._field_gsm_pwd.set_text(data["GSM_PWD"])
        if "MQTT_URL" in data:
            self._field_mqtt.set_text(data["MQTT_URL"])
        if "REG" in data:
            self._combo_reg.setCurrentIndex(0 if data["REG"] == "4" else 1)
        if "Gps" in data:
            self._combo_gps.setCurrentIndex(0 if data["Gps"] == "GNSS" else 1)

    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(20, 20, 20, 20)

        header = QLabel("Конфигурация")
        header.setStyleSheet("font-size: 24px; font-weight: 700; color: #e6edf3;")
        main_layout.addWidget(header)

        gsm_group = QGroupBox("Настройки SIM-карты / GSM")
        gsm_layout = QVBoxLayout(gsm_group)
        gsm_layout.setSpacing(12)

        self._field_apn = ConfigField(
            "APN (Точка доступа)", "internet.provider.com", "apn"
        )
        self._field_gsm_user = ConfigField(
            "Логин (если нужен)", "login", "gsm_user"
        )
        self._field_gsm_pwd = ConfigField(
            "Пароль (если нужен)", "password", "password"
        )

        gsm_layout.addWidget(self._field_apn)
        gsm_layout.addWidget(self._field_gsm_user)
        gsm_layout.addWidget(self._field_gsm_pwd)

        gsm_btn_row = QHBoxLayout()
        gsm_btn_row.addStretch()
        self._btn_apply_gsm = QPushButton("Применить GSM")
        self._btn_apply_gsm.setObjectName("primaryButton")
        self._btn_apply_gsm.clicked.connect(self._apply_gsm)
        gsm_btn_row.addWidget(self._btn_apply_gsm)
        gsm_layout.addLayout(gsm_btn_row)

        main_layout.addWidget(gsm_group)

        mqtt_group = QGroupBox("Настройки MQTT-сервера")
        mqtt_layout = QVBoxLayout(mqtt_group)
        mqtt_layout.setSpacing(12)

        self._field_mqtt = ConfigField(
            "Адрес сервера (IP:порт)", "mqtt.oko-server.com:1883", "mqtt_url"
        )
        mqtt_layout.addWidget(self._field_mqtt)

        mqtt_btn_row = QHBoxLayout()
        mqtt_btn_row.addStretch()
        self._btn_apply_mqtt = QPushButton("Применить MQTT")
        self._btn_apply_mqtt.setObjectName("primaryButton")
        self._btn_apply_mqtt.clicked.connect(self._apply_mqtt)
        mqtt_btn_row.addWidget(self._btn_apply_mqtt)
        mqtt_layout.addLayout(mqtt_btn_row)

        main_layout.addWidget(mqtt_group)

        device_group = QGroupBox("Параметры устройства")
        device_layout = QVBoxLayout(device_group)
        device_layout.setSpacing(16)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(12)
        vol_label = QLabel("Громкость динамика")
        vol_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        vol_label.setFixedWidth(160)
        vol_row.addWidget(vol_label)

        self._spin_volume = QDoubleSpinBox()
        self._spin_volume.setRange(0.0, 1.0)
        self._spin_volume.setSingleStep(0.1)
        self._spin_volume.setValue(0.7)
        self._spin_volume.setFixedWidth(100)
        vol_row.addWidget(self._spin_volume)

        vol_row.addStretch()
        self._btn_apply_vol = QPushButton("Установить")
        self._btn_apply_vol.clicked.connect(self._apply_volume)
        vol_row.addWidget(self._btn_apply_vol)
        device_layout.addLayout(vol_row)

        reg_row = QHBoxLayout()
        reg_row.setSpacing(12)
        reg_label = QLabel("Тип регистратора")
        reg_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        reg_label.setFixedWidth(160)
        reg_row.addWidget(reg_label)

        self._combo_reg = QComboBox()
        self._combo_reg.addItems(["4 канала", "8 каналов"])
        self._combo_reg.setFixedWidth(140)
        reg_row.addWidget(self._combo_reg)

        reg_row.addStretch()
        self._btn_apply_reg = QPushButton("Установить")
        self._btn_apply_reg.clicked.connect(self._apply_reg)
        reg_row.addWidget(self._btn_apply_reg)
        device_layout.addLayout(reg_row)

        gps_row = QHBoxLayout()
        gps_row.setSpacing(12)
        gps_label = QLabel("Режим GPS")
        gps_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        gps_label.setFixedWidth(160)
        gps_row.addWidget(gps_label)

        self._combo_gps = QComboBox()
        self._combo_gps.addItems(["GNSS", "GLONASS"])
        self._combo_gps.setFixedWidth(140)
        gps_row.addWidget(self._combo_gps)

        gps_row.addStretch()
        self._btn_apply_gps = QPushButton("Установить")
        self._btn_apply_gps.clicked.connect(self._apply_gps)
        gps_row.addWidget(self._btn_apply_gps)
        device_layout.addLayout(gps_row)

        main_layout.addWidget(device_group)

        save_card = QFrame()
        save_card.setObjectName("card")
        save_layout = QHBoxLayout(save_card)
        save_layout.setContentsMargins(16, 12, 16, 12)

        save_info = QLabel("Сохраняет настройки в EEPROM (постоянную память)")
        save_info.setStyleSheet("color: #ffbb33; font-size: 11px;")
        save_layout.addWidget(save_info)
        save_layout.addStretch()

        self._btn_save = QPushButton("Сохранить всё (SET AS)")
        self._btn_save.setObjectName("primaryButton")
        self._btn_save.clicked.connect(self._save_all)
        save_layout.addWidget(self._btn_save)

        main_layout.addWidget(save_card)

        # ── Export/Import ────────────────────────────────────────────────
        io_card = QFrame()
        io_card.setObjectName("card")
        io_layout = QVBoxLayout(io_card)

        io_title = QLabel("Экспорт / Импорт настроек")
        io_title.setObjectName("cardTitle")
        io_layout.addWidget(io_title)

        io_btn_row = QHBoxLayout()

        self._btn_export = QPushButton("📤 Экспорт в JSON")
        self._btn_export.clicked.connect(self._export_config)
        io_btn_row.addWidget(self._btn_export)

        self._btn_import = QPushButton("📥 Импорт из JSON")
        self._btn_import.clicked.connect(self._import_config)
        io_btn_row.addWidget(self._btn_import)

        io_layout.addLayout(io_btn_row)
        main_layout.addWidget(io_card)

        # ── Current settings ───────────────────────────────────────────
        view_card = QFrame()
        view_card.setObjectName("card")
        view_layout = QVBoxLayout(view_card)
        view_layout.setSpacing(10)

        view_title = QLabel("Текущие настройки")
        view_title.setObjectName("cardTitle")
        view_layout.addWidget(view_title)

        self._btn_view_settings = QPushButton("Запросить настройки (SET)")
        self._btn_view_settings.clicked.connect(self._view_settings)
        view_layout.addWidget(self._btn_view_settings)

        self._cfg_status = QLabel("")
        self._cfg_status.setStyleSheet("color: #8b949e; font-size: 11px;")
        view_layout.addWidget(self._cfg_status)

        main_layout.addWidget(view_card)
        main_layout.addStretch()

        scroll.setWidget(container)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def _set_busy(self, busy: bool) -> None:
        for btn in (self._btn_apply_gsm, self._btn_apply_mqtt,
                    self._btn_apply_vol, self._btn_apply_reg,
                    self._btn_apply_gps, self._btn_save,
                    self._btn_view_settings):
            btn.setEnabled(not busy)

    def _show_toast(self, message: str, toast_type: str = "info") -> None:
        """Show toast notification (will be connected externally)."""
        # Signal will be connected from MainWindow
        pass

    def _queue_writes(self, commands: list) -> None:
        if not self._worker.is_connected:
            self._cfg_status.setText("Нет подключения")
            return
        self._set_busy(True)
        self._cfg_status.setText("Применение настроек...")
        for cmd in commands:
            rid = self._worker.queue_command(cmd, "line", 8000, 0, owner="cfg")
            self._cfg_pending.add(rid)
        rid = self._worker.queue_command(
            build_command_string(CMD_SET_NO_PARAM), "set", 15000, 1, owner="cfg-reread"
        )
        self._cfg_pending.add(rid)

    @pyqtSlot(int, str, str)
    def _on_cfg_done(self, request_id: int, command: str, response: str) -> None:
        if request_id not in self._cfg_pending:
            return
        self._cfg_pending.discard(request_id)
        if not self._cfg_pending:
            self._set_busy(False)
            self._cfg_status.setText("Настройки обновлены")
            # Show toast notification
            if "SET" in command.upper():
                self._show_toast("Настройки применены", "success")
            else:
                self._show_toast("Операция завершена", "info")

    @pyqtSlot(int, str)
    def _on_cfg_cancelled(self, request_id: int, command: str) -> None:
        if request_id not in self._cfg_pending:
            return
        self._cfg_pending.discard(request_id)
        if not self._cfg_pending:
            self._set_busy(False)
            self._cfg_status.setText("Операция отменена")

    def _apply_gsm(self) -> None:
        if not self._field_apn.validate_and_show():
            return
        if not self._field_gsm_user.validate_and_show():
            return
        if not self._field_gsm_pwd.validate_and_show():
            return

        apn = self._field_apn.text()
        user = self._field_gsm_user.text()
        pwd = self._field_gsm_pwd.text()
        cmds = []
        if apn:
            cmds.append(build_command_string(CMD_SET_GSM_APN, apn))
        if user:
            cmds.append(build_command_string(CMD_SET_GSM_USER, user))
        if pwd:
            cmds.append(build_command_string(CMD_SET_GSM_PWD, pwd))
        if cmds:
            self._queue_writes(cmds)

    def _apply_mqtt(self) -> None:
        if not self._field_mqtt.validate_and_show():
            return

        addr = self._field_mqtt.text()
        if addr:
            self._queue_writes([build_command_string(CMD_SET_MQTT_URL, addr)])

    def _apply_volume(self) -> None:
        vol = self._spin_volume.value()
        self._queue_writes([build_command_string(CMD_SET_SPK_VOL, str(vol))])

    def _apply_reg(self) -> None:
        val = "4" if self._combo_reg.currentIndex() == 0 else "8"
        self._queue_writes([build_command_string(CMD_SET_REG, val)])

    def _apply_gps(self) -> None:
        val = "GNSS" if self._combo_gps.currentIndex() == 0 else "GLONASS"
        self._queue_writes([build_command_string(CMD_SET_GPS, val)])

    def _save_all(self) -> None:
        if not self._worker.is_connected:
            self._cfg_status.setText("Нет подключения")
            return
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Сохранить настройки в EEPROM (SET AS)?",
            QMessageBox.Yes | QMessageBox.No,
        )
        if reply != QMessageBox.Yes:
            return
        self._set_busy(True)
        self._cfg_status.setText("Сохранение в EEPROM...")
        rid = self._worker.queue_command(
            build_command_string(CMD_SET_AS), "line", 10000, 0, owner="cfg"
        )
        self._cfg_pending.add(rid)
        rid2 = self._worker.queue_command(
            build_command_string(CMD_SET_NO_PARAM), "set", 15000, 1, owner="cfg-reread"
        )
        self._cfg_pending.add(rid2)

    def _view_settings(self) -> None:
        if not self._worker.is_connected:
            self._cfg_status.setText("Нет подключения")
            return
        self._cfg_status.setText("Запрос настроек...")
        rid = self._worker.queue_command(
            build_command_string(CMD_SET_NO_PARAM), "set", 15000, 1, owner="cfg-reread"
        )
        self._cfg_pending.add(rid)

    # ── Export / Import ────────────────────────────────────────────────

    def _export_config(self) -> None:
        """Export current configuration fields to a JSON file."""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Экспорт конфигурации", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        config = {
            "version": "1.0",
            "gsm": {
                "apn": self._field_apn.text(),
                "user": self._field_gsm_user.text(),
                "password": self._field_gsm_pwd.text(),
            },
            "mqtt": {
                "url": self._field_mqtt.text(),
            },
            "device": {
                "volume": self._spin_volume.value(),
                "registrar_channels": "4" if self._combo_reg.currentIndex() == 0 else "8",
                "gps_mode": self._combo_gps.currentText(),
            },
        }

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            self._cfg_status.setText("Конфигурация экспортирована: {}".format(file_path))
            self._cfg_status.setStyleSheet("color: #44ff88; font-size: 11px;")
            self._show_toast("Конфигурация экспортирована", "success")
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", "Не удалось сохранить файл:\n{}".format(exc))
            self._show_toast("Ошибка экспорта", "error")

    def _import_config(self) -> None:
        """Import configuration from a JSON file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Импорт конфигурации", "", "JSON Files (*.json)"
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as exc:
            QMessageBox.warning(self, "Ошибка", "Не удалось прочитать файл:\n{}".format(exc))
            return

        # Populate fields
        gsm = config.get("gsm", {})
        self._field_apn.set_text(gsm.get("apn", ""))
        self._field_gsm_user.set_text(gsm.get("user", ""))
        self._field_gsm_pwd.set_text(gsm.get("password", ""))

        mqtt = config.get("mqtt", {})
        self._field_mqtt.set_text(mqtt.get("url", ""))

        device = config.get("device", {})
        volume = device.get("volume", 0.7)
        self._spin_volume.setValue(float(volume))

        reg_channels = device.get("registrar_channels", "4")
        self._combo_reg.setCurrentIndex(0 if reg_channels == "4" else 1)

        gps_mode = device.get("gps_mode", "GNSS")
        self._combo_gps.setCurrentIndex(0 if gps_mode == "GNSS" else 1)

        self._cfg_status.setText("Конфигурация импортирована: {}".format(file_path))
        self._cfg_status.setStyleSheet("color: #44ff88; font-size: 11px;")
        self._show_toast("Конфигурация импортирована", "success")
