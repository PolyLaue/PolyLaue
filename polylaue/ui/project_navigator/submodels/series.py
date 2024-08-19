# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

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

    def create(self) -> Series:
        return Series(parent=self.section)

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
