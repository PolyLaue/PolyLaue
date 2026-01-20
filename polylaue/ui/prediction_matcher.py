# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

import numpy as np
import pyqtgraph as pg

from polylaue.ui.utils.keep_dialog_on_top import keep_dialog_on_top


class PredictionMatcherDialog(QDialog):
    def __init__(
        self,
        image_view: pg.ImageView,
        reflections_array: np.ndarray,
        crystal_id: int,
        parent=None,
    ):
        super().__init__(parent=parent)
        keep_dialog_on_top(self)

        self.image_view = image_view
        self.reflections_array = reflections_array
        self.crystal_id = crystal_id

        self.setWindowTitle(
            f'Find Matching Reflections for Crystal ID "{crystal_id}"'
        )

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        label = QLabel(
            'Find the matching reflections in a frame.\n'
            'Click OK to save this reflections table to the external '
            'predictions file.'
        )
        layout.addWidget(label)
        layout.setAlignment(label, Qt.AlignHCenter)

        # Add a button box for accept/cancel
        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.button_box = QDialogButtonBox(buttons, self)
        layout.addWidget(self.button_box)

        self.setup_connections()

    def setup_connections(self):
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.finished.connect(self.on_finished)

    def accept(self):
        # Save the reflections pattern the external predictions file
        crystal_id = self.crystal_id
        external_reflections = self.image_view.reflections

        # Get the current scan number and scan position
        frame_tracker = self.image_view.frame_tracker
        scan_num = frame_tracker.scan_num
        row = frame_tracker.scan_pos_x
        col = frame_tracker.scan_pos_y

        # Add the crystal ID to our array
        reflections_array = np.insert(
            self.reflections_array, 9, crystal_id, axis=1
        )

        # Get the reflections table
        current_table = external_reflections.reflections_table(
            row, col, scan_num
        )
        if current_table is not None:
            # Remove all rows that match our crystal id
            array = np.delete(
                current_table,
                np.where(current_table[:, 9].astype(int) == crystal_id)[0],
                axis=0,
            )
            # Append our array to the end
            array = np.vstack((array, reflections_array))
            # Sort by crystal ID
            array = array[array[:, 9].argsort()]
        else:
            # The current table doesn't exist, and ours is the only one
            array = reflections_array

        # Write it to the HDF5 file
        external_reflections.write_reflections_table(array, row, col, scan_num)

        print(
            f'Reflections for Crystal ID "{crystal_id}" written to:',
            external_reflections.filepath,
        )

        super().accept()

    def on_finished(self):
        self.disconnect()

    def run(self):
        # Set the reflections array to be the one we provided and lock it
        self.image_view.active_search_crystal_id = self.crystal_id
        self.image_view.active_search_array = self.reflections_array
        self.image_view.update_reflection_overlays()
        self.show()

    def disconnect(self):
        self.image_view.active_search_crystal_id = None
        self.image_view.active_search_array = None
        self.image_view.update_reflection_overlays()
