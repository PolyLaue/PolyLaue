# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.project_manager import ProjectManager
from polylaue.model.project import Project
from polylaue.ui.project_navigator.submodels.base import BaseSubmodel


class ProjectsSubmodel(BaseSubmodel):
    type = 'projects'

    def __init__(self, project_manager: ProjectManager):
        self.project_manager = project_manager

    @property
    def entry_list(self) -> list[Project]:
        return self.project_manager.projects

    def create(self) -> Project:
        return Project(parent=self.project_manager)

    @property
    def columns(self) -> dict[str, str]:
        return {
            'name': 'Name',
            'description': 'Description',
            'num_sections': 'Number of Sections',
        }

    @property
    def uneditable_column_keys(self) -> list[str]:
        return ['num_sections']
