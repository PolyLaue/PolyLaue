# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

import sys
from typing import Callable

from PySide6.QtCore import QSettings, QThreadPool, Qt
from PySide6.QtWidgets import (
    QDialogButtonBox,
    QMessageBox,
    QProgressDialog,
    QWidget,
)

import numpy as np

from polylaue.model.core import (
    apply_angular_shift,
    compute_angle,
    compute_angular_shift,
    track,
    track_py,
)
from polylaue.model.project import Project
from polylaue.model.reflections.external import ExternalReflections
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
        parent: QWidget | None = None,
    ):
        self.ui = UiLoader().load_file('track_dialog.ui', parent)

        self.point_selector_dialog = point_selector_dialog
        self.reflections_editor = reflections_editor

        self.load_settings()
        self.setup_connections()

    def setup_connections(self):
        apply_button = self.ui.button_box.button(QDialogButtonBox.Apply)
        apply_button.clicked.connect(self.on_apply)

    def show(self):
        return self.ui.show()

    def validate(self) -> bool:
        crystal_id = self.selected_crystal_id
        crystals_table = self.reflections.crystals_table
        num_crystals = len(crystals_table)

        min_res = self.project.min_tracking_resolution
        if self.resolution_limit < min_res:
            msg = (
                f'The resolution limit "{self.resolution_limit}" is smaller '
                'than the minimum allowed value defined in this '
                f'project\'s settings: "{min_res}"'
            )
            print(msg, file=sys.stderr)
            QMessageBox.critical(None, 'Validation Error', msg)
            return False

        if crystal_id >= num_crystals:
            msg = (
                f'Crystal ID "{crystal_id}" is invalid '
                f'because the table contains "{num_crystals}" crystals'
            )
            print(msg, file=sys.stderr)
            QMessageBox.critical(None, 'Validation Error', msg)
            return False

        if self.replace_abc_matrix:
            # Verify this crystal has a scan number set.
            # That would only *not* be true for older reflections files
            # that did not set this, or ones that are manually created.
            if self.reflections.crystal_scan_number(crystal_id) == 0:
                msg = (
                    f'Crystal ID "{crystal_id}" does not have '
                    'a valid scan number set, and cannot be replaced. '
                    'Please uncheck "Replace ABC Matrix?"'
                )
                print(msg, file=sys.stderr)
                QMessageBox.critical(None, 'Validation Error', msg)
                return False

        return True

    def on_apply(self):
        if (
            self.is_tracking_original_abc_matrix
            and not self.replace_abc_matrix
        ):
            # If we are tracking the original ABC matrix, we must replace
            # the matrix with a new one. Verify with the user that they
            # wish to do this, and then proceed if so.
            title = 'Tracking Original Scan Number'
            msg = (
                'You are running "Track Orientation" on the original scan '
                'number that was used to generate the ABC matrix. '
                'You must replace the original ABC matrix if you proceed.\n\n'
                'Proceed anyways?'
            )
            if QMessageBox.question(self.ui, title, msg) == QMessageBox.No:
                # Abort
                return

            # Force a replacement on the ABC matrix
            self.replace_abc_matrix = True

        if not self.validate():
            return

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

        msg = self.create_track_success_message(abc_matrix, angular_shift)

        QMessageBox.information(
            None,
            'Track Succeeded',
            msg,
        )

        if self.replace_abc_matrix:
            # Replace the whole ABC matrix and recompute all
            # angular shifts from it.
            self.replace_crystal_abc_matrix(abc_matrix)
        else:
            # Just save the angular shift
            self.save_angular_shift(abc_matrix)

        self.show_burn_dialog()

    @property
    def is_tracking_original_abc_matrix(self) -> bool:
        crystal_id = self.selected_crystal_id
        scan_num = self.scan_num
        return scan_num == self.reflections.crystal_scan_number(crystal_id)

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

    def create_track_success_message(
        self, new_abc_matrix: np.ndarray, angular_shift: float
    ) -> str:
        root_scan_num = self.reflections.crystal_scan_number(
            self.selected_crystal_id
        )

        nearest_scan_num = None
        if self.use_nearest_abc_matrix:
            nearest_scan_num = self.nearest_tracked_scan_number

        if nearest_scan_num is None:
            root_ang_shift = angular_shift
        else:
            root_abc_matrix = self.original_abc_matrix
            root_ang_shift = np.degrees(
                compute_angle(
                    compute_angular_shift(root_abc_matrix, new_abc_matrix)
                )
            )

        msg = ''
        if nearest_scan_num is not None:
            msg += (
                'Angular shift from the starting ABC matrix (scan number '
                f'{nearest_scan_num}) is: {angular_shift:.2f}°\n\n'
            )

        msg += (
            'Angular shift from the original ABC matrix (scan number '
            f'{root_scan_num}) is: {root_ang_shift:.2f}°'
        )

        return msg

    def replace_crystal_abc_matrix(self, new_abc_matrix: np.ndarray):
        # We have to replace the ABC matrix and recompute all angular shift
        # matrices.
        crystal_id = self.selected_crystal_id
        reflections = self.reflections

        # Store these and use them later. Ensure we have deep copies.
        old_abc_matrix = self.original_abc_matrix.copy()
        old_ang_shifts = reflections.angular_shifts_table(crystal_id).copy()
        old_scan_num = reflections.crystal_scan_number(crystal_id)

        # Set the new ABC matrix to the crystals table
        crystals_table = reflections.crystals_table
        crystals_table[crystal_id] = new_abc_matrix
        reflections.crystals_table = crystals_table

        # Now update the ABC matrix scan number
        reflections.set_crystal_scan_number(crystal_id, self.scan_num)

        # Now update the angular shifts table.
        # We will replace rows in the old angular shift table with the new ones
        new_ang_shifts = reflections.angular_shifts_table(crystal_id)

        for i, ang_shift in enumerate(old_ang_shifts):
            if i == self.scan_num - 1:
                # This should be all nans now
                new_ang_shifts[i] = np.full((9,), np.nan)
                continue

            if np.isnan(ang_shift[0]):
                # This one is invalid. Just skip it.
                continue

            # Compute the ABC matrix for this angular shift
            this_abc_matrix = apply_angular_shift(old_abc_matrix, ang_shift)

            # Now compute the angular shift between the new ABC matrix and
            # that one
            new_shift = compute_angular_shift(new_abc_matrix, this_abc_matrix)
            new_ang_shifts[i] = new_shift

        # Set the new angular shifts table
        reflections.set_angular_shifts_table(crystal_id, new_ang_shifts)

        if self.scan_num != old_scan_num:
            # Now also set the angular shift to get back to the old matrix
            new_shift = compute_angular_shift(new_abc_matrix, old_abc_matrix)
            reflections.set_angular_shift_matrix(
                crystal_id,
                old_scan_num,
                new_shift,
            )

    def save_angular_shift(self, abc_matrix: np.ndarray):
        # Write the angular shift matrix for this crystal
        abc_matrix0 = self.original_abc_matrix
        angular_shift = compute_angular_shift(abc_matrix0, abc_matrix)

        self.reflections.set_angular_shift_matrix(
            self.selected_crystal_id,
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
        dialog.apply_angular_shift = not self.replace_abc_matrix
        dialog.angular_shift_from_another_crystal = False

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
            'use_nearest_abc_matrix',
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
    def reflections(self) -> ExternalReflections:
        return self.reflections_editor.reflections

    @property
    def original_abc_matrix(self) -> np.ndarray:
        crystals_table = self.reflections.crystals_table
        return crystals_table[self.selected_crystal_id]

    @property
    def selected_abc_matrix(self) -> np.ndarray:
        if self.use_nearest_abc_matrix:
            return self.nearest_abc_matrix
        else:
            return self.original_abc_matrix

    @property
    def nearest_tracked_scan_number(self) -> int | None:
        if self.is_tracking_original_abc_matrix:
            # If we are tracking the original ABC matrix, the nearest
            # scan number must be the original one.
            # Return `None` to force the original to be used everywhere.
            return None

        scan_num = self.scan_num
        crystal_id = self.selected_crystal_id
        ang_shifts = self.reflections.angular_shifts_table(crystal_id)
        if ang_shifts is None:
            return None

        scan_num_idx = scan_num - 1
        ang_shift_is_valid = ~np.isnan(ang_shifts[:, 0])

        # Pad it up to the scan number minus 1
        padding_needed = scan_num - 1 - ang_shift_is_valid.size
        if padding_needed > 0:
            ang_shift_is_valid = np.hstack(
                (
                    ang_shift_is_valid,
                    np.zeros(padding_needed, dtype=bool),
                )
            )

        # Reverse the below ordering so we try the nearest first
        below_r = ang_shift_is_valid[:scan_num_idx][::-1]
        above = ang_shift_is_valid[scan_num_idx + 1 :]
        max_len = max(len(below_r), len(above))

        i = 0
        while i < max_len:
            if i < len(below_r) and below_r[i]:
                return scan_num - i - 1
            if i < len(above) and above[i]:
                return scan_num + i + 1

            i += 1

        return None

    @property
    def nearest_abc_matrix(self) -> np.ndarray:
        orig_mat = self.original_abc_matrix
        nearest = self.nearest_tracked_scan_number
        if nearest is None:
            # The actual nearest one is the original one
            return orig_mat

        reflections = self.reflections
        crystal_id = self.selected_crystal_id
        ang_shift = reflections.angular_shift_matrix(crystal_id, nearest)
        return apply_angular_shift(orig_mat, ang_shift)

    @property
    def selected_crystal_id(self) -> int:
        return self.ui.crystal_id.value()

    @selected_crystal_id.setter
    def selected_crystal_id(self, v: int):
        # Verify that it is valid within the table. If not,
        # skip setting it.
        crystals_table = self.reflections.crystals_table

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
    def use_nearest_abc_matrix(self) -> bool:
        return self.ui.use_nearest_abc_matrix.isChecked()

    @use_nearest_abc_matrix.setter
    def use_nearest_abc_matrix(self, b: bool):
        self.ui.use_nearest_abc_matrix.setChecked(b)

    @property
    def replace_abc_matrix(self) -> bool:
        return self.ui.replace_abc_matrix.isChecked()

    @replace_abc_matrix.setter
    def replace_abc_matrix(self, b: bool):
        self.ui.replace_abc_matrix.setChecked(b)

    @property
    def conserve_memory(self) -> bool:
        return self.ui.conserve_memory.isChecked()

    @conserve_memory.setter
    def conserve_memory(self, b: bool):
        self.ui.conserve_memory.setChecked(b)

    @property
    def thread_pool(self) -> QThreadPool:
        return QThreadPool.globalInstance()
