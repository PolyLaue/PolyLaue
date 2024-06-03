import json
import os
from pathlib import Path

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
