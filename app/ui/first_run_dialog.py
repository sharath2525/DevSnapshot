"""First-run folder selection."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from app.utils.paths import paths_are_same, resource_path


class FirstRunDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.project_path = ""
        self.backup_path = ""
        self.setWindowTitle("Welcome to DevSnapshot")
        self.setMinimumSize(680, 500)
        self.resize(720, 540)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(16)
        logo = QLabel()
        logo.setFixedSize(68, 68)
        pixmap = QPixmap(str(resource_path("resources/icons/devsnapshot.png")))
        if not pixmap.isNull():
            logo.setPixmap(
                pixmap.scaled(
                    68,
                    68,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        title_column = QVBoxLayout()
        title = QLabel("Welcome to DevSnapshot")
        title.setObjectName("productTitle")
        tagline = QLabel("Your local safety checkpoint for AI-assisted development.")
        tagline.setObjectName("tagline")
        title_column.addWidget(title)
        title_column.addWidget(tagline)
        header.addWidget(logo)
        header.addLayout(title_column)
        header.addStretch()
        layout.addLayout(header)
        privacy = QLabel("LOCAL ONLY  •  NO CLOUD  •  NO ACCOUNT")
        privacy.setObjectName("pill")
        layout.addWidget(privacy, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(4)

        project_card, self.project_label, project_button = self._folder_card(
            "STEP 1  ·  PROJECT", "No project selected", "Select Project"
        )
        project_button.clicked.connect(self._select_project)
        backup_card, self.backup_label, backup_button = self._folder_card(
            "STEP 2  ·  BACKUP LOCATION", "No backup folder selected", "Select Backup Location"
        )
        backup_button.clicked.connect(self._select_backup)
        layout.addWidget(project_card)
        layout.addWidget(backup_card)
        layout.addStretch()

        buttons = QHBoxLayout()
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        self.start_button = QPushButton("Start Using DevSnapshot")
        self.start_button.setObjectName("primary")
        self.start_button.setEnabled(False)
        self.start_button.clicked.connect(self._accept_setup)
        buttons.addStretch()
        buttons.addWidget(cancel_button)
        buttons.addWidget(self.start_button)
        layout.addLayout(buttons)

    @staticmethod
    def _folder_card(title: str, placeholder: str, button_text: str):
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        path_label = QLabel(placeholder)
        path_label.setObjectName("pathLabel")
        path_label.setWordWrap(True)
        path_label.setMinimumWidth(0)
        path_label.setSizePolicy(
            QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred
        )
        path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        button = QPushButton(button_text)
        layout.addWidget(heading)
        layout.addWidget(path_label)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignLeft)
        return card, path_label, button

    def _select_project(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Project Folder")
        if selected:
            self.project_path = selected
            self.project_label.setText(selected)
            self._update_start_button()

    def _select_backup(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Select Backup Location")
        if selected:
            self.backup_path = selected
            self.backup_label.setText(selected)
            self._update_start_button()

    def _update_start_button(self) -> None:
        self.start_button.setEnabled(bool(self.project_path and self.backup_path))

    def _accept_setup(self) -> None:
        if paths_are_same(Path(self.project_path), Path(self.backup_path)):
            QMessageBox.warning(
                self,
                "Choose another backup location",
                "The backup folder cannot be the project folder itself. "
                "Choose a subfolder or a folder outside the project.",
            )
            return
        self.accept()
