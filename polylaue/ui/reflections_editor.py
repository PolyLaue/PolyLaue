# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = UiLoader().load_file('reflections_editor.ui', parent)

        self.reflections_style_editor = ReflectionsStyleEditor(self.ui)
        self.ui.reflections_style_editor_layout.addWidget(
            self.reflections_style_editor.ui
        )

        self.setup_connections()

    def setup_connections(self):
        self.ui.open_external_reflections.clicked.connect(
            self.open_external_reflections
        )

        self.ui.prediction_matcher.clicked.connect(
            self.prediction_matcher_triggered.emit
        )

        self.reflections_style_editor.style_edited.connect(
            self.reflections_style_changed.emit
        )

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
