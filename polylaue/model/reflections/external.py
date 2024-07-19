import h5py
import numpy as np

from polylaue.typing import PathLike
from polylaue.model.reflections.base import BaseReflections


class ExternalReflections(BaseReflections):
    def __init__(self, filepath: PathLike):
        self.filepath = filepath
        self.h5_file = h5py.File(filepath, 'r')

    def reflections_table(
        self, row: int, column: int, scan_number: int
    ) -> np.ndarray | None:
        path = self._reflections_table_path(row, column, scan_number)

        if path not in self.h5_file:
            return None

        return self.h5_file[path][()]

    @property
    def num_crystals(self):
        return len(self.h5_file['/crystals'])

    def _reflections_table_path(
        self, row: int, column: int, scan_number: int
    ) -> str:
        return f'/predictions/{scan_number}/{row + 1}/{column + 1}'
