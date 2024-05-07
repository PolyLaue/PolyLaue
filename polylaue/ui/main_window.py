import logging
from pathlib import Path

from PySide6.QtCore import QPointF
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFileDialog, QWidget

import numpy as np
from pyqtgraph import GraphicsScene, ImageItem

from polylaue.model.io import identify_loader_function
from polylaue.model.series import Series
from polylaue.typing import PathLike
from polylaue.ui.image_view import PolyLaueImageView
from polylaue.ui.series_editor import SeriesEditorDialog
from polylaue.ui.utils.ui_loader import UiLoader


logger = logging.getLogger(__name__)


class MainWindow:
    def __init__(self, parent: QWidget | None = None):
        self.ui = UiLoader().load_file('main_window.ui', parent)

        # Keep track of the working directory
        self.working_dir = None
        self.series = None
        self._last_mouse_position = None

        # We currently assume all image files in a series will have the
        # same image loader. Cache that image loader so we do not have
        # to identify the image loader every time a new file is opened.
        self.image_loader_func = None

        self.reset_scan_position()

        # Add the pyqtgraph view to its layout
        self.image_view = PolyLaueImageView(self.ui, 'CentralView')
        self.add_cmap_reverse_menu_action()
        self.ui.image_view_layout.addWidget(self.image_view)

        self.setup_connections()

    def setup_connections(self):
        self.ui.action_open_series.triggered.connect(self.on_open_series)

        self.image_view.shift_scan_number.connect(self.on_shift_scan_number)
        self.image_view.shift_scan_position.connect(
            self.on_shift_scan_position
        )
        self.scene.sigMouseMoved.connect(self.on_mouse_move)

    @property
    def image_item(self) -> ImageItem:
        return self.image_view.getImageItem()

    @property
    def scene(self) -> GraphicsScene:
        return self.image_item.scene()

    @property
    def image_data(self) -> np.ndarray:
        return self.image_item.image

    def reset_scan_position(self):
        self.scan_pos = np.array([0, 0])
        self.scan_num = 0

    def on_open_series(self):
        selected_directory = QFileDialog.getExistingDirectory(
            self.ui, 'Open Series Directory', self.working_dir
        )

        if not selected_directory:
            # User canceled
            return

        self.load_series(selected_directory)

    def load_series(self, selected_directory: PathLike):
        """Load the series located in the directory.

        This will also reset the current image settings and scan position.
        """
        series = Series(selected_directory)
        editor = SeriesEditorDialog(series, self.ui)
        if not editor.exec():
            # User canceled.
            return

        self.series = series

        # Set the window title to be the name of this directory
        self.ui.setWindowTitle(f'PolyLaue - {Path(selected_directory).name}')

        # Identify the image loader we will use for the series
        self.identify_image_loader()

        # Reset scan position
        self.reset_scan_position()
        self.load_current_image()
        self.reset_image_view_settings()
        self.update_info_label()

    def identify_image_loader(self):
        self.image_loader_func = None
        if self.series is None:
            return

        # Assume that all files in the series use the same image loader.
        # Use that loader for all files, rather than identifying the loader
        # each time an individual file is loaded.
        first_file = self.series.file_list[0]
        logger.debug(f'Identifying loader function for: {first_file}')
        self.image_loader_func = identify_loader_function(first_file)
        logger.debug(f'Identified loader function: {self.image_loader_func}')

    def reset_image_view_settings(self):
        self.auto_level_colors()
        self.auto_level_histogram_range()
        self.image_view.autoRange()

    def auto_level_colors(self):
        # These levels appear to work well for the data we have
        data = self.image_data
        lower = np.nanpercentile(data, 1.0)
        upper = np.nanpercentile(data, 99.75)
        self.image_view.setLevels(lower, upper)

    def auto_level_histogram_range(self):
        # Make the histogram range a little bigger than the auto level colors
        data = self.image_data
        lower = np.nanpercentile(data, 0.5)
        upper = np.nanpercentile(data, 99.8)
        self.image_view.setHistogramRange(lower, upper)

    def on_shift_scan_number(self, i: int):
        """Shift the scan number by `i`"""
        if self.series is None:
            # No series. Skip it.
            return

        # Clip it so we don't go out of bounds
        max_idx = self.series.num_scans - 1
        self.scan_num = np.clip(self.scan_num + i, a_min=0, a_max=max_idx)
        self.on_frame_changed()

    def on_shift_scan_position(self, i: int, j: int):
        """Shift the scan position by `i` rows and `j` columns"""
        if self.series is None:
            # No series. Skip it.
            return

        # Clip it so we don't go out of bounds
        np.clip(
            self.scan_pos + (i, j),
            a_min=[0, 0],
            a_max=np.asarray(self.series.scan_shape) - 1,
            out=self.scan_pos,
        )
        self.on_frame_changed()

    def on_frame_changed(self):
        self.load_current_image()
        self.update_info_label()

        if self._last_mouse_position:
            # Update the mouse hover info with the new frame
            self.on_mouse_move(self._last_mouse_position)

    def load_current_image(self):
        filepath = self.series.filepath(*self.scan_pos, self.scan_num)
        img = self.image_loader_func(filepath)
        self.image_view.setImage(
            img, autoRange=False, autoLevels=False, autoHistogramRange=False
        )

    def on_mouse_move(self, pos: QPointF):
        if self.image_data is None:
            # No data
            return

        # Keep a record of the last position in case we change frames,
        # so we can call this function again.
        self._last_mouse_position = pos

        # First, map the scene coordinates to the view
        pos = self.image_view.view.mapSceneToView(pos)

        # We get the correct pixel coordinates by flooring these
        j, i = np.floor(pos.toTuple()).astype(int)

        data_shape = self.image_data.shape
        if not 0 <= i < data_shape[0] or not 0 <= j < data_shape[1]:
            # The mouse is out of bounds
            self.ui.status_bar.clearMessage()
            return

        # For display, x and y are the same as j and i, respectively
        x, y = j, i

        intensity = self.image_data[i, j]
        self.ui.status_bar.showMessage(f'{x=}, {y=}, {intensity=}')

    def update_info_label(self):
        if self.series is None:
            text = ''
        else:
            text = (
                f'Scan {self.scan_num + 1}, '
                f'Position {tuple(self.scan_pos + 1)}'
            )

        self.ui.info_label.setText(text)

    def set_icon(self, icon: QIcon):
        self.ui.setWindowIcon(icon)

    def show(self):
        """Show the window"""
        self.ui.show()

    def add_cmap_reverse_menu_action(self):
        """Add a 'reverse' action to the pyqtgraph colormap menu

        This assumes pyqtgraph won't change its internal attribute structure.
        If it does change, then this function just won't work...
        """
        w = self.image_view.getHistogramWidget()
        if not w:
            # There should be a histogram widget. Not sure why it's missing...
            return

        try:
            gradient = w.item.gradient
            menu = gradient.menu
        except AttributeError:
            # pyqtgraph must have changed its attribute structure
            return

        if not menu:
            return

        def reverse():
            cmap = gradient.colorMap()
            cmap.reverse()
            gradient.setColorMap(cmap)

        menu.addSeparator()
        action = menu.addAction('reverse')
        action.triggered.connect(reverse)
