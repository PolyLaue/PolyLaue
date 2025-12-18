# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.project_manager import ProjectManager
from polylaue.model.project import Project
from polylaue.ui.project_navigator.submodels.base import BaseSubmodel
from polylaue.ui.utils.custom_validators import empty_folder_validator


class ProjectsSubmodel(BaseSubmodel):
    type = 'projects'

    def __init__(self, project_manager: ProjectManager):
        self.project_manager = project_manager
        for project in self.project_manager.projects:
            project.custom_validators['directory_str'] = empty_folder_validator

    @property
    def entry_list(self) -> list[Project]:
        return self.project_manager.projects

    def create(self, row: int) -> Project:
        project = Project(self.project_manager)
        project.custom_validators['directory_str'] = empty_folder_validator
        return project

    @property
    def columns(self) -> dict[str, str]:
        return {
            'name': 'Name',
            'directory_str': 'Directory',
            'num_sections': 'Number of Sections',
        }

    @property
    def custom_edit_column_keys(self) -> dict[str, str]:
        return {'directory_str': 'directory_path'}

    @property
    def uneditable_column_keys(self) -> list[str]:
        return ['num_sections']
