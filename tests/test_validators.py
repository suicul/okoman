"""Tests for OKO configuration validators."""

from __future__ import annotations

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from oko_app.core.validators import ConfigValidator


def test_validate_apn_valid_hostname() -> None:
    valid, msg = ConfigValidator.validate_apn("internet.provider.com")
    assert valid is True
    assert msg == ""


def test_validate_apn_valid_simple() -> None:
    valid, msg = ConfigValidator.validate_apn("internet")
    assert valid is True
    assert msg == ""


def test_validate_apn_empty() -> None:
    valid, msg = ConfigValidator.validate_apn("")
    assert valid is False
    assert "пустым" in msg


def test_validate_apn_too_long() -> None:
    valid, msg = ConfigValidator.validate_apn("a" * 254)
    assert valid is False
    assert "длинный" in msg


def test_validate_mqtt_url_valid() -> None:
    valid, msg = ConfigValidator.validate_mqtt_url("192.168.1.50:1883")
    assert valid is True
    assert msg == ""


def test_validate_mqtt_url_hostname() -> None:
    valid, msg = ConfigValidator.validate_mqtt_url("mqtt.example.com:8883")
    assert valid is True
    assert msg == ""


def test_validate_mqtt_url_empty() -> None:
    valid, msg = ConfigValidator.validate_mqtt_url("")
    assert valid is False
    assert "пустым" in msg


def test_validate_mqtt_url_invalid_format() -> None:
    valid, msg = ConfigValidator.validate_mqtt_url("not-a-url")
    assert valid is False


def test_validate_mqtt_url_invalid_port() -> None:
    valid, msg = ConfigValidator.validate_mqtt_url("192.168.1.1:99999")
    assert valid is False
    assert "порт" in msg


def test_validate_password_valid() -> None:
    valid, msg = ConfigValidator.validate_password("mypassword")
    assert valid is True
    assert msg == ""


def test_validate_password_empty() -> None:
    valid, msg = ConfigValidator.validate_password("")
    assert valid is True  # Password is optional
    assert msg == ""


def test_validate_password_too_long() -> None:
    valid, msg = ConfigValidator.validate_password("a" * 129)
    assert valid is False
    assert "длинный" in msg


def test_validate_gsm_user_valid() -> None:
    valid, msg = ConfigValidator.validate_gsm_user("user_name-1")
    assert valid is True
    assert msg == ""


def test_validate_gsm_user_empty() -> None:
    valid, msg = ConfigValidator.validate_gsm_user("")
    assert valid is True  # Username is optional
    assert msg == ""


def test_validate_gsm_user_invalid_chars() -> None:
    valid, msg = ConfigValidator.validate_gsm_user("user@name!")
    assert valid is False
    assert "содержать" in msg


def test_validate_port_valid() -> None:
    valid, msg = ConfigValidator.validate_port(20000)
    assert valid is True
    assert msg == ""


def test_validate_port_invalid_low() -> None:
    valid, msg = ConfigValidator.validate_port(0)
    assert valid is False
    assert "порт" in msg


def test_validate_port_invalid_high() -> None:
    valid, msg = ConfigValidator.validate_port(65536)
    assert valid is False
    assert "порт" in msg


def test_validate_ip_address_valid() -> None:
    valid, msg = ConfigValidator.validate_ip_address("192.168.1.100")
    assert valid is True
    assert msg == ""


def test_validate_ip_address_invalid() -> None:
    valid, msg = ConfigValidator.validate_ip_address("256.168.1.1")
    assert valid is False
    assert "IP" in msg


def test_validate_ip_address_empty() -> None:
    valid, msg = ConfigValidator.validate_ip_address("")
    assert valid is False
    assert "пустым" in msg


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
    print("All validator tests passed!")
