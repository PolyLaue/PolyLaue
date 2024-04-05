from typing import TYPE_CHECKING

from PySide6.QtWidgets import QFileDialog

from pyqtgraph import ImageView

from polylaue.ui.utils.ui_loader import UiLoader
from polylaue.model.io import load_image_file
from polylaue.typing import PathLike


if TYPE_CHECKING:
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QWidget


class MainWindow:
    def __init__(self, parent: 'QWidget | None' = None):
        self.ui = UiLoader().load_file('main_window.ui', parent)

        # Keep track of the working directory
        self.working_dir = None

        # Add the pyqtgraph view to the central widget
        self.image_view = ImageView(self.ui, 'CentralView')
        self.ui.central_widget.layout().addWidget(self.image_view)

        self.setup_connections()

    def setup_connections(self):
        self.ui.action_open_file.triggered.connect(self.on_open_file)

    def on_open_file(self):
        selected_file, selected_filter = QFileDialog.getOpenFileName(
            self.ui, 'Open Image File', self.working_dir, 'TIFF files (*.tif)'
        )

        if not selected_file:
            # User canceled
            return

        self.load_image_file(selected_file)

    def load_image_file(self, filepath: PathLike):
        img = load_image_file(filepath)
        self.image_view.setImage(img)

    def set_icon(self, icon: 'QIcon'):
        self.ui.setWindowIcon(icon)

    def show(self):
        """Show the window"""
        self.ui.show()
