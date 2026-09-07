"""Stable Complete or Custom snapshot preferences."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.core.config import AppConfig
from app.core.exclusions import SUGGESTED_EXCLUDED_FOLDERS, normalize_exclusion


class SettingsDialog(QDialog):
    """Edit snapshot contents without moving or resizing the window."""

    WIDTH = 720
    HEIGHT = 560

    def __init__(self, config: AppConfig, parent=None) -> None:
        super().__init__(parent)
        self._dirty = False
        self._initializing = True
        self._project_path = Path(config.project_path) if config.project_path else None
        self.setWindowTitle("Snapshot settings")
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self._build_ui(config)
        self._initializing = False
        self._mode_changed()

    def _build_ui(self, config: AppConfig) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 20)
        layout.setSpacing(9)

        title = QLabel("What should be backed up?")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        subtitle = QLabel("Complete by default. Customize only when you need a smaller ZIP.")
        subtitle.setObjectName("muted")
        layout.addWidget(subtitle)

        mode_row = QHBoxLayout()
        mode_row.setSpacing(10)
        self.complete_card, self.complete_mode = self._create_mode_card(
            "Complete snapshot",
            "Recommended · Includes every file and folder.",
        )
        self.custom_card, self.custom_mode = self._create_mode_card(
            "Custom snapshot",
            "Skip only the folders you choose.",
        )
        mode_row.addWidget(self.complete_card, stretch=1)
        mode_row.addWidget(self.custom_card, stretch=1)
        layout.addLayout(mode_row)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.mode_group.addButton(self.complete_mode, 0)
        self.mode_group.addButton(self.custom_mode, 1)
        if config.snapshot_mode == "custom":
            self.custom_mode.setChecked(True)
        else:
            self.complete_mode.setChecked(True)
        self.complete_mode.toggled.connect(self._mode_changed)
        self.custom_mode.toggled.connect(self._mode_changed)

        self.mode_pages = QStackedWidget()
        self.mode_pages.setObjectName("modePages")
        self.mode_pages.addWidget(self._build_complete_page())
        self.mode_pages.addWidget(self._build_custom_page(config))
        layout.addWidget(self.mode_pages, stretch=1)

        self.change_status = QLabel("Complete snapshot is selected.")
        self.change_status.setObjectName("settingsStatus")
        self.change_status.setMinimumHeight(42)
        self.change_status.setWordWrap(True)
        layout.addWidget(self.change_status)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        reset_button = buttons.addButton(
            "Use complete snapshot", QDialogButtonBox.ButtonRole.ResetRole
        )
        reset_button.clicked.connect(self._reset_complete)
        self.save_button = buttons.addButton(
            "Save changes", QDialogButtonBox.ButtonRole.AcceptRole
        )
        self.save_button.setObjectName("primary")
        buttons.accepted.connect(self._save_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_exclusion_count()

    @staticmethod
    def _create_mode_card(title: str, description: str) -> tuple[QFrame, QRadioButton]:
        card = QFrame()
        card.setObjectName("modeCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(15, 11, 15, 11)
        card_layout.setSpacing(4)
        option = QRadioButton(title)
        option.setObjectName("modeOption")
        note = QLabel(description)
        note.setObjectName("muted")
        note.setWordWrap(True)
        card_layout.addWidget(option)
        card_layout.addWidget(note)
        return card, option

    def _build_complete_page(self) -> QFrame:
        page = QFrame()
        page.setObjectName("customPanel")
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 18, 20, 18)
        page_layout.setSpacing(8)

        label = QLabel("EVERYTHING INCLUDED")
        label.setObjectName("sectionTitle")
        heading = QLabel("A faithful copy of the project on disk")
        heading.setObjectName("completeHeading")
        description = QLabel(
            "Source, dependencies, build output, hidden items, .env files, and local "
            "Git history are all added to the snapshot."
        )
        description.setObjectName("muted")
        description.setWordWrap(True)
        safety = QLabel(
            "Safety rule: if the backup destination is inside the project, only that "
            "destination is skipped to prevent a snapshot from containing itself."
        )
        safety.setObjectName("settingsStatus")
        safety.setWordWrap(True)
        page_layout.addWidget(label)
        page_layout.addWidget(heading)
        page_layout.addWidget(description)
        page_layout.addStretch(1)
        page_layout.addWidget(safety)
        return page

    def _build_custom_page(self, config: AppConfig) -> QFrame:
        self.custom_panel = QFrame()
        self.custom_panel.setObjectName("customPanel")
        panel_layout = QVBoxLayout(self.custom_panel)
        panel_layout.setContentsMargins(16, 12, 16, 12)
        panel_layout.setSpacing(6)

        options_title = QLabel("INCLUDE SPECIAL FILES")
        options_title.setObjectName("sectionTitle")
        panel_layout.addWidget(options_title)
        self.include_git = QCheckBox("Local Git history (.git)")
        self.include_git.setChecked(config.include_git)
        self.include_hidden = QCheckBox("Hidden files and folders")
        self.include_hidden.setChecked(config.include_hidden)
        self.include_env = QCheckBox("Environment files (.env)")
        self.include_env.setChecked(config.include_env)
        checks = QHBoxLayout()
        checks.setSpacing(14)
        for checkbox in (self.include_git, self.include_hidden, self.include_env):
            checkbox.stateChanged.connect(self._mark_dirty)
            checks.addWidget(checkbox)
        checks.addStretch(1)
        panel_layout.addLayout(checks)

        exclusions_row = QHBoxLayout()
        exclusions_title = QLabel("FOLDERS TO SKIP")
        exclusions_title.setObjectName("sectionTitle")
        self.exclusions_count = QLabel()
        self.exclusions_count.setObjectName("muted")
        exclusions_row.addWidget(exclusions_title)
        exclusions_row.addStretch()
        exclusions_row.addWidget(self.exclusions_count)
        panel_layout.addLayout(exclusions_row)

        self.exclusions_stack = QStackedWidget()
        self.exclusions_stack.setFixedHeight(84)
        self.empty_exclusions = QLabel("Nothing is skipped. Add a folder only if needed.")
        self.empty_exclusions.setObjectName("emptyState")
        self.empty_exclusions.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.exclusions = QListWidget()
        self.exclusions.addItems(config.excluded_folders)
        self.exclusions_stack.addWidget(self.empty_exclusions)
        self.exclusions_stack.addWidget(self.exclusions)
        panel_layout.addWidget(self.exclusions_stack)

        quick_row = QHBoxLayout()
        quick_label = QLabel("Quick add")
        quick_label.setObjectName("muted")
        quick_row.addWidget(quick_label)
        for suggestion in SUGGESTED_EXCLUDED_FOLDERS:
            button = QPushButton(suggestion)
            button.setObjectName("chip")
            button.clicked.connect(
                lambda _checked=False, value=suggestion: self._add_value(value)
            )
            quick_row.addWidget(button)
        quick_row.addStretch(1)
        panel_layout.addLayout(quick_row)

        add_row = QHBoxLayout()
        self.exclusion_input = QLineEdit()
        self.exclusion_input.setPlaceholderText("Folder name or project-relative path")
        self.exclusion_input.returnPressed.connect(self._add_exclusion)
        browse_button = QPushButton("Choose folder…")
        browse_button.clicked.connect(self._choose_folder)
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_exclusion)
        self.remove_button = QPushButton("Remove")
        self.remove_button.clicked.connect(self._remove_selected)
        add_row.addWidget(self.exclusion_input, stretch=1)
        add_row.addWidget(browse_button)
        add_row.addWidget(add_button)
        add_row.addWidget(self.remove_button)
        panel_layout.addLayout(add_row)
        return self.custom_panel

    def _mode_changed(self, *_args) -> None:
        custom = self.custom_mode.isChecked()
        self.mode_pages.setCurrentIndex(1 if custom else 0)
        self.complete_card.setProperty("selected", not custom)
        self.custom_card.setProperty("selected", custom)
        for card in (self.complete_card, self.custom_card):
            card.style().unpolish(card)
            card.style().polish(card)
        if self._initializing:
            return
        self._mark_dirty()
        self.change_status.setText(
            "Custom snapshot selected. Only your choices will be skipped."
            if custom
            else "Complete snapshot selected. Nothing will be skipped."
        )

    def _mark_dirty(self, *_args) -> None:
        if self._initializing:
            return
        self._dirty = True
        self.change_status.setText("Unsaved changes — click Save changes to apply them.")

    def _refresh_exclusion_count(self) -> None:
        count = self.exclusions.count()
        self.exclusions_count.setText(f"{count} skipped")
        self.exclusions_stack.setCurrentIndex(0 if count == 0 else 1)
        self.remove_button.setEnabled(count > 0)

    def _add_value(self, value: str) -> bool:
        normalized = normalize_exclusion(value)
        if not normalized:
            self.change_status.setText("Use a folder name or a path inside the project.")
            return False
        existing = {
            self.exclusions.item(index).text().casefold()
            for index in range(self.exclusions.count())
        }
        if normalized.casefold() in existing:
            self.change_status.setText(f"“{normalized}” is already skipped.")
            return True
        self.custom_mode.setChecked(True)
        self.exclusions.addItem(normalized)
        self.exclusions.setCurrentRow(self.exclusions.count() - 1)
        self.exclusions.scrollToBottom()
        self._refresh_exclusion_count()
        self._mark_dirty()
        return True

    def _add_exclusion(self) -> bool:
        raw_value = self.exclusion_input.text()
        if not raw_value.strip():
            self.change_status.setText("Type a folder name before clicking Add.")
            return False
        added = self._add_value(raw_value)
        if added:
            self.exclusion_input.clear()
        return added

    def _choose_folder(self) -> None:
        start = str(self._project_path) if self._project_path else ""
        selected = QFileDialog.getExistingDirectory(self, "Choose a folder to skip", start)
        if not selected:
            return
        chosen = Path(selected)
        if self._project_path is None:
            self.change_status.setText("Select a project folder before choosing an exclusion.")
            return
        try:
            relative = chosen.resolve().relative_to(self._project_path.resolve())
        except (OSError, ValueError):
            self.change_status.setText("Choose a folder inside the selected project.")
            return
        if relative == Path("."):
            self.change_status.setText("The whole project cannot be skipped.")
            return
        self._add_value(relative.as_posix())

    def _remove_selected(self) -> None:
        selected = self.exclusions.selectedItems()
        if not selected:
            self.change_status.setText("Select a folder before removing it.")
            return
        for item in selected:
            self.exclusions.takeItem(self.exclusions.row(item))
        self._refresh_exclusion_count()
        self._mark_dirty()

    def _reset_complete(self) -> None:
        self.complete_mode.setChecked(True)
        self.exclusions.clear()
        self.include_git.setChecked(True)
        self.include_hidden.setChecked(True)
        self.include_env.setChecked(True)
        self._refresh_exclusion_count()
        self._mark_dirty()
        self.change_status.setText("Complete snapshot selected. Nothing will be skipped.")

    def _save_and_accept(self) -> None:
        if (
            self.custom_mode.isChecked()
            and self.exclusion_input.text().strip()
            and not self._add_exclusion()
        ):
            return
        self.accept()

    def reject(self) -> None:
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Discard settings changes?",
                "Your settings changes have not been saved. Discard them?",
                QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Discard:
                return
        super().reject()

    def apply_to(self, config: AppConfig) -> None:
        if self.complete_mode.isChecked():
            config.snapshot_mode = "complete"
            config.include_git = True
            config.include_hidden = True
            config.include_env = True
            config.excluded_folders = []
            return
        config.snapshot_mode = "custom"
        config.include_git = self.include_git.isChecked()
        config.include_hidden = self.include_hidden.isChecked()
        config.include_env = self.include_env.isChecked()
        config.excluded_folders = [
            self.exclusions.item(index).text() for index in range(self.exclusions.count())
        ]
