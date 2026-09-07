"""DevSnapshot Windows application entry point."""

from __future__ import annotations

import os
import sys
import ctypes

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QDialog, QMessageBox

from app import __version__
from app.core.config import ConfigManager
from app.ui.first_run_dialog import FirstRunDialog
from app.ui.main_window import MainWindow
from app.ui.theme import DARK_STYLESHEET, DevSnapshotStyle
from app.utils.logging_config import configure_logging
from app.utils.paths import resource_path


def main() -> int:
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "DevSnapshot.App"
            )
        except (AttributeError, OSError):
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("DevSnapshot")
    app.setApplicationDisplayName("DevSnapshot")
    app.setApplicationVersion(__version__)
    app.setOrganizationName("DevSnapshot")
    app.setDesktopFileName("devsnapshot")
    app.setStyle(DevSnapshotStyle())
    app.setStyleSheet(DARK_STYLESHEET)

    icon_path = resource_path("resources/icons/devsnapshot.png")
    if not icon_path.is_file():
        icon_path = resource_path("resources/icons/devsnapshot.ico")
    if icon_path.is_file():
        app.setWindowIcon(QIcon(str(icon_path)))

    logger = configure_logging()
    logger.info("DevSnapshot started")

    def handle_unexpected_error(error_type, error, traceback) -> None:
        logger.critical("Unexpected application error", exc_info=(error_type, error, traceback))
        QMessageBox.critical(
            None,
            "Unexpected error",
            "DevSnapshot encountered an unexpected error. Details were written to the local log.",
        )

    sys.excepthook = handle_unexpected_error

    # Used only by build.bat to verify the final packaged executable. All Qt
    # and application modules have loaded by this point. Avoid entering the
    # first-run modal dialog because QApplication.quit() does not reliably
    # close that nested event loop on every Qt version.
    if os.environ.get("DEVSNAPSHOT_SMOKE_TEST") == "1":
        QTimer.singleShot(1500, app.quit)
        return app.exec()

    config_manager = ConfigManager()
    config = config_manager.load()
    if not config.project_path or not config.backup_path:
        setup = FirstRunDialog()
        if setup.exec() != QDialog.DialogCode.Accepted:
            return 0
        config.project_path = setup.project_path
        config.backup_path = setup.backup_path
        try:
            config_manager.save(config)
        except OSError as exc:
            logger.error("Could not save first-run configuration: %s", exc)
            QMessageBox.warning(
                None,
                "Settings could not be saved",
                "DevSnapshot will continue, but the selected folders may not be remembered.",
            )

    window = MainWindow(config, config_manager, logger)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
