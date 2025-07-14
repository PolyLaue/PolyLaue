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

from polylaue.model.core import track, track_py
from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.ui.async_worker import AsyncWorker
from polylaue.ui.reflections_editor import ReflectionsEditor
from polylaue.ui.utils.ui_loader import UiLoader


class TrackDialog:

    def __init__(
        self,
        points: np.ndarray,
        reflections_editor: ReflectionsEditor,
    ):
        self.ui = UiLoader().load_file('track_dialog.ui')

        self.points = points
        self.reflections_editor = reflections_editor
        self.writing_crystal_id = None

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
            QMessageBox.critical(self, 'PolyLaue', str(error[1]))

        # Get the results and close the progress dialog when finished
        worker.signals.result.connect(self.on_track_finished)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(on_finished)

        self.thread_pool.start(worker)

        progress.exec()

    def on_track_finished(self, abc_matrix: np.ndarray):
        if abc_matrix is None:
            msg = (
                'Tracking orientation failed.\n'
                'Try again with different settings or picks.'
            )
            QMessageBox.critical(None, 'Track Failed', msg)
            return

        self.save_settings()
        self.show_reflections(abc_matrix)

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
            'ref_thr': self.reference_threshold,
        }

    def run_track(self) -> np.ndarray | None:
        return self.track_func(**self.track_kwargs)

    def show_reflections(self, abc_matrix: np.ndarray):
        reflections = self.reflections_editor.reflections

        new_burn = False
        if self.reflections_editor._burn_workflow is None:
            self.reflections_editor.start_burn()
            new_burn = True

        burn_workflow = self.reflections_editor._burn_workflow

        if burn_workflow.burn_dialog is None:
            burn_workflow.start()
            new_burn = True

        if self.writing_crystal_id is None:
            # Add the new crystal to the back
            self.writing_crystal_id = reflections.num_crystals

        crystal_id = self.writing_crystal_id

        dialog = burn_workflow.burn_dialog
        dialog.set_crystal_orientation_to_hdf5_file()
        dialog.crystal_id = crystal_id

        crystals_table = reflections.crystals_table
        while len(crystals_table) < crystal_id + 1:
            crystals_table = np.vstack((crystals_table, np.zeros((9,))))

        crystals_table[crystal_id] = abc_matrix
        reflections.crystals_table = crystals_table

        if new_burn:
            # Set the dmin to 0.5
            dialog.dmin = 0.5

        # Activate burn to trigger drawing of the reflections
        dialog.burn_activated = True

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
            'reference_threshold',
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
    def reference_threshold(self) -> float:
        return self.ui.reference_threshold.value()

    @reference_threshold.setter
    def reference_threshold(self, v: float):
        self.ui.reference_threshold.setValue(v)

    @property
    def conserve_memory(self) -> bool:
        return self.ui.conserve_memory.isChecked()

    @conserve_memory.setter
    def conserve_memory(self, b: bool):
        self.ui.conserve_memory.setChecked(b)

    @property
    def thread_pool(self) -> QThreadPool:
        return QThreadPool.globalInstance()
