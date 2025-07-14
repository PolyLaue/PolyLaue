# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import json
import os
from pathlib import Path

import numpy as np
import pytest

TEST_DIR = Path(__file__).resolve().parent


@pytest.fixture
def test_data_path():
    if 'POLYLAUE_TEST_DATA_PATH' not in os.environ:
        pytest.fail('Environment varable POLYLAUE_TEST_DATA_PATH not set!')

    repo_path = os.environ['POLYLAUE_TEST_DATA_PATH']
    return Path(repo_path)


@pytest.fixture
def test_project_manager_serialized():
    path = TEST_DIR / 'test_project_manager.json'
    with open(path, 'r') as rf:
        return json.load(rf)


@pytest.fixture
def test_dir() -> Path:
    return TEST_DIR


@pytest.fixture
def test_geometry(test_dir: Path) -> dict[str, np.ndarray]:
    npz_file = np.load(test_dir / 'data/geometry.npz')
    return {
        'det_org': npz_file['iitt1'],
        'beam_dir': npz_file['iitt2'],
        'pix_dist': npz_file['iitt3'],
    }
