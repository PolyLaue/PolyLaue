# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import Qt, QObject, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

import numpy as np
import pyqtgraph as pg

MouseButton = Qt.MouseButton


class PointSelector(QObject):
    """Emitted when the points have been edited"""

    points_modified = Signal()

    def __init__(self, image_view: pg.ImageView, parent: QObject = None):
        super().__init__(parent=parent)

        self.image_view = image_view
        self.scatter_artist = artist = pg.ScatterPlotItem(
            pxMode=True,
            symbol='x',
            pen=pg.mkPen('blue'),
            brush=pg.mkBrush('blue'),
            size=10,
            hoverable=True,
            tip=self._create_point_tooltip,
        )

        # These points MUST not be reordered. Keep same ordering.
        self.points = []

        image_view.addItem(artist)

        # Disable the context menu while this is active
        self._prev_menu_enabled = image_view.context_menu_enabled
        image_view.context_menu_enabled = False

        self.setup_connections()

    def setup_connections(self):
        self._mouse_click_connection = (
            self.image_view.scene.sigMouseClicked.connect(self.mouse_clicked)
        )

    def disconnect(self):
        if self.scatter_artist:
            self.scatter_artist.clear()
            self.image_view.removeItem(self.scatter_artist)
            self.scatter_artist = None

        if self.image_view:
            self.image_view.context_menu_enabled = self._prev_menu_enabled
            self.image_view.scene.sigMouseClicked.disconnect(
                self._mouse_click_connection
            )
            self.image_view = None

    def clear_scatter_artist(self):
        self.scatter_artist.clear()

        # This fixes a bug where points would stick around
        # after changing frames when they shouldn't be (but they would
        # disappear immediately after any interaction). I'm guessing
        # pyqtgraph should be doing this.
        self.scatter_artist.prepareGeometryChange()

    def _create_point_tooltip(self, x, y, data):
        return f'{x}, {y}'

    def mouse_clicked(self, event):
        pos = self.image_view.view.mapSceneToView(event.pos())
        pos = np.round(pos.toTuple(), 3)

        if event.button() == MouseButton.RightButton:
            # Right-click removes the nearest point
            self.remove_nearest_point(pos)
            return

        if event.button() != MouseButton.LeftButton:
            # At this point, ignore anything that is not left-click
            return

        # These points MUST not be reordered. Keep same ordering.
        self.points.append(pos)
        self.points_changed()

    def remove_nearest_point(self, point: np.ndarray):
        if not self.points:
            return

        all_points = np.asarray(self.points)
        distances = np.linalg.norm(all_points - point, axis=1)
        closest_idx = np.argmin(distances)
        self.points.pop(closest_idx)
        self.points_changed()

    def points_changed(self):
        """This function should be called whenever the points have changed"""
        self.update_scatter_plot()
        self.points_modified.emit()

    def update_scatter_plot(self):
        if not self.points:
            self.clear_scatter_artist()
            return

        self.scatter_artist.setData(*np.asarray(self.points).T)


class PointSelectorDialog(QDialog):
    def __init__(self, image_view, window_title='Select Points', parent=None):
        super().__init__(parent=parent)
        self.point_selector = PointSelector(image_view)

        self.setWindowTitle(window_title)

        layout = QVBoxLayout(self)
        self.setLayout(layout)

        label = QLabel(
            'Left-click to add points, right-click to remove points'
        )
        layout.addWidget(label)
        layout.setAlignment(label, Qt.AlignHCenter)

        combo = QComboBox()
        combo.addItems(['Indexing', 'Refinement', 'Arbitrary File'])
        combo.setToolTip(
            'The type of picks indicates where they should be saved.\n\n'
            'If "Indexing" or "Refinement" is selected, the file is '
            'saved at the root of the Project directory as '
            '"indexing.xy" or "refinement.xy", respectively.\n\n'
            'If "Arbitrary File" is selected, a file dialog will '
            'appear, allowing the user to specify a file.'
        )
        layout.addWidget(combo)
        self.save_file_combo = combo

        self.num_points_label = QLabel()
        layout.addWidget(self.num_points_label)
        self.update_num_points_label()

        # Add a button box for accept/cancel
        buttons = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        self.button_box = QDialogButtonBox(buttons, self)
        layout.addWidget(self.button_box)

        self.setup_connections()

    @property
    def filename(self) -> str | None:
        filenames = {
            'Indexing': 'indexing.xy',
            'Refinement': 'refinement.xy',
            'Arbitrary File': None,
        }
        return filenames[self.save_file_combo.currentText()]

    @property
    def indexing_selected(self) -> bool:
        return self.save_file_combo.currentText() == 'Indexing'

    @property
    def refinement_selected(self) -> bool:
        return self.save_file_combo.currentText() == 'Refinement'

    def setup_connections(self):
        self.point_selector.points_modified.connect(self.on_points_modified)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.rejected.connect(self.on_rejected)

    def on_points_modified(self):
        self.update_num_points_label()

    def update_num_points_label(self):
        num_points = len(self.points)
        self.num_points_label.setText(f'Number of points: {num_points}')

    def on_rejected(self):
        self.disconnect()

    def disconnect(self):
        self.point_selector.disconnect()

    @property
    def points(self):
        return self.point_selector.points
