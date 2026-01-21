# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QBuffer, QByteArray, QFile, QObject
from PySide6.QtWidgets import QDialog, QWidget
from PySide6.QtUiTools import QUiLoader

from polylaue.typing import PathLike
from polylaue.utils import resource_loader
from polylaue.ui.utils.keep_dialog_on_top import keep_dialog_on_top
from polylaue.ui.utils.qsingleton import QSingleton
import polylaue.ui.resources.ui


class UiLoader(QUiLoader, QSingleton):
    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)

        self.register_custom_widgets()

    def register_custom_widgets(self):
        from polylaue.ui.scientificspinbox import ScientificDoubleSpinBox

        register_list = (ScientificDoubleSpinBox,)
        for item in register_list:
            self.registerCustomWidget(item)

    def load_file(self, filename: PathLike, parent: QWidget | None = None) -> QWidget:
        """Load a UI file and return the widget

        Returns a widget created from the UI file.

        :param filename: The name of the ui file to load (must be located
                         in polylaue.ui.resources.ui).
        """
        module = polylaue.ui.resources.ui
        with resource_loader.filepath(module, filename) as path:
            # Need to use a QIODevice for loading
            f = QFile(path)
            f.open(QFile.ReadOnly)
            ui = self.load(f, parent)

        self.process_ui(ui)
        return ui

    def load_bytes(self, data: bytes, parent: QWidget | None = None) -> QWidget:
        """Load a UI file from a string and return the widget"""
        buf = QBuffer(QByteArray(data))
        ui = self.load(buf, parent)

        # Perform any custom processing on the ui
        self.process_ui(ui)
        return ui

    def process_ui(self, ui: QWidget):
        """Perform any additional processing on loaded UI objects"""
        if isinstance(ui, QDialog):
            # We always make dialogs stay on top by default
            keep_dialog_on_top(ui)
