"""Tests for OKO transport layer."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oko_app.transport import TcpTransport, SerialTransport, TransportType


def test_transport_type_enum() -> None:
    assert TransportType.SERIAL.value == "serial"
    assert TransportType.TCP.value == "tcp"


def test_tcp_transport_creation() -> None:
    tcp = TcpTransport()
    assert tcp.type == TransportType.TCP
    assert tcp.is_connected is False


def test_serial_transport_creation() -> None:
    serial = SerialTransport()
    assert serial.type == TransportType.SERIAL
    assert serial.is_connected is False


def test_tcp_transport_disconnect_when_not_connected() -> None:
    tcp = TcpTransport()
    # Should not raise
    tcp.disconnect()


def test_tcp_transport_send_when_not_connected() -> None:
    tcp = TcpTransport()
    result = tcp.send("test")
    assert result is False


def test_serial_transport_scan_returns_list() -> None:
    ports = SerialTransport.scan_ports()
    assert isinstance(ports, list)


def test_tcp_transport_scan_returns_list() -> None:
    network = TcpTransport.scan_network("192.168.4")
    assert isinstance(network, list)
    assert len(network) == 1  # плата — ТД с фиксированным адресом
    assert network[0].address == "192.168.4.1"


def test_tcp_transport_parse_line_crlf() -> None:
    tcp = TcpTransport()
    lines = tcp.parse_line(b"hello\r\n")
    assert lines == ["hello"]


def test_tcp_transport_parse_line_lf() -> None:
    tcp = TcpTransport()
    lines = tcp.parse_line(b"hello\n")
    assert lines == ["hello"]


def test_tcp_transport_parse_line_multiple() -> None:
    tcp = TcpTransport()
    lines = tcp.parse_line(b"line1\r\nline2\r\n")
    assert lines == ["line1", "line2"]


def test_tcp_transport_parse_line_empty() -> None:
    tcp = TcpTransport()
    lines = tcp.parse_line(b"\r\n")
    assert lines == []


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            failed += 1
            print(f"FAIL: {test.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERROR: {test.__name__}: {e}")

    print(f"\nResults: {passed} passed, {failed} failed, {passed + failed} total")
    if failed > 0:
        sys.exit(1)
    print("All transport tests passed!")
