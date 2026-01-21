# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Optional

from PySide6.QtCore import (
    Qt,
)
from PySide6.QtWidgets import (
    QTableView,
    QWidget,
)


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

        # This will apply to all cells, however.
        self.setTextElideMode(Qt.ElideLeft)
        self.setWordWrap(False)
