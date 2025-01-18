# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject, Signal

from polylaue.typing import WorldPoint

import numpy as np

HKL = tuple[int, int, int]


class InvalidHklError(Exception):
    pass


class HklNotFound(InvalidHklError):
    pass


class CrystalNotFound(InvalidHklError):
    pass


class HklProvider(QObject):
    sigHklsChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self._i = 0
        self._hkls: list[tuple[HKL, WorldPoint]] = []
        dx, dy = 200, 200
        start, stop = -1, 2

        for i, h in enumerate(range(start, stop)):
            for j, k in enumerate(range(start, stop)):
                hkl = (h, k, 0)
                center = np.array([(i + 1) * dx, (j + 1) * dy])
                self._hkls.append((hkl, center))

        self._update_hkls()

    def _update_hkls(self):
        self._hkl = {}
        dx, dy = 50, 50
        delta = self._i * np.array([dx, dy])

        for i, (hkl, center) in enumerate(self._hkls):
            if i % 3 == self._i:
                continue

            self._hkl[hkl] = center + delta

        self._i = (self._i + 1) % 2

        self.sigHklsChanged.emit()

    def get_hkls(self) -> list[HKL]:
        return list(self._hkl.keys())

    def get_hkl_center(self, crystal_id: int, hkl: HKL) -> WorldPoint:
        if not hkl in self._hkl:
            raise HklNotFound()

        if crystal_id < 0 or crystal_id > 5:
            raise CrystalNotFound()

        position = self._hkl[hkl]
        dx, dy = 0, 25
        delta = crystal_id * np.array([dx, dy])
        return position + delta
