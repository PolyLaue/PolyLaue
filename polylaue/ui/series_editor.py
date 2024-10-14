# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

import copy
import logging

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from polylaue.model.series import Series
from polylaue.ui.utils.ui_loader import UiLoader

logger = logging.getLogger(__name__)


class SeriesEditor:
    def __init__(self, series: Series, parent: QWidget = None):
        self.ui = UiLoader().load_file('series_editor.ui', parent)

        self.series = series

        self.update_ui()
        self.setup_connections()

    def setup_connections(self):
        self.ui.select_series_dir.clicked.connect(self.select_series_dir)
        self.ui.select_background_image.clicked.connect(
            self.select_background_image_path
        )

    def serialize_series_ui(self) -> dict:
        # Serialize UI settings into a dict
        # These names should match attributes we will set on the Series
        return {
            'dirpath_str': self.ui.series_dir.text(),
            'scan_shape': self.ui_scan_shape,
            'skip_frames': self.ui.skip_frames.value(),
            'scan_range_tuple': self.ui_scan_range,
            'background_image_path_str': self.ui_background_image,
        }

    def update_ui(self):
        d = self.series.serialize()

        # Add a property for the scan_range_tuple
        d['scan_range_tuple'] = self.series.scan_range_tuple

        setters = {
            'dirpath_str': lambda v: self.ui.series_dir.setText(str(v)),
            'scan_shape': lambda v: setattr(self, 'ui_scan_shape', v),
            'skip_frames': self.ui.skip_frames.setValue,
            'scan_range_tuple': lambda v: setattr(self, 'ui_scan_range', v),
            'background_image_path_str': lambda v: (
                setattr(self, 'ui_background_image', v),
            ),
        }
        for k, v in d.items():
            if k in setters:
                setters[k](v)

    def save_ui_to_series(self, series):
        # Deserialize the ui settings into the series
        d = self.serialize_series_ui()

        for k, v in d.items():
            setattr(series, k, v)

    def select_series_dir(self):
        selected_directory = QFileDialog.getExistingDirectory(
            self.ui,
            'Open Series Directory',
            self.ui.series_dir.text(),
        )

        if not selected_directory:
            # User canceled
            return

        self.ui.series_dir.setText(selected_directory)

    def select_background_image_path(self):
        selected_file, selected_filter = QFileDialog.getOpenFileName(
            self.ui,
            'Select Background Image',
            self.ui.background_image.text(),
        )

        if not selected_file:
            # User canceled
            return

        self.ui.background_image.setText(selected_file)

    # UI properties that match config properties
    @property
    def ui_scan_shape(self) -> tuple[int, int]:
        return (
            self.ui.scan_shape_y.value(),
            self.ui.scan_shape_z.value(),
        )

    @ui_scan_shape.setter
    def ui_scan_shape(self, v: tuple[int, int]):
        self.ui.scan_shape_y.setValue(v[0])
        self.ui.scan_shape_z.setValue(v[1])

    @property
    def ui_scan_range(self) -> tuple[int, int]:
        return (
            self.ui.scan_range_start.value(),
            self.ui.scan_range_stop.value(),
        )

    @ui_scan_range.setter
    def ui_scan_range(self, v: tuple[int, int]):
        self.ui.scan_range_start.setValue(v[0])
        self.ui.scan_range_stop.setValue(v[1])

    @property
    def ui_background_image(self) -> str | None:
        t = self.ui.background_image.text()
        return t if t else None

    @ui_background_image.setter
    def ui_background_image(self, v: str | None):
        t = v if v else ''
        self.ui.background_image.setText(t)


class SeriesEditorDialog(QDialog):
    def __init__(self, series: Series, parent: QWidget = None):
        super().__init__(parent)
        self.series_editor = SeriesEditor(series, parent)

        self.setWindowTitle('Series Editor')

        self.setLayout(QVBoxLayout(self))
        layout = self.layout()
        layout.addWidget(self.series_editor.ui)

        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.button_box = QDialogButtonBox(buttons, self)
        layout.addWidget(self.button_box)

        self.setup_connections()

    def setup_connections(self):
        self.button_box.accepted.connect(self.on_accepted)
        self.button_box.rejected.connect(self.on_rejected)

    @property
    def series(self):
        return self.series_editor.series

    def on_accepted(self):
        # Make a deep copy, write to that one and validate, before
        # writing to the actual series.
        series_copy = copy.deepcopy(self.series)

        # Validate first. If it fails, keep showing the dialog.
        self.series_editor.save_ui_to_series(series_copy)
        try:
            series_copy.validate()
        except Exception as e:
            msg = f'Validation error. Check settings and try again.\n\n{e}'
            logger.critical(msg)
            QMessageBox.critical(None, 'Series Validation Failed', msg)
            return

        # Validation succeeded. Save to the original series. Accept the dialog.
        self.series_editor.save_ui_to_series(self.series)

        if self.series.name == 'Series':
            # If the series name is the default of 'Series', update the name to
            # the name of the directory.
            self.series.name = self.series.dirpath.name

        self.accept()

    def on_rejected(self):
        self.reject()
