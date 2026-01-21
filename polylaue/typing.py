# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import os

from typing import Literal, TypeVar
import numpy as np

PathLike = str | bytes | os.PathLike


T = TypeVar('T', bound=np.number)
S = TypeVar('S', bound=np.number)

Array2 = np.ndarray[tuple[Literal[2]], np.dtype[T]]

DisplayPoint = Array2[np.int32]
WorldPoint = Array2[np.float32]
