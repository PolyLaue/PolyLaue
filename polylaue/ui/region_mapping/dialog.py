# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path
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
    QEvent,
    QPointF,
    QRectF,
    QSettings,
    Qt,
    QTimer,
    Signal,
)

from PySide6.QtGui import (
    QShowEvent,
)

from PySide6.QtWidgets import (
    QCheckBox,
    QMessageBox,
)

import pyqtgraph as pg

import numpy as np

from polylaue.model.io import Bounds
from polylaue.model.series import Series
from polylaue.model.roi_manager import ROIManager
from polylaue.ui.region_mapping.grid_item import CustomGridItem
from polylaue.utils.coordinates import world_to_display, ij_to_xy

Key = Qt.Key


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


class CustomViewBox(pg.ViewBox):
    sigMouseClicked = Signal(QPointF)

    def mouseClickEvent(self, ev):
        pos = self.mapSceneToView(ev.scenePos())
        self.sigMouseClicked.emit(pos)
        return super().mouseClickEvent(ev)


DEFAULT_ROI_ITEM_ARGS = {
    'scaleSnap': True,
    'translateSnap': True,
    'rotatable': False,
    'resizable': True,
    'movable': True,
    'removable': True,
}

SHOW_HIGHLIGHT_MSG = 'Show Highlight Region'
HIDE_HIGHLIGHT_MSG = 'Hide Highlight Region'
SHOW_DOMAIN_MSG = 'Show Map Shape'
HIDE_DOMAIN_MSG = 'Hide Map Shape'


class RegionMappingDialog(QDialog):
    """Emitted when the scan position should be changed"""

    change_scan_position = Signal(int, int)
    shift_scan_number = Signal(int)
    shift_scan_position = Signal(int, int)
    sigShowHighlightChanged = Signal(bool)
    sigShowDomainChanged = Signal(bool)
    sigMappingHighlightChanged = Signal(int, int, int, int)
    sigMappingDomainChanged = Signal(int, int, int, int)

    def __init__(
        self,
        id: str,
        roi_manager: ROIManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.auto_refresh = True
        self.visible = False
        self.debounced_refresh = Debouncer(self.on_refresh_clicked, 500)

        # Keep track of the current map data so we can save it as an npy file
        # if the user requests it.
        self._current_map_data = []

        self.setLayout(QVBoxLayout())

        w = pg.GraphicsView()
        view = CustomViewBox(invertY=True)
        view.setAspectLocked(True)
        w.setCentralItem(view)
        image_item = pg.ImageItem()
        view.addItem(image_item)

        grid_item = CustomGridItem()
        view.addItem(grid_item)

        view.sigMouseClicked.connect(self.on_map_click)

        self.layout().addWidget(w)

        self.resize(800, 800)

        buttons_widget = QWidget(self)
        buttons_layout = QHBoxLayout()
        buttons_widget.setLayout(buttons_layout)
        self.layout().addWidget(buttons_widget)

        self.refresh_button = QPushButton('Refresh Map', self)
        self.refresh_button.clicked.connect(self.on_refresh_clicked)

        self.save_data_button = QPushButton('Save Map Data', self)
        self.save_data_button.clicked.connect(self.on_save_data_clicked)

        self.show_highlight_button = QPushButton(SHOW_HIGHLIGHT_MSG, self)
        self.show_highlight_button.clicked.connect(self.on_highlight_clicked)

        self.show_domain_button = QPushButton(SHOW_DOMAIN_MSG, self)
        self.show_domain_button.clicked.connect(self.on_domain_clicked)

        buttons_layout.addWidget(self.show_highlight_button)
        buttons_layout.addWidget(self.show_domain_button)
        buttons_layout.addWidget(self.refresh_button)
        buttons_layout.addWidget(self.save_data_button)

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
        self.roi_size_ij = np.array([1, 1])
        self.map_size_ij = np.array([1, 1])

        self.linked_histogram_item: Optional[pg.HistogramLUTItem] = None

        self.finished.connect(self.on_close)

        self._view = view
        self._show_highlight = False
        self._show_domain = False

        self._domain_roi = {
            "position": np.array((0, 0)),
            "size": np.array((1, 1)),
        }
        self._domain_roi_item = pg.RectROI(
            (0, 0), (1, 1), **DEFAULT_ROI_ITEM_ARGS
        )
        self._domain_roi_item.pen.setColor(Qt.red)
        self._domain_roi_item.pen.setWidth(2)
        self._domain_roi_item.sigRegionChanged.connect(
            self._on_update_domain_region
        )
        self._domain_roi_item.sigRegionChangeFinished.connect(
            self._on_update_domain_region_finished
        )

        self._highlight_roi = {
            "position": np.array((0, 0)),
            "size": np.array((1, 1)),
        }
        self._highlight_roi_item = pg.RectROI(
            (0, 0), (1, 1), **DEFAULT_ROI_ITEM_ARGS
        )
        self._highlight_roi_item.pen.setColor(Qt.green)
        self._highlight_roi_item.pen.setWidth(2)
        self._highlight_roi_item.sigRegionChanged.connect(
            self._on_update_highlight_region
        )
        self._highlight_roi_item.sigRegionChangeFinished.connect(
            self._on_update_highlight_region_finished
        )

        # By default pyqtgraph ROIs have clicking disable to prevent them from stealing
        # the event from the items below them,
        # however the click event still doesn't make it through for whatever reason.
        # Workaround: explicitly enable clicking on the ROI item and then pass the event
        # to the callback we intended originally
        self._domain_roi_item.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
        )
        self._domain_roi_item.sigClicked.connect(self.on_roi_click)
        self._highlight_roi_item.setAcceptedMouseButtons(
            Qt.MouseButton.LeftButton
        )
        self._highlight_roi_item.sigClicked.connect(self.on_roi_click)

        self._update_window_title()
        self._update_highlight_btn()
        self._update_domain_btn()

    def showEvent(self, event: QShowEvent) -> None:
        self.visible = True
        self.debounced_refresh()

        return super().showEvent(event)

    def keyPressEvent(self, event: QEvent):
        """Override the key press event to navigate between scan numbers"""

        def shift_position(i, j):
            self.shift_scan_position.emit(i, j)
            event.accept()

        def shift_scan_number(i):
            self.shift_scan_number.emit(i)
            event.accept()

        match event.key():
            case Key.Key_Right:
                # Move right one column
                return shift_position(0, 1)
            case Key.Key_Left:
                # Move left one column
                return shift_position(0, -1)
            case Key.Key_Down:
                # Move down one row
                return shift_position(1, 0)
            case Key.Key_Up:
                # Move up one row
                return shift_position(-1, 0)
            case Key.Key_PageUp:
                # Move up one scan
                return shift_scan_number(1)
            case Key.Key_PageDown:
                # Move down one scan
                return shift_scan_number(-1)

        return super().keyPressEvent(event)

    def on_close(self, *_args):
        self.visible = False
        self.debounced_refresh.cancel()

    def set_series(self, series: Series):
        self.series = series
        self.set_stale(True)

    def set_scan_number(self, scan_number: int):
        self.scan_number = scan_number
        self.set_stale(True)

    def set_scan_position(self, i: int, j: int):
        self.grid_item.set_active_cell((j, i))
        self.grid_item.update()

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
        self.roi_size_ij = roi_size_ij
        self.map_size_ij = np.array(img.shape)
        roi_size_xy = ij_to_xy(roi_size_ij, 'row-major')
        map_size_xy = ij_to_xy(self.map_size_ij, 'row-major')
        n_y, n_x = self.series.scan_shape
        x_ticks = tuple(i * roi_size_xy[0] for i in range(n_x + 1))
        y_ticks = tuple(i * roi_size_xy[1] for i in range(n_y + 1))
        self.grid_item.set_x_ticks(x_ticks)
        self.grid_item.set_y_ticks(y_ticks)
        self.grid_item.set_x_limits((0, map_size_xy[0]))
        self.grid_item.set_y_limits((0, map_size_xy[1]))
        self.grid_item.update()
        self.image_item.setImage(img)
        self.on_levels_changed()
        self.on_lookup_table_changed()
        self._update_highlight_roi_item()
        self._update_domain_roi_item()
        self.set_stale(False)

    def set_show_highlight(self, show: bool):
        if self._show_highlight == show:
            return

        self._show_highlight = show

        if show:
            self._view.addItem(self._highlight_roi_item)
        else:
            self._view.removeItem(self._highlight_roi_item)

        self._update_highlight_btn()

    def set_show_domain(self, show: bool):
        if self._show_domain == show:
            return

        self._show_domain = show

        if show:
            self._view.addItem(self._domain_roi_item)
        else:
            self._view.removeItem(self._domain_roi_item)

        self._update_domain_btn()

    def on_highlight_clicked(self):
        self.set_show_highlight(not self._show_highlight)
        self.sigShowHighlightChanged.emit(self._show_highlight)

    def on_domain_clicked(self):
        self.set_show_domain(not self._show_domain)
        self.sigShowDomainChanged.emit(self._show_domain)

    def on_save_data_clicked(self):
        if not self._current_map_data:
            msg = 'No map data. Cannot save.'
            QMessageBox.critical(None, 'No Map Data', msg)
            return

        path = Path('.').resolve()
        if self.series and self.series.parent and self.series.parent.parent:
            # Use project directory if available (it should be)
            project = self.series.parent.parent
            path = project.directory

        filepath = path / 'map_data.npy'

        np.save(filepath, self._current_map_data)

        msg = f'Map data saved to: {filepath}'

        print(msg)

        settings = QSettings()
        skip_message_key = '_skip_region_mapping_save_data_message'
        skip_message = settings.value(skip_message_key, False)
        if not skip_message:
            box = QMessageBox(
                QMessageBox.Icon.Information,
                'Files saved',
                msg,
                QMessageBox.StandardButton.Ok,
            )
            cb = QCheckBox("Don't show this again")
            box.setCheckBox(cb)
            box.layout().setAlignment(cb, Qt.AlignRight)
            box.exec_()
            if cb.isChecked():
                settings.setValue(skip_message_key, True)

    def _update_highlight_roi_item(self):
        pos = self.roi_size_ij * self._highlight_roi["position"]
        size = self.roi_size_ij * self._highlight_roi["size"]
        pos_xy = ij_to_xy(pos)
        size_xy = ij_to_xy(size)

        self._highlight_roi_item.maxBounds = QRectF(
            0, 0, self.map_size_ij[1], self.map_size_ij[0]
        )
        self._highlight_roi_item.setPos(pos_xy, update=False)
        self._highlight_roi_item.setSize(size_xy, update=False)
        self._highlight_roi_item.getHandles()[0].setPos(size_xy[0], size_xy[1])
        self._highlight_roi_item.update()

    def _update_domain_roi_item(self):
        pos = self.roi_size_ij * self._domain_roi["position"]
        size = self.roi_size_ij * self._domain_roi["size"]
        pos_xy = ij_to_xy(pos)
        size_xy = ij_to_xy(size)

        self._domain_roi_item.maxBounds = QRectF(
            0, 0, self.map_size_ij[1], self.map_size_ij[0]
        )
        self._domain_roi_item.setPos(pos_xy, update=False)
        self._domain_roi_item.setSize(size_xy, update=False)
        self._domain_roi_item.getHandles()[0].setPos(size_xy[0], size_xy[1])
        self._domain_roi_item.update()

    def _update_highlight_btn(self):
        if self._show_highlight:
            msg = HIDE_HIGHLIGHT_MSG
        else:
            msg = SHOW_HIGHLIGHT_MSG

        self.show_highlight_button.setText(msg)
        self.show_highlight_button.update()

    def _update_domain_btn(self):
        if self._show_domain:
            msg = HIDE_DOMAIN_MSG
        else:
            msg = SHOW_DOMAIN_MSG

        self.show_domain_button.setText(msg)
        self.show_domain_button.update()

    def _on_update_highlight_region(self):
        pos_xy = np.array(self._highlight_roi_item.pos())
        size_xy = np.array(self._highlight_roi_item.size())

        pos = world_to_display(pos_xy)
        size = world_to_display(size_xy)

        # We can't use pyqtgraph internal snapping because it can't have different snapping
        # values for x and y.
        # So we must snap and override the posizion/size of the widget at each interaction
        snapped_pos, snapped_size, new_roi_position, new_roi_size = (
            self._snap_to_grid(pos, size, self.roi_size_ij)
        )

        snapped_pos_xy = ij_to_xy(snapped_pos)
        snapped_size_xy = ij_to_xy(snapped_size)

        self._highlight_roi_item.setPos(snapped_pos_xy, update=False)
        self._highlight_roi_item.setSize(snapped_size_xy, update=False)
        self._highlight_roi_item.update()

        new_roi = {"position": new_roi_position, "size": new_roi_size}

        if not self._rois_are_same(new_roi, self._highlight_roi):
            self.set_highlight_roi(new_roi)
            self.sigMappingHighlightChanged.emit(
                new_roi["position"][0],
                new_roi["position"][1],
                new_roi["size"][0],
                new_roi["size"][1],
            )

    def _on_update_highlight_region_finished(self):
        # Make the handles snap to the grid once we finish interacting with the widget
        item_size = self._highlight_roi_item.size()
        self._highlight_roi_item.getHandles()[0].setPos(
            item_size[0], item_size[1]
        )

    def _on_update_domain_region(self):
        pos_xy = np.array(self._domain_roi_item.pos())
        size_xy = np.array(self._domain_roi_item.size())

        pos = world_to_display(pos_xy)
        size = world_to_display(size_xy)

        # We can't use pyqtgraph internal snapping because it can't have different snapping
        # values for x and y.
        # So we must snap and override the posizion/size of the widget at each interaction
        snapped_pos, snapped_size, new_roi_position, new_roi_size = (
            self._snap_to_grid(pos, size, self.roi_size_ij)
        )

        snapped_pos_xy = ij_to_xy(snapped_pos)
        snapped_size_xy = ij_to_xy(snapped_size)

        self._domain_roi_item.setPos(snapped_pos_xy, update=False)
        self._domain_roi_item.setSize(snapped_size_xy, update=False)
        self._domain_roi_item.update()

        new_roi = {"position": new_roi_position, "size": new_roi_size}

        if not self._rois_are_same(new_roi, self._domain_roi):
            self.set_domain_roi(new_roi)
            self.sigMappingDomainChanged.emit(
                new_roi["position"][0],
                new_roi["position"][1],
                new_roi["size"][0],
                new_roi["size"][1],
            )

    def _on_update_domain_region_finished(self):
        # Make the handles snap to the grid once we finish interacting with the widget
        item_size = self._domain_roi_item.size()
        self._domain_roi_item.getHandles()[0].setPos(
            item_size[0], item_size[1]
        )

    @staticmethod
    def _snap_to_grid(pos: np.ndarray, size: np.ndarray, grid: np.ndarray):
        grid_pos = np.round(pos / grid).astype(np.int32)
        grid_size = np.round(size / grid).astype(np.int32)

        snapped_pos = grid_pos * grid
        snapped_size = grid_size * grid

        return snapped_pos, snapped_size, grid_pos, grid_size

    @staticmethod
    def _rois_are_same(roi0, roi1) -> bool:
        return np.array_equal(
            roi0["position"], roi1["position"]
        ) and np.array_equal(roi0["size"], roi1["size"])

    def set_highlight_roi(self, roi):
        if not self._rois_are_same(roi, self._highlight_roi):
            self._highlight_roi = roi
            self._update_highlight_roi_item()

    def set_domain_roi(self, roi):
        if not self._rois_are_same(roi, self._domain_roi):
            self._domain_roi = roi
            self.set_stale(True)

    def on_roi_click(self, target, ev, *args):
        pos = self._view.mapSceneToView(ev.scenePos())
        self.on_map_click(pos)

    def on_map_click(self, pos: QPointF):
        pos_ij = world_to_display(np.array((pos.x(), pos.y())))

        if (
            pos_ij[0] < 0
            or pos_ij[0] >= self.map_size_ij[0]
            or pos_ij[1] < 0
            or pos_ij[1] >= self.map_size_ij[1]
        ):
            return

        scan_pos = (
            int(pos_ij[0] // self.roi_size_ij[0]),
            int(pos_ij[1] // self.roi_size_ij[1]),
        )

        self.change_scan_position.emit(scan_pos[0], scan_pos[1])

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

        size_ij = world_to_display(size_xy) - (pos_ij - pos_ij_unclamped)
        size_ij = np.clip(size_ij, (1, 1), (w - pos_ij[0], h - pos_ij[1]))

        n_y, n_x = series.scan_shape

        map_size = (n_y * size_ij[0], n_x * size_ij[1])

        map_img = np.zeros(map_size)

        i0 = self._domain_roi["position"][0]
        i1 = i0 + self._domain_roi["size"][0]

        j0 = self._domain_roi["position"][1]
        j1 = j0 + self._domain_roi["size"][1]

        self.progress_bar.setRange(i0, i1)
        self.progress_bar.setValue(i0)

        self._current_map_data.clear()
        for i in range(i0, i1):
            self.progress_bar.setValue(i)
            map_data_row = []
            for j in range(j0, j1):
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

                region_img = self.open_image_fn(
                    series,
                    scan_number,
                    scan_position,
                    (frame_i_start, frame_i_end, frame_j_start, frame_j_end),
                )[1]

                map_data_row.append(region_img)
                map_img[i_start:i_end, j_start:j_end] = region_img

            self._current_map_data.append(map_data_row)

        self.progress_bar.setValue(i1)

        return pos_ij, size_ij, map_img
