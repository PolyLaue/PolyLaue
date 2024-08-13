# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from abc import ABC, abstractmethod

from PySide6.QtCore import QModelIndex, Qt

from polylaue.model.serializable import Serializable


# Enum shortcuts
ItemFlags = Qt.ItemFlags


class BaseSubmodel(ABC):
    @property
    @abstractmethod
    def type(self) -> str:
        pass

    @property
    @abstractmethod
    def entry_list(self) -> list[object]:
        pass

    @abstractmethod
    def create(self) -> Serializable:
        # Create a new instance of the managed type
        pass

    @property
    @abstractmethod
    def columns(self) -> dict[str, str]:
        # The "columns" dict is a map of object attributes to labels
        pass

    @property
    def uneditable_column_keys(self) -> list[str]:
        # Keys of columns that are not editable
        return []

    @property
    def custom_edit_column_keys(self) -> dict[str, str]:
        # A set of column keys which have custom edit functions.
        # The value is the name of the custom edit function.
        return {}

    @property
    def default_flags(self):
        x = ItemFlags
        return x.ItemIsSelectable | x.ItemIsEditable | x.ItemIsEnabled

    def column_editable(self, column: int) -> bool:
        # Assume all columns are editable by default
        return self.column_to_key(column) not in self.uneditable_column_keys

    @property
    def headers(self) -> list[str]:
        return list(self.columns.values())

    @property
    def num_columns(self) -> int:
        return len(self.columns)

    @property
    def num_rows(self) -> int:
        return len(self.entry_list)

    def flags(self, index: QModelIndex):
        flags = self.default_flags
        if not self.column_editable(index.column()):
            flags &= ~ItemFlags.ItemIsEditable

        return flags

    def set_data(self, index: QModelIndex, value: object, role: int):
        # Convert column integer
        key = self.column_to_key(index.column())
        obj = self.entry_list[index.row()]
        setattr(obj, key, value)

    def data(self, index: QModelIndex, role: int):
        if role not in (Qt.DisplayRole, Qt.EditRole):
            # Don't show anything other than for displaying or editing.
            # This prevents unwanted checkboxes from showing up, for instance.
            return None

        row = index.row()
        column = index.column()
        if role == Qt.EditRole:
            # Make sure this column is editable
            if not self.column_editable(column):
                return None

        obj = self.entry_list[row]
        key = self.column_to_key(column)
        return getattr(obj, key)

    def column_to_key(self, column: int) -> str:
        keys = list(self.columns)
        return keys[column]

    def insert_entries(self, row: int, count: int = 1):
        while count > 0:
            # Create a new instance with default values
            instance = self.create()

            # Add this instance to the entry list
            self.entry_list.insert(row, instance)
            row += 1
            count -= 1

    def delete_entries(self, row: int, count: int = 1):
        while count > 0:
            self.entry_list.pop(row)
            count -= 1
