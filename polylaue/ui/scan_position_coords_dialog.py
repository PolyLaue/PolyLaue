# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QWidget

from polylaue.ui.utils.ui_loader import UiLoader


class ScanPositionCoordsDialog:

    SETTINGS_KEY = 'scan_position_coords_dialog_settings'

    def __init__(self, parent: QWidget | None = None):
        self.ui = UiLoader().load_file('scan_position_coords_dialog.ui', parent)

    def exec(self, initial_params: dict | None = None) -> dict | None:
        """Show the dialog and return the parameters if accepted.

        If `initial_params` is provided, those values are loaded into the
        dialog.  Otherwise, the last-used values from QSettings are loaded.

        Returns the parameter dict on OK, or None on Cancel.
        """
        if initial_params is not None:
            self.settings_serialized = initial_params
        else:
            self.load_settings()

        result = self.ui.exec()
        if result != QDialog.Accepted:
            return None

        # Save to QSettings so next invocation remembers these values
        self.save_settings()
        return self.settings_serialized

    # ------------------------------------------------------------------
    # QSettings persistence
    # ------------------------------------------------------------------
    def load_settings(self):
        settings = QSettings()
        self.settings_serialized = settings.value(self.SETTINGS_KEY, {})

    def save_settings(self):
        settings = QSettings()
        settings.setValue(self.SETTINGS_KEY, self.settings_serialized)

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    @property
    def _attrs_to_serialize(self) -> list[str]:
        return [
            'center_y',
            'center_z',
            'y_min',
            'y_max',
            'z_min',
            'z_max',
        ]

    @property
    def settings_serialized(self) -> dict:
        return {k: getattr(self, k) for k in self._attrs_to_serialize}

    @settings_serialized.setter
    def settings_serialized(self, values: dict):
        for k, v in values.items():
            if hasattr(self, k):
                setattr(self, k, v)

    # ------------------------------------------------------------------
    # Property accessors for each widget
    # ------------------------------------------------------------------
    @property
    def center_y(self) -> float:
        return self.ui.center_y.value()

    @center_y.setter
    def center_y(self, v: float):
        self.ui.center_y.setValue(v)

    @property
    def center_z(self) -> float:
        return self.ui.center_z.value()

    @center_z.setter
    def center_z(self, v: float):
        self.ui.center_z.setValue(v)

    @property
    def y_min(self) -> float:
        return self.ui.y_min.value()

    @y_min.setter
    def y_min(self, v: float):
        self.ui.y_min.setValue(v)

    @property
    def y_max(self) -> float:
        return self.ui.y_max.value()

    @y_max.setter
    def y_max(self, v: float):
        self.ui.y_max.setValue(v)

    @property
    def z_min(self) -> float:
        return self.ui.z_min.value()

    @z_min.setter
    def z_min(self, v: float):
        self.ui.z_min.setValue(v)

    @property
    def z_max(self) -> float:
        return self.ui.z_max.value()

    @z_max.setter
    def z_max(self, v: float):
        self.ui.z_max.setValue(v)
