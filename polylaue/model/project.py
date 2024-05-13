from polylaue.model.section import Section
from polylaue.model.serializable import Serializable


class Project(Serializable):
    """A project contains a set of sections"""

    def __init__(
        self,
        name: str = 'Project',
        sections: list[Section] = [],
        description: str = 'Description',
    ):
        self.name = name
        self.sections = sections
        self.description = description

    @property
    def num_sections(self):
        return len(self.sections)

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'description',
        'sections_serialized',
    ]

    @property
    def sections_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.sections]

    @sections_serialized.setter
    def sections_serialized(self, v: list[dict]):
        self.sections = [Section.from_serialized(x) for x in v]
