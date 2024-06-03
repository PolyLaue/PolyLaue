from PySide6.QtCore import (
    QAbstractItemModel,
    QEvent,
    QSortFilterProxyModel,
    Qt,
    Signal,
)
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QMenu, QMessageBox, QTableView, QWidget

from polylaue.model.series import Series
from polylaue.ui.project_navigator.navigation_bar import NavigationBar
from polylaue.ui.series_editor import SeriesEditorDialog


# A few shortcuts to enums
EditTrigger = QTableView.EditTrigger
ItemFlag = Qt.ItemFlag
SelectionBehavior = QTableView.SelectionBehavior


class ProjectNavigatorView(QTableView):
    """A generic table view for navigating projects

    Double-clicking on a row will descend into that path, unless it
    is a series, in which case it will be opened.
    """

    """Emitted when a series should be opened"""
    open_series = Signal(Series)

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

        self.setup_connections()

    def setup_connections(self):
        if self.navigation_bar is not None:
            self.navigation_bar.button_clicked.connect(
                self.on_navigation_bar_button_clicked
            )

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
    def is_submodel_series(self):
        return self.submodel.type == 'series'

    @property
    def selected_rows(self):
        return [
            self.proxy_model.mapToSource(x).row()
            for x in self.selectionModel().selectedRows()
        ]

    def contextMenuEvent(self, event: QEvent):
        actions = {}

        # Set up variables that will be used in the actions
        index = self.indexAt(event.pos())
        source_index = self.proxy_model.mapToSource(index)
        row_clicked = source_index.row()
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
            self.edit(index)

        def edit_series():
            self.edit_series(row_clicked)

        if ItemFlag.ItemIsEditable in index.flags():
            add_actions({'Edit': edit_item})

        if is_series:
            add_actions({'Series Settings': edit_series})

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

        if self.model.submodel.type == 'series':
            # We double-clicked on a series. Open it.
            series = self.model.submodel.entry_list[row]
            self.open_series.emit(series)
        else:
            # If it is anything except a series, navigate inside it.
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

    def on_navigation_bar_button_clicked(self, i: int):
        # Truncate the path based upon the index the user clicked
        self.model.set_path(self.model.path[:i])
        self.on_path_modified()

    def edit_series(self, row: int):
        series = self.submodel.entry_list[row]
        if SeriesEditorDialog(series, self).exec():
            # Indicate that the data was modified.
            self.model.data_modified.emit()

            # Trigger the series to be re-opened
            self.open_series.emit(series)

    def insert_row(self, row: int):
        # A row of -1 indicates it should be added to the end
        row = row if row != -1 else len(self.submodel.entry_list)

        self.model.insertRows(row, 1)
        if self.is_submodel_series:
            # Bring up the series editor dialog
            self.edit_series(row)

    def remove_selected_rows(self):
        self.delete_rows(self.selected_rows)

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
