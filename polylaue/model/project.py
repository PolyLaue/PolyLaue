# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from __future__ import annotations
from functools import lru_cache
from pathlib import Path
import shutil
from typing import TYPE_CHECKING

import numpy as np

from polylaue.model.core.geometry import (
    DEFAULT_DETECTOR_SETUP,
    parse_poni,
    write_geometry_file,
)
from polylaue.model.editable import (
    Editable,
    ParameterDescription,
    ValidationError,
    default_path_validator,
)
from polylaue.model.section import Section
from polylaue.typing import PathLike

if TYPE_CHECKING:
    from polylaue.model.project_manager import ProjectManager


class Project(Editable):
    """A project contains a set of sections"""

    def __init__(
        self,
        parent: ProjectManager,
        name: str = 'Project',
        sections: list[Section] | None = None,
        directory: PathLike = '',
        description: str = '',
        energy_range: tuple[float, float] = (5, 70),
        # The frame shape here defaults to the Pilatus settings at HPCAT
        frame_shape: tuple[int, int] = (981, 1043),
        white_beam_shift: float = 0.01,
        min_find_resolution: float = 0,
        min_tracking_resolution: float = 0,
    ):
        super().__init__()

        if sections is None:
            sections = []

        self.parent = parent
        self.name = name
        self.sections = sections
        self.directory = directory
        self.description = description
        self.energy_range = energy_range
        self.frame_shape = frame_shape
        # white_beam_shift has no UI, but it is used when converting
        # an imported PONI file into the geometry file.
        self.white_beam_shift = white_beam_shift
        self.min_find_resolution = min_find_resolution
        self.min_tracking_resolution = min_tracking_resolution

        # If the geometry was imported from a PONI file, this contains
        # the parameters that were parsed from it, so that the UI can
        # offer to review and edit them.
        self.last_poni_import_params: dict | None = None

        self.custom_validators['geometry_path_str'] = geometry_file_validator

    @property
    def num_sections(self):
        return len(self.sections)

    @property
    def path_from_root(self) -> list[int]:
        index = self.parent.projects.index(self)
        return self.parent.path_from_root + [index]

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
    def expected_geometry_file_path(self) -> Path:
        return self.directory / 'geometry.npz'

    @property
    def geometry_path(self) -> Path | None:
        # This simply returns `self.expected_geometry_file_path`
        # if the file exists. Otherwise, it returns `None`.
        path = self.expected_geometry_file_path
        return path if path.is_file() else None

    @geometry_path.setter
    def geometry_path(self, v: PathLike | None):
        # A new geometry source resets any previous PONI import record
        self.last_poni_import_params = None

        if v is not None:
            v = Path(v).resolve()

        write_path = self.expected_geometry_file_path
        if v == write_path:
            return

        if v is None:
            # Delete the current geometry file in the project directory
            write_path.unlink(missing_ok=True)
            return

        if v.suffix.lower() == '.poni':
            # Convert the PONI file into a PolyLaue geometry file, and
            # keep a record of the parameters, so that the UI can offer
            # to review and edit them afterward.
            params = parse_poni(v)
            self.write_poni_geometry(params)
            self.last_poni_import_params = params
            return

        write_path.write_bytes(v.read_bytes())

    @property
    def geometry_path_str(self) -> str | None:
        p = self.geometry_path
        return str(p) if p is not None else None

    @geometry_path_str.setter
    def geometry_path_str(self, v: str | None):
        if v is not None and v.strip() == '':
            v = None

        self.geometry_path = v

    def write_poni_geometry(
        self, params: dict, detector_setup: str = DEFAULT_DETECTOR_SETUP
    ):
        """Write PONI parameters as this project's geometry file

        The params match the output of parse_poni(). The project's
        frame shape and white beam shift are used for the conversion.
        """
        write_geometry_file(
            str(self.expected_geometry_file_path),
            image_size_x=self.frame_shape[0],
            image_size_y=self.frame_shape[1],
            white_beam_shift=self.white_beam_shift,
            detector_setup=detector_setup,
            **params,
        )

        # The geometry file cache is keyed on the path. Clear it, or a
        # previously loaded geometry could be served for this path.
        load_geometry_file.cache_clear()

    @property
    def auto_generated_paths(self) -> list[Path]:
        # Files and directories that PolyLaue automatically generates
        # inside the project directory. Raw data never lives here.
        return [
            self.expected_geometry_file_path,
            self.directory / 'abc_matrix.npy',
            self.directory / 'abc_matrix0.npy',
            self.directory / 'map_data.npy',
            self.directory / 'indexing.xy',
            self.directory / 'refinement.xy',
            self.directory / 'Sections',
        ]

    def delete_auto_generated_files(self):
        for path in self.auto_generated_paths:
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)

    @property
    def geometry_data(self) -> dict:
        path = self.geometry_path
        if path is None:
            raise RuntimeError(
                'Geometry file does not exist: ' f'{self.expected_geometry_file_path}'
            )

        return load_geometry_file(path)

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'directory_str',
        'description',
        'sections_serialized',
        'frame_shape',
        'energy_range',
        'white_beam_shift',
        'min_find_resolution',
        'min_tracking_resolution',
    ]

    @property
    def sections_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.sections]

    @sections_serialized.setter
    def sections_serialized(self, v: list[dict]):
        self.sections = [Section.from_serialized(x, parent=self) for x in v]

    def deserialize(self, d: dict):
        # For backward-compatibility, rename `directory` to `directory_str`,
        # if present. We can remove this in a couple of releases, after
        # we have verified that PolyLaue has been ran on all relevant
        # computers that had the old setup.
        if 'directory' in d:
            d['directory_str'] = d.pop('directory')

        return super().deserialize(d)

    # Editable fields
    @classmethod
    def get_parameters_description(cls) -> dict[str, ParameterDescription]:
        return {
            'name': {
                'type': 'string',
                'label': 'Name',
                'min': 1,
                'tooltip': 'The name of the project (must be unique)',
            },
            'description': {
                'type': 'string',
                'label': 'Description',
                'required': False,
                'tooltip': 'A description for personal records',
            },
            'directory_str': {
                'type': 'folder',
                'label': 'Directory',
                'tooltip': (
                    'The project directory is a location where PolyLaue will '
                    'automatically create and store files, such as '
                    'predicted reflections and coordinate selections. '
                ),
            },
            'frame_shape': {
                'type': 'tuple',
                'label': 'Frame Shape',
                'subtype': 'integer',
                'length': 2,
                'min': 1,
                'max': 10000000,
                'tooltip': 'The shape of the data frames (in pixels)',
            },
            'energy_range': {
                'type': 'tuple',
                'label': 'Energy Range',
                'subtype': 'float',
                'length': 2,
                'min': 1e-16,
                'max': float('inf'),
                'tooltip': 'The energy range of the x-ray beam in keV',
            },
            'geometry_path_str': {
                'type': 'file',
                'label': 'Geometry',
                'extensions': ['npz', 'poni'],
                'required': False,
                'tooltip': (
                    'Path to a PolyLaue geometry file (NPZ format), or to '
                    'a PONI file to import. This file is necessary for '
                    'predicting reflections.\n\n'
                    'An NPZ file will be copied into the project directory '
                    'as "geometry.npz". A PONI file will instead be '
                    'converted and written there, and the imported '
                    'parameters may be reviewed and edited after clicking '
                    '"OK".'
                ),
            },
            'min_find_resolution': {
                'type': 'float',
                'label': 'Minimum Find Resolution Limit',
                'min': 0,
                'max': float('inf'),
                'tooltip': (
                    'The minimum resolution limit (Å) allowed when performing '
                    'find.\n\nThis setting is intended to prevent '
                    'users from accidentally choosing a resolution limit '
                    'that is too low, which then may cause the algorithm '
                    'to run forever.\n\nThis resolution can be different from '
                    'project to project.'
                ),
            },
            'min_tracking_resolution': {
                'type': 'float',
                'label': 'Minimum Tracking Resolution Limit',
                'min': 0,
                'max': float('inf'),
                'tooltip': (
                    'The minimum resolution limit (Å) allowed when performing '
                    'tracking.\n\nThis setting is intended to prevent '
                    'users from accidentally choosing a resolution limit '
                    'that is too low, which then may cause the algorithm '
                    'to run forever.\n\nThis resolution can be different from '
                    'project to project.'
                ),
            },
        }


def geometry_file_validator(name: str, value, description: ParameterDescription, *args):
    # Perform the regular file checks first
    default_path_validator(name, value, description, *args)

    if not isinstance(value, str) or not value.strip():
        # An empty value already passed the default validation
        return

    path = Path(value)
    if path.suffix.lower() == '.poni':
        # Verify that the PONI file can actually be parsed
        try:
            parse_poni(path)
        except (ValueError, OSError) as e:
            raise ValidationError(f"{description['label']}:\n{e}")


# We probably only need to cache one geometry file, but since they are
# small, just cache 2...
@lru_cache(maxsize=2)
def load_geometry_file(path: str) -> dict:
    return _load_geometry_file(path)


def _load_geometry_file(path: str) -> dict:
    npz_file = np.load(path)
    return {
        'det_org': npz_file['iitt1'],
        'beam_dir': npz_file['iitt2'],
        'pix_dist': npz_file['iitt3'],
    }
