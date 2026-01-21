# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Optional

from functools import partial

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGraphicsSceneMouseEvent,
)

from PySide6.QtCore import (
    QObject,
    QEvent,
    Qt,
    Signal,
    QModelIndex,
    QItemSelection,
    QItemSelectionModel,
)

from PySide6.QtGui import (
    QPalette,
    QColor,
)

import pyqtgraph as pg

import numpy as np

from polylaue.model.roi_manager import ROIManager
from polylaue.typing import WorldPoint
from polylaue.ui.regions_navigator.model import RegionsNavigatorModel
from polylaue.ui.regions_navigator.view import RegionsNavigatorView
from polylaue.ui.utils.keep_dialog_on_top import keep_dialog_on_top

DEFAULT_ROI_ITEM_ARGS = {
    'scaleSnap': True,
    'translateSnap': True,
    'rotatable': False,
    'resizable': True,
    'movable': True,
    'removable': True,
}


class RegionItemsManager(QObject):
    sigActiveROIChanged = Signal(str)
    sigROIModified = Signal(str)

    def __init__(
        self,
        image_view: pg.ImageView,
        roi_manager: ROIManager,
        roi_model: RegionsNavigatorModel,
    ):
        super().__init__()
        self.image_view = image_view
        self.roi_manager = roi_manager
        self.roi_model = roi_model

        self.roi_model.dataChanged.connect(self.on_roi_table_update)

        self.current_roi_id: str | None = None

        self.roi_items: dict[str, pg.ROI] = {}

        for id, roi in self.roi_manager.items():
            position = roi['position']
            size = roi['size']
            self.create_roi_item(id, position, size)

        self._pressed = False

    def enable_interactive_add(self):
        self.image_view.getView().installEventFilter(self)
        for roi_item in self.roi_items.values():
            roi_item.translatable = False
            roi_item.resizable = False

    def disable_interactive_add(self):
        self.image_view.getView().removeEventFilter(self)
        for roi_item in self.roi_items.values():
            roi_item.translatable = True
            roi_item.resizable = True

    def show_items(self, show: bool):
        self.do_show = show

        for roi_item in self.roi_items.values():
            if show:
                self.image_view.getView().addItem(roi_item)
            else:
                self.image_view.getView().removeItem(roi_item)

    def on_mouse_pressed(
        self, target: pg.GraphicsScene, event: QGraphicsSceneMouseEvent
    ):
        self._pressed = True

        pos = self.image_view.getView().mapSceneToView(event.scenePos())

        position: WorldPoint = np.array((pos.x(), pos.y()), dtype=np.float32)
        np.round(position, out=position)

        initial_size: WorldPoint = np.array((1, 1), dtype=np.float32)

        id = self.roi_model.add_roi(position, initial_size)

        self.current_roi_id = id

        self.create_roi_item(id, position, initial_size)

        self.sigActiveROIChanged.emit(id)

        return True

    def on_mouse_released(
        self, target: pg.GraphicsScene, event: QGraphicsSceneMouseEvent
    ):
        self._pressed = False
        self.current_roi_id = None

        return True

    def on_mouse_moved(self, target: pg.GraphicsScene, event: QGraphicsSceneMouseEvent):
        if not self._pressed or self.current_roi_id is None:
            return False

        roi_item = self.roi_items[self.current_roi_id]
        p0 = roi_item.pos()
        p1 = self.image_view.getView().mapSceneToView(event.scenePos())
        size = (round(max(0, p1.x() - p0.x())), round(max(0, p1.y() - p0.y())))

        roi_item.setSize(size)

        return True

    def create_roi_item(self, id, position, size):
        roi_item = pg.RectROI(position, size, **DEFAULT_ROI_ITEM_ARGS)
        roi_item.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        roi_item.sigRegionChanged.connect(partial(self.on_roi_update, id))
        roi_item.sigClicked.connect(partial(self.on_roi_click, id))
        self.roi_items[id] = roi_item
        self.image_view.getView().addItem(roi_item)

    def remove_roi_item(self, id) -> bool:
        if id in self.roi_items:
            roi_item = self.roi_items[id]
            self.image_view.getView().removeItem(roi_item)
            del self.roi_items[id]

            return True

        return False

    def on_roi_update(self, id: str, roi_item: pg.ROI):
        pos: WorldPoint = np.empty(2, dtype=np.float32)
        np.round(roi_item.pos(), out=pos)

        size: WorldPoint = np.empty(2, dtype=np.float32)
        np.round(roi_item.size(), out=size)

        roi = self.roi_manager.get_roi(id)

        if np.array_equal(pos, roi['position']) and np.array_equal(size, roi['size']):
            return

        self.roi_model.refresh_roi(id, pos, size)

        self.sigActiveROIChanged.emit(id)
        self.sigROIModified.emit(id)

    def on_roi_table_update(self, index: QModelIndex):
        row = index.row()
        id = self.roi_manager.index_to_id(row)
        roi = self.roi_manager.get_roi(id)
        roi_item = self.roi_items[id]

        if np.array_equal(roi_item.pos(), roi['position']) and np.array_equal(
            roi_item.size(), roi['size']
        ):
            return

        roi_item.setPos(roi['position'])
        roi_item.setSize(roi['size'])

    def on_roi_click(self, id: str, roi: pg.ROI, *args):
        self.sigActiveROIChanged.emit(id)

    def eventFilter(self, target: QObject, event: QEvent):
        if (
            event.type() == QGraphicsSceneMouseEvent.GraphicsSceneMousePress
            and event.button() == Qt.MouseButton.LeftButton
        ):
            return self.on_mouse_pressed(target, event)

        if event.type() == QGraphicsSceneMouseEvent.GraphicsSceneMouseMove:
            return self.on_mouse_moved(target, event)

        if (
            event.type() == QGraphicsSceneMouseEvent.GraphicsSceneMouseRelease
            and event.button() == Qt.MouseButton.LeftButton
        ):
            return self.on_mouse_released(target, event)

        return False


START_INTERACTIVE_MSG = 'Start Interactive Add'
STOP_INTERACTIVE_MSG = 'Stop Interactive Add'
SHOW_MSG = 'Show Regions'
HIDE_MSG = 'Hide Regions'
REMOVE_MSG = 'Remove Region'
DISPLAY_MSG = 'Display Region'


class RegionsNavigatorDialog(QDialog):
    sigDisplayRoiClicked = Signal(str)
    sigRemoveRoiClicked = Signal(str)
    sigRoiModified = Signal(str)

    def __init__(
        self,
        image_view: pg.ImageView,
        roi_manager: ROIManager,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        keep_dialog_on_top(self)

        self.setWindowTitle('Mapping Regions')

        self.add_status = False
        self.show_status = True

        self.selected_roi_id: Optional[str] = None

        self.roi_manager = roi_manager
        self.model = RegionsNavigatorModel(roi_manager, self)
        self.view = RegionsNavigatorView(self)
        self.view.setModel(self.model)

        self.roi_items_manager = RegionItemsManager(image_view, roi_manager, self.model)
        self.roi_items_manager.show_items(True)

        self.setLayout(QVBoxLayout())

        self.layout.addWidget(self.view)

        add_remove_buttons_widget = QWidget(self)
        add_remove_layout = QHBoxLayout()
        add_remove_buttons_widget.setLayout(add_remove_layout)
        self.layout.addWidget(add_remove_buttons_widget)

        self.add_button = QPushButton(START_INTERACTIVE_MSG, self)
        self.show_button = QPushButton(HIDE_MSG, self)
        self.remove_button = QPushButton(REMOVE_MSG, self)
        self.display_button = QPushButton(DISPLAY_MSG, self)
        self.remove_button.setEnabled(False)
        self.display_button.setEnabled(False)
        add_remove_layout.addWidget(self.add_button)
        add_remove_layout.addWidget(self.show_button)
        add_remove_layout.addWidget(self.remove_button)
        add_remove_layout.addWidget(self.display_button)

        self.resize(600, 300)

        self.update_add_button()

        self.setup_connections()

    def setup_connections(self):
        self.finished.connect(self.on_close)
        self.add_button.clicked.connect(self.on_add_clicked)
        self.show_button.clicked.connect(self.on_show_clicked)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        self.display_button.clicked.connect(self.on_display_clicked)
        self.roi_items_manager.sigActiveROIChanged.connect(self.on_active_roi_changed)
        self.roi_items_manager.sigROIModified.connect(self.sigRoiModified)
        self.view.selectionModel().selectionChanged.connect(self.on_selection_changed)

    def on_close(self, *_args):
        # Disable interactive add when the dialog is closed
        self.add_status = True
        self.on_add_clicked()

    def update_add_button(self):
        if self.add_status:
            msg = STOP_INTERACTIVE_MSG
            color = Qt.red
        else:
            msg = START_INTERACTIVE_MSG
            color = Qt.green

        pal = self.add_button.palette()
        pal.setColor(QPalette.Button, QColor(color))
        self.add_button.setAutoFillBackground(True)
        self.add_button.setPalette(pal)
        self.add_button.setText(msg)
        self.add_button.update()

    def on_add_clicked(self):
        self.add_status = not self.add_status

        self.update_add_button()

        if self.add_status:
            self.roi_items_manager.enable_interactive_add()
        else:
            self.roi_items_manager.disable_interactive_add()

    def on_show_clicked(self):
        self.show_status = not self.show_status

        if self.show_status:
            self.show_button.setText(HIDE_MSG)
        else:
            self.show_button.setText(SHOW_MSG)

        self.roi_items_manager.show_items(self.show_status)

    def on_remove_clicked(self):
        if self.selected_roi_id is None:
            return

        id = self.selected_roi_id
        self.remove_roi(id)

    def remove_roi(self, id: str):
        self.model.remove_roi(id)
        self.roi_items_manager.remove_roi_item(id)
        self.view.selectionModel().clear()

        self.sigRemoveRoiClicked.emit(id)

    def remove_all_rois(self):
        for id in list(self.model.roi_manager.rois):
            self.remove_roi(id)

    def on_display_clicked(self):
        if self.selected_roi_id is None:
            return

        id = self.selected_roi_id
        self.sigDisplayRoiClicked.emit(id)

    def on_active_roi_changed(self, id: str):
        row = self.roi_manager.id_to_index(id)

        index = self.model.createIndex(row, 0)
        flags = (
            QItemSelectionModel.SelectionFlag.Clear
            | QItemSelectionModel.SelectionFlag.Select
            | QItemSelectionModel.SelectionFlag.Rows
        )
        self.view.selectionModel().select(index, flags)

    def on_selection_changed(self, current: QItemSelection, previous: QItemSelection):
        # Reset color of previously selected roi, if any
        roi_item = self.roi_items_manager.roi_items.get(self.selected_roi_id)
        if roi_item is not None:
            roi_item.pen.setColor(Qt.white)
            roi_item.update()

        if current.count() > 0:
            index = current.indexes()[0]
            self.selected_roi_id = self.roi_manager.index_to_id(index.row())
            roi_item = self.roi_items_manager.roi_items.get(self.selected_roi_id)
            self.remove_button.setEnabled(True)
            self.display_button.setEnabled(True)

            if roi_item is not None:
                roi_item.pen.setColor(Qt.green)
                roi_item.update()

            self.view.scrollTo(index)
        else:
            self.selected_roi_id = None
            self.remove_button.setEnabled(False)
            self.display_button.setEnabled(False)

    @property
    def layout(self):
        return super().layout()
