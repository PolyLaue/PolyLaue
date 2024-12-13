# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Callable

from functools import partial

from polylaue.model.project import Project
from polylaue.model.section import Section
from polylaue.ui.utils.custom_validators import unique_value_validator
from polylaue.ui.project_navigator.submodels.base import BaseSubmodel


def is_unique(project: Project, value: str) -> bool:
    unique = True

    lower_value = value.lower()

    for section in project.sections:
        unique = unique and section.name.lower() != lower_value

    return unique


class SectionsSubmodel(BaseSubmodel):
    type = 'sections'

    def __init__(self, project: Project):
        self.project = project
        for section in self.project.sections:
            section.custom_validators['name'] = partial(
                unique_value_validator, partial(is_unique, self.project)
            )

    @property
    def entry_list(self) -> list[Section]:
        return self.project.sections

    def create(self, row: int) -> Section:
        section = Section(self.project)
        section.custom_validators['name'] = partial(
            unique_value_validator, partial(is_unique, self.project)
        )
        return section

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
