# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import os

from types import SimpleNamespace

import numpy as np
import pytest

from PySide6.QtWidgets import QApplication

from polylaue.model.roi_manager import HklROIManager, ROIManager
from polylaue.ui.acquisition_times_dialog import AcquisitionTimesDialog
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
