#!/usr/bin/env python3
"""ОКО — Управление БОД (Блок обработки данных).

Entry point for the OKO Device Manager application.
На Android (python-for-android выставляет ANDROID_ARGUMENT) запускается
мобильный KivyMD-интерфейс, на десктопе — PyQt5.
"""

import os
import sys
import traceback


def _android_boot_log(message: str) -> None:
    if "ANDROID_ARGUMENT" not in os.environ:
        return
    line = "{}\n".format(message)
    paths = [
        os.path.join(os.environ.get("ANDROID_PRIVATE", "."), "oko-startup.log"),
        "/sdcard/Download/oko-startup.log",
    ]
    for path in paths:
        try:
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
            with open(path, "a", encoding="utf-8") as log_file:
                log_file.write(line)
        except (OSError, UnicodeError):
            continue


_android_boot_log("ENTRYPOINT: main.py loaded")

if "ANDROID_ARGUMENT" in os.environ:
    _android_boot_log("IMPORT: oko_mobile.main")
    try:
        from oko_mobile.main import OkoMobileApp
    except BaseException:
        _android_boot_log("IMPORT FAILED:\n{}".format(traceback.format_exc()))
        raise

    def main() -> None:
        _android_boot_log("APP: constructing OkoMobileApp")
        try:
            OkoMobileApp().run()
        except BaseException:
            _android_boot_log("APP FAILED:\n{}".format(traceback.format_exc()))
            raise
else:
    import logging
    from PyQt5.QtWidgets import QApplication, QMessageBox

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
        log_path = os.path.join(os.path.expanduser("~"), "oko-manager.log")
        OkoLogger.init(log_file=log_path)
        logging.getLogger("oko").info("Desktop application started")

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
