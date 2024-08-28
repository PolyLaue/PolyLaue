# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Optional

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QTableView,
    QWidget,
)


# A few shortcuts to enums
EditTrigger = QTableView.EditTrigger
ItemFlag = Qt.ItemFlag


class RegionsNavigatorView(QTableView):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        # Hide the vertical header
        self.verticalHeader().hide()

        header = self.horizontalHeader()
        header.setStretchLastSection(True)

        # Select rows
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)

        # The directory names are really long. Only show the
        # right side of them, and elide to the left.
        # This will apply to all cells, however.
        self.setTextElideMode(Qt.ElideLeft)
        self.setWordWrap(False)
