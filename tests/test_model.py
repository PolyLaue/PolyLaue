# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

import pytest

from polylaue.model.project_manager import ProjectManager
from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.model.series import Series
from polylaue.model.scan import Scan


@pytest.fixture
def project_manager():
    pm = ProjectManager()
    project = Project(parent=pm, name='TestProject', description='A test project')
    pm.projects.append(project)
    section = Section(parent=project, name='TestSection', description='A test section')
    project.sections.append(section)
    series = Series(
        parent=section,
        name='TestSeries',
        description='A test series',
        dirpath='/tmp/test_series',
        scan_start_number=1,
        scan_shape=(5, 7),
        skip_frames=10,
    )
    section.series.append(series)
    return pm


class TestScan:
    def test_scan_number(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        scan = series.scans[0]
        assert scan.number == series.scan_start_number

    def test_scan_serialize_roundtrip(self):
        pm = ProjectManager()
        project = Project(parent=pm, name='P')
        pm.projects.append(project)
        section = Section(parent=project, name='S')
        project.sections.append(section)
        series = Series(
            parent=section,
            name='Ser',
            dirpath='/tmp/test',
            scan_start_number=1,
            scan_shape=(3, 3),
        )
        section.series.append(series)

        scan = series.scans[0]
        scan.shift_x = 5
        scan.shift_y = -3

        serialized = scan.serialize()
        assert serialized == {
            'shift_x': 5,
            'shift_y': -3,
            'scan_center_params': None,
        }

        new_scan = Scan.from_serialized(serialized, parent=series)
        assert new_scan.shift_x == 5
        assert new_scan.shift_y == -3
        assert new_scan.scan_center_params is None


class TestSeries:
    def test_scan_range(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        assert series.scan_range == range(1, 2)
        assert series.scan_range_tuple == (1, 1)

    def test_scan_range_multiple_scans(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        series.scan_range_tuple = (1, 3)
        assert series.num_scans == 3
        assert series.scan_range == range(1, 4)

    def test_scan_shape_reversed(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        assert series.scan_shape == (5, 7)
        assert series.scan_shape_reversed == (7, 5)

        series.scan_shape_reversed = (10, 20)
        assert series.scan_shape == (20, 10)

    def test_scan_by_number(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        series.scan_range_tuple = (5, 7)

        scan = series.scan_by_number(5)
        assert scan is not None
        assert scan.number == 5

        scan = series.scan_by_number(7)
        assert scan is not None
        assert scan.number == 7

        assert series.scan_by_number(4) is None
        assert series.scan_by_number(8) is None

    def test_scan_by_number_single_scan(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        assert series.scan_by_number(1) is series.scans[0]
        assert series.scan_by_number(0) is None
        assert series.scan_by_number(2) is None

    def test_dirpath_resolves(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        assert isinstance(series.dirpath, Path)
        assert series.dirpath.is_absolute()

    def test_serialize_roundtrip(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        serialized = series.serialize()

        assert serialized['name'] == 'TestSeries'
        assert serialized['scan_shape'] == (5, 7)
        assert serialized['scan_start_number'] == 1
        assert serialized['skip_frames'] == 10


class TestSection:
    def test_series_with_scan_index(self, project_manager):
        section = project_manager.projects[0].sections[0]
        series = section.series[0]

        found = section.series_with_scan_index(1)
        assert found is series

        assert section.series_with_scan_index(999) is None


class TestProjectManager:
    def test_empty_project_manager(self):
        pm = ProjectManager()
        assert pm.num_projects == 0
        assert pm.projects == []

    def test_serialize_empty(self):
        pm = ProjectManager()
        serialized = pm.serialize()
        assert serialized == {'projects_serialized': []}

    def test_full_roundtrip(self, project_manager):
        serialized = project_manager.serialize()
        pm2 = ProjectManager.from_serialized(serialized)

        assert pm2.num_projects == 1
        assert pm2.projects[0].name == 'TestProject'
        assert pm2.projects[0].sections[0].name == 'TestSection'
        assert pm2.projects[0].sections[0].series[0].name == 'TestSeries'
