# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import threading
from typing import Callable

from PySide6.QtCore import QObject, Signal


class BackgroundPoller(QObject):
    """Runs a callable on a background thread at regular intervals.

    Emits ``result_ready`` with the return value of each successful
    call, or ``check_error`` if the callable raises an exception.
    Both signals are delivered on the main thread via Qt's queued
    connections.

    After receiving a result, the caller **must** call
    ``notify_ready()`` to allow the next poll cycle.  This ensures the
    target state being polled is not modified while the background
    thread reads it.

    Thread-safety: the callable passed to this poller must be safe to
    call from a background thread.  See the ``_worker`` method for the
    full synchronization protocol.
    """

    result_ready = Signal(object)
    check_error = Signal()

    def __init__(
        self,
        check_func: Callable,
        interval_ms: int = 333,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self._check_func = check_func
        self._interval = interval_ms / 1000.0
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        # Set by the main thread after it finishes processing a result,
        # telling the background thread it is safe to poll again.
        self._ready = threading.Event()

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        """Start the background polling thread."""
        if self.is_running:
            return
        self._stop.clear()
        self._ready.set()  # Ready for the first poll
        self._thread = threading.Thread(
            target=self._worker,
            daemon=True,
            name="background-poller",
        )
        self._thread.start()

    def stop(self) -> None:
        """Signal the background thread to stop."""
        self._stop.set()
        self._ready.set()  # Wake the thread if it is waiting

    def notify_ready(self) -> None:
        """Tell the background thread it may poll again.

        Must be called by the main thread after it has finished
        processing the previous result.
        """
        self._ready.set()

    def _worker(self) -> None:
        """Polling loop (runs on a dedicated background thread).

        Thread-safety: calls ``_check_func`` which must be safe to call
        from a background thread (read-only access to shared state).
        Results are delivered to the main thread via Qt signals (queued
        connections).

        Synchronization protocol::

            [BG] wait for _ready -> clear _ready -> call _check_func
                 -> emit signal -> sleep
            [Main] receive signal -> process result -> set _ready
            [BG] (next iteration) wait for _ready -> ...

        This guarantees the background thread never reads shared state
        while the main thread is writing to it.
        """
        stop = self._stop
        ready = self._ready

        while not stop.is_set():
            # Wait until the main thread signals it is safe to read.
            while not ready.is_set() and not stop.is_set():
                ready.wait(timeout=0.5)
            if stop.is_set():
                break
            ready.clear()

            try:
                result = self._check_func()
                self.result_ready.emit(result)
            except Exception:
                self.check_error.emit()

            # Pause between polls.
            stop.wait(timeout=self._interval)
