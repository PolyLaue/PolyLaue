# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.reflections.external import ExternalReflections
from polylaue.typing import WorldPoint
from polylaue.ui.frame_tracker import FrameTracker

import numpy as np

HKL = tuple[int, int, int]


class HklProvider:
    def __init__(self, frame_tracker: FrameTracker):
        self.frame_tracker = frame_tracker
        self._reflections = None

    @property
    def reflections(self) -> ExternalReflections | None:
        return self._reflections

    @reflections.setter
    def reflections(self, v: ExternalReflections | None):
        self._reflections = v

    def get_hkl_center(self, crystal_id: int, hkl: HKL) -> WorldPoint:
        # Extract the HKL center from the reflections table by averaging
        # together all HKL centers for the current scan number.
        reflections = self.reflections
        if reflections is None:
            raise ReflectionsNotFound

        if crystal_id >= len(reflections.crystals_table):
            raise CrystalNotFound

        hkl_centers = []

        scan_num = self.frame_tracker.scan_num
        for row, col in reflections.iterate_scan_positions(scan_num):
            table = reflections.reflections_table(row, col, scan_num)
            if table.size == 0:
                continue

            # Remove rows that don't match the crystal ID
            table = table[table[:, 9].astype(int) == crystal_id]

            if table.size == 0:
                continue

            # Remove all rows that don't match the HKL.
            matches = np.all(table[:, 2:5].astype(int) == hkl, axis=1)
            table = table[matches]

            if table.size == 0:
                continue
            elif table.shape[0] > 1:
                print(
                    f'Scan position ({col + 1}, {row + 1}) unexpectedly '
                    f'contains {table.size} matches for HKL {hkl}, '
                    f'crystal ID {crystal_id}, and scan number {scan_num}. '
                    'We will take the first HKL center and ignore the rest.'
                )

            hkl_centers.append(table[0][:2])

        if not hkl_centers:
            raise HklNotFound

        return np.mean(hkl_centers, axis=0)


class InvalidHklError(Exception):
    pass


class ReflectionsNotFound(InvalidHklError):
    pass


class HklNotFound(InvalidHklError):
    pass


class CrystalNotFound(InvalidHklError):
    pass
