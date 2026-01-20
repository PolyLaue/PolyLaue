# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from PySide6.QtCore import QObject, QSettings, Signal

from polylaue.ui.utils.block_signals import block_signals
from polylaue.ui.utils.ui_loader import UiLoader

import numpy as np
import pyqtgraph as pg
from scipy import ndimage
from skimage import measure, morphology


class PointAutoPicker(QObject):

    points_modified = Signal()

    def __init__(self, image_view: pg.ImageView, parent=None):
        super().__init__(parent)
        self.ui = UiLoader().load_file('point_auto_picker.ui', parent)

        self.image_view = image_view
        self.points = []

        self.load_settings()
        self.update_threshold_slider()
        self.setup_connections()

    def setup_connections(self):
        self.ui.threshold_slider_min.valueChanged.connect(
            self.on_threshold_slider_range_modified
        )
        self.ui.threshold_slider_max.valueChanged.connect(
            self.on_threshold_slider_range_modified
        )
        self.ui.threshold_slider.valueChanged.connect(
            self.on_threshold_slider_modified
        )
        self.ui.threshold.valueChanged.connect(self.on_threshold_modified)
        self.ui.max_threshold.valueChanged.connect(
            self.on_max_threshold_modified
        )
        self.ui.min_area.valueChanged.connect(self.on_min_area_modified)

        self.ui.dilation_radius.valueChanged.connect(
            self.on_dilation_radius_modified
        )
        self.ui.accepted.connect(self.on_accepted)

    def run_auto_pick(self):
        # First, binarize the image using the threshold
        bin_img = (self.img > self.threshold) & (self.img < self.max_threshold)

        # Next, perform a dilation
        # IndexLaue did this with a mask of radius 7 and decomposition 0
        footprint = morphology.disk(self.dilation_radius)
        dilated_img = morphology.binary_dilation(bin_img, footprint)

        # Next, label the image
        # Default label structure is OK
        labels, num_peaks = ndimage.label(dilated_img)

        # Compute the weighted centroid of each spot
        # If the dilated spot contains negative values, its
        # center of mass will be computed very incorrectly.
        # Subtract the image from itself first to fix this.
        props = measure.regionprops(labels, self.img - self.img.min())
        coms = np.vstack([x.weighted_centroid for x in props])
        areas = np.hstack([x.area for x in props])

        # Only keep peaks whose areas are greater than the minimum area
        coms = coms[areas > self.min_area]

        # Now make these the selected points
        # Round to 4 decimal places
        self.points = np.round(coms[:, [1, 0]], 4)

        self.points_modified.emit()

    def show(self):
        # Run the auto-picker automatically one time
        self.run_auto_pick()
        self.ui.show()

    def hide(self):
        self.ui.hide()

    def on_accepted(self):
        self.save_settings()

    @property
    def _attrs_to_serialize(self) -> list[str]:
        return [
            'threshold_slider_min',
            'threshold_slider_max',
            'threshold',
            'max_threshold',
            'min_area',
            'dilation_radius',
        ]

    @property
    def settings_serialized(self) -> dict:
        return {k: getattr(self, k) for k in self._attrs_to_serialize}

    @settings_serialized.setter
    def settings_serialized(self, values: dict):
        for k, v in values.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def load_settings(self):
        settings = QSettings()
        self.settings_serialized = settings.value('auto_pick_settings', {})

    def save_settings(self):
        settings = QSettings()
        settings.setValue('auto_pick_settings', self.settings_serialized)

    def on_threshold_slider_range_modified(self):
        # Don't allow invalid min/max
        if self.threshold_slider_min >= self.threshold_slider_max:
            self.threshold_slider_max = self.threshold_slider_min + 1

        # Adjust threshold value if needed
        if self.threshold > self.threshold_slider_max:
            self.threshold = self.threshold_slider_max
        elif self.threshold < self.threshold_slider_min:
            self.threshold = self.threshold_slider_min

        self.update_threshold_slider()

    def on_threshold_slider_modified(self):
        slider_value = self.threshold_slider_value
        slider_min = self.threshold_slider_min
        slider_max = self.threshold_slider_max
        slider_range = slider_max - slider_min

        with block_signals(self.ui.threshold):
            self.threshold = slider_min + slider_range * slider_value / 100

        self.run_auto_pick()

    def on_threshold_modified(self):
        # Expand range if needed
        if self.threshold > self.threshold_slider_max:
            self.threshold_slider_max = self.threshold
        elif self.threshold < self.threshold_slider_min:
            self.threshold_slider_min = self.threshold

        self.update_threshold_slider()
        self.run_auto_pick()

    def on_max_threshold_modified(self):
        self.run_auto_pick()

    def on_min_area_modified(self):
        self.run_auto_pick()

    def on_dilation_radius_modified(self):
        self.run_auto_pick()

    def update_threshold_slider(self):
        slider_min = self.threshold_slider_min
        slider_max = self.threshold_slider_max
        slider_range = slider_max - slider_min

        with block_signals(self.ui.threshold_slider):
            # Our slider always has a range of values from 0 to 100
            # We'll round to the nearest integer.
            self.threshold_slider_value = int(
                round(100 * (self.threshold - slider_min) / slider_range)
            )

    @property
    def img(self):
        return self.image_item.image

    @property
    def image_item(self) -> pg.ImageItem:
        return self.image_view.getImageItem()

    @property
    def threshold(self) -> float:
        return self.ui.threshold.value()

    @threshold.setter
    def threshold(self, v: float):
        self.ui.threshold.setValue(v)

    @property
    def threshold_slider_min(self) -> float:
        return self.ui.threshold_slider_min.value()

    @threshold_slider_min.setter
    def threshold_slider_min(self, v: float):
        self.ui.threshold_slider_min.setValue(v)

    @property
    def threshold_slider_max(self) -> float:
        return self.ui.threshold_slider_max.value()

    @threshold_slider_max.setter
    def threshold_slider_max(self, v: float):
        self.ui.threshold_slider_max.setValue(v)

    @property
    def threshold_slider_value(self) -> int:
        return self.ui.threshold_slider.value()

    @threshold_slider_value.setter
    def threshold_slider_value(self, v: int):
        self.ui.threshold_slider.setValue(v)

    @property
    def max_threshold(self) -> float:
        return self.ui.max_threshold.value()

    @max_threshold.setter
    def max_threshold(self, v: float):
        self.ui.max_threshold.setValue(v)

    @property
    def min_area(self) -> float:
        return self.ui.min_area.value()

    @min_area.setter
    def min_area(self, v: float):
        self.ui.min_area.setValue(v)

    @property
    def dilation_radius(self) -> int:
        return self.ui.dilation_radius.value()

    @dilation_radius.setter
    def dilation_radius(self, v: int):
        self.ui.dilation_radius.setValue(v)
