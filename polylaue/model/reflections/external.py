# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from collections.abc import Generator

import h5py
import numpy as np

from polylaue.typing import PathLike
from polylaue.model.reflections.base import BaseReflections


class ExternalReflections(BaseReflections):
    def __init__(self, filepath: PathLike):
        # We currently do not keep the HDF5 file open by holding onto
        # a file handle, because users want to be able to edit this
        # file while the application is running, and they want to see
        # the updates immediately. On Windows (the primary OS we are
        # supporting), if any application has an open file handle on
        # the file, we cannot edit it. So, for now, only open the
        # file when we are actually reading something from it.
        self.filepath = filepath

    @property
    def num_crystals(self) -> int:
        with h5py.File(self.filepath, 'r') as f:
            if '/crystals' not in f:
                return 0

            return len(f['/crystals'])

    @property
    def crystals_table(self) -> np.ndarray:
        with h5py.File(self.filepath, 'r') as f:
            if '/crystals' not in f:
                return np.empty((0,))

            return f['/crystals'][()]

    @crystals_table.setter
    def crystals_table(self, v: np.ndarray):
        with h5py.File(self.filepath, 'a') as f:
            if '/crystals' in f:
                del f['/crystals']

            f['/crystals'] = v

    @property
    def crystal_names(self) -> np.ndarray:
        """An array of crystal names

        Crystal at index `i` has a crystal name at `crystal_names[i]`

        If the length of the crystal names is less than or equal to
        `i`, then the crystal at index `i` does not have a name.

        The returned numpy array has a dtype of `S`. HDF5 cannot handle
        utf-16 or utf32, so we have to force the numpy arrays to us `S`.
        """
        with h5py.File(self.filepath, 'r') as f:
            if '/crystal_names' not in f:
                return np.empty((0,), dtype='S1')

            return f['/crystal_names'][()]

    @crystal_names.setter
    def crystal_names(self, v: np.ndarray):
        """Set the array of crystal names.

        Crystal at index `i` has a crystal name at `crystal_names[i]`

        If the length of the crystal names is less than or equal to
        `i`, then the crystal at index `i` does not have a name.

        The numpy array must have a dtype of `S`. HDF5 cannot handle
        utf-16 or utf32, so we have to force the numpy arrays to us `S`.
        """
        if not np.issubdtype(v.dtype, 'S'):
            msg = (
                'Crystal names array must have a dtype of "S", '
                f'not "{v.dtype}"'
            )
            raise ValueError(msg)

        with h5py.File(self.filepath, 'a') as f:
            if '/crystal_names' in f:
                del f['/crystal_names']

            f['/crystal_names'] = v

    def reflections_table(
        self, row: int, column: int, scan_number: int
    ) -> np.ndarray | None:
        path = self._reflections_table_path(row, column, scan_number)

        with h5py.File(self.filepath, 'r') as f:
            if path not in f:
                return None

            return f[path][()]

    def write_reflections_table(
        self, table: np.ndarray, row: int, column: int, scan_number: int
    ):
        path = self._reflections_table_path(row, column, scan_number)
        with h5py.File(self.filepath, 'a') as f:
            if path in f:
                del f[path]
            f[path] = table

    def delete_reflections_table(
        self,
        row: int,
        column: int,
        scan_number: int,
    ):
        """Delete a reflections table and all empty parents"""
        path = self._reflections_table_path(row, column, scan_number)
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

    def path_exists(self, row: int, column: int, scan_number: int) -> bool:
        path = self._reflections_table_path(row, column, scan_number)
        with h5py.File(self.filepath, 'r') as f:
            return path in f

    def iterate_scan_positions(
        self,
        scan_number: int,
    ) -> Generator[tuple[int, int]]:
        # Iterate through all scan positions containing reflections tables
        # for a given scan number. The generator returns a tuple of
        # (row, column) intendend to be passed to `reflections_table()`.
        # Note: this holds the file open for reading until iteration is
        # complete.
        with h5py.File(self.filepath, 'r') as f:
            path = f'/predictions/{scan_number}'
            if path not in f:
                # Nothing
                raise StopIteration

            scan = f[path]
            for column in scan.keys():
                for row in scan[column].keys():
                    yield (int(row) - 1, int(column) - 1)

    def _reflections_table_path(
        self, row: int, column: int, scan_number: int
    ) -> str:
        return f'/predictions/{scan_number}/{column + 1}/{row + 1}'
