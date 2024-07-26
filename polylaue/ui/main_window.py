import logging

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QWidget

import numpy as np

from polylaue.model.io import identify_loader_function
from polylaue.model.scan import Scan
from polylaue.model.series import Series
from polylaue.model.state import load_project_manager, save_project_manager
from polylaue.typing import PathLike
from polylaue.ui.frame_tracker import FrameTracker
from polylaue.ui.image_view import PolyLaueImageView
from polylaue.ui.reflections_editor import ReflectionsEditor
from polylaue.ui.project_navigator.dialog import ProjectNavigatorDialog
from polylaue.ui.series_editor import SeriesEditorDialog
from polylaue.ui.utils.ui_loader import UiLoader


logger = logging.getLogger(__name__)


class MainWindow:
    def __init__(self, parent: QWidget | None = None):
        self.ui = UiLoader().load_file('main_window.ui', parent)

        # Keep track of the working directory
        self.working_dir = None
        self.series = None
        self.frame_tracker = FrameTracker()

        # We currently assume all image files in a series will have the
        # same image loader. Cache that image loader so we do not have
        # to identify the image loader every time a new file is opened.
        self.image_loader_func = None

        # Load the project manager
        self.project_manager = load_project_manager()

        self.reset_scan_position()

        # Add the pyqtgraph view to its layout
        self.image_view = PolyLaueImageView(
            self.ui, 'CentralView', frame_tracker=self.frame_tracker
        )
        self.ui.image_view_layout.addWidget(self.image_view)

        self.reflections_editor = ReflectionsEditor(self.ui)

        self.setup_connections()

    def setup_connections(self):
        self.ui.action_open_series.triggered.connect(self.on_open_series)
        self.ui.action_open_project_navigator.triggered.connect(
            self.open_project_navigator
        )
        self.ui.action_overlays_reflections.triggered.connect(
            self.open_reflections_editor
        )

        self.image_view.shift_scan_number.connect(self.on_shift_scan_number)
        self.image_view.shift_scan_position.connect(
            self.on_shift_scan_position
        )
        self.image_view.mouse_move_message.connect(self.on_mouse_move_message)

        self.reflections_editor.reflections_changed.connect(
            self.on_reflections_changed
        )
        self.reflections_editor.reflections_style_changed.connect(
            self.on_reflections_style_changed
        )

    @property
    def scan_pos(self) -> np.ndarray:
        return np.asarray(self.frame_tracker.scan_pos)

    @scan_pos.setter
    def scan_pos(self, v: np.ndarray):
        self.frame_tracker.scan_pos = tuple(v)

    @property
    def scan_num(self) -> int:
        return self.frame_tracker.scan_num

    @scan_num.setter
    def scan_num(self, v: int):
        self.frame_tracker.scan_num = v

    def reset_scan_position(self):
        self.scan_pos = np.array([0, 0])

        if self.series:
            # Reset to the first available position on the series
            self.scan_num = self.series.scan_range_tuple[0]
        else:
            self.scan_num = 1

    def on_open_series(self):
        selected_directory = QFileDialog.getExistingDirectory(
            self.ui, 'Open Series Directory', self.working_dir
        )

        if not selected_directory:
            # User canceled
            return

        self.create_and_load_series(selected_directory)

    def create_and_load_series(self, selected_directory: PathLike):
        series = Series(selected_directory)
        editor = SeriesEditorDialog(series, self.ui)
        if not editor.exec():
            # User canceled.
            return

        self.load_series(series)

    def load_series(self, series: Series, reset_settings: bool = True):
        """Load the series located in the directory.

        This will also reset the current image settings and scan position.
        """

        self.series = series

        # Identify the image loader we will use for the series
        self.identify_image_loader()

        if reset_settings:
            # Reset scan position
            self.reset_scan_position()
            self.load_current_image()
            self.reset_image_view_settings()

        self.update_info_label()

        # After the data has been loaded, set the window title to be
        # the name of this series
        self.ui.setWindowTitle(f'PolyLaue - {series.name}')

    def identify_image_loader(self):
        self.image_loader_func = None
        if self.series is None:
            return

        if not self.series.file_list:
            # Might need to validate...
            self.series.validate()

        # Assume that all files in the series use the same image loader.
        # Use that loader for all files, rather than identifying the loader
        # each time an individual file is loaded.
        first_file = self.series.file_list[0]
        logger.debug(f'Identifying loader function for: {first_file}')
        self.image_loader_func = identify_loader_function(first_file)
        logger.debug(f'Identified loader function: {self.image_loader_func}')

    def open_project_navigator(self):
        if not hasattr(self, '_project_navigator_dialog'):
            d = ProjectNavigatorDialog(self.project_manager, self.ui)
            d.model.data_modified.connect(self.save_project_manager)
            d.view.series_modified.connect(
                self.on_project_navigator_series_modified
            )
            d.view.open_scan.connect(self.on_project_navigator_open_scan)
            self._project_navigator_dialog = d

        self._project_navigator_dialog.show()

    def on_project_navigator_series_modified(self, series: Series):
        if series is self.series:
            # Reload the series
            prev_scan_number = self.scan_num
            self.load_series(series)

            # Set the scan number
            self.scan_num = prev_scan_number
            self.on_frame_changed()

    def on_project_navigator_open_scan(self, scan: Scan):
        series = scan.parent
        if series is None:
            raise Exception('Scan does not have a parent')

        # Load the series
        self.load_series(series)

        # Hide the project navigator dialog
        self._project_navigator_dialog.hide()

        # Set the scan number
        self.scan_num = scan.number
        self.on_frame_changed()

    def save_project_manager(self):
        save_project_manager(self.project_manager)

    def reset_image_view_settings(self):
        self.image_view.auto_level_colors()
        self.image_view.auto_level_histogram_range()
        self.image_view.autoRange()

    def on_shift_scan_number(self, i: int):
        """Shift the scan number by `i`"""
        if self.series is None:
            # No series. Skip it.
            return

        new_scan_idx = self.scan_num + i
        if new_scan_idx in self.series.scan_range:
            # Just change the scan number
            self.scan_num = new_scan_idx
            self.on_frame_changed()
            return

        # See if we have a parent section, and switch to a different
        # series if we can.
        section = self.series.parent
        if section is None:
            # Just return - can't do anything
            return

        new_series = section.series_with_scan_index(new_scan_idx)
        if new_series is None:
            # Just return - can't do anything
            return

        self.scan_num = new_scan_idx

        # Load this series without resetting the settings
        self.load_series(new_series, reset_settings=False)
        self.scan_num = new_scan_idx
        self.on_frame_changed()

    def on_shift_scan_position(self, i: int, j: int):
        """Shift the scan position by `i` rows and `j` columns"""
        if self.series is None:
            # No series. Skip it.
            return

        # Clip it so we don't go out of bounds
        self.scan_pos = np.clip(
            self.scan_pos + (i, j),
            a_min=[0, 0],
            a_max=np.asarray(self.series.scan_shape) - 1,
        )
        self.on_frame_changed()

    def on_frame_changed(self):
        self.load_current_image()
        self.update_info_label()

        # Update the mouse hover info with the new frame
        self.image_view.on_mouse_move()
        self.image_view.update_reflection_overlays()

    def load_current_image(self):
        filepath = self.series.filepath(*self.scan_pos, self.scan_num)
        self.ui.setWindowTitle(filepath.name)
        img = self.image_loader_func(filepath)
        self.image_view.setImage(
            img, autoRange=False, autoLevels=False, autoHistogramRange=False
        )

    def update_info_label(self):
        if self.series is None:
            text = ''
        else:
            # Make sure these are native types, or else on Mac and
            # Windows, they might appear as `np.int64(1)`.
            text = (
                f'Scan {int(self.scan_num)}, '
                f'Position {tuple(map(int, self.scan_pos + 1))}'
            )

        self.ui.info_label.setText(text)

    def set_icon(self, icon: QIcon):
        self.ui.setWindowIcon(icon)

    def show(self):
        """Show the window"""
        self.ui.show()

    def on_mouse_move_message(self, message: str):
        self.ui.status_bar.showMessage(message)

    def open_reflections_editor(self):
        self.reflections_editor.ui.show()

    def on_reflections_changed(self):
        new_reflections = self.reflections_editor.reflections
        self.image_view.reflections = new_reflections

    def on_reflections_style_changed(self):
        new_style = self.reflections_editor.style
        self.image_view.reflections_style = new_style
