# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np
from scipy.spatial.transform import Rotation as R

from polylaue.model.core import apply_angular_shift
from polylaue.model.reflections.external import ExternalReflections


def rotation(degrees, axis):
    return R.from_euler(axis, degrees, degrees=True).as_matrix().flatten()


def test_replace_crystal_abc_matrix(tmp_path):
    reflections = ExternalReflections(tmp_path / 'reflections.h5')

    # One crystal, indexed on scan 1, tracked on scans 2 and 3
    abc = np.array([3.2, 0, 0, 0, 3.2, 0, 0, 0, 5.2])
    reflections.crystals_table = abc[np.newaxis]
    reflections.set_crystal_scan_number(0, 1)
    shifts = {2: rotation(5, 'z'), 3: rotation(12, 'x')}
    for scan, shift in shifts.items():
        reflections.set_angular_shift_matrix(0, scan, shift)

    # The orientations on each scan, before the replacement
    before = {scan: apply_angular_shift(abc, shift) for scan, shift in shifts.items()}

    # Replace the matrix with the orientation on scan 3
    new_abc = before[3]
    reflections.replace_crystal_abc_matrix(0, new_abc, 3)

    assert np.allclose(reflections.crystals_table[0], new_abc)
    assert reflections.crystal_scan_number(0) == 3

    # The orientation on every scan is unchanged
    assert reflections.angular_shift_matrix(0, 3) is None
    for scan in (1, 2):
        shift = reflections.angular_shift_matrix(0, scan)
        expected = abc if scan == 1 else before[scan]
        assert np.allclose(apply_angular_shift(new_abc, shift), expected)
