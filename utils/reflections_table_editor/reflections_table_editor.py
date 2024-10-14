# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

import h5py
import numpy as np


class ReflectionsTableEditor:
    """A custom editor for our reflections table format

    This does not hold open a file handle to the file because
    we don't want to prevent read access by PolyLaue on Windows.
    """

    def __init__(self, filepath: str):
        self.filepath = Path(filepath)

        if not self.filepath.exists():
            # Create an empty HDF5 file
            with h5py.File(filepath, 'w'):
                pass

    def crystals_table(self) -> np.ndarray | None:
        with h5py.File(self.filepath, 'r') as f:
            if 'crystals' not in f:
                # No crystals
                return None

            return f['crystals'][()]

    def set_crystals_table(self, table: np.ndarray):
        table = np.asarray(table)
        self.validate_crystals_table(table)
        with h5py.File(self.filepath, 'a') as f:
            if 'crystals' in f:
                del f['crystals']

            # It is expected that this will be float64.
            # Convert it to such for consistency.
            f['crystals'] = table.astype(float)

    def validate_crystals_table(self, table: np.ndarray):
        if table.ndim != 2:
            msg = 'Crystals table must have 2 dimensions'
            raise InvalidCrystalsTable(msg)

        if table.shape[1] != 9:
            msg = 'Crystals table must have 9 columns'
            raise InvalidCrystalsTable(msg)

    def reflections_table(
        self, scan_num: int, scan_pos_y: int, scan_pos_z: int
    ) -> np.ndarray | None:
        path = self._reflections_table_path(scan_num, scan_pos_y, scan_pos_z)
        with h5py.File(self.filepath, 'r') as f:
            if path not in f:
                return None

            return f[path][()]

    def set_reflections_table(
        self,
        table: np.ndarray,
        scan_num: int,
        scan_pos_y: int,
        scan_pos_z: int,
    ):
        table = np.asarray(table)
        self.validate_reflections_table(table)
        path = self._reflections_table_path(scan_num, scan_pos_y, scan_pos_z)
        with h5py.File(self.filepath, 'a') as f:
            if path in f:
                del f[path]

            # It is expected that this will be float64.
            # Convert it to such for consistency.
            f[path] = table.astype(float)

    def delete_reflections_table(
        self,
        scan_num: int,
        scan_pos_y: int,
        scan_pos_z: int,
    ):
        """Delete a reflections table and all empty parents"""
        path = self._reflections_table_path(scan_num, scan_pos_y, scan_pos_z)
        with h5py.File(self.filepath, 'a') as f:
            parent = None
            if path in f:
                parent = f[path].parent
                del f[path]

            while (
                parent is not None and len(parent) == 0 and parent.name != '/'
            ):
                group = parent
                parent = group.parent
                del f[group.name]

    def validate_reflections_table(self, table: np.ndarray):
        if table.ndim != 2:
            msg = 'Reflections table must have 2 dimensions'
            raise InvalidReflectionsTable(msg)

        if table.shape[1] != 10:
            msg = 'Reflections table must have 10 columns'
            raise InvalidReflectionsTable(msg)

    def _reflections_table_path(
        self, scan_num: int, scan_pos_y: int, scan_pos_z: int
    ) -> str:
        return f'/predictions/{scan_num}/{scan_pos_y}/{scan_pos_z}'


class InvalidCrystalsTable(Exception):
    pass


class InvalidReflectionsTable(Exception):
    pass
