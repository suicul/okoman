from __future__ import annotations

from oko_app.core.serial_worker import _SerialReader, decode_response_line
from oko_app.core.serial_worker import SerialWorker
from oko_app.ui.dashboard import AUTO_SCAN_COMMANDS


class FakePort:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self.is_open = True

    @property
    def in_waiting(self) -> int:
        return len(self._payload)

    def read(self, size: int) -> bytes:
        chunk = self._payload[:size]
        self._payload = self._payload[size:]
        if not self._payload:
            self.is_open = False
        return chunk


def read_lines(payload: bytes) -> list[str]:
    reader = _SerialReader(FakePort(payload))
    lines: list[str] = []
    reader.line_ready.connect(lines.append)
    reader.run()
    return lines


def test_reader_accepts_crlf() -> None:
    assert read_lines(b"first\r\nsecond\r\n") == ["first", "second"]


def test_reader_accepts_cr_only() -> None:
    assert read_lines(b"first\rsecond\r") == ["first", "second"]


def test_reader_accepts_lf_only() -> None:
    assert read_lines(b"first\nsecond\n") == ["first", "second"]


def test_decoder_preserves_utf8_text() -> None:
    assert decode_response_line("Ответ 123".encode("utf-8")) == "Ответ 123"


def test_decoder_supports_cp1251_text() -> None:
    assert decode_response_line("Ответ 123".encode("cp1251")) == "Ответ 123"


def test_decoder_exposes_unrecognised_bytes_as_hex() -> None:
    decoded = decode_response_line(b"\xff\xfe\x00\x80")
    assert "HEX: FF FE 00 80" in decoded


def test_ready_banner_does_not_complete_version_request() -> None:
    worker = SerialWorker()
    port = WritablePort()
    worker._serial = port
    completed: list[str] = []
    worker.command_completed.connect(
        lambda request_id, command, response: completed.append(command)
    )
    worker.queue_command("VER", "ver")
    worker._on_line("OKO_001460 Ready!")
    assert completed == []


def test_worker_emits_raw_response_and_parses_serial_number() -> None:
    worker = SerialWorker()
    raw: list[str] = []
    serial_numbers: list[str] = []
    worker.data_received.connect(raw.append)
    worker.serial_number.connect(serial_numbers.append)

    worker._on_line("Serial: 002503")

    assert raw == ["Serial: 002503"]
    assert serial_numbers == ["002503"]


def test_worker_collects_settings_lines() -> None:
    worker = SerialWorker()
    settings: list[dict] = []
    worker.settings_data.connect(settings.append)

    worker._on_line("GSM_APN=internet.example")
    worker._on_line("MQTT_URL=mqtt.example:1883")

    assert settings[-1] == {
        "GSM_APN": "internet.example",
        "MQTT_URL": "mqtt.example:1883",
    }


class WritablePort:
    def __init__(self) -> None:
        self.is_open = True
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    def flush(self) -> None:
        pass


def test_worker_queues_fifo_until_response() -> None:
    worker = SerialWorker()
    port = WritablePort()
    worker._serial = port
    completed: list[str] = []
    worker.command_completed.connect(
        lambda request_id, command, response: completed.append(command)
    )

    worker.queue_command("VER", "ver")
    worker.queue_command("serial", "serial")

    assert port.writes == [b"VER\r\n"]
    worker._on_line("Firmware Version: 2.2")
    assert port.writes == [b"VER\r\n"]
    worker._on_line("Build Date: Jan 1 2025")
    assert port.writes == [b"VER\r\n", b"serial\r\n"]
    worker._on_line("Serial: 002503")
    assert completed == ["VER", "serial"]


def test_worker_timeout_retries_then_fails() -> None:
    worker = SerialWorker()
    port = WritablePort()
    worker._serial = port
    failures: list[tuple[str, str]] = []
    worker.command_failed.connect(
        lambda request_id, command, reason: failures.append((command, reason))
    )

    worker.queue_command("DEBUG ONLY GSM", "gsm", timeout_ms=1, retries=1)
    worker._on_command_timeout()
    assert port.writes == [b"DEBUG ONLY GSM\r\n", b"DEBUG ONLY GSM\r\n"]
    worker._on_command_timeout()
    assert failures and failures[0][0] == "DEBUG ONLY GSM"


def test_worker_disconnect_cancels_active_and_queued_commands() -> None:
    worker = SerialWorker()
    port = WritablePort()
    worker._serial = port
    cancelled: list[str] = []
    worker.command_cancelled.connect(
        lambda request_id, command: cancelled.append(command)
    )
    worker.queue_command("VER")
    worker.queue_command("serial")
    worker._cancel_commands()
    assert cancelled == ["VER", "serial"]


def test_scan_request_ids_isolate_foreign_commands() -> None:
    worker = SerialWorker()
    port = WritablePort()
    worker._serial = port
    done: list[tuple[int, str]] = []
    worker.command_completed.connect(
        lambda request_id, command, response: done.append((request_id, command))
    )
    scan_id = worker.queue_command("VER", "ver", owner="scan")
    other_id = worker.queue_command("VER", "ver", owner="term")
    assert scan_id != other_id
    worker._on_line("Firmware Version: 2.2")
    worker._on_line("Build Date: Jan 1 2025")
    assert done[0] == (scan_id, "VER")


def test_set_block_completes_only_on_terminator() -> None:
    worker = SerialWorker()
    port = WritablePort()
    worker._serial = port
    done: list[str] = []
    worker.command_completed.connect(
        lambda request_id, command, response: done.append(command)
    )
    worker.queue_command("SET", "set", timeout_ms=5000)
    worker._on_line("GSM_APN=internet")
    assert done == []
    worker._on_line("MQTT_URL=x:1883")
    assert done == []
    worker._on_line("READY")
    assert done == ["SET"]


def test_auto_scan_contains_only_documented_information_commands() -> None:
    commands = [item[0] if isinstance(item[0], str) else item[0].syntax for item in AUTO_SCAN_COMMANDS]
    assert commands == ["VER", "serial", "DEBUG ONLY POS", "DEBUG ONLY GSM", "SET"]
    assert "TEST HW" not in commands
    assert "SET AS" not in commands


if __name__ == "__main__":
    for name, test in sorted(globals().items()):
        if name.startswith("test_"):
            test()
    print("serial worker regression tests passed")
