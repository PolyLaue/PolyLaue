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

    def serialize_series_ui(self) -> dict:
        # These ought to match the serialization keys for series
        return {
            'dirpath_str': self.ui.series_dir.text(),
            'scan_shape': self.ui_scan_shape,
            'skip_frames': self.ui.skip_frames.value(),
            'num_scans': self.ui.num_scans.value(),
        }

    def deserialize_series_ui(self, d: dict):
        setters = {
            'dirpath_str': lambda v: self.ui.series_dir.setText(str(v)),
            'scan_shape': lambda v: setattr(self, 'ui_scan_shape', v),
            'skip_frames': self.ui.skip_frames.setValue,
            'num_scans': self.ui.num_scans.setValue,
        }
        for k, v in d.items():
            if k in setters:
                setters[k](v)

    def update_ui(self):
        self.deserialize_series_ui(self.series.serialize())

    def save_ui_to_series(self, series):
        # Deserialize the ui settings into the series
        series.deserialize(self.serialize_series_ui())

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

    # UI properties that match config properties
    @property
    def ui_scan_shape(self) -> tuple[int, int]:
        return (
            self.ui.scan_shape_i.value(),
            self.ui.scan_shape_j.value(),
        )

    @ui_scan_shape.setter
    def ui_scan_shape(self, v: tuple[int, int]):
        self.ui.scan_shape_i.setValue(v[0])
        self.ui.scan_shape_j.setValue(v[1])


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
        self.accept()

    def on_rejected(self):
        self.reject()
