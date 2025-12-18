# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

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
    ):
        self.parent = parent
        self.shift_x = shift_x
        self.shift_y = shift_y

    @property
    def number(self) -> int:
        # This is based upon the scan info from the parent
        return self.parent.scan_number(self)

    # Serialization code
    _attrs_to_serialize = [
        'shift_x',
        'shift_y',
    ]
