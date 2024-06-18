from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.ui.project_navigator.submodels.base import BaseSubmodel


class SectionsSubmodel(BaseSubmodel):
    type = 'sections'

    def __init__(self, project: Project):
        self.project = project

    @property
    def entry_list(self) -> list[Section]:
        return self.project.sections

    def create(self) -> Section:
        return Section(parent=self.project)

    @property
    def columns(self) -> dict[str, str]:
        return {
            'name': 'Name',
            'description': 'Description',
            'num_series': 'Number of Series',
        }

    @property
    def uneditable_column_keys(self) -> list[str]:
        return ['num_series']
