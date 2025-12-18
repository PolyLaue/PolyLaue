# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from abc import ABC, abstractmethod

import numpy as np


class BaseReflections(ABC):
    @abstractmethod
    def reflections_table(
        self, row: int, column: int, scan_number: int
    ) -> np.ndarray | None:
        pass

    @property
    @abstractmethod
    def num_crystals(self) -> int:
        pass
