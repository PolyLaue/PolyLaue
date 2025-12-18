# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.scan import Scan
from polylaue.model.series import Series
from polylaue.ui.project_navigator.submodels.base import BaseSubmodel


class ScansSubmodel(BaseSubmodel):
    type = 'scans'

    def __init__(self, series: Series):
        self.series = series

    @property
    def entry_list(self) -> list[Scan]:
        return self.series.scans

    def create(self, row: int) -> Scan:
        return Scan(self.series)

    @property
    def columns(self) -> dict[str, str]:
        return {
            'number': 'Number',
            'shift_x': 'Shift X',
            'shift_y': 'Shift Y',
        }

    @property
    def uneditable_column_keys(self) -> list[str]:
        return ['number']
