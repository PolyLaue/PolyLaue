# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from functools import partial

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QDialogButtonBox, QPushButton, QWidget

DOCS_URL = 'https://polylaue.github.io/'

# Documentation pages for the editors, keyed by the editable class name
EDITOR_HELP_PAGES = {
    'Project': 'projects/#creating-a-project',
    'Section': 'projects/#creating-a-section',
    'Series': 'projects/#creating-a-series',
    'PoniGeometry': 'projects/#importing-a-poni-file-as-the-geometry',
}


def help_url(page: str = '') -> str:
    """The documentation URL for a page, such as 'mapping/#map-windows'"""
    return DOCS_URL + page


def open_help(page: str = ''):
    """Open a documentation page in the web browser"""
    QDesktopServices.openUrl(QUrl(help_url(page)))


def add_help_button(button_box: QDialogButtonBox, page: str) -> QPushButton:
    """Add a Help button to a button box that opens the documentation page"""
    button = button_box.addButton(QDialogButtonBox.StandardButton.Help)
    button_box.helpRequested.connect(partial(open_help, page))
    return button


def help_button(page: str, parent: QWidget | None = None) -> QPushButton:
    """Create a Help button that opens the documentation page"""
    button = QPushButton('Help', parent)
    button.clicked.connect(partial(open_help, page))
    return button
