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

    def crystal_scan_number(self, crystal_id: int) -> int:
        """Get a crystal's scan number

        Return the scan number that was used to create the crystal's
        ABC matrix.

        If no scan number is found, 0 is returned.
        """
        path = '/crystal_scan_numbers'
        with h5py.File(self.filepath, 'r') as f:
            if path not in f:
                return 0

            if len(f[path]) <= crystal_id:
                return 0

            return f[path][crystal_id]

    def set_crystal_scan_number(self, crystal_id: int, scan_num: int):
        """Set a crystal's scan number

        Set the scan number that was used to create the crystal's
        ABC matrix.
        """
        path = '/crystal_scan_numbers'
        with h5py.File(self.filepath, 'a') as f:
            old_table = np.empty((0,), dtype=int)
            if path in f:
                if crystal_id < len(f[path]):
                    f[path][crystal_id] = scan_num
                    return

                old_table = f[path][()]
                del f[path]

            # Either the old table doesn't exist, or it doesn't
            # have enough rows. Make a new one with enough rows.
            new_table = np.zeros((crystal_id + 1,), dtype=int)
            # Set the old values into the new table
            new_table[: len(old_table)] = old_table
            new_table[crystal_id] = scan_num
            f[path] = new_table

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

    def angular_shifts_table(self, crystal_id: int) -> np.ndarray:
        """Get the angular shifts table for a crystal ID

        Row `i` of the table corresponds to the angular shift matrix which
        transforms the crystal's ABC matrix to scan number `i + 1`.

        An angular shift matrix is a flattened 3x3 rotation matrix that,
        when applied to a specified crystal's ABC matrix, produces the
        correctly rotated ABC matrix for the specified scan number.
        """
        path = f'/angular_shifts/{crystal_id}'
        with h5py.File(self.filepath, 'r') as f:
            if path not in f:
                return np.empty((0, 9))

            return f[path][()]

    def set_angular_shifts_table(
        self,
        crystal_id: int,
        angular_shifts: np.ndarray,
    ):
        """Set the angular shifts table for a crystal ID

        Row `i` of the table corresponds to the angular shift matrix which
        transforms the crystal's ABC matrix to scan number `i + 1`.

        An angular shift matrix is a flattened 3x3 rotation matrix that,
        when applied to a specified crystal's ABC matrix, produces the
        correctly rotated ABC matrix for the specified scan number.
        """
        path = f'/angular_shifts/{crystal_id}'
        with h5py.File(self.filepath, 'a') as f:
            if path in f:
                del f[path]

            f[path] = angular_shifts

    def angular_shift_matrix(
        self,
        crystal_id: int,
        scan_number: int,
    ) -> np.ndarray | None:
        """Get the angular shift matrix for a crystal ID and scan number

        An angular shift matrix is a flattened 3x3 rotation matrix that,
        when applied to a specified crystal's ABC matrix, produces the
        correctly rotated ABC matrix for the specified scan number.
        """
        # Rather than pulling the whole table out of the file,
        # pull just the specific row that is needed.
        idx = scan_number - 1
        path = f'/angular_shifts/{crystal_id}'
        with h5py.File(self.filepath, 'r') as f:
            if path not in f:
                # Doesn't exist
                return None

            dataset = f[path]
            if idx >= len(dataset):
                # Doesn't exist
                return None

            matrix = dataset[idx]

        if np.isnan(matrix[0]):
            # A row full of nans indicates an invalid ABC matrix
            return None

        return matrix

    def set_angular_shift_matrix(
        self,
        crystal_id: int,
        scan_number: int,
        angular_shift: np.ndarray,
    ):
        """Set the angular shift matrix for a crystal ID and scan number

        An angular shift matrix is a flattened 3x3 rotation matrix that,
        when applied to a specified crystal's ABC matrix, produces the
        correctly rotated ABC matrix for the specified scan number.
        """
        # First, get the table for this crystal ID
        table = self.angular_shifts_table(crystal_id)
        idx = scan_number - 1
        if len(table) <= idx:
            # Add nan (invalid) rows until the table is at least the right size
            num_new_rows = idx + 1 - len(table)
            table = np.vstack(
                (
                    table,
                    np.full((num_new_rows, 9), np.nan),
                )
            )

        table[idx] = angular_shift
        self.set_angular_shifts_table(crystal_id, table)

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
