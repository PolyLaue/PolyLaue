from polylaue.model.project import Project
from polylaue.model.serializable import Serializable


class ProjectManager(Serializable):
    """The project manager contains a set of projects"""

    def __init__(self, projects: list[Project] = []):
        self.projects = projects

    @property
    def num_projects(self):
        return len(self.projects)

    # Serialization code
    _attrs_to_serialize = [
        'projects_serialized',
    ]

    @property
    def projects_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.projects]

    @projects_serialized.setter
    def projects_serialized(self, v: list[dict]):
        self.projects = [Project.from_serialized(x) for x in v]
