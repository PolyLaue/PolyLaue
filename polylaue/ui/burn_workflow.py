# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtWidgets import QCheckBox, QMessageBox, QWidget

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
        self.angular_shifts = None
        self.burn_dialog = None

    def start(self):
        try:
            self.validate()
        except ValidationError as e:
            QMessageBox.critical(None, 'Validation Failed', str(e))
            return

        self.show_burn_dialog()

    def validate(self):
        if self.project.geometry_path is None:
            msg = (
                'Geometry path must be defined for this project '
                f'({self.project.name}) in order to burn reflections'
            )
            raise ValidationError(msg)

    def clear(self):
        self.abc_matrix = None
        if self.burn_dialog is not None:
            self.burn_dialog.ui.hide()
            self.burn_dialog = None

    def on_frame_changed(self):
        if self.burn_dialog is not None:
            # When the frame changes, deactivate burn
            self.burn_dialog.deactivate_burn()

    @property
    def project_dir_abc_matrix_path(self) -> Path:
        return self.project.directory / 'abc_matrix.npy'

    @property
    def angular_shifts_path(self) -> Path:
        return self.project.directory / 'ang_shifts.npy'

    def load_abc_matrix(self):
        self.abc_matrix = None
        if self.burn_dialog.crystal_orientation_is_from_project_dir:
            path = self.project_dir_abc_matrix_path
            if not path.exists():
                crystal_orientation = self.burn_dialog.crystal_orientation
                msg = (
                    f'Crystal orientation is set to "{crystal_orientation}", '
                    'but the ABC Matrix file is missing from its expected '
                    f'location ({path})'
                )
                print(msg)
                QMessageBox.critical(None, 'Failed to Load ABC Matrix', msg)
                return

            self.abc_matrix = np.load(path)
            self.set_abc_matrix_to_crystals_table_if_missing()
        elif self.burn_dialog.crystal_orientation_is_from_hdf5_file:
            crystals_table = self.reflections.crystals_table
            if self.crystal_id >= len(crystals_table):
                crystal_orientation = self.burn_dialog.crystal_orientation
                msg = (
                    f'Crystal orientation is set to "{crystal_orientation}", '
                    f'but the selected crystal ID ({self.crystal_id}) '
                    'is out of range for the crystals table at "/crystals" '
                    f'(length {len(crystals_table)})'
                )
                print(msg)
                QMessageBox.critical(None, 'Failed to Load ABC Matrix', msg)
                return

            self.abc_matrix = crystals_table[self.crystal_id]
        else:
            msg = (
                f'Crystal Orientation: {self.burn_dialog.crystal_orientation}'
            )
            raise NotImplementedError(msg)

    def set_abc_matrix_to_crystals_table_if_missing(self):
        # This sets the ABC Matrix to the crystals table (using
        # the currently selected Crystal ID) if the ABC matrix
        # is not already present for this crystal ID.
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

    def load_angular_shifts(self):
        self.angular_shifts = None
        if not self.apply_angular_shift:
            return

        path = self.angular_shifts_path
        if not path.exists():
            msg = (
                '"Apply Angular Shift" is enabled, but the angular shifts '
                f'file does not exist at its expected path ({path})'
            )
            print(msg)
            QMessageBox.critical(None, 'Failed to Load Angular Shifts', msg)
            return

        self.angular_shifts = np.load(path)

    def show_burn_dialog(self):
        if self.burn_dialog:
            self.burn_dialog.ui.hide()

        self.burn_dialog = BurnDialog(self.parent)
        self.burn_dialog.burn_triggered.connect(self.run_burn)
        self.burn_dialog.crystal_name_modified.connect(self.write_crystal_name)
        self.burn_dialog.load_crystal_name.connect(self.load_crystal_name)
        self.burn_dialog.overwrite_crystal.connect(self.overwrite_crystal)
        self.burn_dialog.write_crystal_orientation.connect(
            self.write_crystal_orientation
        )
        self.burn_dialog.clear_reflections.connect(self.clear_reflections)
        self.load_crystal_name()
        self.burn_dialog.ui.show()

    @property
    def project(self):
        return self.section.parent

    @property
    def apply_angular_shift(self) -> bool:
        return self.burn_dialog.apply_angular_shift

    @property
    def crystal_id(self) -> int:
        return self.burn_dialog.crystal_id

    @property
    def angular_shift_scan_number(self) -> int:
        # This returns the current scan number if angular_shifts is not
        # None, and it returns `-1` if angular_shifts is None.
        if self.angular_shifts is None:
            return -1

        return self.frame_tracker.scan_num

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
            'nscan': self.angular_shift_scan_number,
            'ang_shifts': self.angular_shifts,
        }

    def run_burn(self):
        self.load_abc_matrix()
        if self.abc_matrix is None:
            print('Failed to load ABC matrix. Aborting burn()...')
            return

        self.load_angular_shifts()
        if self.apply_angular_shift and self.angular_shifts is None:
            print('Failed to load angular shifts. Aborting burn()...')
            return

        pred_list1, pred_list2 = burn(**self.burn_kwargs)

        crystal_id = self.crystal_id

        if pred_list1.size != 0:
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
            table = np.insert(table, 9, crystal_id, axis=1)
        else:
            table = pred_list2

        # Check if there's an existing table. If so, replace any
        # reflections matching our crystal ID with the new reflections.
        existing_table = self.reflections.reflections_table(
            *self.frame_tracker.scan_pos,
            self.frame_tracker.scan_num,
        )
        if existing_table is not None and existing_table.size > 0:
            # Remove all rows that match our crystal id
            existing_table = np.delete(
                existing_table,
                np.where(existing_table[:, 9].astype(int) == crystal_id)[0],
                axis=0,
            )

            if table.size != 0:
                # Add our new table
                table = np.vstack((existing_table, table))
            else:
                table = existing_table

            # Sort by crystal ID
            table = table[table[:, 9].argsort()]

        self.reflections.write_reflections_table(
            table,
            *self.frame_tracker.scan_pos,
            self.frame_tracker.scan_num,
        )

        self.reflections_edited.emit()

    def write_crystal_name(self):
        # Encode the crystal name to utf-8
        # We may need to adjust size.
        name = self.burn_dialog.crystal_name.encode()
        crystal_id = self.crystal_id
        crystal_names = self.reflections.crystal_names

        size = max(crystal_names.itemsize, len(name))
        crystal_names = crystal_names.astype(f'|S{size}')

        if crystal_id >= len(crystal_names):
            # Need to add some empty crystal names until we get to `i`
            to_add = crystal_id - len(crystal_names) + 1
            crystal_names = np.append(crystal_names, [b''] * to_add)

        crystal_names[crystal_id] = name
        self.reflections.crystal_names = crystal_names

    def load_crystal_name(self):
        crystal_id = self.crystal_id
        crystal_names = self.reflections.crystal_names
        if crystal_id < len(crystal_names):
            name = crystal_names[crystal_id].decode()
        else:
            name = ''

        self.burn_dialog.crystal_name = name

    def overwrite_crystal(self):
        self.load_abc_matrix()
        if self.abc_matrix is None:
            print('Failed to load ABC matrix. Aborting crystal overwrite...')
            return

        crystal_id = self.crystal_id
        crystals_table = self.reflections.crystals_table
        if crystal_id >= len(crystals_table):
            # Re-use the logic where we are missing the crystal
            self.set_abc_matrix_to_crystals_table_if_missing()
            return

        # Otherwise, we'll overwrite the crystal!
        crystals_table[crystal_id] = self.abc_matrix
        self.reflections.crystals_table = crystals_table

    def write_crystal_orientation(self):
        self.load_abc_matrix()
        if self.abc_matrix is None:
            QMessageBox.critical(
                None,
                'Failed to load ABC matrix',
                'Failed to load ABC matrix. Aborting write...',
            )
            return

        project_dir = self.project.directory
        filenames = [
            'abc_matrix.npy',
            'abc_matrix0.npy',
        ]
        filenames_joined = ' and '.join(f'"{x}"' for x in filenames)
        msg = f'{filenames_joined} were saved to:\n\n{project_dir}\n'

        for filename in filenames:
            filepath = project_dir / filename
            np.save(filepath, self.abc_matrix)

        print(msg)

        settings = QSettings()
        skip_message_key = '_skip_burn_write_crystal_orientation_message'
        skip_message = settings.value(skip_message_key, False)
        if not skip_message:
            box = QMessageBox(
                QMessageBox.Icon.Information,
                'Files saved',
                msg,
                QMessageBox.StandardButton.Ok,
            )
            cb = QCheckBox("Don't show this again")
            box.setCheckBox(cb)
            box.layout().setAlignment(cb, Qt.AlignRight)
            box.exec_()
            if cb.isChecked():
                settings.setValue(skip_message_key, True)

    def clear_reflections(self):
        # Delete any reflections matching the currently selected crystal ID
        crystal_id = self.crystal_id

        table = self.reflections.reflections_table(
            *self.frame_tracker.scan_pos,
            self.frame_tracker.scan_num,
        )
        if table is None:
            # Nothing to do...
            return

        if table.size > 0:
            # Remove all rows that match the crystal id
            table = np.delete(
                table,
                np.where(table[:, 9].astype(int) == crystal_id)[0],
                axis=0,
            )

        if table.size == 0:
            # After deleting reflections, if the table size is now zero,
            # just delete the whole thing.
            self.reflections.delete_reflections_table(
                *self.frame_tracker.scan_pos,
                self.frame_tracker.scan_num,
            )
        else:
            # Otherwise, write the table back
            self.reflections.write_reflections_table(
                table,
                *self.frame_tracker.scan_pos,
                self.frame_tracker.scan_num,
            )

        self.reflections_edited.emit()


class ValidationError(Exception):
    pass
