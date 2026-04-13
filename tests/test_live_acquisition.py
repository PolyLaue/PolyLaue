# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from polylaue.model.project_manager import ProjectManager
from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.model.series import Series

# A small valid TIF image, created once and reused for all test files.
_SMALL_TIF = Image.new('L', (1, 1))


def _create_files(dirpath: Path, prefix: str, indices: Iterable[int]) -> None:
    """Create small valid .tif files with the given indices."""
    for idx in indices:
        _SMALL_TIF.save(dirpath / f'{prefix}_{idx:03d}.tif')


def _make_series(
    dirpath: Path,
    scan_shape: tuple[int, int] = (2, 3),
    skip_frames: int = 0,
) -> Series:
    """Create a minimal Series object pointing at dirpath."""
    pm = ProjectManager()
    project = Project(parent=pm, name='P')
    pm.projects.append(project)
    section = Section(parent=project, name='S')
    project.sections.append(section)
    series = Series(
        parent=section,
        name='Ser',
        dirpath=str(dirpath),
        scan_start_number=1,
        scan_shape=scan_shape,
        skip_frames=skip_frames,
    )
    section.series.append(series)
    return series


class TestLiveAcquisition:
    """Tests for the live acquisition scan-detection properties."""

    def test_newest_available_scan_number_none(self, tmp_path: Path) -> None:
        """No new scan data → None."""
        # scan_shape=(2,3) → 6 files per scan, skip_frames=0
        # 1 scan needs files 001-006
        _create_files(tmp_path, 'img', range(1, 7))
        series = _make_series(tmp_path)
        series.self_validate(check_dark_file=False)

        assert series.num_scans == 1
        assert series.newest_available_scan_number is None

    def test_newest_available_scan_number_one_new(self, tmp_path: Path) -> None:
        """Exactly one new scan available."""
        # 1 existing scan (001-006) + 1 new (007-012)
        _create_files(tmp_path, 'img', range(1, 13))
        series = _make_series(tmp_path)
        series.self_validate(check_dark_file=False)

        assert series.newest_available_scan_number == 2

    def test_newest_available_scan_number_multiple_new(self, tmp_path: Path) -> None:
        """Three new scans available — should return the newest."""
        # 1 existing scan (001-006) + 3 new scans (007-024)
        _create_files(tmp_path, 'img', range(1, 25))
        series = _make_series(tmp_path)
        series.self_validate(check_dark_file=False)

        assert series.newest_available_scan_number == 4

    def test_newest_available_scan_number_partial_scan(self, tmp_path: Path) -> None:
        """Two complete new scans + partial third → returns scan 3."""
        # 1 existing (001-006) + 2 complete (007-018) + partial (019-020)
        _create_files(tmp_path, 'img', range(1, 21))
        series = _make_series(tmp_path)
        series.self_validate(check_dark_file=False)

        # Only 2 complete new scans, so newest is scan 3
        assert series.newest_available_scan_number == 3

    def test_jumps_to_newest(self, tmp_path: Path) -> None:
        """Jump directly to the newest scan in one step."""
        # Start with 1 scan, 3 new scans worth of data available
        _create_files(tmp_path, 'img', range(1, 25))
        series = _make_series(tmp_path)
        series.self_validate(check_dark_file=False)

        assert series.num_scans == 1
        assert series.scan_range_tuple == (1, 1)

        newest = series.newest_available_scan_number
        assert newest == 4

        first_scan = series.scan_range_tuple[0]
        current_final = series.scan_range_tuple[1]
        num_new = newest - current_final

        series.scan_range_tuple = (first_scan, newest)
        series.self_validate(check_dark_file=False)

        # Jumped to scan 4 in a single step
        assert num_new == 3
        assert series.num_scans == 4
        assert series.scan_range_tuple == (1, 4)

    def test_with_skip_frames(self, tmp_path: Path) -> None:
        """Verify newest_available_scan_number accounts for skip_frames."""
        # skip_frames=2, scan_shape=(2,3)=6 files per scan
        # Skipped files: 001, 002
        # Scan 1: 003-008
        # Scan 2 (new): 009-014
        # File index for new scan check: 2 + (1+1)*6 = 14
        _create_files(tmp_path, 'img', range(1, 15))
        series = _make_series(tmp_path, skip_frames=2)
        series.self_validate(check_dark_file=False)

        assert series.num_scans == 1
        assert series.newest_available_scan_number == 2

    def test_newest_advances_as_files_arrive(self, tmp_path: Path) -> None:
        """Simulate files arriving over time."""
        # Start with just 1 scan
        _create_files(tmp_path, 'img', range(1, 7))
        series = _make_series(tmp_path)
        series.self_validate(check_dark_file=False)

        assert series.newest_available_scan_number is None

        # Add files for 1 more scan
        _create_files(tmp_path, 'img', range(7, 13))
        assert series.newest_available_scan_number == 2

        # Add files for 2 more scans at once (simulating fast acquisition)
        _create_files(tmp_path, 'img', range(13, 25))
        assert series.newest_available_scan_number == 4

        # Jump to newest and verify
        series.scan_range_tuple = (1, 4)
        series.self_validate(check_dark_file=False)
        assert series.num_scans == 4

        # No more new scans
        assert series.newest_available_scan_number is None
