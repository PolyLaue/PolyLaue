# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Optional

from functools import partial

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from PySide6.QtCore import (
    QObject,
    Qt,
    Signal,
    QModelIndex,
    QItemSelection,
    QItemSelectionModel,
)

import pyqtgraph as pg

import numpy as np

from polylaue.model.hkl_provider import HklProvider, InvalidHklError
from polylaue.model.roi_manager import HklROIManager
from polylaue.typing import WorldPoint
from polylaue.ui.hkl_regions_navigator.model import (
    RegionsNavigatorModel,
    OUT_OF_BOUNDS,
)
from polylaue.ui.hkl_regions_navigator.view import RegionsNavigatorView
from polylaue.ui.utils.keep_dialog_on_top import keep_dialog_on_top


DEFAULT_ROI_ITEM_ARGS = {
    'scaleSnap': True,
    'translateSnap': True,
    'rotatable': False,
    'resizable': True,
    'movable': False,
    'removable': True,
}


class RegionItemsManager(QObject):
    sigActiveROIChanged = Signal(str)
    sigROIModified = Signal(str)

    def __init__(
        self,
        image_view: pg.ImageView,
        roi_manager: HklROIManager,
        roi_model: RegionsNavigatorModel,
        hkl_provider: HklProvider,
    ):
        super().__init__()
        self.image_view = image_view
        self.roi_manager = roi_manager
        self.roi_model = roi_model
        self.hkl_provider = hkl_provider

        self.roi_model.dataChanged.connect(self.on_roi_table_update)

        self.current_roi_id: str | None = None

        self.roi_items: dict[str, pg.ROI] = {}

        for id, roi in self.roi_manager.items():
            position = roi['position']
            size = roi['size']
            self.create_roi_item(id, position, size)

        self.do_show = True

    def show_items(self, show: bool):
        self.do_show = show

        for id in self.roi_items.keys():
            self._show_item(id, show)

    def _show_item(self, id: str, show: bool):
        roi_item = self.roi_items.get(id)

        if roi_item is None:
            return

        roi = self.roi_manager.get_roi(id)

        assert 'hkl' in roi and 'crystal_id' in roi
        hkl = roi['hkl']
        crystal_id = roi['crystal_id']

        actually_show = show

        if show:
            try:
                self.hkl_provider.get_hkl_center(crystal_id, hkl)
            except InvalidHklError:
                actually_show = False

        view = self.image_view.getView()

        if actually_show:
            view.addItem(roi_item)
        elif roi_item.scene() is self.image_view.scene:
            view.removeItem(roi_item)

    def create_roi_item(self, id, position, size):
        roi_item = pg.RectROI(position, size, **DEFAULT_ROI_ITEM_ARGS)
        roi_item.setAcceptedMouseButtons(Qt.MouseButton.LeftButton)
        roi_item.sigRegionChanged.connect(partial(self.on_roi_update, id))
        roi_item.sigClicked.connect(partial(self.on_roi_click, id))
        self.roi_items[id] = roi_item
        self._show_item(id, self.do_show)

    def remove_roi_item(self, id) -> bool:
        if id in self.roi_items:
            roi_item = self.roi_items[id]
            self.image_view.getView().removeItem(roi_item)
            del self.roi_items[id]

            return True

        return False

    def on_roi_update(self, id: str, roi_item: pg.ROI):
        item_pos: WorldPoint = np.empty(2, dtype=np.float32)
        np.round(roi_item.pos(), out=item_pos)

        item_size: WorldPoint = np.empty(2, dtype=np.float32)
        np.round(roi_item.size(), out=item_size)

        roi = self.roi_manager.get_roi(id)

        assert 'hkl' in roi and 'crystal_id' in roi
        hkl = roi['hkl']
        crystal_id = roi['crystal_id']

        try:
            center = self.hkl_provider.get_hkl_center(crystal_id, hkl)
        except InvalidHklError:
            return

        size = roi['size']

        size_diff = item_size - size
        new_size = size + 2 * size_diff
        new_position = center - new_size // 2

        # if np.array_equal(item_size, size):
        if np.array_equal(item_pos, new_position) and np.array_equal(
            item_size, new_size
        ):
            return

        self.roi_model.refresh_roi(id, crystal_id, hkl, new_position, new_size)

        self.sigActiveROIChanged.emit(id)
        self.sigROIModified.emit(id)

    def on_roi_table_update(self, index: QModelIndex):
        row = index.row()
        id = self.roi_manager.index_to_id(row)
        self._update_item(id)
        self._show_item(id, self.do_show)

    def _update_item(self, id: str):
        roi = self.roi_manager.get_roi(id)
        roi_item = self.roi_items[id]

        assert 'hkl' in roi and 'crystal_id' in roi
        hkl = roi['hkl']
        crystal_id = roi['crystal_id']

        try:
            center = self.hkl_provider.get_hkl_center(crystal_id, hkl)
        except InvalidHklError:
            center = np.array([OUT_OF_BOUNDS, OUT_OF_BOUNDS])

        size = roi['size']
        position = center - size // 2

        if np.array_equal(roi_item.pos(), position) and np.array_equal(
            roi_item.size(), size
        ):
            return

        roi_item.setSize(size, update=False)
        roi_item.setPos(position, update=False)
        roi_item.stateChanged()

        self.sigROIModified.emit(id)

    def on_roi_click(self, id: str, roi: pg.ROI, *args):
        self.sigActiveROIChanged.emit(id)

    def on_hkls_changed(self):
        for id in self.roi_items.keys():
            roi = self.roi_manager.get_roi(id)

            assert 'hkl' in roi and 'crystal_id' in roi
            hkl = roi['hkl']
            crystal_id = roi['crystal_id']

            try:
                center = self.hkl_provider.get_hkl_center(crystal_id, hkl)
            except InvalidHklError:
                continue

            size = roi['size']
            position = center - size // 2
            self.roi_model.refresh_roi(id, crystal_id, hkl, position, size)

        # Update visibility of the items
        self.show_items(self.do_show)


ADD_MSG = 'Add Region'
SHOW_MSG = 'Show Regions'
HIDE_MSG = 'Hide Regions'
REMOVE_MSG = 'Remove Region'
DISPLAY_MSG = 'Display Region'


class HklRegionsNavigatorDialog(QDialog):
    sigDisplayRoiClicked = Signal(str)
    sigRemoveRoiClicked = Signal(str)
    sigRoiModified = Signal(str)

    def __init__(
        self,
        image_view: pg.ImageView,
        roi_manager: HklROIManager,
        hkl_provider: HklProvider,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)
        keep_dialog_on_top(self)

        self.setWindowTitle('HKL Mapping Regions')

        self.add_status = False
        self.show_status = True

        self.selected_roi_id: Optional[str] = None

        self.roi_manager = roi_manager
        self.hkl_provider = hkl_provider
        self.model = RegionsNavigatorModel(roi_manager, hkl_provider, self)
        self.view = RegionsNavigatorView(self)
        self.view.setModel(self.model)

        self.roi_items_manager = RegionItemsManager(
            image_view, roi_manager, self.model, self.hkl_provider
        )
        self.roi_items_manager.show_items(self.show_status)

        self.setLayout(QVBoxLayout())

        self.layout.addWidget(self.view)

        add_remove_buttons_widget = QWidget(self)
        add_remove_layout = QHBoxLayout()
        add_remove_buttons_widget.setLayout(add_remove_layout)
        self.layout.addWidget(add_remove_buttons_widget)

        self.add_button = QPushButton(ADD_MSG, self)
        self.show_button = QPushButton(HIDE_MSG, self)
        self.remove_button = QPushButton(REMOVE_MSG, self)
        self.display_button = QPushButton(DISPLAY_MSG, self)
        self.remove_button.setEnabled(False)
        self.display_button.setEnabled(False)
        add_remove_layout.addWidget(self.add_button)
        add_remove_layout.addWidget(self.show_button)
        add_remove_layout.addWidget(self.remove_button)
        add_remove_layout.addWidget(self.display_button)

        self.resize(800, 300)

        self.setup_connections()

    def setup_connections(self):
        self.finished.connect(self.on_close)
        self.add_button.clicked.connect(self.on_add_clicked)
        self.show_button.clicked.connect(self.on_show_clicked)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        self.display_button.clicked.connect(self.on_display_clicked)
        self.roi_items_manager.sigActiveROIChanged.connect(
            self.on_active_roi_changed
        )
        self.roi_items_manager.sigROIModified.connect(self.sigRoiModified)
        self.view.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )

    def on_close(self, *_args):
        pass

    def on_add_clicked(self):
        hkl = (0, 0, 0)
        crystal_id = 0

        center = np.array((OUT_OF_BOUNDS, OUT_OF_BOUNDS), dtype=np.float32)

        size = np.array([150, 150])
        position = center - size // 2
        id = self.model.add_roi(crystal_id, hkl, position, size)

        self.roi_items_manager.create_roi_item(id, position, size)

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

    def on_selection_changed(
        self, current: QItemSelection, previous: QItemSelection
    ):
        # Reset color of previously selected roi, if any
        roi_item = self.roi_items_manager.roi_items.get(self.selected_roi_id)
        if roi_item is not None:
            roi_item.pen.setColor(Qt.white)
            roi_item.update()

        if current.count() > 0:
            index = current.indexes()[0]
            self.selected_roi_id = self.roi_manager.index_to_id(index.row())
            roi_item = self.roi_items_manager.roi_items.get(
                self.selected_roi_id
            )
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
