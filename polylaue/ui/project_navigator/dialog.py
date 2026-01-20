# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from polylaue.model.project_manager import ProjectManager
from polylaue.ui.project_navigator.model import ProjectNavigatorModel
from polylaue.ui.project_navigator.navigation_bar import NavigationBar
from polylaue.ui.project_navigator.view import ProjectNavigatorView
from polylaue.ui.utils.keep_dialog_on_top import keep_dialog_on_top


class ProjectNavigatorDialog(QDialog):
    def __init__(self, project_manager: ProjectManager, parent: QWidget = None):
        super().__init__(parent)
        keep_dialog_on_top(self)

        self.setWindowTitle('Project Navigator')

        self.navigation_bar = NavigationBar(self)
        self.model = ProjectNavigatorModel(project_manager, self)
        self.view = ProjectNavigatorView(self.navigation_bar, self)
        self.view.setModel(self.model)

        self.setLayout(QVBoxLayout())

        self.layout.addWidget(self.navigation_bar)
        self.layout.addWidget(self.view)

        add_remove_buttons_widget = QWidget(self)
        add_remove_layout = QHBoxLayout()
        add_remove_buttons_widget.setLayout(add_remove_layout)
        self.layout.addWidget(add_remove_buttons_widget)

        self.add_button = QPushButton('Add', self)
        self.edit_button = QPushButton('Edit', self)
        self.remove_button = QPushButton('Remove', self)
        add_remove_layout.addWidget(self.add_button)
        add_remove_layout.addWidget(self.edit_button)
        add_remove_layout.addWidget(self.remove_button)

        # This seems like a reasonable default.
        # Can we come up with something without hard-coding, though?
        self.resize(600, 300)

        self.update_enable_states()

        self.setup_connections()

    def setup_connections(self):
        self.add_button.clicked.connect(self.on_add_clicked)
        self.edit_button.clicked.connect(self.on_edit_clicked)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        self.view.selectionModel().selectionChanged.connect(self.update_enable_states)
        self.view.path_changed.connect(self.update_enable_states)

    def on_add_clicked(self):
        self.view.insert_row(-1)

    def on_edit_clicked(self):
        self.view.edit_selected_rows()

    def on_remove_clicked(self):
        self.view.remove_selected_rows()

    def update_enable_states(self):
        num_rows_selected = len(self.view.selected_rows)
        is_scans = self.view.is_submodel_scans

        self.add_button.setEnabled(not is_scans)
        self.edit_button.setEnabled(not is_scans and num_rows_selected > 0)
        self.remove_button.setEnabled(not is_scans and num_rows_selected > 0)

    @property
    def layout(self):
        return super().layout()
