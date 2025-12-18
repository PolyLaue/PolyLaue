# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Literal, Callable
import numpy as np

from functools import partial

from polylaue.typing import Array2, T, S, WorldPoint, DisplayPoint

RowMajor = 'row-major'
ColMajor = 'col-major'
AxisOrder = Literal['row-major', 'col-major']

Transform = Callable[[Array2[T]], Array2[S]]


def identity(val: Array2[T]) -> Array2[T]:
    return val


def xy_to_ij(
    xy: Array2[T],
    axisOrder: AxisOrder = RowMajor,
    transform: Transform[T, S] = identity,
) -> Array2[S]:
    t_xy = transform(xy)

    if axisOrder == RowMajor:
        return np.array((t_xy[1], t_xy[0]))
    else:
        return t_xy


def ij_to_xy(
    ij: Array2[T],
    axisOrder: AxisOrder = RowMajor,
    transform: Transform[T, S] = identity,
) -> Array2[S]:
    return xy_to_ij(ij, axisOrder, transform)


TO_INT32 = partial(lambda d, a: np.astype(a, d), np.int32)
TO_FLOAT32 = partial(lambda d, a: np.astype(a, d), np.float32)


def world_to_display(p: WorldPoint) -> DisplayPoint:
    return xy_to_ij(p, 'row-major', TO_INT32)


def display_to_world(p: DisplayPoint) -> WorldPoint:
    return ij_to_xy(p, 'row-major', TO_FLOAT32)
