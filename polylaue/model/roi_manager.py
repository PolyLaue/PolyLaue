# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import TypedDict, Tuple
from collections import OrderedDict

Point = Tuple[int, int]


class ROI(TypedDict):
    id: str
    position: Point
    size: Point


class ROIManager:
    def __init__(self):
        self._unique_id = 0
        self.rois: OrderedDict[str, ROI] = OrderedDict()
        self._ordered_keys: list[str] = []
        self._indices: dict[str, int] = {}

    def add_roi(self, position: Point, size: Point) -> str:
        id = str(self._unique_id)
        self._unique_id += 1

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

            return True

        return False

    def update_roi(self, id: str, position: Point, size: Point):
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
