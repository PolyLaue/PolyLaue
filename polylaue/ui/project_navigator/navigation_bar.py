# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QWidget,
)


class NavigationBar(QWidget):
    """A row of buttons to allow jumping to a parent in a path.

    This is intended to be similar to the navigation bar at the top
    of file dialogs.
    """

    """Signal indicating a navigation bar button was clicked.

    This emits the index of the button that was clicked. It is
    the caller's responsibility to update the path of the navigation
    bar afterward.
    """
    button_clicked = Signal(int)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)

        self.setLayout(QHBoxLayout())
        self.layout.addStretch()

        self.widgets = []

    def clear_widgets(self):
        while self.widgets:
            w = self.widgets.pop()
            self.layout.removeWidget(w)
            w.deleteLater()

    def add_widget(self, w: QWidget):
        """Add the widget immediately before the stretch

        This is because the stretch at the end is kind of hard to remove...
        """
        pos = self.layout.count() - 1
        self.widgets.append(w)
        self.layout.insertWidget(pos, w)

    def setup_path(self, path: list[str]):
        self.clear_widgets()

        # Always add the first separator label
        self.add_separator_label()

        for i, text in enumerate(path):
            if i != 0:
                self.add_separator_label()

            button = QPushButton(f'{text}', self)
            button.clicked.connect(partial(self.button_clicked.emit, i))

            self.add_widget(button)

    def add_separator_label(self):
        label = QLabel('/', self)

        policy = QSizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Policy.Minimum)
        label.setSizePolicy(policy)

        self.add_widget(label)

    @property
    def layout(self):
        return super().layout()
