# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Any

from PySide6.QtCore import (
    QAbstractTableModel,
    QModelIndex,
    QObject,
    Qt,
    Signal,
)

from polylaue.model.project_manager import ProjectManager
from polylaue.ui.project_navigator.submodels import (
    BaseSubmodel,
    ProjectsSubmodel,
    ScansSubmodel,
    SectionsSubmodel,
    SeriesSubmodel,
)


class ProjectNavigatorModel(QAbstractTableModel):
    """Model for navigating through tiers in a project.

    The current tiers are (from most broad to most specific):

    1. Project Manager
    2. Project
    3. Section
    4. Series
    5. Scan

    The ProjectNavigatorModel shares some characteristics of a file system
    model, but also contains some differences. Notably, each tier has a
    different set of columns that need to be shown (whereas for a filesystem
    model, each tier typically has the same set of columns that need to be
    shown, such as "Name", "Size", and "Modified").

    Having a different set of columns per tier seems to be somewhat complicated
    in Qt, so this ProjectNavigatorModel has a concept of the "current path",
    and, depending on what the current path is, it returns a different set of
    data, different columns, different headers, etc. When the "current path"
    changes, the whole model is reset, and the view has to load everything
    from the current path. We refer to the current tier as a "submodel."

    It is intended that we will only view one tier at a time (at the
    "current path"), so that we can change all the columns depending on the
    tier, and thus a table view is probably the best way to view this.
    """

    """Emitted when setData() is finished

    This happens, for instance, when a user edits an entry.
    """
    data_modified = Signal()

    def __init__(
        self, project_manager: ProjectManager, parent: QObject = None
    ):
        super().__init__(parent)
        self.project_manager = project_manager
        self.path = []
        self.root_submodel = ProjectsSubmodel(project_manager)
        self.submodels = []
        self.update_submodels()

    def set_path(self, new_path: list[int]):
        self.path = new_path
        self.update_submodels()

    @property
    def path_names(self) -> list[str]:
        # Get a list of the current path names.
        # Note that the path names may not be unique.
        names = []

        for idx, submodel in zip(self.path, self.submodels[:-1]):
            names.append(submodel.entry_list[idx].name)

        return names

    def update_submodels(self):
        self.beginResetModel()

        submodel = self.root_submodel
        self.submodels = [submodel]
        for i, idx in enumerate(self.path):
            next_class = SUBMODELS[i + 1]
            submodel = next_class(submodel.entry_list[idx])
            self.submodels.append(submodel)

        self.endResetModel()

    @property
    def submodel(self) -> BaseSubmodel:
        """Return the last (i.e., active) submodel in the list of submodels"""
        return self.submodels[-1]

    @property
    def headers(self) -> list[str]:
        return self.submodel.headers

    def flags(self, index: QModelIndex) -> int:
        return self.submodel.flags(index)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        return self.submodel.data(index, role)

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole):
        self.submodel.set_data(index, value, role)
        self.data_modified.emit()
        return True

    def headerData(
        self, section: int, orientation: int, role: int = Qt.DisplayRole
    ):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.headers[section]

        return super().headerData(section, orientation, role)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return self.submodel.num_columns

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return self.submodel.num_rows

    def insertRows(
        self, row: int, count: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        self.beginInsertRows(parent, row, row + count - 1)
        self.submodel.insert_entries(row, count)
        self.endInsertRows()
        self.data_modified.emit()
        return True

    def removeRows(
        self, row: int, count: int, parent: QModelIndex = QModelIndex()
    ) -> bool:
        self.beginRemoveRows(parent, row, row + count - 1)
        self.submodel.delete_entries(row, count)
        self.endRemoveRows()
        self.data_modified.emit()
        return True


SUBMODELS = [
    ProjectsSubmodel,
    SectionsSubmodel,
    SeriesSubmodel,
    ScansSubmodel,
]
