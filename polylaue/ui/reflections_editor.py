# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import numpy as np

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QFileDialog

from polylaue.model.reflections.external import ExternalReflections
from polylaue.ui.reflections_style import ReflectionsStyle
from polylaue.ui.reflections_style_editor import ReflectionsStyleEditor
from polylaue.ui.utils.ui_loader import UiLoader


class ReflectionsEditor(QObject):
    """Emitted when the reflections are modified"""

    reflections_changed = Signal()

    """Emitted when the prediction matcher should be started"""
    prediction_matcher_triggered = Signal()

    """Emitted when the reflections style was modified"""
    reflections_style_changed = Signal()

    def __init__(self, frame_tracker, parent=None):
        super().__init__(parent)
        self.ui = UiLoader().load_file('reflections_editor.ui', parent)

        self.frame_tracker = frame_tracker

        self.reflections_style_editor = ReflectionsStyleEditor(self.ui)
        self.ui.reflections_style_editor_layout.addWidget(
            self.reflections_style_editor.ui
        )

        self.setup_connections()

    def setup_connections(self):
        self.ui.burn.clicked.connect(self.burn)
        self.ui.open_external_reflections.clicked.connect(
            self.open_external_reflections
        )

        self.ui.prediction_matcher.clicked.connect(
            self.prediction_matcher_triggered.emit
        )

        self.reflections_style_editor.style_edited.connect(
            self.reflections_style_changed.emit
        )

    def burn(self):
        from polylaue.model.PolyLaueCore import burn

        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QHBoxLayout, QLabel, QSlider, QVBoxLayout

        layout = QHBoxLayout()
        parent_layout = QVBoxLayout()
        parent_layout.addLayout(layout)

        dialog = QDialog()
        dialog.setLayout(parent_layout)
        dialog.setWindowTitle('Burn')

        slider = QSlider(Qt.Orientation.Horizontal)

        upper = QDoubleSpinBox()
        upper.setValue(1.0)

        value_sb = QDoubleSpinBox()
        value_sb.setValue(0.35)
        parent_layout.addWidget(value_sb)

        slider_max = 100

        def run_burn():
            value = value_sb.value()
            burn(value)

            ret = np.load('predicted_list.npz')
            pred_list1 = ret['ipred_list1']
            pred_list2 = ret['ipred_list2']
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
            crystal_id = 0
            table = np.insert(table, 9, crystal_id, axis=1)
            reflections = self.reflections

            frame_tracker = self.frame_tracker
            reflections.write_reflections_table(
                table,
                *frame_tracker.scan_pos,
                frame_tracker.scan_num,
            )
            self.reflections_changed.emit()


        def slider_value_changed():
            print('hi')
            value = slider.value()
            # Re-map it to our range and compute value
            value = (slider_max - value) * upper.value() / slider_max
            value_sb.setValue(value)

            run_burn()

        # Our slider will have a resolution of 100
        slider.setMaximum(slider_max)
        slider.setMinimum(0)
        slider.setSingleStep(1)
        slider.valueChanged.connect(slider_value_changed)

        layout.addWidget(upper)
        layout.addWidget(slider)
        layout.addWidget(QLabel('0.0'))
        dialog.show()

        self._burn_dialog = dialog

    def open_external_reflections(self):
        selected_file, selected_filter = QFileDialog.getOpenFileName(
            self.ui,
            'Open External Reflections',
            None,
            'HDF5 files (*.h5 *.hdf5)',
        )

        if not selected_file:
            return

        self.reflections = ExternalReflections(selected_file)
        self.update_info()
        self.reflections_changed.emit()

    def update_info(self):
        self.ui.file.setText(str(self.reflections.filepath))
        self.ui.number_of_crystals.setValue(self.reflections.num_crystals)
        self.ui.prediction_matcher.setEnabled(True)

    @property
    def style(self) -> ReflectionsStyle:
        return self.reflections_style_editor.style

    @style.setter
    def style(self, v: ReflectionsStyle):
        self.reflections_style_editor.style = v
