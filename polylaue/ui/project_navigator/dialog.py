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


class ProjectNavigatorDialog(QDialog):
    def __init__(
        self, project_manager: ProjectManager, parent: QWidget = None
    ):
        super().__init__(parent)

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
        self.remove_button = QPushButton('Remove', self)
        add_remove_layout.addWidget(self.add_button)
        add_remove_layout.addWidget(self.remove_button)

        # This seems like a reasonable default.
        # Can we come up with something without hard-coding, though?
        self.resize(600, 300)

        self.on_selection_changed()

        self.setup_connections()

    def setup_connections(self):
        self.add_button.clicked.connect(self.on_add_clicked)
        self.remove_button.clicked.connect(self.on_remove_clicked)
        self.view.selectionModel().selectionChanged.connect(
            self.on_selection_changed
        )

    def on_add_clicked(self):
        self.view.insert_row(-1)

    def on_remove_clicked(self):
        self.view.remove_selected_rows()

    def on_selection_changed(self):
        num_rows_selected = len(self.view.selected_rows)
        self.remove_button.setEnabled(num_rows_selected > 0)

    @property
    def layout(self):
        return super().layout()
