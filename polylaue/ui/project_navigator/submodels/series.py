# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.section import Section
from polylaue.model.series import Series
from polylaue.ui.project_navigator.submodels.base import BaseSubmodel


class SeriesSubmodel(BaseSubmodel):
    type = 'series'

    def __init__(self, section: Section):
        self.section = section

    @property
    def entry_list(self) -> list[Series]:
        return self.section.series

    def create(self, row: int) -> Series:
        series = Series(self.section)
        if len(self.entry_list) > 0:
            # Set the directory to be the parent of a neighboring series,
            # since the user will probably need to navigate there anyways.
            neighbor_row = row - 1 if row > 0 else len(self.entry_list) - 1
            neighbor_series = self.entry_list[neighbor_row]
            series.dirpath = neighbor_series.dirpath.parent

        return series

    @property
    def columns(self) -> dict[str, str]:
        return {
            'name': 'Name',
            'description': 'Description',
            'scan_range_formatted': 'Scan Range',
        }

    @property
    def uneditable_column_keys(self) -> list[str]:
        return ['scan_range_formatted']
