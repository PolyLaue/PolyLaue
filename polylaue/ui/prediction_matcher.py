from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout

import numpy as np
import pyqtgraph as pg


class PredictionMatcherDialog(QDialog):
    def __init__(
        self,
        image_view: pg.ImageView,
        reflections_array: np.ndarray,
        parent=None,
    ):
        super().__init__(parent=parent)
        self.image_view = image_view
        self.reflections_array = reflections_array

        self.setWindowTitle('Find Matching Reflections')

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
        external_reflections = self.image_view.reflections

        # Get the current scan number and scan position
        frame_tracker = self.image_view.frame_tracker
        scan_num = frame_tracker.scan_num
        row = frame_tracker.scan_pos_x
        col = frame_tracker.scan_pos_y

        if external_reflections.path_exists(row, col, scan_num):
            # If it already exists, warn the user
            # FIXME
            pass

        # Write it to the HDF5 file
        external_reflections.write_reflections_table(
            self.reflections_array, row, col, scan_num
        )

        print('Pattern saved to:', external_reflections.filepath)

        super().accept()

    def on_finished(self):
        self.disconnect()

    def run(self):
        # Set the reflections array to be the one we provided and lock it
        self.image_view.reflections_array = self.reflections_array
        self.image_view.lock_reflections_array = True
        self.image_view.update_reflection_overlays()
        self.show()

    def disconnect(self):
        self.image_view.lock_reflections_array = False
        self.image_view.update_reflection_overlays()
