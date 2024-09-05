# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Optional, Any, Callable

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

from PySide6.QtCore import (
    QTimer,
)

from PySide6.QtGui import (
    QShowEvent,
)

import pyqtgraph as pg

import numpy as np

from polylaue.model.io import Bounds
from polylaue.model.series import Series
from polylaue.model.roi_manager import ROIManager
from polylaue.ui.region_mapping.grid_item import CustomGridItem
from polylaue.utils.coordinates import world_to_display, ij_to_xy


class Debouncer:
    def __init__(self, callable: Callable, msec: int):
        self.msec = msec
        self.callable = callable
        self.args = []
        self.kwargs = {}
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self._invoke)

    def cancel(self):
        self.timer.stop()
        self.args = []
        self.kwargs = {}

    def __call__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.timer.start(self.msec)

    def _invoke(self):
        self.callable(*self.args, **self.kwargs)
        self.args = []
        self.kwargs = {}


class RegionMappingDialog(QDialog):
    def __init__(
        self,
        id: str,
        roi_manager: ROIManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.auto_refresh = True
        self.visible = False
        self.debounced_refresh = Debouncer(self.on_refresh_clicked, 250)

        self.setLayout(QVBoxLayout())

        w = pg.GraphicsView()
        view = pg.ViewBox(invertY=True)
        view.setAspectLocked(True)
        w.setCentralItem(view)
        image_item = pg.ImageItem()
        view.addItem(image_item)

        grid_item = CustomGridItem()
        view.addItem(grid_item)

        self.layout().addWidget(w)

        self.resize(800, 800)

        buttons_widget = QWidget(self)
        buttons_layout = QHBoxLayout()
        buttons_widget.setLayout(buttons_layout)
        self.layout().addWidget(buttons_widget)

        self.refresh_button = QPushButton('Refresh Map', self)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)

        buttons_layout.addWidget(self.refresh_button)

        self.progress_bar = QProgressBar()
        self.layout().addWidget(self.progress_bar)

        self.image_item = image_item
        self.grid_item = grid_item

        self.open_image_fn: Optional[
            Callable[
                [Series, int, np.ndarray, Optional[Bounds]],
                tuple[Any, np.ndarray],
            ]
        ] = None
        self.roi_manager = roi_manager
        self.series = None
        self.scan_number = -1
        self.roi_id = id
        self.stale = True

        self.linked_histogram_item: Optional[pg.HistogramLUTItem] = None

        self.finished.connect(self.on_close)

        self._update_window_title()

    def showEvent(self, event: QShowEvent) -> None:
        self.visible = True
        self.debounced_refresh()

        return super().showEvent(event)

    def on_close(self, *_args):
        self.visible = False
        self.debounced_refresh.cancel()

    def set_series(self, series: Series):
        self.series = series
        self.set_stale(True)

    def set_scan_number(self, scan_number: int):
        self.scan_number = scan_number
        self.set_stale(True)

    def link_levels_and_lookuptable(self, histogramItem: pg.HistogramLUTItem):
        if self.linked_histogram_item:
            self.linked_histogram_item.sigLevelsChanged.disconnect(
                self.on_levels_changed
            )
            self.linked_histogram_item.sigLookupTableChanged.disconnect(
                self.on_lookup_table_changed
            )

        self.linked_histogram_item = histogramItem

        if self.linked_histogram_item:
            self.linked_histogram_item.sigLevelsChanged.connect(
                self.on_levels_changed
            )
            self.linked_histogram_item.sigLookupTableChanged.connect(
                self.on_lookup_table_changed
            )

    def set_stale(self, stale: bool):
        self.stale = stale
        self.refresh_button.setEnabled(self.stale)
        self._update_window_title()

        if self.visible and self.auto_refresh:
            self.debounced_refresh()

    def on_levels_changed(self, *args):
        if self.linked_histogram_item:
            self.image_item.setLevels(self.linked_histogram_item.getLevels())

    def on_lookup_table_changed(self, *args):
        if self.linked_histogram_item:
            if self.linked_histogram_item.gradient.isLookupTrivial():
                self.image_item.setLookupTable(None)
            else:
                self.image_item.setLookupTable(
                    self.linked_histogram_item.getLookupTable
                )

    def on_refresh_clicked(self):
        if not self.stale:
            return

        if self.open_image_fn is None:
            return

        if self.series is None:
            return

        if self.scan_number < 0:
            return

        _, roi_size_ij, img = self._create_map_image(
            self.roi_id, self.series, self.scan_number
        )
        roi_size_xy = ij_to_xy(roi_size_ij, 'row-major')
        map_size_xy = ij_to_xy(img.shape, 'row-major')
        n_x, n_y = self.series.scan_shape
        x_ticks = tuple(i * roi_size_xy[0] for i in range(n_x + 1))
        y_ticks = tuple(i * roi_size_xy[1] for i in range(n_y + 1))
        self.grid_item.set_x_ticks(x_ticks)
        self.grid_item.set_y_ticks(y_ticks)
        self.grid_item.set_x_limits((0, map_size_xy[0]))
        self.grid_item.set_y_limits((0, map_size_xy[1]))
        self.image_item.setImage(img)
        self.on_levels_changed()
        self.on_lookup_table_changed()
        self.set_stale(False)

    def _update_window_title(self):
        if self.stale:
            self.setWindowTitle(f'Mapping for Region {self.roi_id} [STALE]')
        else:
            self.setWindowTitle(f'Mapping for Region {self.roi_id}')

    def _create_map_image(self, roi_id: str, series: Series, scan_number: int):
        # NOTE: The image is row-major,
        # flip the cartesian coordinates coming from the roi
        roi = self.roi_manager.get_roi(roi_id)

        scan_position = np.array([0, 0])
        # open first image to figure out width and height
        _, img = self.open_image_fn(series, scan_number, scan_position, None)

        w, h = img.shape

        pos_xy = roi['position']
        size_xy = roi['size']

        pos_ij_unclamped = world_to_display(pos_xy)
        pos_ij = np.clip(pos_ij_unclamped, (0, 0), (w - 1, h - 1))

        size_ij = world_to_display(size_xy)
        size_ij = np.clip(size_ij, (0, 0), (w - pos_ij[0], h - pos_ij[1]))

        n_x, n_y = series.scan_shape

        self.progress_bar.setRange(0, n_x)
        self.progress_bar.setValue(0)

        map_size = (n_y * size_ij[0], n_x * size_ij[1])

        map_img = np.zeros(map_size)

        for i in range(n_x):
            self.progress_bar.setValue(i)
            for j in range(n_y):
                scan_position[0] = i
                scan_position[1] = j

                i_start = i * size_ij[0]
                i_end = i_start + size_ij[0]
                j_start = j * size_ij[1]
                j_end = j_start + size_ij[1]

                frame_i_start = pos_ij[0]
                frame_i_end = frame_i_start + size_ij[0]
                frame_j_start = pos_ij[1]
                frame_j_end = frame_j_start + size_ij[1]

                _, map_img[i_start:i_end, j_start:j_end] = self.open_image_fn(
                    series,
                    scan_number,
                    scan_position,
                    (frame_i_start, frame_i_end, frame_j_start, frame_j_end),
                )

        self.progress_bar.setValue(n_x)

        return pos_ij, size_ij, map_img
