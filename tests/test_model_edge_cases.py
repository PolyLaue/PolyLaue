# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np
import pytest

from polylaue.model.project import Project
from polylaue.model.project_manager import ProjectManager
from polylaue.model.reflections.external import ExternalReflections
from polylaue.model.section import Section
from polylaue.model.serializable import ValidationError
from polylaue.model.series import Series


def _touch(directory, names):
    for name in names:
        (directory / name).touch()


def test_file_prefix_is_matched_literally_and_anchored(tmp_path):
    # A shorter prefix must not pick up files from a longer one
    _touch(tmp_path, [f'run_{i:03d}.tif' for i in range(1, 5)])
    _touch(tmp_path, [f'dryrun_{i:03d}.tif' for i in range(1, 3)])
    prefix, files = Series.generate_file_list(tmp_path, skip_frames=0)
    assert prefix == 'run'
    assert files == [f'run_{i:03d}.tif' for i in range(1, 5)]


def test_file_prefix_with_regex_characters(tmp_path):
    _touch(tmp_path, [f'Fe+Ni (2)_{i:03d}.tif' for i in range(1, 4)])
    prefix, files = Series.generate_file_list(tmp_path, skip_frames=0)
    assert prefix == 'Fe+Ni (2)'
    assert len(files) == 3


def test_skipping_every_frame_is_a_validation_error(tmp_path):
    _touch(tmp_path, [f'run_{i:03d}.tif' for i in range(1, 4)])
    with pytest.raises(ValidationError):
        Series.generate_file_list(tmp_path, skip_frames=3)


def test_scan_range_and_shape_are_validated(tmp_path):
    _touch(tmp_path, [f'run_{i:03d}.tif' for i in range(1, 5)])
    series = object.__new__(Series)
    with pytest.raises(ValidationError, match='scan range'):
        series.validate_files(str(tmp_path), 0, (2, 2), (5, 3), dry=True)
    with pytest.raises(ValidationError, match='scan shape'):
        series.validate_files(str(tmp_path), 0, (0, 2), (1, 1), dry=True)
    # And a consistent set still passes
    series.validate_files(str(tmp_path), 0, (2, 2), (1, 1), dry=True)


def test_loading_a_project_does_not_touch_the_disk(tmp_path):
    pm = ProjectManager()
    project = Project(parent=pm, name='P', directory=tmp_path / 'proj')
    section = Section.from_serialized({'name': 'S', 'description': ''}, parent=project)
    assert section.name == 'S'
    assert not (tmp_path / 'proj').exists()

    # Renaming through the setter still manages the directory
    section.name = 'T'
    assert (tmp_path / 'proj' / 'Sections' / 'T').is_dir()

    with pytest.raises(ValueError):
        section.name = ''
    assert section.name == 'T'


def test_legacy_directory_key_is_applied_before_the_sections(tmp_path):
    pm = ProjectManager()
    serialized = {
        'name': 'P',
        'sections_serialized': [{'name': 'S', 'description': ''}],
        'directory': str(tmp_path),
    }
    project = Project.from_serialized(serialized, parent=pm)
    assert project.directory == tmp_path.resolve()
    assert project.sections[0].directory == tmp_path.resolve() / 'Sections' / 'S'


def test_new_project_has_no_directory_chosen(tmp_path):
    project = Project(parent=ProjectManager(), name='P')
    assert project.directory_str == ''
    project.directory_str = str(tmp_path)
    assert project.directory_str == str(tmp_path.resolve())


def test_reflections_without_predictions(tmp_path):
    reflections = ExternalReflections(tmp_path / 'reflections.h5')
    reflections.crystals_table = np.eye(3).reshape(1, 9)

    # A scan that was never burned simply has no positions
    assert list(reflections.iterate_scan_positions(3)) == []

    # And the crystal can be deleted before anything was predicted
    reflections.delete_crystal(0)
    assert reflections.num_crystals == 0
