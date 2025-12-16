# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

from PySide6.QtCore import QObject, Signal

import h5py

from polylaue.model.reflections.external import ExternalReflections
from polylaue.model.section import Section
from polylaue.ui.burn_workflow import BurnWorkflow
from polylaue.ui.frame_tracker import FrameTracker
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

    def __init__(self, frame_tracker: FrameTracker, parent=None):
        super().__init__(parent)
        self.ui = UiLoader().load_file('reflections_editor.ui', parent)

        self.frame_tracker = frame_tracker
        self._section = None
        self.reflections = None
        self._burn_workflow = None

        self.reflections_style_editor = ReflectionsStyleEditor(self.ui)
        self.ui.reflections_style_editor_layout.addWidget(
            self.reflections_style_editor.ui
        )

        self.setup_connections()

    def setup_connections(self):
        self.ui.show_reflections.toggled.connect(
            lambda: self.reflections_changed.emit()
        )

        self.ui.prediction_matcher.clicked.connect(
            lambda: self.prediction_matcher_triggered.emit()
        )

        self.reflections_style_editor.style_edited.connect(
            lambda: self.reflections_style_changed.emit()
        )

        self.ui.burn.clicked.connect(self.start_burn)

    def clear(self):
        self.reflections = None
        self.update_info()
        self.reflections_changed.emit()

    @property
    def show_reflections(self) -> bool:
        return self.ui.show_reflections.isChecked()

    @show_reflections.setter
    def show_reflections(self, b: bool):
        self.ui.show_reflections.setChecked(b)

    @property
    def reflections_file_path(self) -> Path | None:
        if self.section is None:
            return None

        return self.section.reflections_file_path

    @property
    def section(self) -> Section | None:
        return self._section

    @section.setter
    def section(self, v: Section | None):
        if self._section == v:
            return

        self._section = v
        self.load_reflections()

        workflow = self._burn_workflow
        if workflow is not None and workflow.burn_dialog_is_visible():
            # Restart the burn workflow
            self.start_burn()

    def load_reflections(self):
        if self.reflections_file_path is None:
            self.clear()
            return

        self.reflections = ExternalReflections(self.reflections_file_path)
        self.update_info()
        self.reflections_changed.emit()

    def update_info(self):
        has_reflections = self.reflections is not None
        file_text = str(self.reflections.filepath) if has_reflections else ''
        num_crystals = self.reflections.num_crystals if has_reflections else 0

        self.ui.file.setText(file_text)
        self.ui.number_of_crystals.setValue(num_crystals)
        self.ui.prediction_matcher.setEnabled(has_reflections)

    def on_frame_changed(self):
        if self._burn_workflow is not None:
            self._burn_workflow.on_frame_changed()

    def on_series_or_scan_changed(self):
        if self._burn_workflow is not None:
            self._burn_workflow.on_series_or_scan_changed()

    @property
    def style(self) -> ReflectionsStyle:
        return self.reflections_style_editor.style

    @style.setter
    def style(self, v: ReflectionsStyle):
        self.reflections_style_editor.style = v

    def create_empty_reflections_file(self):
        path = self.section.expected_reflections_file_path
        with h5py.File(path, 'w'):
            pass

        self.load_reflections()

    def start_burn(self):
        if self.reflections is None:
            # We ought to make some default reflections
            self.create_empty_reflections_file()

        # Turn on reflections
        self.show_reflections = True

        if self._burn_workflow is not None:
            self._burn_workflow.clear()

        self._burn_workflow = BurnWorkflow(
            self.section,
            self.frame_tracker,
            self.reflections,
            parent=self.ui,
        )

        def on_reflections_edited():
            self.reflections_changed.emit()
            self.update_info()

        self._burn_workflow.reflections_edited.connect(on_reflections_edited)

        self._burn_workflow.start()
