# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QDialog, QWidget

from polylaue.ui.utils.ui_loader import UiLoader


class AcquisitionTimesDialog:

    SETTINGS_KEY = 'acquisition_times_dialog_settings'

    def __init__(self, parent: QWidget | None = None):
        self.ui = UiLoader().load_file('acquisition_times_dialog.ui', parent)

        # The interval widgets only matter when the acquisition times
        # are applied, so gray them out when they are not
        self.ui.apply_acquisition_times.toggled.connect(
            self.ui.intervals_widget.setEnabled
        )
        self.ui.intervals_widget.setEnabled(
            self.ui.apply_acquisition_times.isChecked()
        )

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
            'enabled',
            'frame_period',
            'row_break',
            'scan_break',
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
    def enabled(self) -> bool:
        return self.ui.apply_acquisition_times.isChecked()

    @enabled.setter
    def enabled(self, v: bool):
        # QSettings may return the value as a string
        self.ui.apply_acquisition_times.setChecked(v in ('true', True))

    @property
    def frame_period(self) -> float:
        return self.ui.frame_period.value()

    @frame_period.setter
    def frame_period(self, v: float):
        self.ui.frame_period.setValue(float(v))

    @property
    def row_break(self) -> float:
        return self.ui.row_break.value()

    @row_break.setter
    def row_break(self, v: float):
        self.ui.row_break.setValue(float(v))

    @property
    def scan_break(self) -> float:
        return self.ui.scan_break.value()

    @scan_break.setter
    def scan_break(self, v: float):
        self.ui.scan_break.setValue(float(v))
