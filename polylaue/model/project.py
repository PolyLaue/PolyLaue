# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from polylaue.model.section import Section
from polylaue.model.serializable import Serializable
from polylaue.model.editable import Editable, ParameterDescription


class Project(Editable):
    """A project contains a set of sections"""

    def __init__(
        self,
        name: str = 'Project',
        sections: list[Section] | None = None,
        directory: str = '',
        description: str = '',
        energy_range: tuple[float, float] = (5, 70),
        frame_shape: tuple[int, int] = (2048, 2048),
        white_beam_shift: float = 0.01,
        parent: Serializable | None = None,
    ):
        super().__init__()

        if sections is None:
            sections = []

        self.name = name
        self.sections = sections
        self.directory = directory
        self.description = description
        self.energy_range = energy_range
        self.frame_shape = frame_shape
        self.white_beam_shift = white_beam_shift
        self.parent = parent

    @property
    def num_sections(self):
        return len(self.sections)

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'directory',
        'description',
        'sections_serialized',
        'frame_shape',
        'energy_range',
        'white_beam_shift',
    ]

    @property
    def sections_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.sections]

    @sections_serialized.setter
    def sections_serialized(self, v: list[dict]):
        self.sections = [Section.from_serialized(x, parent=self) for x in v]

    # Editable fields
    @classmethod
    def get_parameters_description(cls) -> dict[str, ParameterDescription]:
        return {
            "name": {
                "type": "string",
                "label": "Name",
                "min": 1,
            },
            "description": {
                "type": "string",
                "label": "Description",
                "required": False,
            },
            "directory": {
                "type": "folder",
                "label": "Directory",
            },
            "frame_shape": {
                "type": "tuple",
                "label": "Frame Shape",
                "subtype": "integer",
                "length": 2,
                "min": 1,
                "max": 4096,
            },
            "energy_range": {
                "type": "tuple",
                "label": "Energy Range",
                "subtype": "float",
                "length": 2,
                "min": 1e-8,
                "max": float("inf"),
            },
            "white_beam_shift": {
                "type": "float",
                "label": "Beam Shift",
            },
        }
