"""Qt worker that keeps ZIP creation off the GUI thread."""

from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Slot

from app.core.snapshot import SnapshotEngine, SnapshotOptions, SnapshotResult


class SnapshotWorker(QObject):
    stage_changed = Signal(str)
    progress_changed = Signal(int, int, str)
    finished = Signal(object)

    def __init__(
        self, options: SnapshotOptions, logger: logging.Logger | None = None
    ) -> None:
        super().__init__()
        self.engine = SnapshotEngine(options, logger)

    @Slot()
    def run(self) -> None:
        result: SnapshotResult = self.engine.create_snapshot(
            progress_callback=self.progress_changed.emit,
            status_callback=self.stage_changed.emit,
        )
        self.finished.emit(result)

    def cancel(self) -> None:
        # This only sets a threading.Event, so it is safe to call from the GUI thread.
        self.engine.cancel()
