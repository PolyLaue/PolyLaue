# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.section import Section
from polylaue.model.serializable import Serializable


class Project(Serializable):
    """A project contains a set of sections"""

    def __init__(
        self,
        name: str = 'Project',
        sections: list[Section] | None = None,
        description: str = 'Description',
        parent: Serializable | None = None,
    ):
        if sections is None:
            sections = []

        self.name = name
        self.sections = sections
        self.description = description
        self.parent = parent

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
        self.sections = [Section.from_serialized(x, parent=self) for x in v]
