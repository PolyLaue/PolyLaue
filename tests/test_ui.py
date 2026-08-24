# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import os

from types import SimpleNamespace

import numpy as np
import pytest

from PySide6.QtCore import QPointF
from PySide6.QtWidgets import QApplication

import pyqtgraph as pg

from polylaue.model.project import Project
from polylaue.model.project_manager import ProjectManager
from polylaue.model.roi_manager import HklROIManager, ROIManager
from polylaue.model.section import Section
from polylaue.model.series import Series
from polylaue.ui.acquisition_times_dialog import AcquisitionTimesDialog
from polylaue.ui.frame_tracker import FrameTracker
from polylaue.ui.hkl_regions_navigator.dialog import HklRegionsNavigatorDialog
from polylaue.ui.image_view import PolyLaueImageView
from polylaue.ui.main_window import MainWindow
from polylaue.ui.point_selector import PointSelectorDialog
from polylaue.ui.poni_importer import PoniGeometry
from polylaue.ui.region_mapping.dialog import RegionMappingDialog


@pytest.fixture(scope='module')
def qapp():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_region_mapping_dialog_lock(qapp):
    roi_manager = ROIManager()
    roi_id = roi_manager.add_roi((10, 20), (30, 30))
    dialog = RegionMappingDialog(roi_id, roi_manager)
    series = object()
    dialog.set_series(series)
    dialog.set_scan_number(5)

    # While locked, the series and scan number stay pinned
    dialog.lock_scan_number_checkbox.setChecked(True)
    dialog.set_series(object())
    dialog.set_scan_number(7)
    assert dialog.series is series
    assert dialog.scan_number == 5
    assert '[LOCKED]' in dialog.windowTitle()

    # A plain region only moves when the user edits it, so a locked
    # dialog keeps following it. Otherwise, editing a region would stop
    # updating the maps of it that happen to be locked.
    assert not dialog.roi_frozen
    roi_manager.update_roi(roi_id, (100, 200), (30, 30))
    assert np.array_equal(dialog.current_roi['position'], (100, 200))

    # Unlocking allows updates again
    dialog.lock_scan_number_checkbox.setChecked(False)
    assert '[LOCKED]' not in dialog.windowTitle()

    dialog.set_scan_number(7)
    assert dialog.scan_number == 7


def test_locked_region_mapping_dialog_does_not_shift(qapp):
    # HKL regions are moved to a new center every time the scan number
    # changes. A locked map must keep cropping the same part of the
    # frames, or it would shift even though its scan number did not
    # change.
    roi_manager = HklROIManager()
    roi_id = roi_manager.add_roi(0, (1, 1, 1), (10, 20), (30, 30))
    dialog = RegionMappingDialog(roi_id, roi_manager)

    frame = np.arange(100 * 100).reshape(100, 100)
    requested_bounds = []

    def open_image(series, scan_number, scan_position, bounds=None):
        if bounds is None:
            return None, frame

        requested_bounds.append(tuple(map(int, bounds)))
        return None, frame[bounds[0] : bounds[1], bounds[2] : bounds[3]]

    series = SimpleNamespace(scan_shape=(2, 2))
    dialog.open_image_fn = open_image
    dialog.set_series(series)
    dialog.set_scan_number(5)

    dialog._create_map_image(series, 5)
    bounds_at_lock_time = list(requested_bounds)
    assert bounds_at_lock_time

    # Lock, then move the region the way changing the scan number does
    dialog.lock_scan_number_checkbox.setChecked(True)
    assert dialog.roi_frozen
    dialog.set_stale(False)
    roi_manager.update_roi(roi_id, 0, (1, 1, 1), (40, 50), (30, 30))

    requested_bounds.clear()
    dialog._create_map_image(series, 5)
    assert requested_bounds == bounds_at_lock_time

    # Unlocking catches up with the region it froze out and follows it
    # again
    dialog.lock_scan_number_checkbox.setChecked(False)
    assert not dialog.roi_frozen
    assert dialog.stale

    requested_bounds.clear()
    dialog._create_map_image(series, 5)
    assert requested_bounds != bounds_at_lock_time


def test_settings_serialize_after_project_deletion():
    # Deleting the project of the currently loaded series used to make
    # saving the settings on app close raise a ValueError, since the
    # series could no longer compute its path from the root.
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

    class FakeMainWindow:
        current_series_path = MainWindow.current_series_path
        _serialize_last_loaded_frame = MainWindow._serialize_last_loaded_frame

    window = FakeMainWindow()
    window.series = series
    window.scan_num = 1
    window.scan_pos = np.array([0, 0])

    assert window._serialize_last_loaded_frame() == {
        'series_path': [0, 0, 0],
        'scan_num': 1,
        'scan_pos': [0, 0],
    }

    # Delete the project. The loaded series is now detached, and the
    # settings should serialize as if no series were loaded.
    pm.projects.remove(project)
    assert window.current_series_path is None
    assert window._serialize_last_loaded_frame() == {}

    window.series = None
    assert window._serialize_last_loaded_frame() == {}


def test_hkl_regions_add_roi(qapp):
    class StubHklProvider:
        def get_hkl_center(self, crystal_id, hkl):
            return np.array([100.0, 200.0], dtype=np.float32)

    image_view = pg.ImageView()
    roi_manager = HklROIManager()
    dialog = HklRegionsNavigatorDialog(image_view, roi_manager, StubHklProvider())

    roi_id = dialog.add_hkl_roi(2, (1, 2, 3))

    roi = roi_manager.get_roi(roi_id)
    assert roi['crystal_id'] == 2
    assert roi['hkl'] == (1, 2, 3)

    # The region should be centered on the HKL center
    assert np.array_equal(roi['position'], (25, 125))
    assert np.array_equal(roi['size'], (150, 150))

    # It should have appeared in the table and in the image view
    assert dialog.model.rowCount() == 1
    assert roi_id in dialog.roi_items_manager.roi_items


def test_reflection_right_click_menu(qapp):
    view = PolyLaueImageView(frame_tracker=FrameTracker())

    # One reflection: x, y, h, k, l, energy, first order, last order,
    # d-spacing, crystal id
    view.reflections_array = np.array(
        [[10.0, 20.0, 1, 2, 3, 45.0, 1, 1, 1.5, 4]],
    )

    emitted = []
    view.create_hkl_map.connect(lambda cid, hkl: emitted.append((cid, hkl)))

    point = SimpleNamespace(data=lambda: 0)
    ev = SimpleNamespace(screenPos=lambda: QPointF(0, 0))
    view.on_reflection_right_clicked(point, ev)

    menu = view._reflection_context_menu
    try:
        actions = menu.actions()
        assert len(actions) == 1
        assert actions[0].text() == 'Create HKL map for (1 2 3)'

        actions[0].trigger()
        assert emitted == [(4, (1, 2, 3))]
    finally:
        menu.close()


def test_auto_pick_points_do_not_accumulate(qapp, monkeypatch):
    # Running "Auto-pick Points" multiple times without closing the
    # dialog used to add the new picks on top of the previous run's
    # picks, nearly doubling the number of points every time (and then
    # hanging Find and Track/Refine). A new run must replace the
    # previous run's picks, while keeping manually picked points.
    from polylaue.ui import point_selector as point_selector_module

    # The picking algorithm itself is not under test here
    monkeypatch.setattr(
        point_selector_module.PointAutoPicker,
        'run_auto_pick',
        lambda self: None,
    )

    image_view = PolyLaueImageView(frame_tracker=FrameTracker())
    dialog = PointSelectorDialog(image_view)

    # One manually picked point
    dialog.point_selector.points.append(np.array([1.0, 2.0]))
    dialog.point_selector.points_changed()

    def run_auto_picker(picks, accept: bool):
        assert dialog.start_auto_picker()
        picker = dialog._auto_point_picker
        picker.points = np.array(picks)
        picker.points_modified.emit()
        if accept:
            picker.ui.accepted.emit()
        else:
            picker.ui.rejected.emit()

    run_auto_picker([[10.0, 10.0], [20.0, 20.0]], accept=True)
    assert len(dialog.points) == 3  # manual + 2 picks

    # A second run replaces the previous picks instead of adding to them
    run_auto_picker([[10.0, 10.0], [20.0, 20.0], [30.0, 30.0]], accept=True)
    assert len(dialog.points) == 4  # manual + 3 picks

    # Canceling a run restores all points from before the run
    run_auto_picker([[50.0, 50.0]], accept=False)
    assert len(dialog.points) == 4

    dialog.disconnect()


def test_poni_geometry_editor_dialog(qapp):
    from polylaue.ui.editor import EditorDialog

    geometry = PoniGeometry(
        pixel_size=0.079,
        detector_distance=190.0,
        poni1=0.041,
        poni2=0.0405,
        rot1=0.002,
        rot2=-0.003,
    )

    dialog = EditorDialog(geometry)

    # The parsed values survive the round trip through the widgets,
    # including small and negative ones
    fields = dialog.editor.fields
    assert np.isclose(fields['pixel_size'].value, 0.079)
    assert np.isclose(fields['detector_distance'].value, 190.0)
    assert np.isclose(fields['rot1'].value, 0.002)
    assert np.isclose(fields['rot2'].value, -0.003)

    # Accepting the dialog applies edits back onto the editable
    fields['pixel_size'].value = 0.158
    dialog.on_accepted()
    assert np.isclose(geometry.pixel_size, 0.158)
    assert np.isclose(geometry.rot2, -0.003)


def test_poni_geometry_write(tmp_path):
    pm = ProjectManager()
    project = Project(
        parent=pm,
        name='P',
        directory=tmp_path,
        frame_shape=(981, 1043),
    )
    pm.projects.append(project)

    geometry = PoniGeometry(
        pixel_size=0.079,
        detector_distance=190.0,
        poni1=0.041,
        poni2=0.0405,
        rot1=0.002,
        rot2=-0.003,
    )

    assert project.geometry_path is None
    geometry.write_geometry_file(project)

    # The geometry landed in the project directory and loads correctly
    assert project.geometry_path == tmp_path / 'geometry.npz'
    data = project.geometry_data
    assert set(data.keys()) == {'det_org', 'beam_dir', 'pix_dist'}
    assert np.isclose(data['pix_dist'][0], 0.079)

    # Writing an edited geometry must not serve stale cached data
    geometry.pixel_size = 0.158
    geometry.write_geometry_file(project)
    assert np.isclose(project.geometry_data['pix_dist'][0], 0.158)


def test_acquisition_times_dialog(qapp):
    dialog = AcquisitionTimesDialog()

    # Unchecked by default, with the interval widgets grayed out
    assert dialog.enabled is False
    assert not dialog.ui.intervals_widget.isEnabled()

    params = {
        'enabled': True,
        'frame_period': 0.05,
        'row_break': 2.5,
        'scan_break': 30.0,
    }
    dialog.settings_serialized = params
    assert dialog.settings_serialized == params
    assert dialog.ui.intervals_widget.isEnabled()
