# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

from polylaue.model.section import Section
from polylaue.model.serializable import Serializable
from polylaue.model.editable import Editable, ParameterDescription
from polylaue.typing import PathLike


class Project(Editable):
    """A project contains a set of sections"""

    def __init__(
        self,
        name: str = 'Project',
        sections: list[Section] | None = None,
        directory: PathLike = '',
        description: str = '',
        energy_range: tuple[float, float] = (5, 70),
        frame_shape: tuple[int, int] = (2048, 2048),
        white_beam_shift: float = 0.01,
        geometry_path: PathLike | None = None,
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
        self.geometry_path = geometry_path

    @property
    def num_sections(self):
        return len(self.sections)

    @property
    def directory(self) -> Path:
        return self._directory

    @directory.setter
    def directory(self, v: PathLike):
        self._directory = Path(v).resolve()

    @property
    def directory_str(self) -> str:
        return str(self.directory)

    @directory_str.setter
    def directory_str(self, v: str):
        self.directory = v

    @property
    def geometry_path(self) -> Path | None:
        return getattr(self, '_geometry_path', None)

    @geometry_path.setter
    def geometry_path(self, v: PathLike | None):
        if v is not None:
            v = Path(v).resolve()

        if v == self.geometry_path:
            return

        # Delete the current geometry file in the project directory
        if (
            self.geometry_path is not None
            and self.directory in self.geometry_path.parents
        ):
            self.geometry_path.unlink(missing_ok=True)

        if v is None:
            self._geometry_path = v
            return

        # If the file is not in the project directory,
        # copy it over and set the new path
        if self.directory not in v.parents:
            v_copy = self.directory / v.name
            v_copy.write_bytes(v.read_bytes())
            self._geometry_path = v_copy
        else:
            self._geometry_path = v

    @property
    def geometry_path_str(self) -> str | None:
        p = self.geometry_path
        return str(p) if p is not None else None

    @geometry_path_str.setter
    def geometry_path_str(self, v: str | None):
        if v is not None and v.strip() == '':
            v = None

        self.geometry_path = v

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'directory_str',
        'description',
        'sections_serialized',
        'frame_shape',
        'energy_range',
        'white_beam_shift',
        'geometry_path_str',
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
            "directory_str": {
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
            "geometry_path_str": {
                "type": "file",
                "label": "Geometry",
                "extensions": ["npz"],
                "required": False,
            },
        }
