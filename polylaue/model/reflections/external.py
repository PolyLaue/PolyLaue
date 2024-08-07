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

    def reflections_table(
        self, row: int, column: int, scan_number: int
    ) -> np.ndarray | None:
        path = self._reflections_table_path(row, column, scan_number)

        with h5py.File(self.filepath, 'r') as f:
            if path not in f:
                return None

            return f[path][()]

    @property
    def num_crystals(self):
        with h5py.File(self.filepath, 'r') as f:
            return len(f['/crystals'])

    def _reflections_table_path(
        self, row: int, column: int, scan_number: int
    ) -> str:
        return f'/predictions/{scan_number}/{row + 1}/{column + 1}'
