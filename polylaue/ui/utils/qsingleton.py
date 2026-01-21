# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject


class QSingletonMetaclass(type(QObject)):
    """A singleton metaclass that has a QObject base"""

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)

        return cls._instances[cls]


class QSingleton(metaclass=QSingletonMetaclass):
    """Inherit from this class to be a QSingleton"""

    pass
