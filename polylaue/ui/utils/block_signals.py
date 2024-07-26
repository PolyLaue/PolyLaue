from contextlib import contextmanager

from PySide6.QtCore import QSignalBlocker


@contextmanager
def block_signals(*objects):
    """Block signals of objects via a with block:

    with block_signals(object):
        ...

    """
    blocked = [QSignalBlocker(o) for o in objects]
    try:
        yield
    finally:
        blocked.clear()
