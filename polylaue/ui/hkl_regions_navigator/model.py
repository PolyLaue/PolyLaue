# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Any, Optional
import numpy as np

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)

from PySide6.QtGui import (
    QBrush,
)

from polylaue.model.hkl_provider import HklProvider, InvalidHklError, HKL
from polylaue.model.roi_manager import HklROIManager
from polylaue.typing import WorldPoint


ID_COL = 0
CRYSTAL_COL = 1
H_COL = 2
K_COL = 3
L_COL = 4
SIZE_X_COL = 5
SIZE_Y_COL = 6

COL_HEADERS = {
    ID_COL: 'ID',
    CRYSTAL_COL: 'Crystal ID',
    H_COL: 'H',
    K_COL: 'K',
    L_COL: 'L',
    SIZE_X_COL: 'Size X',
    SIZE_Y_COL: 'Size Y',
}

OUT_OF_BOUNDS = -100_000


class RegionsNavigatorModel(QAbstractTableModel):
    def __init__(
        self,
        roi_manager: HklROIManager,
        hkl_provider: HklProvider,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)

        self.roi_manager = roi_manager
        self.hkl_provider = hkl_provider

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            return COL_HEADERS.get(section, "")
        else:
            return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            id = self.roi_manager.index_to_id(index.row())
            roi = self.roi_manager.get_roi(id)
            assert 'hkl' in roi and 'crystal_id' in roi

            col = index.column()

            if col == ID_COL:
                return roi['id']
            elif col == CRYSTAL_COL:
                return roi['crystal_id']
            elif col == H_COL:
                return roi['hkl'][0]
            elif col == K_COL:
                return roi['hkl'][1]
            elif col == L_COL:
                return roi['hkl'][2]
            elif col == SIZE_X_COL:
                return float(roi['size'][0])
            elif col == SIZE_Y_COL:
                return float(roi['size'][1])
        elif role == Qt.ItemDataRole.FontRole:
            return QBrush(Qt.GlobalColor.green)
        elif role == Qt.ItemDataRole.BackgroundRole:
            id = self.roi_manager.index_to_id(index.row())
            roi = self.roi_manager.get_roi(id)
            assert 'hkl' in roi and 'crystal_id' in roi

            col = index.column()

            if col in (CRYSTAL_COL, H_COL, K_COL, L_COL):
                try:
                    self.hkl_provider.get_hkl_center(
                        roi['crystal_id'], roi['hkl']
                    )
                except InvalidHklError:
                    return QBrush(Qt.GlobalColor.red)

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole):
        if role == Qt.EditRole:
            try:
                value = int(value)
            except ValueError:
                return False

            row = index.row()
            col = index.column()

            id = self.roi_manager.index_to_id(row)
            roi = self.roi_manager.get_roi(id)
            assert 'hkl' in roi and 'crystal_id' in roi
            current_size = roi['size']
            current_crystal_id = roi['crystal_id']
            current_hkl = roi['hkl']
            current_position = roi['position']
            new_size = current_size
            new_crystal_id = current_crystal_id
            new_hkl = current_hkl
            new_position = current_position

            if col == CRYSTAL_COL:
                new_crystal_id = value
            elif col == H_COL:
                new_hkl = (value, current_hkl[1], current_hkl[2])
            elif col == K_COL:
                new_hkl = (current_hkl[0], value, current_hkl[2])
            elif col == L_COL:
                new_hkl = (current_hkl[0], current_hkl[1], value)
            elif col == SIZE_X_COL:
                new_size = (value, current_size[1])
            elif col == SIZE_Y_COL:
                new_size = (current_size[0], value)
            else:
                return False

            new_size = np.array(new_size)

            try:
                center = self.hkl_provider.get_hkl_center(
                    new_crystal_id, new_hkl
                )
                new_position = center - new_size // 2
            except InvalidHklError:
                new_position = np.array([OUT_OF_BOUNDS, OUT_OF_BOUNDS])

            self.roi_manager.update_roi(
                id, new_crystal_id, new_hkl, new_position, new_size
            )

            self.dataChanged.emit(index, index, role)

            return True

        return False

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return 7

    def rowCount(self, parent: Optional[QModelIndex] = None) -> int:
        return self.roi_manager.size()

    def insertRows(
        self, row: int, count: int, parent: Optional[QModelIndex] = None
    ):
        if parent is None:
            parent = QModelIndex()

        return super().insertRows(row, count, parent)

    def flags(self, index: QModelIndex | QPersistentModelIndex) -> Qt.ItemFlag:
        col = index.column()

        if col == ID_COL:
            return (
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemNeverHasChildren
            )
        elif col in (CRYSTAL_COL, H_COL, K_COL, L_COL):
            return (
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemNeverHasChildren
                | Qt.ItemFlag.ItemIsEditable
            )
        else:
            return (
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemNeverHasChildren
                | Qt.ItemFlag.ItemIsEditable
            )

    def add_roi(
        self, crystal_id: int, hkl: HKL, position: WorldPoint, size: WorldPoint
    ) -> str:
        row_count = self.rowCount()
        self.beginInsertRows(QModelIndex(), row_count, row_count)
        id = self.roi_manager.add_roi(crystal_id, hkl, position, size)
        self.endInsertRows()

        return id

    def remove_roi(self, id: str):
        row = self.roi_manager.id_to_index(id)
        self.beginRemoveRows(QModelIndex(), row, row)
        self.roi_manager.remove_roi(id)
        self.endRemoveRows()

    def refresh_roi(
        self,
        id: str,
        crystal_id: int,
        hkl: HKL,
        position: WorldPoint,
        size: WorldPoint,
    ):
        row = self.roi_manager.id_to_index(id)
        self.roi_manager.update_roi(id, crystal_id, hkl, position, size)
        top_left = self.createIndex(row, H_COL)
        bottom_right = self.createIndex(row, SIZE_Y_COL)
        self.dataChanged.emit(top_left, bottom_right, Qt.EditRole)
