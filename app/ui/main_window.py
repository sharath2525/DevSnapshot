"""Main DevSnapshot dashboard."""

from __future__ import annotations

import logging
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, QUrl
from PySide6.QtGui import (
    QCloseEvent,
    QDesktopServices,
    QDragEnterEvent,
    QDropEvent,
    QPixmap,
)
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig, ConfigManager
from app.core.history import SnapshotInfo, list_recent_snapshots
from app.core.snapshot import SnapshotOptions, SnapshotResult, SnapshotWarning
from app.ui.details_dialog import WarningDetailsDialog
from app.ui.settings_dialog import SettingsDialog
from app.utils.paths import is_path_within, paths_are_same, resource_path
from app.workers.snapshot_worker import SnapshotWorker


def format_size(size: int) -> str:
    value = float(size)
    units = ("bytes", "KB", "MB", "GB", "TB")
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "bytes":
                return f"{int(value)} {unit}"
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{size} bytes"


def format_when(moment: datetime) -> str:
    today = date.today()
    if moment.date() == today:
        prefix = "Today"
    elif moment.date() == today - timedelta(days=1):
        prefix = "Yesterday"
    else:
        prefix = moment.strftime("%d %b %Y")
    return f"{prefix} · {moment.strftime('%I:%M %p').lstrip('0')}"


class MainWindow(QMainWindow):
    def __init__(
        self,
        config: AppConfig,
        config_manager: ConfigManager,
        logger: logging.Logger,
    ) -> None:
        super().__init__()
        self.config = config
        self.config_manager = config_manager
        self.logger = logger
        self._thread: QThread | None = None
        self._worker: SnapshotWorker | None = None
        self._warnings: list[SnapshotWarning] = []
        self._close_when_finished = False

        self.setWindowTitle("DevSnapshot")
        self.setMinimumSize(900, 620)
        self.resize(1080, 700)
        self.setAcceptDrops(True)
        self._build_ui()
        self._refresh_paths()
        self._refresh_history()

    def _build_ui(self) -> None:
        shell = QWidget()
        shell.setObjectName("appShell")
        self.setCentralWidget(shell)
        outer = QHBoxLayout(shell)
        outer.setContentsMargins(18, 14, 18, 16)
        outer.addStretch(1)

        content = QWidget()
        content.setObjectName("content")
        content.setMaximumWidth(1180)
        outer.addWidget(content, stretch=20)
        outer.addStretch(1)

        root = QVBoxLayout(content)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(13)
        logo = QLabel()
        logo.setObjectName("appLogo")
        logo.setFixedSize(52, 52)
        pixmap = QPixmap(str(resource_path("resources/icons/devsnapshot.png")))
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    52,
                    52,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        title_column = QVBoxLayout()
        title_column.setSpacing(1)
        title = QLabel("DevSnapshot")
        title.setObjectName("productTitle")
        tagline = QLabel("Checkpoint your project before AI changes it.")
        tagline.setObjectName("tagline")
        title_column.addWidget(title)
        title_column.addWidget(tagline)
        local_badge = QLabel("LOCAL  •  PRIVATE")
        local_badge.setObjectName("pill")
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self._open_settings)
        header.addWidget(logo)
        header.addLayout(title_column)
        header.addStretch()
        header.addWidget(local_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        header.addWidget(self.settings_button, alignment=Qt.AlignmentFlag.AlignVCenter)
        root.addLayout(header)

        columns = QHBoxLayout()
        columns.setSpacing(14)
        left = QVBoxLayout()
        left.setSpacing(14)
        right = QVBoxLayout()
        right.setSpacing(14)

        workspace_card = QFrame()
        workspace_card.setObjectName("card")
        workspace_layout = QVBoxLayout(workspace_card)
        workspace_layout.setContentsMargins(18, 16, 18, 18)
        workspace_layout.setSpacing(10)
        workspace_title = QLabel("Workspace")
        workspace_title.setObjectName("cardTitle")
        workspace_note = QLabel("Select the project to protect and where its checkpoints are stored.")
        workspace_note.setObjectName("muted")
        workspace_layout.addWidget(workspace_title)
        workspace_layout.addWidget(workspace_note)

        project_row, self.project_label, self.project_button = self._path_row(
            "PROJECT FOLDER", "Change"
        )
        self.project_button.clicked.connect(self._choose_project)
        backup_row, self.backup_label, self.backup_button = self._path_row(
            "BACKUP LOCATION", "Change"
        )
        self.backup_button.clicked.connect(self._choose_backup)
        self.backup_notice = QLabel()
        self.backup_notice.setObjectName("warning")
        self.backup_notice.setWordWrap(True)
        workspace_layout.addWidget(project_row)
        workspace_layout.addWidget(backup_row)
        workspace_layout.addWidget(self.backup_notice)
        left.addWidget(workspace_card)

        action_card = QFrame()
        action_card.setObjectName("actionCard")
        action_layout = QVBoxLayout(action_card)
        action_layout.setContentsMargins(20, 18, 20, 18)
        action_layout.setSpacing(10)
        status_row = QHBoxLayout()
        self.status_label = QLabel("Ready for a checkpoint")
        self.status_label.setObjectName("statusTitle")
        self.details_button = QPushButton("View details")
        self.details_button.setObjectName("quiet")
        self.details_button.clicked.connect(self._show_warning_details)
        self.details_button.hide()
        status_row.addWidget(self.status_label)
        status_row.addStretch()
        status_row.addWidget(self.details_button)
        self.status_detail = QLabel(
            "Create a verified local ZIP before an agent makes project-wide changes."
        )
        self.status_detail.setObjectName("muted")
        self.status_detail.setWordWrap(True)
        self.contents_summary = QLabel()
        self.contents_summary.setObjectName("contentsSummary")
        self.contents_summary.setWordWrap(True)
        action_layout.addLayout(status_row)
        action_layout.addWidget(self.status_detail)
        action_layout.addWidget(self.contents_summary)
        action_layout.addStretch(1)

        self.snapshot_button = QPushButton("Create snapshot")
        self.snapshot_button.setObjectName("primary")
        self.snapshot_button.clicked.connect(self._start_snapshot)
        action_layout.addWidget(self.snapshot_button)

        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.hide()
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("danger")
        self.cancel_button.clicked.connect(self._cancel_snapshot)
        self.cancel_button.hide()
        progress_row.addWidget(self.progress_bar, stretch=1)
        progress_row.addWidget(self.cancel_button)
        action_layout.addLayout(progress_row)
        self.progress_label = QLabel()
        self.progress_label.setObjectName("muted")
        self.progress_label.setWordWrap(True)
        self.progress_label.hide()
        action_layout.addWidget(self.progress_label)
        left.addWidget(action_card, stretch=1)

        last_card = QFrame()
        last_card.setObjectName("card")
        last_layout = QVBoxLayout(last_card)
        last_layout.setContentsMargins(18, 16, 18, 16)
        last_layout.setSpacing(5)
        last_title = QLabel("LAST CHECKPOINT")
        last_title.setObjectName("sectionTitle")
        self.last_snapshot_label = QLabel("No snapshots yet")
        self.last_snapshot_label.setObjectName("metric")
        self.last_snapshot_meta = QLabel("Create your first local checkpoint.")
        self.last_snapshot_meta.setObjectName("muted")
        self.last_snapshot_meta.setWordWrap(True)
        last_layout.addWidget(last_title)
        last_layout.addWidget(self.last_snapshot_label)
        last_layout.addWidget(self.last_snapshot_meta)
        right.addWidget(last_card)

        history_card = QFrame()
        history_card.setObjectName("card")
        history_layout = QVBoxLayout(history_card)
        history_layout.setContentsMargins(14, 14, 14, 14)
        history_layout.setSpacing(10)
        history_header = QHBoxLayout()
        history_title = QLabel("Recent snapshots")
        history_title.setObjectName("cardTitle")
        history_header.addWidget(history_title)
        history_header.addStretch()
        history_layout.addLayout(history_header)

        self.history_list = QListWidget()
        self.history_list.setObjectName("historyList")
        self.history_list.setMinimumWidth(300)
        self.history_list.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.history_list.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        self.history_list.setWordWrap(True)
        self.history_list.itemDoubleClicked.connect(
            lambda _item: self._open_backup_folder()
        )
        history_layout.addWidget(self.history_list, stretch=1)

        self.open_folder_button = QPushButton("Open backup folder")
        self.open_folder_button.setObjectName("secondary")
        self.open_folder_button.clicked.connect(self._open_backup_folder)
        history_layout.addWidget(self.open_folder_button)
        right.addWidget(history_card, stretch=1)

        columns.addLayout(left, stretch=3)
        columns.addLayout(right, stretch=2)
        root.addLayout(columns, stretch=1)

        footer = QHBoxLayout()
        privacy = QLabel("No cloud  •  No account  •  No telemetry")
        privacy.setObjectName("footer")
        hint = QLabel("Tip: drag a project folder anywhere onto this window")
        hint.setObjectName("footer")
        footer.addWidget(privacy)
        footer.addStretch()
        footer.addWidget(hint)
        root.addLayout(footer)

    @staticmethod
    def _path_row(title: str, button_text: str):
        row = QFrame()
        row.setObjectName("pathRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(13, 10, 10, 10)
        layout.setSpacing(10)
        text_column = QVBoxLayout()
        text_column.setSpacing(3)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        path_field = QLineEdit("Not selected")
        path_field.setObjectName("pathField")
        path_field.setReadOnly(True)
        path_field.setFrame(False)
        path_field.setToolTip("Click in the path and press Ctrl+C to copy it.")
        button = QPushButton(button_text)
        button.setObjectName("compact")
        text_column.addWidget(heading)
        text_column.addWidget(path_field)
        layout.addLayout(text_column, stretch=1)
        layout.addWidget(button)
        return row, path_field, button

    def _save_config(self) -> None:
        try:
            self.config_manager.save(self.config)
        except OSError as exc:
            self.logger.error("Could not save configuration: %s", exc)
            QMessageBox.warning(
                self,
                "Settings could not be saved",
                "DevSnapshot can continue for this session, but it could not save "
                f"its settings locally.\n\n{exc}",
            )

    def _refresh_paths(self) -> None:
        self.project_label.setText(self.config.project_path or "Not selected")
        self.backup_label.setText(self.config.backup_path or "Not selected")
        configured = bool(self.config.project_path and self.config.backup_path)
        self.snapshot_button.setEnabled(configured and self._thread is None)
        self.open_folder_button.setEnabled(bool(self.config.backup_path))
        if self.config.snapshot_mode == "complete":
            self.contents_summary.setText(
                "Complete snapshot  •  Every file and folder is included"
            )
        else:
            count = len(self.config.excluded_folders)
            skipped = f"{count} folder{'s' if count != 1 else ''} skipped"
            self.contents_summary.setText(f"Custom snapshot  •  {skipped}")

        self.backup_notice.hide()
        if configured:
            project = Path(self.config.project_path)
            backup = Path(self.config.backup_path)
            if paths_are_same(project, backup):
                self.backup_notice.setText(
                    "Choose a different backup location before creating a snapshot."
                )
                self.backup_notice.show()
            elif is_path_within(backup, project, allow_equal=False):
                self.backup_notice.setText(
                    "Backup folder is inside this project. It will automatically be "
                    "excluded from snapshots."
                )
                self.backup_notice.show()

    def _choose_project(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Select Project Folder", self.config.project_path
        )
        if selected:
            self.config.project_path = selected
            self._save_config()
            self._refresh_paths()
            self._refresh_history()

    def _choose_backup(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Select Backup Location", self.config.backup_path
        )
        if selected:
            self.config.backup_path = selected
            self._save_config()
            self._refresh_paths()
            self._refresh_history()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            dialog.apply_to(self.config)
            self._save_config()
            self._refresh_paths()
            self.status_label.setText("Settings saved.")
            self.status_detail.setText("New settings will be used for the next snapshot.")

    def _validate_and_prepare_paths(self) -> tuple[Path, Path] | None:
        if not self.config.project_path or not self.config.backup_path:
            QMessageBox.warning(self, "Folders required", "Select both folders first.")
            return None
        project = Path(self.config.project_path)
        backup = Path(self.config.backup_path)
        if not project.is_dir():
            QMessageBox.warning(
                self, "Project unavailable", "The selected project folder does not exist."
            )
            return None
        if paths_are_same(project, backup):
            QMessageBox.warning(
                self,
                "Choose another backup location",
                "The backup folder cannot be the project folder itself. Choose a "
                "subfolder or a folder outside the project.",
            )
            return None
        if not backup.exists():
            answer = QMessageBox.question(
                self,
                "Create backup folder?",
                "The selected backup folder does not exist. Create it now?",
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None
            try:
                backup.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                QMessageBox.critical(
                    self, "Folder could not be created", f"DevSnapshot could not create it.\n\n{exc}"
                )
                return None
        if not backup.is_dir():
            QMessageBox.warning(
                self, "Backup unavailable", "The selected backup path is not a folder."
            )
            return None

        try:
            free_space = shutil.disk_usage(backup).free
        except OSError:
            free_space = None
        if free_space is not None and free_space < 100 * 1024 * 1024:
            answer = QMessageBox.warning(
                self,
                "Very little free space",
                f"Only {format_size(free_space)} is available at the backup location. "
                "The snapshot may fail. Continue anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return None
        return project, backup

    def _start_snapshot(self) -> None:
        paths = self._validate_and_prepare_paths()
        if paths is None:
            return
        project, backup = paths
        options = SnapshotOptions(
            project_path=project,
            backup_path=backup,
            excluded_directories=tuple(self.config.excluded_folders),
            include_git=self.config.include_git,
            include_hidden=self.config.include_hidden,
            include_env=self.config.include_env,
        )
        self._warnings = []
        self.details_button.hide()
        self._set_busy(True)
        self.progress_bar.setRange(0, 0)
        self.progress_bar.show()
        self.progress_label.setText("Scanning project files...")
        self.progress_label.show()
        self.status_label.setText("Creating snapshot...")
        self.status_detail.setText("The application will remain responsive while files are copied.")

        thread = QThread(self)
        worker = SnapshotWorker(options, self.logger)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.stage_changed.connect(self._snapshot_stage_changed)
        worker.progress_changed.connect(self._snapshot_progress_changed)
        worker.finished.connect(self._snapshot_finished)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(self._thread_finished)
        self._thread = thread
        self._worker = worker
        thread.start()

    def _set_busy(self, busy: bool) -> None:
        self.snapshot_button.setEnabled(not busy)
        self.project_button.setEnabled(not busy)
        self.backup_button.setEnabled(not busy)
        self.settings_button.setEnabled(not busy)
        self.cancel_button.setVisible(busy)

    def _snapshot_stage_changed(self, stage: str) -> None:
        self.status_label.setText(stage)
        self.progress_label.setText(stage)
        self.progress_bar.setRange(0, 0)

    def _snapshot_progress_changed(self, current: int, total: int, path: str) -> None:
        self.progress_bar.setRange(0, max(total, 1))
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current} / {total} files  ·  {path}")

    def _cancel_snapshot(self) -> None:
        if self._worker is None:
            return
        self._worker.cancel()
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelling snapshot...")
        self.status_detail.setText("The incomplete ZIP will be deleted safely.")

    def _snapshot_finished(self, result: SnapshotResult) -> None:
        # Keep project/settings/snapshot controls disabled until QThread has
        # fully stopped. Re-enabling them here creates a small window in which
        # a second run can overwrite the reference to the first thread.
        self.cancel_button.hide()
        self.progress_bar.hide()
        self.progress_label.hide()
        self._warnings = result.warnings
        self.details_button.setVisible(bool(result.warnings))

        if result.cancelled:
            self.status_label.setText("Snapshot cancelled.")
            self.status_detail.setText("The incomplete ZIP was removed.")
            return

        if not result.success or result.output_file is None:
            self.status_label.setText("Snapshot could not be created.")
            self.status_detail.setText(result.error or "No project files were changed.")
            QMessageBox.critical(
                self,
                "Snapshot failed",
                result.error or "The snapshot could not be created. No project files were changed.",
            )
            return

        if result.warnings:
            self.status_label.setText("Snapshot created with warnings.")
            summary = f"{len(result.warnings)} item(s) could not be included. "
        else:
            self.status_label.setText("Snapshot created successfully.")
            summary = ""
        try:
            created_at = datetime.fromtimestamp(result.output_file.stat().st_mtime)
        except OSError:
            # The archive was already verified by the worker. If an external
            # process moves it immediately afterwards, keep the UI responsive.
            created_at = datetime.now()
        self.status_detail.setText(
            f"{summary}{result.output_file.name}\n"
            f"Saved to {result.output_file.parent}\n"
            f"{created_at.strftime('%d %b %Y · %I:%M:%S %p').lstrip('0')} · "
            f"{format_size(result.size)} · {result.file_count} files · "
            f"{result.duration:.1f} seconds\nSnapshot verified successfully."
        )
        self._refresh_history()

    def _thread_finished(self) -> None:
        if self._thread is not None:
            self._thread.deleteLater()
        self._thread = None
        self._worker = None
        self.cancel_button.setEnabled(True)
        self._set_busy(False)
        self._refresh_paths()
        if self._close_when_finished:
            QTimer.singleShot(0, self.close)

    def _show_warning_details(self) -> None:
        if self._warnings:
            WarningDetailsDialog(self._warnings, self).exec()

    def _recent_snapshots(self) -> list[SnapshotInfo]:
        if not self.config.project_path or not self.config.backup_path:
            return []
        return list_recent_snapshots(
            Path(self.config.backup_path), Path(self.config.project_path).name, limit=6
        )

    def _refresh_history(self) -> None:
        snapshots = self._recent_snapshots()
        self.history_list.clear()
        for snapshot in snapshots:
            item = QListWidgetItem(
                f"{snapshot.path.name}\n{format_size(snapshot.size)} · "
                f"{format_when(snapshot.modified)}"
            )
            item.setData(Qt.ItemDataRole.UserRole, str(snapshot.path))
            self.history_list.addItem(item)

        if snapshots:
            latest = snapshots[0]
            self.last_snapshot_label.setText(format_when(latest.modified))
            self.last_snapshot_meta.setText(
                f"{latest.path.name} · {format_size(latest.size)}"
            )
        else:
            self.last_snapshot_label.setText("No snapshots yet")
            self.last_snapshot_meta.setText("Create your first local checkpoint below.")

    def _open_backup_folder(self) -> None:
        if not self.config.backup_path:
            return
        path = Path(self.config.backup_path)
        if not path.is_dir():
            QMessageBox.warning(
                self, "Folder unavailable", "The selected backup folder does not exist."
            )
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path.resolve())))

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        urls = event.mimeData().urls()
        if any(url.isLocalFile() and Path(url.toLocalFile()).is_dir() for url in urls):
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if url.isLocalFile() and path.is_dir():
                self.config.project_path = str(path)
                self._save_config()
                self._refresh_paths()
                self._refresh_history()
                self.status_label.setText("Project selected.")
                self.status_detail.setText(str(path))
                event.acceptProposedAction()
                return

    def closeEvent(self, event: QCloseEvent) -> None:
        if self._thread is not None and self._thread.isRunning():
            if self._close_when_finished:
                event.ignore()
                return
            answer = QMessageBox.question(
                self,
                "Cancel snapshot and exit?",
                "A snapshot is being created. Cancel it, remove the incomplete ZIP, and exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer == QMessageBox.StandardButton.Yes:
                self._close_when_finished = True
                self._cancel_snapshot()
            event.ignore()
            return
        event.accept()
