# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

import os

import pytest

from PySide6.QtWidgets import QApplication

from polylaue.model.roi_manager import ROIManager
from polylaue.ui.region_mapping.dialog import RegionMappingDialog


@pytest.fixture(scope='module')
def qapp():
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_region_mapping_dialog_lock(qapp):
    dialog = RegionMappingDialog('roi0', ROIManager())
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

    # Unlocking allows updates again
    dialog.lock_scan_number_checkbox.setChecked(False)
    dialog.set_scan_number(7)
    assert dialog.scan_number == 7
    assert '[LOCKED]' not in dialog.windowTitle()
