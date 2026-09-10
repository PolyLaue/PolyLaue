# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Any, Callable

from PySide6.QtCore import Qt, QThreadPool
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QProgressDialog, QWidget

from polylaue.ui.async_worker import AsyncWorker


class UndismissableProgressDialog(QProgressDialog):
    """A progress dialog that only the code can close

    Escape and the window's close action would otherwise close it while
    the work is still running. Closing it via `reject()` is unaffected.
    """

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Cancel):
            # Swallow it, or it propagates to the parent dialog
            event.accept()
            return

        super().keyPressEvent(event)

    def closeEvent(self, event):
        event.ignore()


def run_with_progress(
    message: str,
    fn: Callable,
    parent: QWidget | None = None,
) -> tuple[Any, tuple | None]:
    """Run a function in a worker thread behind a progress dialog

    Returns the result of the function and the error it raised, as an
    `(exception type, exception, traceback)` tuple, if any.

    The progress dialog cannot be canceled, so it is closed via the
    worker's `finished` signal, which is emitted whether the function
    succeeded or failed.
    """
    progress = UndismissableProgressDialog(message, '', 0, 0, parent)
    progress.setCancelButton(None)
    # No close button in the corner
    flags = progress.windowFlags()
    progress.setWindowFlags(
        (flags | Qt.CustomizeWindowHint) & ~Qt.WindowCloseButtonHint
    )

    outcome = {}
    worker = AsyncWorker(fn)
    worker.signals.result.connect(lambda result: outcome.update(result=result))
    worker.signals.error.connect(lambda error: outcome.update(error=error))
    # Connect to the C++ slot directly, so that closing the dialog cannot
    # be interrupted by an error in Python
    worker.signals.finished.connect(progress.reject)

    QThreadPool.globalInstance().start(worker)
    progress.exec()

    return outcome.get('result'), outcome.get('error')
