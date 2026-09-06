"""Logging module for OKO БОД Manager.

Provides file + console logging with configurable levels.
All log messages are also emitted as Qt signals for UI integration.
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from typing import Optional

from PyQt5.QtCore import QObject, pyqtSignal


class LogEmitter(QObject):
    """Emits log messages as Qt signals."""

    log_message = pyqtSignal(str, str)  # level, message


class OkoLogger:
    """Application logger for OKO БОД Manager."""

    _instance: Optional[OkoLogger] = None
    _emitter: Optional[LogEmitter] = None

    def __init__(self, log_file: Optional[str] = None) -> None:
        self._logger = logging.getLogger("oko")
        self._logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        if self._logger.handlers:
            self._logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_format = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%H:%M:%S",
        )
        console_handler.setFormatter(console_format)
        self._logger.addHandler(console_handler)

        # File handler (if path specified)
        if log_file:
            os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            self._logger.addHandler(file_handler)

        self._emitter = LogEmitter()

    @classmethod
    def init(cls, log_file: Optional[str] = None) -> "OkoLogger":
        """Initialize the singleton logger."""
        if cls._instance is None:
            cls._instance = cls(log_file)
        return cls._instance

    @classmethod
    def get(cls) -> "OkoLogger":
        """Get the singleton logger instance."""
        if cls._instance is None:
            cls.init()
        return cls._instance

    @classmethod
    def get_emitter(cls) -> Optional[LogEmitter]:
        """Get the log emitter for Qt signal integration."""
        return cls._instance._emitter if cls._instance else None

    @classmethod
    def debug(cls, message: str) -> None:
        cls.get()._logger.debug(message)

    @classmethod
    def info(cls, message: str) -> None:
        cls.get()._logger.info(message)

    @classmethod
    def warning(cls, message: str) -> None:
        cls.get()._logger.warning(message)

    @classmethod
    def error(cls, message: str) -> None:
        cls.get()._logger.error(message)

    @classmethod
    def critical(cls, message: str) -> None:
        cls.get()._logger.critical(message)

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton (for testing)."""
        if cls._instance:
            for handler in cls._instance._logger.handlers[:]:
                handler.close()
            cls._logger.handlers.clear()
            cls._instance = None
