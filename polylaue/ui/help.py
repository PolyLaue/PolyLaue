# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from functools import partial

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QAction, QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QBoxLayout,
    QDialogButtonBox,
    QPushButton,
    QStyle,
    QWidget,
)

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


def add_help_action(action: QAction, page: str = ''):
    """Connect a menu action to open the documentation page

    The page is bound here, so that the `checked` argument of
    `triggered` is not mistaken for it.
    """
    action.triggered.connect(partial(open_help, page))


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


def help_button_on_left() -> bool:
    """Whether this platform puts the Help button first in a dialog

    Windows keeps it with the other buttons on the right, while macOS,
    KDE and GNOME put it on the left. This is the same rule that
    QDialogButtonBox follows.
    """
    # styleHint() returns a plain int, which never compares equal to the
    # enum member, so convert it first.
    hint = QApplication.style().styleHint(QStyle.StyleHint.SH_DialogButtonLayout)
    layout = QDialogButtonBox.ButtonLayout(hint)
    return layout != QDialogButtonBox.ButtonLayout.WinLayout


def help_alignment() -> Qt.AlignmentFlag:
    """Where to align a Help button that is on a row of its own"""
    if help_button_on_left():
        return Qt.AlignmentFlag.AlignLeft

    return Qt.AlignmentFlag.AlignRight


def insert_help_button(
    layout: QBoxLayout, page: str, parent: QWidget | None = None
) -> QPushButton:
    """Add a Help button to a row of buttons, where the platform puts it"""
    button = help_button(page, parent)
    if help_button_on_left():
        layout.insertWidget(0, button)
    else:
        layout.addWidget(button)

    return button
