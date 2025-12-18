# Copyright © 2025, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.project import Project
from polylaue.model.serializable import Serializable


class ProjectManager(Serializable):
    """The project manager contains a set of projects"""

    def __init__(
        self,
        projects: list[Project] | None = None,
        parent: Serializable | None = None,
    ):
        if projects is None:
            projects = []

        self.projects = projects
        self.parent = parent

    @property
    def num_projects(self):
        return len(self.projects)

    @property
    def path_from_root(self) -> list[int]:
        # This is the root
        return []

    # Serialization code
    _attrs_to_serialize = [
        'projects_serialized',
    ]

    @property
    def projects_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.projects]

    @projects_serialized.setter
    def projects_serialized(self, v: list[dict]):
        self.projects = [Project.from_serialized(x, parent=self) for x in v]
