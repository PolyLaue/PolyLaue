# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QMessageBox, QWidget

import numpy as np

from polylaue.model.core import burn
from polylaue.model.reflections.external import ExternalReflections
from polylaue.model.section import Section
from polylaue.ui.burn_dialog import BurnDialog
from polylaue.ui.frame_tracker import FrameTracker


class BurnWorkflow(QObject):

    reflections_edited = Signal()

    def __init__(
        self,
        section: Section,
        frame_tracker: FrameTracker,
        reflections: ExternalReflections,
        parent: QWidget = None,
    ):
        super().__init__(parent)

        self.section = section
        self.frame_tracker = frame_tracker
        self.reflections = reflections
        self.parent = parent

        self.abc_matrix = None
        self.burn_dialog = None

    def start(self):
        try:
            self.validate()
        except ValidationError as e:
            QMessageBox.critical(None, 'Validation Failed', str(e))
            return

        self.abc_matrix = np.load(self.abc_matrix_path)
        self.show_burn_dialog()

    def validate(self):
        if self.project.geometry_path is None:
            msg = (
                'Geometry path must be defined for this project '
                f'({self.project.name}) in order to burn reflections'
            )
            raise ValidationError(msg)

        if not self.abc_matrix_path.exists():
            msg = (
                'ABC Matrix file must be present in the root project '
                f'directory ({self.abc_matrix_path})'
            )
            raise ValidationError(msg)

    def clear(self):
        self.abc_matrix = None
        if self.burn_dialog is not None:
            self.burn_dialog.ui.hide()
            self.burn_dialog = None

    @property
    def abc_matrix_path(self) -> Path:
        return self.project.directory / 'abc_matrix.npy'

    def validate_crystal_id(self):
        # Check if the ABC matrix is already present within the predictions
        # file. If it is, set the crystal ID to match. If it is not, add it
        # and set the crystal id.
        crystals_table = self.reflections.crystals_table

        if self.crystal_id < len(crystals_table):
            # It's a valid ID. Just return.
            return

        # It's not valid. We will create a new entry for it.
        if crystals_table.size == 0:
            crystals_table = np.zeros((0, 9), dtype=float)

        while len(crystals_table) < self.crystal_id:
            crystals_table = np.vstack((crystals_table, np.zeros((9,))))

        if len(crystals_table) == self.crystal_id:
            # Set the current abc matrix as a new crystal id
            crystals_table = np.vstack((crystals_table, self.abc_matrix))

        self.reflections.crystals_table = crystals_table

    def show_burn_dialog(self):
        if self.burn_dialog:
            self.burn_dialog.ui.hide()

        self.burn_dialog = BurnDialog(self.parent)
        self.burn_dialog.settings_changed.connect(self.run_burn)
        self.burn_dialog.ui.show()

    @property
    def project(self):
        return self.section.parent

    @property
    def crystal_id(self):
        return self.burn_dialog.crystal_id

    @property
    def burn_kwargs(self) -> dict:
        project = self.project
        geometry = project.geometry_data

        return {
            'energy_highest': project.energy_range[1],
            'energy_lowest': project.energy_range[0],
            'structure_type': self.burn_dialog.structure_type,
            'image_size_x': project.frame_shape[0],
            'image_size_y': project.frame_shape[1],
            'abc': self.abc_matrix,
            'det_org': geometry['det_org'],
            'beam_dir': geometry['beam_dir'],
            'pix_dist': geometry['pix_dist'],
            'res_lim': self.burn_dialog.dmin,
        }

    def run_burn(self):
        self.validate_crystal_id()
        pred_list1, pred_list2 = burn(**self.burn_kwargs)

        table = np.hstack(
            (
                # x, y
                pred_list2[:, 0:2],
                # h, k, l
                pred_list1[:, 0:3],
                # energy
                pred_list2[:, 2:3],
                # First order, last order
                pred_list1[:, 3:5],
                # d-spacing
                pred_list2[:, 3:4],
            )
        )

        # Add the crystal ID into the 9th column
        crystal_id = self.crystal_id
        table = np.insert(table, 9, crystal_id, axis=1)

        # Check if there's an existing table. If so, replace any
        # reflections matching our crystal ID with the new reflections.
        existing_table = self.reflections.reflections_table(
            *self.frame_tracker.scan_pos,
            self.frame_tracker.scan_num,
        )
        if existing_table is not None:
            # Remove all rows that match our crystal id
            existing_table = np.delete(
                existing_table,
                np.where(existing_table[:, 9].astype(int) == crystal_id)[0],
                axis=0,
            )

            # Add our new table
            table = np.vstack((existing_table, table))

            # Sort by crystal ID
            table = table[table[:, 9].argsort()]

        self.reflections.write_reflections_table(
            table,
            *self.frame_tracker.scan_pos,
            self.frame_tracker.scan_num,
        )

        self.reflections_edited.emit()


class ValidationError(Exception):
    pass
