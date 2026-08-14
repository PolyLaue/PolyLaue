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
        assert scan.serialize() == {}

        new_scan = Scan.from_serialized(scan.serialize(), parent=series)
        assert new_scan.parent is series

    def test_scan_deserialize_ignores_unknown_attributes(self, capsys):
        # Older settings files may contain attributes that have since
        # been removed, such as the scan shifts. These should be
        # skipped without errors.
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

        legacy = {
            'shift_x': 5,
            'shift_y': -3,
        }
        scan = Scan.from_serialized(legacy, parent=series)
        assert not hasattr(scan, 'shift_x')
        assert not hasattr(scan, 'shift_y')
        assert scan.serialize() == {}

        # The removed scan shifts are skipped silently
        assert capsys.readouterr().err == ''

        # But other unknown attributes still produce a warning
        Scan.from_serialized({'unknown_attribute': 1}, parent=series)
        assert 'unknown_attribute' in capsys.readouterr().err


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

    def test_computed_frame_time(self, project_manager):
        series = project_manager.projects[0].sections[0].series[0]
        section = series.parent

        # No intervals configured, so no computed times
        assert section.acquisition_intervals is None
        assert series.computed_frame_time(0, 0, 1) is None

        section.acquisition_intervals = {
            'frame_period': 0.1,
            'row_break': 2.0,
            'scan_break': 30.0,
        }
        series.scan_range_tuple = (1, 3)

        compute = series.computed_frame_time

        # The scan shape is 5 rows x 7 columns, so each row takes 0.7 s
        # and each scan takes 5 * 0.7 + 4 * 2.0 = 11.5 s
        assert compute(0, 0, 1) == 0.0
        assert compute(0, 3, 1) == pytest.approx(0.3)
        assert compute(1, 0, 1) == pytest.approx(0.7 + 2.0)
        assert compute(4, 6, 1) == pytest.approx(4 * 2.7 + 0.6)
        assert compute(0, 0, 2) == pytest.approx(11.5 + 30.0)
        assert compute(1, 2, 3) == pytest.approx(2 * 41.5 + 2.7 + 0.2)

        # Disabling the intervals reverts to no computed times, while
        # keeping the interval values
        section.acquisition_intervals['enabled'] = False
        assert compute(0, 0, 1) is None
        section.acquisition_intervals['enabled'] = True
        assert compute(0, 3, 1) == pytest.approx(0.3)

    def test_computed_frame_time_1x1_scans(self, project_manager):
        # Fast processes are collected as a series of 1x1 scans. With a
        # scan break of zero, the frame time should reduce to the scan
        # index times the frame period.
        section = project_manager.projects[0].sections[0]
        series = Series(
            parent=section,
            name='TimeScan',
            dirpath='/tmp/test_series',
            scan_start_number=1,
            scan_shape=(1, 1),
        )
        section.series.append(series)
        series.scan_range_tuple = (1, 100)

        section.acquisition_intervals = {
            'frame_period': 0.05,
            'row_break': 12.34,  # unused for a 1x1 scan shape
            'scan_break': 0.0,
        }

        for scan_number in (1, 2, 50, 100):
            expected = (scan_number - 1) * 0.05
            assert series.computed_frame_time(0, 0, scan_number) == pytest.approx(
                expected
            )

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
