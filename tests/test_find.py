# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

import numpy as np
import pytest

from polylaue.model.core import find, find_py


@pytest.fixture
def indexing_points(test_dir: Path) -> np.ndarray:
    path = test_dir / 'data/indexing.xy'
    return np.loadtxt(path)


@pytest.fixture
def ref_abc_matrix(test_dir: Path) -> np.ndarray:
    path = test_dir / 'data/ref_indexing_abc_matrix0.npy'
    return np.load(path)


@pytest.fixture
def find_kwargs(
    indexing_points: np.ndarray,
    test_geometry: dict[str, np.ndarray],
) -> dict:
    return {
        'obs_xy': indexing_points,
        'energy_highest': 70,
        'cell_parameters': [4.96, 4.96, 3.09, 90.0, 90.0, 120.0],
        'det_org': test_geometry['det_org'],
        'beam_dir': test_geometry['beam_dir'],
        'pix_dist': test_geometry['pix_dist'],
        'ang_tol': 0.07,
        'res_lim': 0.4,
        'ref_thr': 3,
    }


def test_find(
    find_kwargs: dict,
    ref_abc_matrix: np.ndarray,
):
    output = find(**find_kwargs)

    # The output abc matrix should be close to the reference one
    tol = 1e-5
    assert np.max(np.abs(output - ref_abc_matrix)) < tol


def test_find_py(
    find_kwargs: dict,
    ref_abc_matrix: np.ndarray,
):
    output = find_py(**find_kwargs)

    # The output abc matrix should be close to the reference one
    tol = 1e-5
    assert np.max(np.abs(output - ref_abc_matrix)) < tol
