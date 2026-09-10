"""Transport abstraction layer for OKO БОД communication.

Unified interface for serial (USB) and TCP (WiFi) transports.
"""

from __future__ import annotations

import asyncio
import socket
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal, QThread, pyqtSlot


class TransportType(Enum):
    """Type of transport."""
    SERIAL = "serial"
    TCP = "tcp"


@dataclass
class TransportInfo:
    """Information about a transport connection."""
    transport_type: TransportType
    address: str
    description: str = ""
    is_connected: bool = False


class BaseTransport(QObject):
    """Abstract base class for all transports.

    Note: Cannot use abc.ABC with QObject due to metaclass conflict.
    Instead, use NotImplementedError for abstract methods.
    """

    connected = pyqtSignal(str)  # address
    disconnected = pyqtSignal()
    data_received = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, transport_type: TransportType, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._type = transport_type
        self._is_connected = False

    @property
    def type(self) -> TransportType:
        """Transport type. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement 'type'")

    @property
    def is_connected(self) -> bool:
        """Whether transport is connected. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement 'is_connected'")

    def connect(self, address: str, **kwargs: Any) -> None:
        """Connect to device. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement 'connect'")

    def disconnect(self) -> None:
        """Disconnect from device. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement 'disconnect'")

    def send(self, data: str) -> bool:
        """Send data to device. Returns True on success. Must be overridden."""
        raise NotImplementedError("Subclasses must implement 'send'")

    def scan(self) -> list[TransportInfo]:
        """Scan for available connections. Must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement 'scan'")

    def _emit_data(self, line: str) -> None:
        """Emit parsed line."""
        if line:
            self.data_received.emit(line)


class SerialTransport(BaseTransport):
    """Serial port transport (USB)."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(TransportType.SERIAL, parent)
        self._serial = None
        self._read_thread = None
        self._running = False

    @property
    def type(self) -> TransportType:
        return TransportType.SERIAL

    @property
    def is_connected(self) -> bool:
        return self._serial is not None and self._serial.is_open

    @staticmethod
    def scan_ports() -> list[TransportInfo]:
        """Scan for available serial ports."""
        try:
            import serial.tools.list_ports
        except ImportError:
            return []

        USB_KEYWORDS = [
            "USB", "usb", "CH34", "ch34", "CP210", "cp210", "CP21", "cp21",
            "FTDI", "ftdi", "FT", "ft", "UART", "uart", "ACM", "acm",
            "SERIAL", "serial", "CDC", "cdc", "STM", "stm", "STMicro",
            "stmicro", "Virtual COM", "virtual com", "VCP", "vcp",
            "0483", "339b", "2232", "1a86", "10c4", "ea60",
        ]

        result = []
        for p in serial.tools.list_ports.comports():
            try:
                desc = p.description or ""
                hwid = p.hwid or ""
                is_usb = any(kw in desc or kw in hwid for kw in USB_KEYWORDS)
                result.append(TransportInfo(
                    transport_type=TransportType.SERIAL,
                    address=p.device,
                    description=desc[:40] or p.device,
                    is_connected=False,
                ))
            except Exception:
                # Skip ports that can't be enumerated
                continue
        return result

    def connect(self, address: str, baud: int = 115200, **kwargs: Any) -> None:
        """Connect to serial port."""
        if self.is_connected:
            self.disconnect()

        try:
            import serial
            self._serial = serial.Serial(
                port=address,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1,
            )
            self._is_connected = True
            self.connected.emit(address)
        except Exception as exc:
            self._is_connected = False
            self.error.emit("Serial connection failed: {}".format(exc))

    def disconnect(self) -> None:
        """Disconnect from serial port."""
        if self._serial and self._serial.is_open:
            self._serial.close()
        self._serial = None
        self._is_connected = False
        self.disconnected.emit()

    def send(self, data: str) -> bool:
        """Send data via serial."""
        if not self.is_connected or not self._serial:
            self.error.emit("Not connected")
            return False
        try:
            self._serial.write((data + "\r\n").encode("ascii"))
            self._serial.flush()
            return True
        except Exception as exc:
            self.error.emit(f"Send error: {exc}")
            return False

    def scan(self) -> list[TransportInfo]:
        """Scan for serial ports."""
        return self.scan_ports()


class _TcpReader(QThread):
    """Фоновое чтение TCP-сокета, нарезка на строки \\r\\n/\\n."""

    line_ready = pyqtSignal(str)
    finished = pyqtSignal()
    read_error = pyqtSignal(str)

    def __init__(self, sock: socket.socket) -> None:
        super().__init__()
        self._sock = sock
        self._running = True

    def run(self) -> None:
        buf = b""
        log = logging.getLogger("oko.tcp")
        try:
            while self._running:
                try:
                    chunk = self._sock.recv(4096)
                except socket.timeout:
                    continue
                except (OSError, ConnectionError) as exc:
                    self.read_error.emit("Ошибка чтения WiFi: {}".format(exc))
                    break
                if not chunk:
                    self.read_error.emit("Устройство закрыло WiFi-соединение")
                    break
                # Сырой дамп: какой бы EOL ни слала прошивка (\r\n, \n или
                # голый \r), по hex видно реальный формат строк.
                log.debug("TCP RX raw %d bytes: %s", len(chunk), chunk.hex(" "))
                # Нормализация окончаний: \r\n и голый \r → \n, чтобы ответы
                # с \r без \n не застревали в буфере навсегда.
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    raw = raw.rstrip(b"\r")
                    line = raw.decode("utf-8", errors="replace").strip()
                    if line:
                        log.debug("TCP RX line hex: %s", raw.hex(" "))
                        self.line_ready.emit(line)
        finally:
            if buf:
                line = buf.decode("utf-8", errors="replace").strip()
                if line:
                    self.line_ready.emit(line)
            self.finished.emit()

    def stop(self) -> None:
        self._running = False


class TcpTransport(BaseTransport):
    """TCP/IP transport (WiFi: ТД OKO_XXXXXX, 192.168.4.1:1234)."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(TransportType.TCP, parent)
        self._socket: Optional[socket.socket] = None
        self._read_buffer = b""
        self._read_thread: Optional[_TcpReader] = None
        self._reader: Optional[_TcpReader] = None

    @property
    def type(self) -> TransportType:
        return TransportType.TCP

    @property
    def is_connected(self) -> bool:
        return self._socket is not None and self._socket.fileno() != -1

    @staticmethod
    def scan_network(subnet: str = "192.168.4") -> list[TransportInfo]:
        """Сканирование сети: активного пробинга нет (плата — точка доступа
        с фиксированным 192.168.4.1:1234), поэтому возвращаем кандидата
        по умолчанию, а не 254 фейковых хоста."""
        return [TransportInfo(
            transport_type=TransportType.TCP,
            address="192.168.4.1",
            description="БОД (ТД OKO_XXXXXX) 192.168.4.1:1234",
            is_connected=False,
        )]

    def connect(self, address: str = "192.168.4.1", port: int = 1234, **kwargs: Any) -> None:
        """Connect to device via TCP (WiFi ТД платы)."""
        if self.is_connected:
            self.disconnect()

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((address, port))
            self._socket.settimeout(1.0)
            self._is_connected = True
            logging.getLogger("oko.tcp").info("TCP connected to %s:%s", address, port)
            self._start_reader()
            self.connected.emit(f"{address}:{port}")
        except Exception as exc:
            self._is_connected = False
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
            self.error.emit(f"TCP connection failed: {exc}")

    def disconnect(self) -> None:
        """Disconnect TCP socket."""
        if self._reader is not None:
            self._reader.stop()
        if self._read_thread is not None and self._read_thread.isRunning():
            self._read_thread.quit()
            self._read_thread.wait(2000)
        self._reader = None
        self._read_thread = None
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._is_connected = False
        self.disconnected.emit()

    def send_raw(self, data: bytes) -> None:
        """Отправить готовые байты (мост для SerialWorker)."""
        if not self.is_connected or not self._socket:
            raise OSError("Нет подключения")
        logging.getLogger("oko.tcp").info("TCP TX %s bytes: %s", len(data), data.hex(" "))
        self._socket.sendall(data)
        logging.getLogger("oko.tcp").info("TCP TX completed")

    def _start_reader(self) -> None:
        assert self._socket is not None
        self._read_thread = QThread(self)
        self._reader = _TcpReader(self._socket)
        self._reader.moveToThread(self._read_thread)
        self._reader.line_ready.connect(self._on_reader_line)
        self._reader.read_error.connect(self._on_reader_error)
        self._reader.finished.connect(self._read_thread.quit)
        self._read_thread.started.connect(self._reader.run)
        self._read_thread.start()

    @pyqtSlot(str)
    def _on_reader_line(self, line: str) -> None:
        logging.getLogger("oko.tcp").info("TCP RX: %s", line)
        self._emit_data(line)

    @pyqtSlot(str)
    def _on_reader_error(self, message: str) -> None:
        logging.getLogger("oko.tcp").error("TCP reader error: %s", message)
        self.error.emit(message)
        if self.is_connected:
            self.disconnect()

    def send(self, data: str) -> bool:
        """Send data via TCP."""
        if not self.is_connected or not self._socket:
            self.error.emit("Not connected")
            return False
        try:
            self._socket.sendall((data + "\r\n").encode("ascii"))
            return True
        except Exception as exc:
            self.error.emit(f"Send error: {exc}")
            self.disconnect()
            return False

    def scan(self) -> list[TransportInfo]:
        """Scan for TCP devices."""
        return self.scan_network()

    def parse_line(self, data: bytes) -> list[str]:
        """Parse lines from TCP data (handles \\r\\n, \\r, \\n)."""
        lines = []
        self._read_buffer += data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        while b"\n" in self._read_buffer:
            line_bytes, self._read_buffer = self._read_buffer.split(b"\n", 1)
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if line:
                lines.append(line)
        return lines
