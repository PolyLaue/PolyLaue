from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog

import numpy as np

from polylaue.ui.image_view import PolyLaueImageView
from polylaue.ui.utils.ui_loader import UiLoader
from polylaue.model.io import load_image_file
from polylaue.model.series import Series
from polylaue.typing import PathLike


if TYPE_CHECKING:
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QWidget

    from pyqtgraph import GraphicsScene, ImageItem


class MainWindow:
    def __init__(self, parent: 'QWidget | None' = None):
        self.ui = UiLoader().load_file('main_window.ui', parent)

        # Keep track of the working directory
        self.working_dir = None
        self.series = None
        self._last_mouse_position = None

        self.reset_scan_position()

        # Add the pyqtgraph view to its layout
        self.image_view = PolyLaueImageView(self.ui, 'CentralView')
        self.ui.image_view_layout.addWidget(self.image_view)

        self.setup_connections()

    def setup_connections(self):
        self.ui.action_open_series.triggered.connect(self.on_open_series)

        self.image_view.shift_scan_position.connect(
            self.on_shift_scan_position
        )
        self.scene.sigMouseMoved.connect(self.on_mouse_move)

    @property
    def image_item(self) -> 'ImageItem':
        return self.image_view.getImageItem()

    @property
    def scene(self) -> 'GraphicsScene':
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
        self.series = Series(
            selected_directory,
            # Hard-coded for now...
            num_scans=3,
            scan_shape=(21, 21),
            num_background_frames=10,
        )

        # Reset scan position
        self.reset_scan_position()
        self.load_current_image()
        self.reset_image_view_settings()
        self.update_info_label()

    def reset_image_view_settings(self):
        self.image_view.autoLevels()
        self.image_view.autoRange()

    def on_shift_scan_position(self, i: int, j: int):
        """Shift the scan position by `i` rows and `j` columns"""
        self.scan_pos += (i, j)

        # Clip it so we don't go out of bounds
        np.clip(
            self.scan_pos,
            a_min=[0, 0],
            a_max=np.asarray(self.series.scan_shape) - 1,
            out=self.scan_pos,
        )

        self.load_current_image()
        self.update_info_label()

        if self._last_mouse_position:
            # Update the mouse hover info with the new frame
            self.on_mouse_move(self._last_mouse_position)

    def load_current_image(self):
        filepath = self.series.filepath(*self.scan_pos, self.scan_num)
        img = load_image_file(filepath)
        self.image_view.setImage(img, autoRange=False, autoLevels=False)

    def on_mouse_move(self, pos: 'QPointF'):
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

        intensity = self.image_data[i, j]
        self.ui.status_bar.showMessage(f'{i=}, {j=}, {intensity=}')

    def update_info_label(self):
        if self.series is None:
            text = ''
        else:
            text = (
                f'Scan Number: {self.scan_num + 1}, '
                f'Position: {tuple(self.scan_pos + 1)}'
            )

        self.ui.info_label.setText(text)

    def set_icon(self, icon: 'QIcon'):
        self.ui.setWindowIcon(icon)

    def show(self):
        """Show the window"""
        self.ui.show()
