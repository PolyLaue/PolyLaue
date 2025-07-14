# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

import numpy as np
import pytest

from polylaue.model.core import track, track_py


@pytest.fixture
def refinement_points(test_dir: Path) -> np.ndarray:
    path = test_dir / 'data/refinement.xy'
    return np.loadtxt(path)


@pytest.fixture
def abc_matrix0(test_dir: Path) -> np.ndarray:
    path = test_dir / 'data/ref_indexing_abc_matrix0.npy'
    return np.load(path)


@pytest.fixture
def ref_abc_matrix(test_dir: Path) -> np.ndarray:
    path = test_dir / 'data/ref_refinement_abc_matrix.npy'
    return np.load(path)


@pytest.fixture
def track_kwargs(
    refinement_points: np.ndarray,
    abc_matrix0: np.ndarray,
    test_geometry: dict[str, np.ndarray],
) -> dict:
    return {
        'obs_xy': refinement_points,
        'abc': abc_matrix0,
        'energy_highest': 70,
        'det_org': test_geometry['det_org'],
        'beam_dir': test_geometry['beam_dir'],
        'pix_dist': test_geometry['pix_dist'],
        'ang_tol': 0.07,
        'ang_lim': 29,
        'res_lim': 0.3,
        'ref_thr': 3,
    }


def test_track(
    track_kwargs: dict,
    ref_abc_matrix: np.ndarray,
):
    output = track(**track_kwargs)

    # The output abc matrix should be close to the reference one
    tol = 1e-5
    assert np.max(np.abs(output - ref_abc_matrix)) < tol


def test_track_py(
    track_kwargs: dict,
    ref_abc_matrix: np.ndarray,
):
    # Now try out the Python version
    output = track_py(**track_kwargs)
    tol = 1e-5
    assert np.max(np.abs(output - ref_abc_matrix)) < tol
