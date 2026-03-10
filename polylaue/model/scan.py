# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from __future__ import annotations
from typing import TYPE_CHECKING

from polylaue.model.serializable import Serializable

if TYPE_CHECKING:
    from polylaue.model.series import Series


class Scan(Serializable):
    def __init__(
        self,
        parent: Series,
        shift_x: int = 0,
        shift_y: int = 0,
        scan_center_params: dict | None = None,
    ):
        self.parent = parent
        self.shift_x = shift_x
        self.shift_y = shift_y
        self.scan_center_params = scan_center_params

    @property
    def number(self) -> int:
        # This is based upon the scan info from the parent
        return self.parent.scan_number(self)

    def compute_position_um(
        self, scan_pos_y: int, scan_pos_z: int
    ) -> tuple[float, float] | None:
        """Compute the physical position in µm for a given scan position.

        The number of points along each axis is obtained from the series
        scan_shape (rows=Z, columns=Y).

        Returns (y_um, z_um) or None if scan center params are not set.
        """
        params = self.scan_center_params
        if params is None:
            return None

        center_y = params['center_y']
        center_z = params['center_z']
        y_min = params['y_min']
        y_max = params['y_max']
        z_min = params['z_min']
        z_max = params['z_max']

        # scan_shape is (rows, cols) = (z_num_points, y_num_points)
        scan_shape = self.parent.scan_shape
        y_num_points = scan_shape[1]
        z_num_points = scan_shape[0]

        if y_num_points > 1:
            y_step = (y_max - y_min) / (y_num_points - 1)
            y_um = center_y + y_min + scan_pos_y * y_step
        else:
            y_um = center_y

        if z_num_points > 1:
            z_step = (z_max - z_min) / (z_num_points - 1)
            z_um = center_z + z_min + scan_pos_z * z_step
        else:
            z_um = center_z

        return (y_um, z_um)

    # Serialization code
    _attrs_to_serialize = [
        'shift_x',
        'shift_y',
        'scan_center_params',
    ]
