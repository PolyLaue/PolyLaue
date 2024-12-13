# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import TypedDict
from collections import OrderedDict

from polylaue.typing import WorldPoint


class ROI(TypedDict):
    id: str
    position: WorldPoint
    size: WorldPoint


def unique_id_generator(initial_id: int = 0):
    id: int = initial_id

    while True:
        yield id

        id += 1


class ROIManager:
    unique_id = unique_id_generator(0)

    def __init__(self):
        self.rois: OrderedDict[str, ROI] = OrderedDict()
        self._ordered_keys: list[str] = []
        self._indices: dict[str, int] = {}

    def add_roi(self, position: WorldPoint, size: WorldPoint) -> str:
        id = str(next(ROIManager.unique_id))

        roi: ROI = {'id': id, 'position': position, 'size': size}

        self.rois[id] = roi

        self._ordered_keys = list(self.rois.keys())
        self._indices = {}
        for i, key in enumerate(self._ordered_keys):
            self._indices[key] = i

        return id

    def remove_roi(self, id: str) -> bool:
        if id in self.rois:
            del self.rois[id]

            self._ordered_keys = list(self.rois.keys())
            self._indices = {}
            for i, key in enumerate(self._ordered_keys):
                self._indices[key] = i

            # Make roi id starts from 0 again if we removed all existing rois
            if len(self._ordered_keys) == 0:
                ROIManager.unique_id = unique_id_generator(0)

            return True

        return False

    def update_roi(self, id: str, position: WorldPoint, size: WorldPoint):
        if id in self.rois:
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
