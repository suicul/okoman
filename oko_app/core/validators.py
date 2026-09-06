"""Input validators for OKO БОД configuration fields."""

from __future__ import annotations

import re
from typing import Optional


class ConfigValidator:
    """Static methods for validating configuration inputs."""

    @staticmethod
    def validate_apn(value: str) -> tuple[bool, str]:
        """Validate APN value.

        APN should be a valid hostname or IP address.
        Examples: internet, mms.provider.com, 10.0.0.1
        """
        if not value:
            return False, "APN не может быть пустым"

        # Check if it's a valid hostname
        if len(value) > 253:
            return False, "APN слишком длинный (макс. 253 символа)"

        # Hostname validation
        pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,251}[a-zA-Z0-9])?$'
        if not re.match(pattern, value):
            return False, "Неверный формат APN (например: internet.provider.com)"

        return True, ""

    @staticmethod
    def validate_mqtt_url(value: str) -> tuple[bool, str]:
        """Validate MQTT server URL.

        Should be IP:port or hostname:port.
        Examples: 192.168.1.50:1883, mqtt.example.com:8883
        """
        if not value:
            return False, "MQTT URL не может быть пустым"

        # Split into host and port
        if ':' not in value:
            return False, "Неверный формат (например: 192.168.1.50:1883)"

        parts = value.rsplit(':', 1)
        if len(parts) != 2:
            return False, "Неверный формат (например: 192.168.1.50:1883)"

        host_part = parts[0]
        port_str = parts[1]

        # Validate port
        if not port_str.isdigit():
            return False, "Неверный формат порта"

        port = int(port_str)
        if port < 1 or port > 65535:
            return False, "Неверный порт (1-65535)"

        # Validate host (hostname or IP)
        # Check if it's an IP address
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host_part):
            for octet in host_part.split('.'):
                if int(octet) > 255:
                    return False, "Неверный IP-адрес"
        else:
            # Hostname validation
            if len(host_part) > 253:
                return False, "Хост слишком длинный"
            pattern = r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]{0,251}[a-zA-Z0-9])?$'
            if not re.match(pattern, host_part):
                return False, "Неверный формат хоста"

        return True, ""

    @staticmethod
    def validate_password(value: str) -> tuple[bool, str]:
        """Validate password field.

        Password can be empty (optional) or any non-empty string.
        """
        if value and len(value) > 128:
            return False, "Пароль слишком длинный (макс. 128 символов)"
        return True, ""

    @staticmethod
    def validate_gsm_user(value: str) -> tuple[bool, str]:
        """Validate GSM username.

        Username can be empty (optional) or alphanumeric with _-.
        """
        if value and len(value) > 64:
            return False, "Логин слишком длинный (макс. 64 символа)"

        if value:
            pattern = r'^[a-zA-Z0-9_\-\.]+$'
            if not re.match(pattern, value):
                return False, "Логин может содержать буквы, цифры, _-. "

        return True, ""

    @staticmethod
    def validate_port(value: int) -> tuple[bool, str]:
        """Validate TCP port number."""
        if value < 1 or value > 65535:
            return False, "Неверный порт (1-65535)"
        return True, ""

    @staticmethod
    def validate_ip_address(value: str) -> tuple[bool, str]:
        """Validate IP address format."""
        if not value:
            return False, "IP-адрес не может быть пустым"

        pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        if not re.match(pattern, value):
            return False, "Неверный формат IP-адреса (например: 192.168.1.100)"

        for octet in value.split('.'):
            if int(octet) > 255:
                return False, "Неверный IP-адрес"

        return True, ""
