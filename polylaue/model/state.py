# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import json
import logging
from pathlib import Path
import shutil

from platformdirs import user_data_dir

from polylaue.model.project_manager import ProjectManager

logger = logging.getLogger(__name__)

USER_DATA_DIR = Path(user_data_dir('PolyLaue', 'PolyLaue'))
PROJECT_MANAGER_PATH = USER_DATA_DIR / 'project_manager.json'
TMP_PROJECT_MANAGER_PATH = USER_DATA_DIR / 'temporary_project_manager.json'


def save_project_manager(pm: ProjectManager):
    # Save to a temporary file and then move that temporary file.
    # This ensures we are able to save the project fully before overwriting
    # it.
    try:
        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)
        serialized = pm.serialize()
        with open(TMP_PROJECT_MANAGER_PATH, 'w') as wf:
            json.dump(serialized, wf)

        shutil.move(TMP_PROJECT_MANAGER_PATH, PROJECT_MANAGER_PATH)
    except Exception:
        logger.exception('Failed to save project manager')


def load_project_manager() -> ProjectManager:
    if not PROJECT_MANAGER_PATH.exists():
        # Doesn't exist. Just return an empty one.
        return ProjectManager()

    try:
        with open(PROJECT_MANAGER_PATH, 'r') as rf:
            serialized = json.load(rf)

        return ProjectManager.from_serialized(serialized)
    except Exception:
        logger.exception(
            f'Failed to load project manager at path: {PROJECT_MANAGER_PATH}'
        )
        # Return an empty project manager.
        return ProjectManager()
