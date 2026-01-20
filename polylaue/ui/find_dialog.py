# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

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
import pyqtgraph as pg

from polylaue.model.core import find, find_py
from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.ui.async_worker import AsyncWorker
from polylaue.ui.point_selector import PointSelectorDialog
from polylaue.ui.reflections_editor import ReflectionsEditor
from polylaue.ui.utils.ui_loader import UiLoader


class FindDialog:

    def __init__(
        self,
        image_view: pg.ImageView,
        reflections_editor: ReflectionsEditor,
        parent: QWidget | None = None,
    ):
        self.ui = UiLoader().load_file('find_dialog.ui', parent)

        # We use an "always hidden" point selector dialog so we
        # don't have to repeat point selector logic.
        self.point_selector_dialog = PointSelectorDialog(
            image_view,
            window_title='Select Points',
            always_hidden=True,
            parent=self.ui,
        )
        self.reflections_editor = reflections_editor
        self.crystal_id = None

        self.update_enable_states()

        self.load_settings()
        self.setup_connections()

    def setup_connections(self):
        self.ui.auto_pick_points.clicked.connect(self.auto_pick_points)
        self.ui.clear_points.clicked.connect(self.clear_points)

        self.point_selector_dialog.point_selector.points_modified.connect(
            self.on_points_modified
        )

        self.point_selector_dialog.auto_pick_points_finished.connect(
            self.on_auto_pick_points_finished
        )

        apply_button = self.ui.button_box.button(QDialogButtonBox.Apply)
        apply_button.clicked.connect(self.on_apply)
        self.ui.delete_crystal.clicked.connect(self.on_delete_crystal)

        self.ui.finished.connect(self.on_dialog_finished)

    def on_dialog_finished(self):
        self.point_selector_dialog.disconnect()

    def update_enable_states(self):
        self.ui.delete_crystal.setEnabled(self.crystal_id is not None)

    def show(self):
        # Resize according to vertical size hint
        self.ui.resize(self.ui.width(), self.ui.sizeHint().height())
        return self.ui.show()

    def auto_pick_points(self):
        if self.point_selector_dialog.start_auto_picker():
            self.ui.hide()

    def on_auto_pick_points_finished(self):
        self.ui.show()

    def clear_points(self):
        self.point_selector_dialog.clear_points()

    def on_points_modified(self):
        self.update_num_points_label()

    def update_num_points_label(self):
        num_points = len(self.points)
        self.ui.num_points_label.setText(f'Number of points: {num_points}')

    def validate(self) -> bool:
        min_res = self.project.min_find_resolution
        if self.resolution_limit < min_res:
            msg = (
                f'The resolution limit "{self.resolution_limit}" is smaller '
                'than the minimum allowed value defined in this '
                f'project\'s settings: "{min_res}"'
            )
            print(msg, file=sys.stderr)
            QMessageBox.critical(None, 'Validation Error', msg)
            return False

        return True

    def on_apply(self):
        if not self.validate():
            return

        progress = QProgressDialog(
            'Running find. Please wait...', '', 0, 0, self.ui
        )
        progress.setCancelButton(None)
        # No close button in the corner
        flags = progress.windowFlags()
        progress.setWindowFlags(
            (flags | Qt.CustomizeWindowHint) & ~Qt.WindowCloseButtonHint
        )

        worker = AsyncWorker(self.run_find)

        def on_finished():
            progress.reject()

        def on_error(error: tuple):
            print(error[2], file=sys.stderr)
            QMessageBox.critical(self.ui, 'PolyLaue', str(error[1]))

        # Get the results and close the progress dialog when finished
        worker.signals.result.connect(self.on_find_finished)
        worker.signals.error.connect(on_error)
        worker.signals.finished.connect(on_finished)

        self.thread_pool.start(worker)

        progress.exec()

    def on_find_finished(self, abc_matrix: np.ndarray):
        if abc_matrix is None:
            msg = (
                'Finding orientation failed.\n'
                'Try again with different settings or picks.'
            )
            QMessageBox.critical(None, 'Find Failed', msg)
            return

        self.save_settings()

        self.show_reflections(abc_matrix)

    @property
    def points(self) -> np.ndarray:
        return np.asarray(self.point_selector_dialog.points)

    @property
    def find_func(self) -> Callable:
        return find_py if self.conserve_memory else find

    @property
    def find_kwargs(self) -> dict:
        geometry = self.project.geometry_data
        return {
            'obs_xy': self.points,
            'energy_highest': self.project.energy_range[1],
            'cell_parameters': self.cell_parameters,
            'det_org': geometry['det_org'],
            'beam_dir': geometry['beam_dir'],
            'pix_dist': geometry['pix_dist'],
            'ang_tol': self.angular_tolerance,
            'res_lim': self.resolution_limit,
            'ref_thr': self.reflections_threshold,
        }

    def run_find(self) -> np.ndarray | None:
        return self.find_func(**self.find_kwargs)

    def show_reflections(self, abc_matrix: np.ndarray):
        new_burn = False
        if self.reflections_editor._burn_workflow is None:
            self.reflections_editor.start_burn()
            new_burn = True

        burn_workflow = self.reflections_editor._burn_workflow

        if burn_workflow.burn_dialog is None:
            burn_workflow.start()
            new_burn = True

        # Needs to be after burn workflow is started in case one is created
        reflections = self.reflections_editor.reflections

        if self.crystal_id is None:
            # Add the new crystal to the back
            self.crystal_id = reflections.num_crystals

        crystal_id = self.crystal_id

        dialog = burn_workflow.burn_dialog
        dialog.set_crystal_orientation_to_hdf5_file()
        dialog.crystal_id = crystal_id
        dialog.apply_angular_shift = False

        crystals_table = reflections.crystals_table
        if crystals_table.size == 0:
            crystals_table = np.zeros((1, 9))

        while len(crystals_table) < crystal_id + 1:
            crystals_table = np.vstack((crystals_table, np.zeros((9,))))

        crystals_table[crystal_id] = abc_matrix
        reflections.crystals_table = crystals_table
        reflections.set_crystal_scan_number(crystal_id, self.scan_num)

        self.update_enable_states()

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

    def on_delete_crystal(self):
        if self.crystal_id is None:
            return

        reflections = self.reflections_editor.reflections
        if reflections is None:
            return

        reflections.delete_crystal(self.crystal_id)

        # Reset reflections editor and predictions
        self.reflections_editor.load_reflections()

        self.crystal_id = None
        self.update_enable_states()

    def load_settings(self):
        settings = QSettings()
        self.settings_serialized = settings.value('find_dialog_settings', {})

    def save_settings(self):
        settings = QSettings()
        settings.setValue('find_dialog_settings', self.settings_serialized)

    @property
    def _attrs_to_serialize(self) -> list[str]:
        return [
            'cell_parameters',
            'angular_tolerance',
            'resolution_limit',
            'reflections_threshold',
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
    def cell_parameter_widgets(self) -> list[QWidget]:
        names = ['a', 'b', 'c', 'alpha', 'beta', 'gamma']
        return [getattr(self.ui, x) for x in names]

    @property
    def cell_parameters(self) -> list[float]:
        return [w.value() for w in self.cell_parameter_widgets]

    @cell_parameters.setter
    def cell_parameters(self, values: list[float]):
        for w, v in zip(self.cell_parameter_widgets, values):
            w.setValue(v)

    @property
    def angular_tolerance(self) -> float:
        return self.ui.angular_tolerance.value()

    @angular_tolerance.setter
    def angular_tolerance(self, v: float):
        self.ui.angular_tolerance.setValue(v)

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
    def conserve_memory(self) -> bool:
        return self.ui.conserve_memory.isChecked()

    @conserve_memory.setter
    def conserve_memory(self, b: bool):
        self.ui.conserve_memory.setChecked(b)

    @property
    def thread_pool(self) -> QThreadPool:
        return QThreadPool.globalInstance()
