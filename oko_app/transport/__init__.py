"""Transport abstraction layer for OKO БОД communication.

Unified interface for serial (USB) and TCP (WiFi) transports.
"""

from __future__ import annotations

import asyncio
import socket
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from PyQt5.QtCore import QObject, pyqtSignal


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
            self.error.emit(str(exc))
            self.error.emit(f"Serial connection failed: {exc}")

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


class TcpTransport(BaseTransport):
    """TCP/IP transport (WiFi)."""

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(TransportType.TCP, parent)
        self._socket: Optional[socket.socket] = None
        self._read_buffer = b""
        self._server: Optional[socket.socket] = None

    @property
    def type(self) -> TransportType:
        return TransportType.TCP

    @property
    def is_connected(self) -> bool:
        return self._socket is not None and self._socket.fileno() != -1

    @staticmethod
    def scan_network(subnet: str = "192.168.1") -> list[TransportInfo]:
        """Scan network for OKO devices (port 20000)."""
        result = []
        # Scan common subnet addresses
        for i in range(1, 255):
            host = f"{subnet}.{i}"
            result.append(TransportInfo(
                transport_type=TransportType.TCP,
                address=host,
                description=f"Device at {host}:20000",
                is_connected=False,
            ))
        return result

    def connect(self, address: str, port: int = 20000, **kwargs: Any) -> None:
        """Connect to device via TCP."""
        if self.is_connected:
            self.disconnect()

        try:
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.settimeout(5.0)
            self._socket.connect((address, port))
            self._is_connected = True
            self.connected.emit(f"{address}:{port}")
        except Exception as exc:
            self._is_connected = False
            if self._socket:
                self._socket.close()
                self._socket = None
            self.error.emit(f"TCP connection failed: {exc}")

    def disconnect(self) -> None:
        """Disconnect TCP socket."""
        if self._socket:
            try:
                self._socket.close()
            except Exception:
                pass
            self._socket = None
        self._is_connected = False
        self.disconnected.emit()

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
        self._read_buffer += data
        while b"\n" in self._read_buffer:
            line_bytes, self._read_buffer = self._read_buffer.split(b"\n", 1)
            if line_bytes.endswith(b"\r"):
                line_bytes = line_bytes[:-1]
            line = line_bytes.decode("utf-8", errors="replace").strip()
            if line:
                lines.append(line)
        return lines
