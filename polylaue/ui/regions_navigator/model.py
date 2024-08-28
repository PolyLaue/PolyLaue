# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Any, Optional

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    QPersistentModelIndex,
    Qt,
)

from polylaue.model.roi_manager import ROIManager


ID_COL = 0
POS_X_COL = 1
POS_Y_COL = 2
SIZE_X_COL = 3
SIZE_Y_COL = 4


class RegionsNavigatorModel(QAbstractTableModel):
    def __init__(
        self, roi_manager: ROIManager, parent: Optional[QObject] = None
    ):
        super().__init__(parent)

        self.roi_manager = roi_manager

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.DisplayRole,
    ) -> Any:
        if role == Qt.DisplayRole and orientation == Qt.Orientation.Horizontal:
            col = section

            if col == ID_COL:
                return 'ID'
            elif col == POS_X_COL:
                return 'Pos X'
            elif col == POS_Y_COL:
                return 'Pos Y'
            elif col == SIZE_X_COL:
                return 'Size X'
            elif col == SIZE_Y_COL:
                return 'Size Y'
        else:
            return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if role == Qt.DisplayRole:
            id = self.roi_manager.index_to_id(index.row())
            roi = self.roi_manager.get_roi(id)

            col = index.column()

            if col == ID_COL:
                return roi['id']
            elif col == POS_X_COL:
                return roi['position'][0]
            elif col == POS_Y_COL:
                return roi['position'][1]
            elif col == SIZE_X_COL:
                return roi['size'][0]
            elif col == SIZE_Y_COL:
                return roi['size'][1]

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
            current_pos = roi['position']
            current_size = roi['size']
            new_pos = current_pos
            new_size = current_size

            if col == POS_X_COL:
                new_pos = (value, current_pos[1])
            elif col == POS_Y_COL:
                new_pos = (current_pos[0], value)
            elif col == SIZE_X_COL:
                new_size = (value, current_size[1])
            elif col == SIZE_Y_COL:
                new_size = (current_size[0], value)
            else:
                return False

            self.roi_manager.update_roi(id, new_pos, new_size)

            self.dataChanged.emit(index, index, role)

            return True

        return False

    def columnCount(self, parent: Optional[QModelIndex] = None) -> int:
        return 5

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
        else:
            return (
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemNeverHasChildren
                | Qt.ItemFlag.ItemIsEditable
            )
