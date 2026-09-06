#!/usr/bin/env python3
"""ОКО — Управление БОД (Блок обработки данных).

Entry point for the OKO Device Manager application.
"""

import sys
import traceback

from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt

from oko_app import __version__
from oko_app.ui.main_window import MainWindow
from oko_app.ui.theme import MAIN_STYLESHEET
from oko_app.core.logger import OkoLogger


def exception_hook(exc_type, exc_value, exc_traceback) -> None:
    """Show error dialog on unhandled exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    traceback_str = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    print("\n\n=== ERROR ===")
    print(traceback_str)
    print("=== END ERROR ===\n")

    QMessageBox.critical(
        None,
        "Критическая ошибка",
        "Произошла необработанная ошибка:\n\n{}".format(traceback_str[:500]),
    )


def main() -> None:
    # Install exception hook
    sys.excepthook = exception_hook

    # Initialize logger
    OkoLogger.init()

    app = QApplication(sys.argv)
    app.setApplicationName("ОКО БОД Manager")
    app.setOrganizationName("ОКО Системс")
    app.setApplicationVersion(__version__)

    # Apply futuristic dark theme
    app.setStyleSheet(MAIN_STYLESHEET)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
