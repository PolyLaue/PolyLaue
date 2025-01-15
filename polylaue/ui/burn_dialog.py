# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject, Signal

from polylaue.model.core import VALID_STRUCTURE_TYPES
from polylaue.ui.utils.block_signals import block_signals
from polylaue.ui.utils.ui_loader import UiLoader


class BurnDialog(QObject):

    burn_triggered = Signal()
    clear_reflections = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = UiLoader().load_file('burn_dialog.ui', parent)

        self.add_structure_options()

        self.setup_connections()

    def add_structure_options(self):
        self.ui.structure_type.addItems(VALID_STRUCTURE_TYPES)

    def setup_connections(self):
        self.ui.activate_burn.toggled.connect(self.on_activate_burn)

        self.ui.crystal_id.valueChanged.connect(self.on_crystal_id_changed)

        self.ui.crystal_orientation.currentIndexChanged.connect(
            self.on_crystal_orientation_changed
        )

        self.ui.structure_type.currentIndexChanged.connect(
            self.on_structure_type_changed
        )

        self.ui.max_dmin.valueChanged.connect(self.on_max_dmin_changed)

        self.ui.dmin_slider.valueChanged.connect(self.on_dmin_slider_changed)

        self.ui.dmin_value.valueChanged.connect(self.on_dmin_value_changed)

        self.ui.apply_angular_shift.toggled.connect(
            self.on_apply_angular_shift_changed
        )

        self.ui.angular_shift_scan_number.valueChanged.connect(
            self.on_angular_shift_scan_number_changed
        )

        self.ui.clear.clicked.connect(self.on_clear_clicked)

    def activate_burn(self):
        self.burn_activated = True

    def deactivate_burn(self):
        self.burn_activated = False

    @property
    def burn_activated(self) -> bool:
        return self.ui.activate_burn.isChecked()

    @burn_activated.setter
    def burn_activated(self, b: bool):
        self.ui.activate_burn.setChecked(b)

    @property
    def crystal_orientation(self) -> str:
        return self.ui.crystal_orientation.currentText()

    @property
    def crystal_orientation_is_from_hdf5_file(self) -> bool:
        return self.crystal_orientation == 'From HDF5 File'

    @property
    def crystal_orientation_is_from_project_dir(self) -> bool:
        return self.crystal_orientation == 'From Project Directory'

    @property
    def crystal_id(self) -> int:
        return self.ui.crystal_id.value()

    @property
    def structure_type(self) -> str:
        return self.ui.structure_type.currentText()

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

    @property
    def apply_angular_shift(self) -> bool:
        return self.ui.apply_angular_shift.isChecked()

    @apply_angular_shift.setter
    def apply_angular_shift(self, b: bool):
        self.ui.apply_angularShift.setChecked(b)

    @property
    def angular_shift_scan_number(self) -> int:
        if not self.apply_angular_shift:
            return -1

        return self.ui.angular_shift_scan_number.value()

    @angular_shift_scan_number.setter
    def angular_shift_scan_number(self, v: int):
        apply = v > 1
        self.apply_angular_shift = apply

        if apply:
            self.ui.angular_shift_scan_number.setValue(v)

    def on_activate_burn(self):
        self.emit_if_active()

    def on_crystal_id_changed(self):
        # Deactivate the burn function
        self.deactivate_burn()

    def on_crystal_orientation_changed(self):
        # Deactivate the burn function
        self.deactivate_burn()

    def on_structure_type_changed(self):
        self.emit_if_active()

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

        self.emit_if_active()

    def on_apply_angular_shift_changed(self):
        self.emit_if_active()

    def on_angular_shift_scan_number_changed(self):
        self.emit_if_active()

    def emit_if_active(self):
        if not self.burn_activated:
            return

        self.burn_triggered.emit()

    def on_clear_clicked(self):
        self.deactivate_burn()
        self.clear_reflections.emit()
