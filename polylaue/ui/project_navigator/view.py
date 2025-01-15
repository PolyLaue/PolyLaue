# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QItemSelectionModel,
    QModelIndex,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QFileDialog,
    QMenu,
    QMessageBox,
    QTableView,
    QWidget,
)

from polylaue.model.scan import Scan
from polylaue.model.series import Series
from polylaue.ui.project_navigator.navigation_bar import NavigationBar


# A few shortcuts to enums
EditTrigger = QTableView.EditTrigger
ItemFlag = Qt.ItemFlag
SelectionBehavior = QTableView.SelectionBehavior


class ProjectNavigatorView(QTableView):
    """A generic table view for navigating projects

    Double-clicking on a row will descend into that path, unless it
    is a series, in which case it will be opened.
    """

    """Emitted when a series was modified"""
    series_modified = Signal(Series)

    """Emitted when a specific scan should be opened

    The scan should have a parent which is the series
    """
    open_scan = Signal(Scan)

    """Emitted when the current path changes"""
    path_changed = Signal()

    def __init__(
        self,
        navigation_bar: NavigationBar | None = None,
        parent: QWidget = None,
    ):
        super().__init__(parent)

        self.navigation_bar = navigation_bar

        # Hide the vertical header
        self.verticalHeader().hide()

        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(150)

        # Disable edit triggers (only edit via context menu)
        self.setEditTriggers(EditTrigger.NoEditTriggers)

        # Select rows
        self.setSelectionBehavior(SelectionBehavior.SelectRows)

        self.setSortingEnabled(True)

        # The directory names are really long. Only show the
        # right side of them, and elide to the left.
        # This will apply to all cells, however.
        self.setTextElideMode(Qt.ElideLeft)
        self.setWordWrap(False)

        self.setup_connections()

    def setup_connections(self):
        if self.navigation_bar is not None:
            self.navigation_bar.button_clicked.connect(
                self.on_navigation_bar_button_clicked
            )

    def set_current_path(self, current_path: list[int]):
        self.model.set_path(current_path[:-1])
        self.on_path_modified()
        self.select_row(current_path[-1])

    @property
    def proxy_model(self):
        return super().model()

    @property
    def model(self):
        # Return the source model for the sort proxy
        return self.proxy_model.sourceModel()

    @property
    def submodel(self):
        return self.model.submodel

    @property
    def is_submodel_series(self) -> bool:
        return self.submodel.type == 'series'

    @property
    def is_submodel_scans(self) -> bool:
        return self.submodel.type == 'scans'

    @property
    def selected_rows(self):
        return [
            self.proxy_model.mapToSource(x).row()
            for x in self.selectionModel().selectedRows()
        ]

    def select_row(self, i: int):
        if i >= self.model.rowCount():
            # Out of range. Don't do anything.
            return

        # Select the row
        selection_model = self.selectionModel()
        selection_model.clearSelection()

        model_index = selection_model.model().index(i, 0)
        command = QItemSelectionModel.Select | QItemSelectionModel.Rows
        selection_model.select(model_index, command)

    def contextMenuEvent(self, event: QEvent):
        actions = {}

        # Set up variables that will be used in the actions
        index = self.indexAt(event.pos())
        source_index = self.proxy_model.mapToSource(index)
        row_clicked = source_index.row()
        col_clicked = source_index.column()
        is_series = self.is_submodel_series
        selected_rows = self.selected_rows
        num_selected_rows = len(selected_rows)

        menu = QMenu(self)

        # Helper functions
        def add_actions(d: dict):
            actions.update({menu.addAction(k): v for k, v in d.items()})

        def add_separator():
            if not actions:
                return

            menu.addSeparator()

        # Context menu methods
        def insert_row():
            self.insert_row(row_clicked)

        def edit_item():
            column_name = self.model.submodel.column_to_key(col_clicked)
            custom_edit_keys = self.model.submodel.custom_edit_column_keys
            if column_name in custom_edit_keys:
                edit_function_name = custom_edit_keys[column_name]
                self.custom_edit_functions[edit_function_name](source_index)
                return

            # Default behavior is to just use the regular editor
            self.edit(index)

        def edit_entry():
            self.edit_entry(row_clicked)

        def edit_scan_shifts():
            self.descend_into_row(row_clicked)

        if ItemFlag.ItemIsEditable in index.flags():
            add_actions(
                {
                    'Edit': edit_entry,
                    'Edit Field': edit_item,
                }
            )

        if is_series:
            add_actions(
                {
                    'Scan Shifts': edit_scan_shifts,
                }
            )

        if actions:
            add_separator()

        add_actions({'Insert': insert_row})

        if num_selected_rows > 0:
            add_actions({'Delete': self.remove_selected_rows})

        if not actions:
            # No context menu
            return

        # Open up the context menu
        action_chosen = menu.exec(QCursor.pos())

        if action_chosen is None:
            # No action chosen
            return

        # Run the function for the action that was chosen
        actions[action_chosen]()

    def mouseDoubleClickEvent(self, event: QEvent):
        if event.button() != Qt.LeftButton:
            # Perform default behavior if not left-click
            return super().mouseDoubleClickEvent(event)

        # For left-clicks, update the path
        index = self.indexAt(event.pos())
        if index.row() == -1:
            # Empty space was double-clicked
            return super().mouseDoubleClickEvent(event)

        # Map the index to the source model
        index = self.proxy_model.mapToSource(index)
        row = index.row()

        if self.is_submodel_series:
            series = self.model.submodel.entry_list[row]
            # Get the first scan and open that.
            self.open_scan.emit(series.scans[0])
        elif self.is_submodel_scans:
            scan = self.model.submodel.entry_list[row]
            self.open_scan.emit(scan)
        else:
            # If it is anything except a series, navigate inside it.
            self.descend_into_row(row)

    def descend_into_row(self, row: int):
        self.model.set_path(self.model.path + [row])
        self.on_path_modified()

    def keyPressEvent(self, event: QEvent):
        if event.key() == Qt.Key_Delete:
            selected_rows = self.selected_rows
            if selected_rows:
                self.delete_rows(selected_rows)
                return

        return super().keyPressEvent(event)

    def setModel(self, model: QAbstractItemModel):
        # Wrap the model in a QSortFilterProxyModel for sorting
        proxy = QSortFilterProxyModel(self)
        proxy.setSourceModel(model)
        super().setModel(proxy)

        self.on_path_modified()

    def on_path_modified(self):
        if self.navigation_bar is None:
            return

        # Use 'Projects' for the root projects path name
        path_names = ['Projects'] + self.model.path_names
        self.navigation_bar.setup_path(path_names)

        # Invalidate the sorting
        self.sortByColumn(-1, Qt.SortOrder.AscendingOrder)

        self.path_changed.emit()

    def on_navigation_bar_button_clicked(self, i: int):
        # Truncate the path based upon the index the user clicked
        previous_row = self.model.path[i]
        self.model.set_path(self.model.path[:i])
        self.on_path_modified()
        self.select_row(previous_row)

    def edit_entry(self, row: int):
        if self.submodel.edit_entry(row):
            # Indicate that the data was modified.
            self.model.data_modified.emit()

            # If it is a series, trigger the series to be re-opened
            entry = self.submodel.entry_list[row]
            if isinstance(entry, Series):
                self.series_modified.emit(entry)

    def insert_row(self, row: int):
        # A row of -1 indicates it should be added to the end
        row = row if row != -1 else len(self.submodel.entry_list)
        self.model.insertRows(row, 1)

    def edit_selected_rows(self):
        self.edit_rows(self.selected_rows)

    def remove_selected_rows(self):
        self.delete_rows(self.selected_rows)

    def edit_rows(self, rows: list[int]):
        for row in rows:
            self.edit_entry(row)

    def delete_rows(self, rows: list[int], confirm_with_user: bool = True):
        if confirm_with_user:
            if len(rows) < 5:
                names = [self.submodel.entry_list[x].name for x in rows]
                names_str = ', '.join(names)
                msg = f'Delete "{names_str}"?'
            else:
                msg = f'Delete {len(rows)} entries?'

            msg += '\n\nThis cannot be undone.'
            if QMessageBox.question(self, 'Delete?', msg) == QMessageBox.No:
                # User canceled. Return
                return

        # Perform the delete
        for i, row in enumerate(sorted(rows)):
            # Offset according to previously removed rows
            self.model.removeRows(row - i, 1)

    # These are custom edit functions for certain columns
    @property
    def custom_edit_functions(self) -> dict:
        return {
            'directory_path': self.edit_directory_path,
        }

    def edit_directory_path(self, index: QModelIndex):
        current_dir = index.data()
        path = QFileDialog.getExistingDirectory(
            self, 'Select Directory', current_dir
        )
        if not path:
            return

        self.model.setData(index, path)
