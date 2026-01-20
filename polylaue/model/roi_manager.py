# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import TypedDict, NotRequired
from collections import OrderedDict

import numpy as np

from polylaue.typing import WorldPoint

from polylaue.model.hkl_provider import HKL


class ROI(TypedDict):
    id: str
    position: WorldPoint
    size: WorldPoint
    crystal_id: NotRequired[int]
    hkl: NotRequired[HKL]


def unique_id_generator(initial_id: int = 0):
    id: int = initial_id

    while True:
        yield id

        id += 1


class ROIManager:
    global_roi_count = 0
    unique_id = unique_id_generator(0)

    def __init__(self):
        self.rois: OrderedDict[str, ROI] = OrderedDict()
        self._ordered_keys: list[str] = []
        self._indices: dict[str, int] = {}

    def add_roi(self, position: WorldPoint, size: WorldPoint) -> str:
        id = str(next(ROIManager.unique_id))

        if not isinstance(position, np.ndarray):
            position = np.array(position, dtype=np.float32)

        if not isinstance(size, np.ndarray):
            size = np.array(size, dtype=np.float32)

        roi: ROI = {'id': id, 'position': position, 'size': size}

        self.rois[id] = roi

        self._ordered_keys = list(self.rois.keys())
        self._indices = {}
        for i, key in enumerate(self._ordered_keys):
            self._indices[key] = i

        ROIManager.global_roi_count += 1

        return id

    def remove_roi(self, id: str) -> bool:
        if id in self.rois:
            del self.rois[id]

            self._ordered_keys = list(self.rois.keys())
            self._indices = {}
            for i, key in enumerate(self._ordered_keys):
                self._indices[key] = i

            # Make roi id starts from 0 again if we removed all existing rois
            ROIManager.global_roi_count -= 1
            if ROIManager.global_roi_count == 0:
                ROIManager.unique_id = unique_id_generator(0)

            return True

        return False

    def update_roi(self, id: str, position: WorldPoint, size: WorldPoint):
        if id in self.rois:
            if not isinstance(position, np.ndarray):
                position = np.array(position, dtype=np.float32)

            if not isinstance(size, np.ndarray):
                size = np.array(size, dtype=np.float32)

            self.rois[id]['position'] = position
            self.rois[id]['size'] = size

            return True

        return False

    def get_roi(self, id: str) -> ROI:
        return self.rois[id]

    def items(self):
        for id, roi in self.rois.items():
            yield id, roi

    def size(self):
        return len(self._ordered_keys)

    def index_to_id(self, index: int) -> str:
        return self._ordered_keys[index]

    def id_to_index(self, id: str) -> int:
        if id not in self._indices:
            return -1

        return self._indices[id]


class HklROIManager(ROIManager):
    def add_roi(
        self, crystal_id: int, hkl: HKL, position: WorldPoint, size: WorldPoint
    ) -> str:
        id = super().add_roi(position, size)
        self.rois[id]['crystal_id'] = crystal_id
        self.rois[id]['hkl'] = hkl

        return id

    def update_roi(
        self,
        id: str,
        crystal_id: int,
        hkl: HKL,
        position: WorldPoint,
        size: WorldPoint,
    ):
        if super().update_roi(id, position, size):
            self.rois[id]['crystal_id'] = crystal_id
            self.rois[id]['hkl'] = hkl

            return True
        else:
            return False
