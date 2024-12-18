# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject, Signal

from polylaue.ui.utils.block_signals import block_signals
from polylaue.ui.utils.ui_loader import UiLoader


class BurnDialog(QObject):

    dmin_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = UiLoader().load_file('burn_dialog.ui', parent)

        self.setup_connections()

    def setup_connections(self):
        self.ui.max_dmin.valueChanged.connect(self.on_max_dmin_changed)

        self.ui.dmin_slider.valueChanged.connect(self.on_dmin_slider_changed)

        self.ui.dmin_value.valueChanged.connect(self.on_dmin_value_changed)

    @property
    def max_dmin(self) -> float:
        return self.ui.max_dmin.value()

    @max_dmin.setter
    def max_dmin(self, v: float):
        self.ui.max_dmin.setValue(v)

    @property
    def dmin(self) -> float:
        return self.ui.dmin_value.value()

    @dmin.setter
    def dmin(self, v: float):
        self.ui.dmin_value.setValue(v)

    @property
    def slider_max(self) -> int:
        return self.ui.dmin_slider.maximum()

    @property
    def slider_value(self) -> int:
        return self.ui.dmin_slider.value()

    @slider_value.setter
    def slider_value(self, v: int):
        self.ui.dmin_slider.setValue(v)

    def on_max_dmin_changed(self):
        # First, adjust the value if the value is above the new max dmin
        if self.dmin > self.max_dmin:
            # This will update the slider value automatically
            self.dmin = self.max_dmin
        else:
            self.update_slider_value()

    def update_slider_value(self):
        with block_signals(self.ui.dmin_slider):
            # Remap the dmin to slider value
            self.slider_value = self.slider_max - (
                self.dmin / self.max_dmin * self.slider_max
            )

    def on_dmin_slider_changed(self):
        # Remap the slider value to our dmin value
        self.dmin = (
            (self.slider_max - self.slider_value)
            * self.max_dmin
            / self.slider_max
        )

    def on_dmin_value_changed(self):
        self.update_slider_value()

        if self.dmin > self.max_dmin:
            self.max_dmin = self.dmin

        self.dmin_changed.emit()
