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
        return Series()

    @property
    def columns(self) -> dict[str, str]:
        # FIXME: there should potentially be more for series
        return {
            'name': 'Name',
            'description': 'Description',
            'num_scans': 'Number of Scans',
        }
