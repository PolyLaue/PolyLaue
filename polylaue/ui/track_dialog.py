# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import sys
from typing import Callable

from PySide6.QtCore import QSettings, QThreadPool, Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QMessageBox,
    QProgressDialog,
)

import numpy as np

from polylaue.model.core import compute_angular_shift, track, track_py
from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.ui.async_worker import AsyncWorker
from polylaue.ui.point_selector import PointSelectorDialog
from polylaue.ui.reflections_editor import ReflectionsEditor
from polylaue.ui.utils.ui_loader import UiLoader

TrackResults = tuple[np.ndarray | None, float | None]


class TrackDialog:

    def __init__(
        self,
        point_selector_dialog: PointSelectorDialog,
        reflections_editor: ReflectionsEditor,
    ):
        self.ui = UiLoader().load_file('track_dialog.ui')

        self.point_selector_dialog = point_selector_dialog
        self.reflections_editor = reflections_editor

        self.update_visibility_states()
        self.load_settings()
        self.setup_connections()

    def setup_connections(self):
        apply_button = self.ui.button_box.button(QDialogButtonBox.Apply)
        apply_button.clicked.connect(self.on_apply)

    def show(self):
        return self.ui.show()

    def validate(self):
        reflections = self.reflections_editor.reflections
        crystals_table = reflections.crystals_table
        num_crystals = len(crystals_table)

        if self.selected_crystal_id >= num_crystals:
            msg = (
                f'Crystal ID "{self.selected_crystal_id}" is invalid '
                f'because the table contains "{num_crystals}" crystals'
            )
            print(msg, file=sys.stderr)
            QMessageBox.critical(None, 'Validation Error', msg)
            raise Exception(msg)

    def on_apply(self):
        self.validate()

        progress = QProgressDialog(
            'Running track. Please wait...', '', 0, 0, self.ui
        )
        progress.setCancelButton(None)
        # No close button in the corner
        flags = progress.windowFlags()
        progress.setWindowFlags(
            (flags | Qt.CustomizeWindowHint) & ~Qt.WindowCloseButtonHint
        )

        worker = AsyncWorker(self.run_track)

        def on_finished():
            progress.reject()

        def on_error(error: tuple):
            print(error[2], file=sys.stderr)
            QMessageBox.critical(self.ui, 'PolyLaue', str(error[1]))

        # Get the results and close the progress dialog when finished
        worker.signals.result.connect(self.on_track_finished)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(on_finished)

        self.thread_pool.start(worker)

        progress.exec()

    def on_track_finished(self, results: TrackResults):
        abc_matrix = results[0]
        angular_shift = results[1]
        if abc_matrix is None:
            msg = (
                'Tracking orientation failed.\n'
                'Try again with different settings or picks.'
            )
            QMessageBox.critical(None, 'Track Failed', msg)
            return

        self.save_settings()

        msg = f'Angular shift is: {angular_shift:.2f}°'
        QMessageBox.information(
            None,
            'Track Succeeded',
            msg,
        )

        self.save_angular_shift(abc_matrix)
        self.show_burn_dialog()

    @property
    def points(self) -> np.ndarray:
        return np.asarray(self.point_selector_dialog.points)

    @property
    def track_func(self) -> Callable:
        return track_py if self.conserve_memory else track

    @property
    def track_kwargs(self) -> dict:
        geometry = self.project.geometry_data
        return {
            'obs_xy': self.points,
            'abc': self.selected_abc_matrix,
            'energy_highest': self.project.energy_range[1],
            'det_org': geometry['det_org'],
            'beam_dir': geometry['beam_dir'],
            'pix_dist': geometry['pix_dist'],
            'ang_tol': self.angular_tolerance,
            'ang_lim': self.angular_limit,
            'res_lim': self.resolution_limit,
            'ref_thr': self.reflections_threshold,
        }

    def run_track(self) -> TrackResults:
        return self.track_func(**self.track_kwargs)

    def save_angular_shift(self, abc_matrix: np.ndarray):
        # Write the angular shift matrix for this crystal
        abc_matrix0 = self.selected_abc_matrix
        angular_shift = compute_angular_shift(abc_matrix0, abc_matrix)

        reflections = self.reflections_editor.reflections

        if self.angular_shift_apply_all:
            # Apply this angular shift to all crystals
            crystal_ids = list(range(reflections.num_crystals))
        else:
            # Just this one
            crystal_ids = [self.selected_crystal_id]

        for crystal_id in crystal_ids:
            reflections.set_angular_shift_matrix(
                crystal_id,
                self.scan_num,
                angular_shift,
            )

    def show_burn_dialog(self):
        # Set up the burn() dialog and begin to burn
        new_burn = False
        if self.reflections_editor._burn_workflow is None:
            self.reflections_editor.start_burn()
            new_burn = True

        burn_workflow = self.reflections_editor._burn_workflow

        if burn_workflow.burn_dialog is None:
            burn_workflow.start()
            new_burn = True

        dialog = burn_workflow.burn_dialog
        dialog.set_crystal_orientation_to_hdf5_file()
        dialog.crystal_id = self.selected_crystal_id
        dialog.apply_angular_shift = True

        if new_burn:
            # Set the dmin to 0.5
            dialog.dmin = 0.5

        if not dialog.ui.isVisible():
            dialog.ui.show()

        # Activate burn to trigger drawing of the reflections
        if dialog.burn_activated:
            dialog.on_activate_burn()
        else:
            dialog.burn_activated = True

    def update_visibility_states(self):
        reflections = self.reflections_editor.reflections
        visible = reflections is not None and reflections.num_crystals > 1
        w = self.ui.angular_shift_apply_all
        w.setVisible(visible)

    def load_settings(self):
        settings = QSettings()
        self.settings_serialized = settings.value('track_dialog_settings', {})

    def save_settings(self):
        settings = QSettings()
        settings.setValue('track_dialog_settings', self.settings_serialized)

    @property
    def _attrs_to_serialize(self) -> list[str]:
        return [
            'selected_crystal_id',
            'angular_tolerance',
            'angular_limit',
            'resolution_limit',
            'reflections_threshold',
            'angular_shift_apply_all',
            'conserve_memory',
        ]

    @property
    def settings_serialized(self) -> dict:
        return {k: getattr(self, k) for k in self._attrs_to_serialize}

    @settings_serialized.setter
    def settings_serialized(self, values: dict):
        for k, v in values.items():
            if hasattr(self, k):
                setattr(self, k, v)

    @property
    def project(self) -> Project:
        return self.section.parent

    @property
    def section(self) -> Section:
        return self.reflections_editor.section

    @property
    def scan_num(self) -> int:
        return self.reflections_editor.frame_tracker.scan_num

    @property
    def selected_abc_matrix(self) -> np.ndarray:
        reflections = self.reflections_editor.reflections
        crystals_table = reflections.crystals_table
        return crystals_table[self.selected_crystal_id]

    @property
    def selected_crystal_id(self) -> int:
        return self.ui.crystal_id.value()

    @selected_crystal_id.setter
    def selected_crystal_id(self, v: int):
        # Verify that it is valid within the table. If not,
        # skip setting it.
        reflections = self.reflections_editor.reflections
        crystals_table = reflections.crystals_table

        if v < len(crystals_table):
            self.ui.crystal_id.setValue(v)

    @property
    def angular_tolerance(self) -> float:
        return self.ui.angular_tolerance.value()

    @angular_tolerance.setter
    def angular_tolerance(self, v: float):
        self.ui.angular_tolerance.setValue(v)

    @property
    def angular_limit(self) -> float:
        return self.ui.angular_limit.value()

    @angular_limit.setter
    def angular_limit(self, v: float):
        self.ui.angular_limit.setValue(v)

    @property
    def resolution_limit(self) -> float:
        return self.ui.resolution_limit.value()

    @resolution_limit.setter
    def resolution_limit(self, v: float):
        self.ui.resolution_limit.setValue(v)

    @property
    def reflections_threshold(self) -> float:
        return self.ui.reflections_threshold.value()

    @reflections_threshold.setter
    def reflections_threshold(self, v: float):
        self.ui.reflections_threshold.setValue(v)

    @property
    def angular_shift_apply_all(self) -> bool:
        return self.ui.angular_shift_apply_all.isChecked()

    @angular_shift_apply_all.setter
    def angular_shift_apply_all(self, b: bool):
        self.ui.angular_shift_apply_all.setChecked(b)

    @property
    def conserve_memory(self) -> bool:
        return self.ui.conserve_memory.isChecked()

    @conserve_memory.setter
    def conserve_memory(self, b: bool):
        self.ui.conserve_memory.setChecked(b)

    @property
    def thread_pool(self) -> QThreadPool:
        return QThreadPool.globalInstance()
