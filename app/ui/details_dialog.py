"""Readable warning details without exposing internal stack traces."""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QPlainTextEdit, QVBoxLayout

from app.core.snapshot import SnapshotWarning


class WarningDetailsDialog(QDialog):
    def __init__(self, warnings: list[SnapshotWarning], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Snapshot Warnings")
        self.resize(640, 430)
        layout = QVBoxLayout(self)
        label = QLabel(f"{len(warnings)} item(s) could not be included or inspected.")
        label.setWordWrap(True)
        details = QPlainTextEdit()
        details.setReadOnly(True)
        details.setPlainText(
            "\n".join(f"{warning.path}\n  {warning.message}" for warning in warnings)
        )
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(label)
        layout.addWidget(details, stretch=1)
        layout.addWidget(buttons)
