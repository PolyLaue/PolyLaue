# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np
from scipy.spatial.transform import Rotation as R


def compute_angular_shift(
    abc_matrix0: np.ndarray,
    abc_matrix: np.ndarray,
) -> np.ndarray:
    a1 = abc_matrix[6:9] / np.sqrt(np.sum(abc_matrix[6:9] ** 2))
    a2 = np.cross(abc_matrix[3:6], abc_matrix[6:9])
    a2 = a2 / np.sqrt(np.sum(a2**2))
    a3 = np.cross(a1, a2)
    unmov = np.vstack((a1, a2, a3))
    a1 = abc_matrix0[6:9] / np.sqrt(np.sum(abc_matrix0[6:9] ** 2))
    a2 = np.cross(abc_matrix0[3:6], abc_matrix0[6:9])
    a2 = a2 / np.sqrt(np.sum(a2**2))
    a3 = np.cross(a1, a2)
    mov = np.hstack(
        (
            np.expand_dims(a1, axis=1),
            np.expand_dims(a2, axis=1),
            np.expand_dims(a3, axis=1),
        )
    )
    ten = mov @ unmov
    return ten.reshape(9)


def apply_angular_shift(
    abc_matrix: np.ndarray,
    angular_shift: np.ndarray,
) -> np.ndarray:
    a = abc_matrix.reshape(3, -1)
    ten = angular_shift.reshape(3, -1)
    return (a @ ten).flatten()


def compute_angle(angular_shift: np.ndarray) -> float:
    # Compute angle of rotation caused by this angular shift matrix
    # Result in RADIANS
    w = R.from_matrix(angular_shift.reshape(3, -1)).as_quat()[3]
    return 2 * np.arccos(w)
