from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog


def keep_dialog_on_top(dialog: QDialog):
    flags = dialog.windowFlags()
    dialog.setWindowFlags(flags | Qt.Tool)
