# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject, Signal

from polylaue.model.core import VALID_STRUCTURE_TYPES
from polylaue.ui.utils.block_signals import block_signals
from polylaue.ui.utils.ui_loader import UiLoader


class BurnDialog(QObject):

    burn_triggered = Signal()
    overwrite_crystal = Signal()
    crystal_name_modified = Signal()
    load_crystal_name = Signal()
    update_has_angular_shift = Signal()
    write_crystal_orientation = Signal()
    clear_reflections = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.ui = UiLoader().load_file('burn_dialog.ui', parent)

        self.add_structure_options()

        self._custom_internal_abc_matrix = None

        # Make this the default
        self.set_crystal_orientation_to_hdf5_file()
        self.update_enable_states()
        self.setup_connections()

    def add_structure_options(self):
        self.ui.structure_type.addItems(VALID_STRUCTURE_TYPES)

    def setup_connections(self):
        self.ui.activate_burn.toggled.connect(self.on_activate_burn)

        self.ui.structure_type.currentIndexChanged.connect(
            self.on_structure_type_changed
        )

        self.ui.crystal_id.valueChanged.connect(self.on_crystal_id_changed)
        self.ui.crystal_name.textEdited.connect(self.on_crystal_name_edited)

        self.ui.crystal_orientation.currentIndexChanged.connect(
            self.on_crystal_orientation_changed
        )

        self.ui.overwrite_crystal.clicked.connect(
            self.on_overwrite_crystal_clicked
        )

        self.ui.write_crystal_orientation.clicked.connect(
            self.on_write_crystal_orientation_clicked
        )

        self.ui.max_dmin.valueChanged.connect(self.on_max_dmin_changed)

        self.ui.dmin_slider.valueChanged.connect(self.on_dmin_slider_changed)

        self.ui.dmin_value.valueChanged.connect(self.on_dmin_value_changed)

        self.ui.apply_angular_shift.toggled.connect(
            self.on_apply_angular_shift_changed
        )
        self.ui.angular_shift_from_another_crystal.toggled.connect(
            self.on_angular_shift_from_another_crystal_changed
        )
        self.ui.angular_shift_crystal_id.valueChanged.connect(
            self.on_angular_shift_crystal_id_changed
        )
        self.ui.use_custom_internal_abc_matrix.toggled.connect(
            self.on_use_custom_internal_abc_matrix_toggled
        )

        self.ui.clear.clicked.connect(self.on_clear_clicked)

    def update_enable_states(self):
        using_custom_matrix = self.use_custom_internal_abc_matrix

        self.ui.crystal_orientation_label.setEnabled(not using_custom_matrix)
        self.ui.crystal_orientation.setEnabled(not using_custom_matrix)

        enable = (
            not self.crystal_orientation_is_from_hdf5_file
            and not using_custom_matrix
        )
        self.ui.overwrite_crystal.setEnabled(enable)

        self.ui.write_crystal_orientation.setEnabled(not using_custom_matrix)

        self.ui.angular_shift_group.setEnabled(not using_custom_matrix)

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
    def structure_type(self) -> str:
        return self.ui.structure_type.currentText()

    @property
    def crystal_orientation(self) -> str:
        return self.ui.crystal_orientation.currentText()

    def set_crystal_orientation_to_hdf5_file(self):
        self.ui.crystal_orientation.setCurrentText('From HDF5 File')

    @property
    def crystal_orientation_is_from_hdf5_file(self) -> bool:
        return self.crystal_orientation == 'From HDF5 File'

    @property
    def crystal_orientation_is_from_project_dir(self) -> bool:
        return self.crystal_orientation == 'From Project Directory'

    @property
    def crystal_id(self) -> int:
        return self.ui.crystal_id.value()

    @crystal_id.setter
    def crystal_id(self, v: int):
        self.ui.crystal_id.setValue(v)

    @property
    def crystal_name(self) -> str:
        return self.ui.crystal_name.text()

    @crystal_name.setter
    def crystal_name(self, v: str):
        self.ui.crystal_name.setText(v)

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
        self.ui.apply_angular_shift.setChecked(b)

    @property
    def angular_shift_from_another_crystal(self) -> bool:
        return self.ui.angular_shift_from_another_crystal.isChecked()

    @angular_shift_from_another_crystal.setter
    def angular_shift_from_another_crystal(self, b: bool):
        self.ui.angular_shift_from_another_crystal.setChecked(b)

    @property
    def angular_shift_crystal_id(self) -> int:
        return self.ui.angular_shift_crystal_id.value()

    @angular_shift_crystal_id.setter
    def angular_shift_crystal_id(self, v: int):
        self.ui.angular_shift_crystal_id.setValue(v)

    @property
    def use_custom_internal_abc_matrix(self) -> bool:
        return self.ui.use_custom_internal_abc_matrix.isChecked()

    @use_custom_internal_abc_matrix.setter
    def use_custom_internal_abc_matrix(self, b: bool):
        self.ui.use_custom_internal_abc_matrix.setChecked(b)

    @property
    def custom_internal_abc_matrix(self) -> np.ndarray | None:
        """Set the custom internal ABC matrix

        This allows us to burn reflections using a custom ABC matrix that
        is not stored/computed from the reflections file.

        We utilize this currently for tracking within a single scan, where
        we want to see reflections that correspond to the bending of a
        crystal, but we don't want to store them on disk.
        """
        return self._custom_internal_abc_matrix

    @custom_internal_abc_matrix.setter
    def custom_internal_abc_matrix(self, abc_matrix: np.ndarray | None):
        """Set the custom internal ABC matrix

        This allows us to burn reflections using a custom ABC matrix that
        is not stored/computed from the reflections file.

        We utilize this currently for tracking within a single scan, where
        we want to see reflections that correspond to the bending of a
        crystal, but we don't want to store them on disk.
        """
        self._custom_internal_abc_matrix = abc_matrix

        enable = abc_matrix is not None
        w = self.ui.use_custom_internal_abc_matrix
        w.setEnabled(enable)
        if not enable:
            w.setChecked(False)

        self.ui.use_custom_internal_abc_matrix.setToolTip(
            'Use a custom internal ABC matrix. '
            f'The current one is:\n\n{abc_matrix}'
        )

    def on_activate_burn(self):
        self.emit_if_active()

    def on_structure_type_changed(self):
        self.emit_if_active()

    def on_crystal_id_changed(self):
        # Deactivate the burn function
        self.deactivate_burn()

        # Load the crystal name
        self.load_crystal_name.emit()
        self.update_has_angular_shift.emit()

    def on_crystal_name_edited(self):
        self.crystal_name_modified.emit()

    def on_crystal_orientation_changed(self):
        # Deactivate the burn function
        self.deactivate_burn()
        self.update_enable_states()
        self.update_has_angular_shift.emit()

    def on_overwrite_crystal_clicked(self):
        self.overwrite_crystal.emit()

    def on_write_crystal_orientation_clicked(self):
        self.write_crystal_orientation.emit()

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
        if not self.apply_angular_shift:
            # Make sure the angular shift from another crystal is disabled
            self.angular_shift_from_another_crystal = False

        self.emit_if_active()

    def on_angular_shift_from_another_crystal_changed(self):
        self.update_has_angular_shift.emit()
        self.emit_if_active()

    def on_angular_shift_crystal_id_changed(self):
        self.update_has_angular_shift.emit()
        self.emit_if_active()

    def on_use_custom_internal_abc_matrix_toggled(self):
        self.update_enable_states()
        self.emit_if_active()

    def set_has_angular_shift(self, b: bool):
        w = self.ui.has_angular_shift_label
        result = 'Yes' if b else 'No'
        w.setText(f'Has angular shift: {result}')

    def emit_if_active(self):
        if not self.burn_activated:
            return

        self.burn_triggered.emit()

    def on_clear_clicked(self):
        self.deactivate_burn()
        self.clear_reflections.emit()
