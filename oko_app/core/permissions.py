"""Platform-specific permission helpers for serial port access."""

from __future__ import annotations

import os
import platform
import subprocess
import grp
from dataclasses import dataclass
from typing import Optional

SERIAL_GROUPS = ["dialout", "uucp", "lock", "tty"]


@dataclass
class PermissionStatus:
    has_access: bool
    platform: str
    message: str
    fix_command: Optional[str] = None
    needs_elevation: bool = False
    group_name: Optional[str] = None


def check_serial_permissions(port: str = "") -> PermissionStatus:
    system = platform.system()
    if system == "Linux":
        return _check_linux(port)
    elif system == "Windows":
        return _check_windows(port)
    elif system == "Darwin":
        return _check_macos(port)
    return PermissionStatus(
        has_access=True,
        platform=system,
        message="Платформа не поддерживается, проверка пропущена",
    )


def _find_serial_group() -> Optional[str]:
    for name in SERIAL_GROUPS:
        try:
            grp.getgrnam(name)
            return name
        except KeyError:
            continue
    return None


def _check_linux(port: str) -> PermissionStatus:
    user = os.getenv("USER", os.getenv("LOGNAME", ""))
    if not user:
        return PermissionStatus(
            has_access=False, platform="Linux",
            message="Не удалось определить пользователя",
        )

    serial_group = _find_serial_group()

    if serial_group:
        try:
            members = grp.getgrnam(serial_group).gr_mem
            if user in members:
                return PermissionStatus(
                    has_access=True, platform="Linux",
                    message="OK — группа {}".format(serial_group),
                    group_name=serial_group,
                )
        except KeyError:
            pass

    if port and os.path.exists(port):
        try:
            with open(port, "r+"):
                pass
            return PermissionStatus(
                has_access=True, platform="Linux",
                message="Доступ есть (группа не найдена, но порт открыт)",
            )
        except PermissionError:
            pass

    if serial_group:
        return PermissionStatus(
            has_access=False, platform="Linux",
            message="Пользователь '{}' не в группе '{}'.".format(user, serial_group),
            fix_command="sudo usermod -aG {} {}".format(serial_group, user),
            needs_elevation=True,
            group_name=serial_group,
        )

    return PermissionStatus(
        has_access=False, platform="Linux",
        message="Не найдена группа для serial-портов (dialout/uucp/lock).",
        needs_elevation=False,
    )


def _check_windows(port: str) -> PermissionStatus:
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        is_admin = False

    if is_admin:
        return PermissionStatus(
            has_access=True, platform="Windows",
            message="Запущено от администратора",
        )

    return PermissionStatus(
        has_access=False, platform="Windows",
        message="Рекомендуется запуск от администратора для доступа к COM-портам.",
        needs_elevation=True,
    )


def _check_macos(port: str) -> PermissionStatus:
    if port and os.path.exists(port):
        try:
            with open(port, "r+"):
                pass
            return PermissionStatus(
                has_access=True, platform="macOS",
                message="Доступ к порту есть",
            )
        except PermissionError:
            pass

    return PermissionStatus(
        has_access=False, platform="macOS",
        message="Нет прав. Попробуйте: sudo chmod 666 {}".format(port or "/dev/tty.usb*"),
        fix_command="sudo chmod 666 {}".format(port or "/dev/tty.usb*"),
        needs_elevation=True,
    )


def try_apply_fix(status: PermissionStatus) -> tuple:
    if not status.fix_command:
        return False, "Нет доступного исправления"

    system = platform.system()
    if system == "Linux":
        try:
            result = subprocess.run(
                ["bash", "-c", status.fix_command],
                capture_output=True, text=True, timeout=30,
            )
            if result.returncode == 0:
                return True, "Группа добавлена. Перелогиньтесь для применения."
            return False, result.stderr or result.stdout
        except Exception as e:
            return False, str(e)
    elif system == "Windows":
        try:
            script = 'Start-Process cmd -ArgumentList "/c {}" -Verb RunAs'.format(status.fix_command)
            subprocess.run(["powershell", "-Command", script], timeout=10)
            return True, "Запущено повышение привилегий (UAC)"
        except Exception as e:
            return False, str(e)

    return False, "Автоматическое исправление не поддерживается"
