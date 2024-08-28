# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Literal, Callable, TypeVar

RowMajor = 'row-major'
ColMajor = 'col-major'
AxisOrder = Literal['row-major', 'col-major']

T = TypeVar('T', int, float)
S = TypeVar('S', int, float)

Transform = Callable[[T], S]


def clamp(value: T, low: T, high: T) -> T:
    return min(max(value, low), high)


def identity(val: T) -> T:
    return val


def xy_to_ij(
    xy: tuple[T, T],
    axisOrder: AxisOrder = RowMajor,
    transform: Transform[T, S] = identity,
) -> tuple[S, S]:
    if axisOrder == RowMajor:
        return transform(xy[1]), transform(xy[0])
    else:
        return transform(xy[0]), transform(xy[0])


def ij_to_xy(
    ij: tuple[T, T],
    axisOrder: AxisOrder = RowMajor,
    transform: Transform[T, S] = identity,
) -> tuple[S, S]:
    return xy_to_ij(ij, axisOrder, transform)
