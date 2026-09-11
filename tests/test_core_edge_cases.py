# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import contextlib
import io
from pathlib import Path

import numpy as np
from scipy.spatial.transform import Rotation as R

from polylaue.model.core import burn, find, find_py, track, track_py
from polylaue.model.core.angular_shift import compute_angle, compute_angular_shift

DATA = Path(__file__).parent / 'data'


def _geometry():
    g = np.load(DATA / 'geometry.npz')
    return {'det_org': g['iitt1'], 'beam_dir': g['iitt2'], 'pix_dist': g['iitt3']}


def _quiet(fn, *args, **kwargs):
    with contextlib.redirect_stdout(io.StringIO()):
        return fn(*args, **kwargs)


def test_find_with_too_few_points_returns_none():
    kwargs = {
        'energy_highest': 70,
        'cell_parameters': [3.23, 3.23, 5.15, 90, 90, 120],
        'ang_tol': 0.07,
        'res_lim': 0.7,
        'ref_thr': 3,
        **_geometry(),
    }
    for fn in (find, find_py):
        assert _quiet(fn, obs_xy=np.empty((0, 2)), **kwargs) is None
        assert _quiet(fn, obs_xy=np.array([[100.0, 200.0]]), **kwargs) is None


def _track_kwargs():
    return {
        'obs_xy': np.loadtxt(DATA / 'refinement.xy'),
        'energy_highest': 70,
        'ang_tol': 0.07,
        'res_lim': 0.6,
        **_geometry(),
    }


def _rotated_abc(degrees):
    abc0 = np.load(DATA / 'ref_indexing_abc_matrix0.npy').reshape(3, 3)
    rot = R.from_rotvec(np.radians(degrees) * np.array([0, 0, 1.0])).as_matrix()
    return (abc0 @ rot.T).reshape(9)


def test_track_py_respects_reflections_threshold():
    # A 12 degree rotation cannot be recovered from these picks. Both
    # implementations must reject the spurious two-reflection candidate.
    abc = _rotated_abc(12)
    for fn in (track, track_py):
        result = _quiet(fn, abc=abc, ang_lim=8, ref_thr=3, **_track_kwargs())
        assert result[0] is None and result[1] is None, fn.__name__


def test_track_fails_cleanly_when_nothing_is_within_the_angular_limit():
    # The picks sit about 1.2 degrees from the stored matrix, so nothing
    # satisfies a 1.1 degree limit even though candidates pass the threshold
    abc = _rotated_abc(0)
    for fn in (track, track_py):
        result = _quiet(fn, abc=abc, ang_lim=1.1, ref_thr=3, **_track_kwargs())
        assert result[0] is None and result[1] is None, fn.__name__


def _burn(structure_type, cell, euler, energy=(5, 70), shape=(4096, 2048)):
    rot = R.from_euler('xyz', euler, degrees=True).as_matrix()
    abc = (np.diag(cell) @ rot.T).reshape(9)
    g = _geometry()
    predictions, _ = _quiet(
        burn,
        energy[1],
        energy[0],
        structure_type,
        shape[0],
        shape[1],
        abc,
        g['det_org'],
        g['beam_dir'],
        g['pix_dist'],
        res_lim=0.4,
    )
    return predictions


def test_burn_survives_the_filter_removing_every_reflection():
    # A narrow energy window leaves a couple of reflections, all of which
    # are forbidden for Diamond
    predictions = _burn(
        'Diamond', (3.0, 3.0, 3.0), (30, 20, 10), (69, 70), (2048, 2048)
    )
    assert predictions.shape[0] == 0


def test_burn_cmcm_keeps_h0l_harmonics_beyond_the_h_range():
    # For Cmcm, h0l requires h and l even. With c much longer than a, the
    # allowed harmonics of (0 0 1) reach |l| well beyond the h range.
    all_ = _burn('', (2.0, 4.0, 8.0), (10, 80, 30))
    cmcm = _burn('Cmcm', (2.0, 4.0, 8.0), (10, 80, 30))

    def base(row):
        g = np.gcd.reduce(np.abs(row[:3]))
        return tuple(int(x) for x in row[:3] // g)

    ranges = {base(r): (int(r[3]), int(r[4])) for r in cmcm}
    for row in all_:
        h, k, l = base(row)  # noqa: E741
        n1, n2 = int(row[3]), int(row[4])
        allowed = [
            n
            for n in range(n1, n2 + 1)
            if (h + k) * n % 2 == 0 and not (k == 0 and ((h * n) % 2 or (l * n) % 2))
        ]
        if allowed:
            assert ranges.get((h, k, l)) == (allowed[0], allowed[-1]), (h, k, l)
        else:
            assert (h, k, l) not in ranges


def test_compute_angle_is_independent_of_quaternion_sign():
    identity = np.eye(3).reshape(9)
    for degrees in (5, 100, 150, 179):
        rotated = R.from_euler('z', degrees, degrees=True).as_matrix().reshape(9)
        shift = compute_angular_shift(identity, rotated)
        assert np.degrees(compute_angle(shift)) == pytest_approx(degrees)


def pytest_approx(value):
    import pytest

    return pytest.approx(value, abs=1e-6)
