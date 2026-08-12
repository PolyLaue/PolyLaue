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
    ):
        self.parent = parent

    @property
    def number(self) -> int:
        # This is based upon the scan info from the parent
        return self.parent.scan_number(self)

    # The scan shifts were removed, but may still be present in
    # older settings files. Skip them silently.
    _attrs_to_ignore = [
        'shift_x',
        'shift_y',
    ]
