"""Threaded serial connection manager for OKO БОД."""

from __future__ import annotations

import re
import time
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Optional, NamedTuple

import serial
import serial.tools.list_ports
from PyQt5.QtCore import QThread, pyqtSignal, pyqtSlot, QObject, QTimer

from .permissions import check_serial_permissions


USB_KEYWORDS = [
    "USB", "usb", "CH34", "ch34", "CP210", "cp210", "CP21", "cp21",
    "FTDI", "ftdi", "FT", "ft", "UART", "uart", "ACM", "acm",
    "SERIAL", "serial", "CDC", "cdc", "STM", "stm", "STMicro",
    "stmicro", "Virtual COM", "virtual com", "VCP", "vcp",
    "0483", "339b", "2232", "1a86", "10c4", "ea60",
]


def decode_response_line(line_bytes: bytes) -> str:
    if not line_bytes:
        return ""

    # Try UTF-8 first
    try:
        decoded = line_bytes.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded = line_bytes.decode("cp1251")
        except UnicodeDecodeError:
            decoded = line_bytes.decode("ascii", errors="replace")

    # Strip ANSI escape codes: \x1b[...m, \x1b[K, \x1b[2K, etc.
    import re
    decoded = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', decoded)
    # Strip \r\n
    decoded = decoded.strip()

    # Бинарный мусор (нулевые/управляющие символы) показываем как HEX,
    # иначе в терминал попадут «кракозябры» вместо диагностики.
    # Проверка ПОСЛЕ снятия ANSI: сам ESC уже вырезан выше.
    if any(ord(ch) < 32 and ch not in ("\t", "\r", "\n") for ch in decoded):
        hex_view = " ".join("{:02X}".format(b) for b in line_bytes)
        return "HEX: {}".format(hex_view)

    return decoded


class PortInfo(NamedTuple):
    device: str
    description: str
    hwid: str
    is_usb: bool


@dataclass
class CommandRequest:
    command: str
    response_kind: str = "line"
    timeout_ms: int = 10000
    retries: int = 0
    owner: str = ""
    request_id: int = 0


class SerialWorker(QObject):

    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    data_received = pyqtSignal(str)
    error = pyqtSignal(str)
    connection_failed = pyqtSignal(str)
    permission_error = pyqtSignal(str, str)
    device_found = pyqtSignal(str, str)

    version_info = pyqtSignal(str, str)
    serial_number = pyqtSignal(str)
    gps_data = pyqtSignal(dict)
    gsm_data = pyqtSignal(dict)
    hw_test_result = pyqtSignal(dict)
    button_event = pyqtSignal(int)
    sensor_event = pyqtSignal(str)
    power_telemetry = pyqtSignal(str)
    settings_data = pyqtSignal(dict)
    reader_error = pyqtSignal(str)
    command_completed = pyqtSignal(int, str, str)
    command_failed = pyqtSignal(int, str, str)
    command_cancelled = pyqtSignal(int, str)

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._serial: Optional[serial.Serial] = None
        self._reading = False
        self._read_thread: Optional[QThread] = None
        self._reader: Optional[_SerialReader] = None
        self._known_ports: set = set()
        self._pending_fw_ver: Optional[str] = None
        self._pending_settings: dict = {}
        self._in_settings_block = False
        self._command_queue = []
        self._active_request: Optional[CommandRequest] = None
        self._active_attempt = 0
        self._command_timer = QTimer(self)
        self._command_timer.setSingleShot(True)
        self._command_timer.timeout.connect(self._on_command_timeout)
        self._next_request_id = 1
        self._pending_gps: dict = {}
        self._last_gps_time: float = 0  # Throttle GPS updates
        self._last_ver_time: float = 0  # Filter duplicate VER responses
        # Внешний транспорт (WiFi/TCP): функция отправки байт и флаг линка.
        # Позволяет гнать очередь команд и парсинг через общий тракт _on_line
        # как для USB, так и для WiFi — без дублирования логики.
        self._ext_send: Optional[Callable[[bytes], None]] = None
        self._ext_connected: bool = False

    # ── Внешний транспорт (WiFi/TCP) ────────────────────────────────────

    def attach_external(self, send_fn: Callable[[bytes], None]) -> None:
        """Подключить внешний канал отправки (например, TCP-сокет WiFi).

        После attach очередь команд и парсинг ответов работают так же,
        как для USB. Входящие строки внешнего канала нужно подавать
        в on_external_line().
        """
        self._ext_send = send_fn
        self._ext_connected = True
        self._cancel_commands()

    def detach_external(self) -> None:
        """Отключить внешний канал."""
        self._ext_send = None
        self._ext_connected = False
        self._cancel_commands()

    @pyqtSlot(str)
    def on_external_line(self, line: str) -> None:
        """Принять строку от внешнего транспорта (WiFi/TCP)."""
        if self._ext_connected:
            self._on_line(line)

    @staticmethod
    def available_ports() -> list:
        ports = []
        try:
            for p in serial.tools.list_ports.comports():
                # Filter out virtual COM ports (ttyS*)
                if p.device.startswith('/dev/ttyS'):
                    continue
                ports.append(p.device)
        except Exception:
            pass
        return ports

    @staticmethod
    def usb_ports() -> list:
        result = []
        try:
            for p in serial.tools.list_ports.comports():
                # Filter out virtual COM ports (ttyS*)
                if p.device.startswith('/dev/ttyS'):
                    continue
                desc = p.description or ""
                hwid = p.hwid or ""
                is_usb = any(kw in desc or kw in hwid for kw in USB_KEYWORDS)
                if is_usb:
                    result.append(p.device)
        except Exception:
            pass
        return result

    @staticmethod
    def scan_ports() -> list:
        result = []
        try:
            for p in serial.tools.list_ports.comports():
                # Filter out virtual COM ports (ttyS*)
                if p.device.startswith('/dev/ttyS'):
                    continue
                desc = p.description or ""
                hwid = p.hwid or ""
                is_usb = any(kw in desc or kw in hwid for kw in USB_KEYWORDS)
                result.append(PortInfo(
                    device=p.device,
                    description=desc,
                    hwid=hwid,
                    is_usb=is_usb,
                ))
        except Exception:
            pass
        return result

    def get_new_ports(self) -> list:
        current = set(self.available_ports())
        new = current - self._known_ports
        self._known_ports = current
        return list(new)

    def update_known_ports(self) -> None:
        self._known_ports = set(self.available_ports())

    #: Маркеры «живого» ответа БОД на пробный VER (см. руководство, разд. 6).
    _PROBE_MARKERS = (b"Ver", b"ver", b"Version", b"Firmware", b"Serial", b">>", b"OK")

    @staticmethod
    def auto_detect_baud(port: str, bauds: tuple = (115200, 57600, 38400, 19200, 9600)) -> Optional[int]:
        """Try baud rates (сначала 115200 из руководства) и вернуть первый с живым ответом."""
        fallback: Optional[int] = None
        for baud in bauds:
            try:
                s = serial.Serial(
                    port=port, baudrate=baud,
                    bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE, timeout=2,
                )
                try:
                    s.reset_input_buffer()
                    s.write(b"VER\r\n")
                    s.flush()
                    time.sleep(0.8)
                    response = s.read(s.in_waiting or 1024)
                finally:
                    s.close()
                if not response:
                    continue
                if any(m in response for m in SerialWorker._PROBE_MARKERS):
                    return baud
                if fallback is None:
                    fallback = baud  # порт открывается, но молчит — запомним как запасной
            except Exception:
                continue
        return fallback

    @pyqtSlot(str)
    def connect_to(self, port: str, baud: int = 115200) -> None:
        if self.is_connected or (self._read_thread and self._read_thread.isRunning()):
            self.disconnect()

        perm = check_serial_permissions(port)
        if not perm.has_access and perm.needs_elevation:
            self.permission_error.emit(perm.message, perm.fix_command or "")
            self.connection_failed.emit(perm.message)
            return

        # Try connecting with specified baud first
        effective_baud = baud
        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            )
            # Пробный VER: даём устройству время ответить (без сна read почти
            # всегда пустой и проверка бессмысленна).
            self._serial.reset_input_buffer()
            self._serial.write(b"VER\r\n")
            self._serial.flush()
            time.sleep(0.6)
            _resp = self._serial.read(self._serial.in_waiting or 1024)
            # Порт открыт — устройство считаем живым; содержимое проверит автоскан.
        except serial.SerialException:
            # Port failed - try auto-detect
            if self._serial:
                try:
                    self._serial.close()
                except Exception:
                    pass
                self._serial = None

            detected = self.auto_detect_baud(port)
            if detected:
                effective_baud = detected
            else:
                self.connection_failed.emit(
                    "Не удалось открыть порт {}.\n\nВозможные причины:\n"
                    "• Устройство отключено\n• Порт занят другим приложением\n"
                    "• Неверные права доступа".format(port)
                )
                return

        # Connect with effective baud (or reuse existing if already opened)
        try:
            # Only open new port if we closed the previous one
            if self._serial is None:
                self._serial = serial.Serial(
                    port=port,
                    baudrate=effective_baud,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE,
                    timeout=1,
                )
            self._reading = True
            self._in_settings_block = False
            self._pending_settings = {}
            self._cancel_commands()
            self._start_reader()
            self.connected.emit(port)
        except serial.SerialException as exc:
            err = str(exc)
            if any(kw in err.lower() for kw in ("permission", "access", "denied")):
                perm = check_serial_permissions(port)
                err = "{}\n\n{}".format(err, perm.message)
            self.connection_failed.emit("Ошибка подключения к {}: {}".format(port, err))

    def _start_reader(self) -> None:
        if self._read_thread and self._read_thread.isRunning():
            self._reading = False
            self._read_thread.quit()
            self._read_thread.wait()

        self._read_thread = QThread(self)
        self._reader = _SerialReader(self._serial)
        self._reader.moveToThread(self._read_thread)
        self._reader.line_ready.connect(self._on_line)
        self._reader.read_error.connect(self._on_reader_error)
        self._read_thread.started.connect(self._reader.run)
        self._reader.finished.connect(self._read_thread.quit)
        self._read_thread.start()

    @pyqtSlot()
    def disconnect(self) -> None:
        self._cancel_commands()
        self._reading = False
        self._ext_send = None
        self._ext_connected = False
        if self._reader:
            self._reader.stop()
        if self._read_thread and self._read_thread.isRunning():
            self._read_thread.quit()
            self._read_thread.wait(2000)
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._reader = None
        self.disconnected.emit()

    @pyqtSlot(str)
    def _on_reader_error(self, message: str) -> None:
        self.reader_error.emit(message)
        self.error.emit(message)
        if self.is_connected:
            self.disconnect()

    @property
    def is_connected(self) -> bool:
        serial_ok = self._serial is not None and self._serial.is_open
        return serial_ok or self._ext_connected

    @pyqtSlot(str)
    def send_command(self, command: str, response_kind: str = "line",
                     timeout_ms: int = 10000, retries: int = 0,
                     owner: str = "") -> int:
        request = CommandRequest(
            command.strip(), response_kind, timeout_ms, retries,
            owner, self._next_request_id,
        )
        self._next_request_id += 1
        if not self.is_connected:
            self.error.emit("Нет подключения")
            return request.request_id
        self._command_queue.append(request)
        self._start_next_command()
        return request.request_id

    def queue_command(self, command: str, response_kind: str = "line",
                      timeout_ms: int = 10000, retries: int = 0,
                      owner: str = "") -> int:
        return self.send_command(command, response_kind, timeout_ms, retries, owner)

    def _start_next_command(self) -> None:
        if self._active_request is not None or not self.is_connected:
            return
        if not self._command_queue:
            return
        self._active_request = self._command_queue.pop(0)
        self._active_attempt = 0
        self._write_active_command()

    def _write_active_command(self) -> None:
        request = self._active_request
        if request is None or not self.is_connected:
            return
        if request.response_kind == "set":
            self._pending_settings = {}
            self._in_settings_block = False
        if request.response_kind == "ver":
            self._pending_fw_ver = None
        if request.response_kind == "pos":
            self._pending_gps = {}
        try:
            data = (request.command + "\r\n").encode("ascii")
            logging.getLogger("oko.command").info(
                "SEND command=%r bytes=%s external=%s",
                request.command,
                data.hex(" "),
                self._ext_send is not None,
            )
            if self._ext_send is not None and self._ext_connected:
                self._ext_send(data)  # WiFi/TCP тракт
            else:
                assert self._serial is not None
                self._serial.write(data)
                self._serial.flush()
            self._active_attempt += 1
            self._command_timer.start(request.timeout_ms)
        except (serial.SerialException, OSError) as exc:
            self._finish_active(False, "Ошибка отправки: {}".format(exc))

    def _on_command_timeout(self) -> None:
        if self._active_request is not None:
            logging.getLogger("oko.command").warning(
                "TIMEOUT command=%r attempt=%s",
                self._active_request.command,
                self._active_attempt,
            )
        request = self._active_request
        if request is None:
            return
        if self._active_attempt <= request.retries:
            self._write_active_command()
        else:
            self._finish_active(False, "Тайм-аут ответа ({})".format(request.command))

    def _finish_active(self, success: bool, response: str = "") -> None:
        request = self._active_request
        if request is None:
            return
        self._command_timer.stop()
        if request.response_kind == "set":
            self._in_settings_block = False
        self._active_request = None
        if success:
            self.command_completed.emit(request.request_id, request.command, response)
        else:
            self.command_failed.emit(request.request_id, request.command, response)
        self._start_next_command()

    def _cancel_commands(self) -> None:
        self._command_timer.stop()
        requests = list(self._command_queue)
        if self._active_request is not None:
            requests.insert(0, self._active_request)
        self._command_queue = []
        self._active_request = None
        self._in_settings_block = False
        for request in requests:
            self.command_cancelled.emit(request.request_id, request.command)

    def cancel_request(self, request_id: int) -> None:
        if self._active_request is not None and self._active_request.request_id == request_id:
            pending = self._active_request
            self._command_timer.stop()
            self._active_request = None
            self._in_settings_block = False
            self.command_cancelled.emit(pending.request_id, pending.command)
            self._start_next_command()
            return
        for i, request in enumerate(self._command_queue):
            if request.request_id == request_id:
                del self._command_queue[i]
                self.command_cancelled.emit(request.request_id, request.command)
                return

    def _on_line(self, line: str) -> None:
        # Filter empty/whitespace lines immediately
        if not line or not line.strip():
            return
        
        # Strip ANSI codes and timestamp first
        stripped = re.sub(r'\x1b\[[0-9;]*[mGKH]', '', line).strip()
        stripped = re.sub(r'^\d{2}:\d{2}:\d{2}\s+', '', stripped)

        # Filter empty lines after stripping
        if not stripped:
            return
        
        # Filter device prompt lines (>> comes from device)
        if stripped == '>>':
            return

        # Check if this is GPS spam - filter from terminal always
        is_gps = re.search(r"POS:\s*--\s*RMC", stripped, re.IGNORECASE)
        # Check if this is the SET block end marker
        is_set_end = "======" in stripped and "Last Address" in stripped and "Len:" in stripped
        # Check if this is a SET prefix line
        is_set_prefix = re.match(r"^SET:\s*", stripped, re.IGNORECASE)
        # Check if this is a key=value pair (settings block)
        is_kv_pair = re.match(r"^\w[\w]*\s*=\s*", stripped) and not is_gps

        if is_gps:
            # GPS lines - parse for dashboard but NEVER emit to terminal
            self._parse_gps_line(stripped)
            self._match_active_response(stripped)
            return

        if is_set_end or is_set_prefix or is_kv_pair:
            # Settings block lines - NEVER emit to terminal
            if is_set_end:
                self._parse_settings_end(stripped)
            else:
                # Filter GPS spam that appears inside SET block
                if not re.search(r"POS:\s*--\s*RMC", stripped, re.IGNORECASE):
                    self._parse_settings_line(stripped)
                    self._match_active_response(stripped)
            return

        # Filter duplicate VER responses (same line within 2 seconds)
        if "Ver:" in stripped and "MCU" in stripped:
            now = time.time()
            if now - self._last_ver_time < 2.0:
                return  # Skip duplicate VER
            self._last_ver_time = now

        # Конец SET-блока словом-маркером (старые прошивки шлют READY/OK
        # вместо строки «====== Last Address ... Len:»).
        if stripped in ("READY", "OK", "DONE"):
            self._parse_settings_end(stripped)
            self._match_active_response(stripped)
            return

        # All other lines go to terminal
        if stripped:  # Don't emit empty lines
            self.data_received.emit(line)
        self._parse_line(stripped)
        self._match_active_response(stripped)

    def _match_active_response(self, line: str) -> None:
        request = self._active_request
        if request is None:
            return
        kind = request.response_kind
        if kind == "set":
            return
        matched = {
            "line": True,
            # VER из двух строк: «Firmware Version: X» + «Build Date: ...» —
            # завершаем по строке со сборкой (Make:/Build), иначе очередь
            # убежит дальше до прихода даты сборки.
            "ver": any(kw in line for kw in ("Make:", "make:", "Build", "build")),
            "serial": re.search(r"(Serial|SERIAL)[:\s]", line, re.IGNORECASE) is not None,
            "pos": re.search(r"(Lat|Lng|Pos|POS):", line, re.IGNORECASE) is not None,
            "gsm": re.search(r"Signal:\s*\d+", line, re.IGNORECASE) is not None,
        }.get(kind, True)
        if matched:
            self._finish_active(True, line)

    def _parse_line(self, line: str) -> None:
        # ── Firmware version ──
        # Format: "CMD: MCU: ST Ver: 00242.SUEKKUZ [A7682E] Make: May 15 2025 12:23:42"
        # Also: "Ver: 00242.SUEKKUZ [A7682E]"
        ver_match = re.search(r"(Ver|ver|Version|version):\s*(\S+)", line, re.IGNORECASE)
        if ver_match and self._pending_fw_ver is None:
            ver = ver_match.group(2)
            # Extract build date if present
            make_match = re.search(r"Make:\s*(.+?)(?:\s*\]|$)", line, re.IGNORECASE)
            build = make_match.group(1).strip() if make_match else ""
            
            # Extract firmware version from brackets like [A7682E]
            bracket_match = re.search(r"\[([^\]]+)\]", line)
            bracket_ver = bracket_match.group(1) if bracket_match else ""
            
            # Combine: main version + bracket version
            if bracket_ver and bracket_ver not in ver:
                full_ver = "{} [{}]".format(ver, bracket_ver)
            else:
                full_ver = ver
            
            self.version_info.emit(full_ver, build if build else "unknown")
            self._pending_fw_ver = ver
            return

        # ── Serial number ──
        # Format: "SERIAL: The board serial number is 001479"
        serial_match = re.search(r"(Serial|serial|SERIAL)[:\s]+(.+)", line)
        if serial_match:
            serial_text = serial_match.group(2).strip()
            # Extract just the number
            num_match = re.search(r'(\d+)', serial_text)
            if num_match:
                self.serial_number.emit(num_match.group(1))
            else:
                self.serial_number.emit(serial_text)
            return

        # ── GPS position (already filtered in _on_line, but keep for safety) ──
        if re.search(r"POS:\s*--\s*RMC", line, re.IGNORECASE):
            self._parse_gps_line(line)
            return

        # ── GSM debug ──
        gsm_match = re.search(r"\[?GSM\]?\s*Signal:\s*(\d+)", line, re.IGNORECASE)
        if gsm_match:
            gsm = {"signal": int(gsm_match.group(1)), "errors": 0}
            err_m = re.search(r"Errors?:\s*(\d+)", line, re.IGNORECASE)
            if err_m:
                gsm["errors"] = int(err_m.group(1))
            mqtt_m = re.search(r"MQTT[:\]]?\s*(.*)", line, re.IGNORECASE)
            if mqtt_m:
                gsm["mqtt_status"] = mqtt_m.group(1).strip()
            self.gsm_data.emit(gsm)
            return

        # ── Hardware test ──
        hw_match = re.search(
            r"VIBRO=(\d+),\s*SPK=(\d+)/(\d+),\s*GPSANT=(\d+),\s*FTG=(\d+)", line
        )
        if hw_match:
            self.hw_test_result.emit({
                "vibro": int(hw_match.group(1)),
                "spk1": int(hw_match.group(2)),
                "spk2": int(hw_match.group(3)),
                "gpsant": int(hw_match.group(4)),
                "ftg": int(hw_match.group(5)),
            })
            return

        # ── Button ──
        btn_match = re.search(r"Button pressed (\d+) times", line, re.IGNORECASE)
        if btn_match:
            self.button_event.emit(int(btn_match.group(1)))
            return

        # ── Sensor events ──
        if re.search(r"EYES|FACE|PHONE|SMOKE", line, re.IGNORECASE):
            self.sensor_event.emit(line)
            return
        if "The Button" in line:
            self.sensor_event.emit(line)
            return

        # ── Power telemetry ──
        if re.search(r"pwr|VIBRO|SPK=", line, re.IGNORECASE):
            self.power_telemetry.emit(line)

    def _parse_gps_line(self, line: str) -> None:
        """Parse GPS line and emit to dashboard (throttled)."""
        # Throttle GPS updates - max 1 per second
        now = time.time()
        if now - self._last_gps_time < 1.0:
            return  # Skip duplicate GPS
        self._last_gps_time = now

        gps = {}
        for key in ("Time", "Date", "Lat", "Lng", "Vel", "Fix", "Crs"):
            m = re.search(r"{}:\s*([^|]+)".format(key), line, re.IGNORECASE)
            if m:
                gps[key.lower()] = m.group(1).strip()
        if gps:
            self.gps_data.emit(gps)

    def _parse_settings_line(self, line: str) -> None:
        """Parse a SET key=value line and add to pending settings."""
        stripped = line.strip()

        # Format: "SET: Key = Value", "SET: Key=Value" или голый "KEY=VALUE"
        # (плата в разных прошивках шлёт оба варианта).
        set_match = re.match(r"^(?:SET:\s*)?(.+?)\s*=\s*(.+)$", stripped, re.IGNORECASE)
        if set_match:
            key = set_match.group(1).strip()
            val = set_match.group(2).strip()
            # Normalize key names
            key = self._normalize_setting_key(key)
            self._pending_settings[key] = val
            self.settings_data.emit(dict(self._pending_settings))
            return

    def _parse_settings_end(self, line: str) -> None:
        """Handle end of settings block."""
        active = self._active_request
        self._in_settings_block = False

        if active is not None and active.response_kind == "set":
            # Завершаем SET-запрос и при пустом блоке: маркер конца пришёл,
            # висеть до таймаута (60 с в автоскане) нельзя.
            self._finish_active(True, "SET block: {} keys".format(len(self._pending_settings)))

        # Clear settings to avoid duplicate parsing
        self._pending_settings = {}

    def _normalize_setting_key(self, key: str) -> str:
        """Normalize setting key names to match expected format."""
        key_map = {
            "gsm_apn": "GSM_APN",
            "gsm_user": "GSM_USER",
            "gsm_pwd": "GSM_PWD",
            "mqtt_url": "MQTT_URL",
            "mqtt_clientid": "MQTT_CLIENTID",
            "spkvol": "SpkVol",
            "gpsbaudrate": "GPS_BAUDRATE",
            "pwrmode": "PWR_MODE",
            "gsm": "GSM",
            "can": "CAN",
            "reg": "REG",
            "gpsgnss": "Gps",
            "gpsdynamic": "GpsDynamic",
            "gpsvelstab": "GpsVelStab",
            "gpsvelmax": "GpsVelMax",
            "canvelstab": "CanVelStab",
            "cancutoff": "CanCutoff",
            "tmcollect": "TmCollect",
            "tm_pub": "TmPub",
            "update": "Update",
            "debug": "DEBUG",
            "outdelay": "OutDelay",
            "hwtestperiod": "HwTestPeriod",
            "vibrottime": "VibroTime",
        }
        lower_key = key.lower()
        return key_map.get(lower_key, key)


class _SerialReader(QThread):
    """Read serial data in a background thread, split by any line ending."""

    line_ready = pyqtSignal(str)
    finished = pyqtSignal()
    read_error = pyqtSignal(str)

    def __init__(self, serial_port: serial.Serial) -> None:
        super().__init__()
        self._port = serial_port
        self._running = True

    def run(self) -> None:
        buffer = b""
        try:
            while self._running:
                if not self._port or not self._port.is_open:
                    break
                try:
                    waiting = self._port.in_waiting
                    if waiting > 0:
                        chunk = self._port.read(waiting)
                    else:
                        chunk = self._port.read(1)
                    if chunk:
                        buffer += chunk
                        while True:
                            delimiters = [
                                index for index in (buffer.find(b"\r"), buffer.find(b"\n"))
                                if index >= 0
                            ]
                            if not delimiters:
                                break
                            delimiter_index = min(delimiters)
                            line_bytes = buffer[:delimiter_index]
                            delimiter = buffer[delimiter_index:delimiter_index + 1]
                            buffer = buffer[delimiter_index + 1:]
                            if delimiter == b"\r" and buffer.startswith(b"\n"):
                                buffer = buffer[1:]
                            line = decode_response_line(line_bytes)
                            # Strict filter: only emit non-empty, non-whitespace lines
                            if line and line.strip():
                                self.line_ready.emit(line)
                    else:
                        self.msleep(10)
                except (serial.SerialException, OSError) as exc:
                    self.read_error.emit("Ошибка чтения порта: {}".format(exc))
                    break
        finally:
            # Flush remaining buffer (may end with \r only)
            if buffer:
                line = decode_response_line(buffer).strip()
                if line:
                    self.line_ready.emit(line)

            self.finished.emit()

    def stop(self) -> None:
        self._running = False
