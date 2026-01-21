# Copyright © 2026, UChicago Argonne, LLC. See "LICENSE" for full details.

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from polylaue.model.series import Series
from polylaue.model.editable import Editable, ParameterDescription
from polylaue.typing import PathLike

if TYPE_CHECKING:
    from polylaue.model.project import Project


class Section(Editable):
    """A section contains a set of series"""

    def __init__(
        self,
        parent: Project,
        name: str = '',
        series: list[Series] | None = None,
        description: str = '',
    ):
        super().__init__()

        if series is None:
            series = []

        self.parent = parent
        self._name = name
        self.series = series
        self.description = description

    @property
    def num_series(self):
        return len(self.series)

    @property
    def path_from_root(self) -> list[int]:
        index = self.parent.sections.index(self)
        return self.parent.path_from_root + [index]

    def series_with_scan_index(self, scan_index: int) -> Series | None:
        # Return the first series we can find that contains the scan
        # index.
        for series in self.series:
            if scan_index in series.scan_range:
                return series

        # Did not find it. Returning None...
        return None

    @property
    def directory(self) -> Path:
        return self.parent.directory.resolve() / f'Sections/{self.name}'

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value):
        prev_value = self._name

        if value == prev_value:
            return

        current_dir = self.directory

        self._name = value

        destination_dir = self.directory

        if prev_value != '' and current_dir.is_dir():
            Path.rename(current_dir, destination_dir)
        elif not destination_dir.exists():
            Path.mkdir(destination_dir, parents=True)

    @property
    def expected_reflections_file_path(self) -> Path:
        return self.directory / 'reflections.h5'

    @property
    def reflections_file_path(self) -> Path | None:
        # This simply returns `self.expected_reflections_file_path`
        # if the file exists. Otherwise, it returns `None`.
        path = self.expected_reflections_file_path
        return path if path.is_file() else None

    @reflections_file_path.setter
    def reflections_file_path(self, v: PathLike | None):
        if v is not None:
            v = Path(v).resolve()

        write_path = self.expected_reflections_file_path
        if v == write_path:
            return

        if v is None:
            # Delete the current reflections file in the project directory
            write_path.unlink(missing_ok=True)
            return

        write_path.write_bytes(v.read_bytes())

    @property
    def reflections_file_path_str(self) -> str | None:
        p = self.reflections_file_path
        return str(p) if p is not None else None

    @reflections_file_path_str.setter
    def reflections_file_path_str(self, v: str | None):
        if v is not None and v.strip() == '':
            v = None

        self.reflections_file_path = v

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'description',
        'series_serialized',
    ]

    @property
    def series_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.series]

    @series_serialized.setter
    def series_serialized(self, v: list[dict]):
        self.series = [Series.from_serialized(x, parent=self) for x in v]

    # Editable fields
    @classmethod
    def get_parameters_description(cls) -> dict[str, ParameterDescription]:
        return {
            'name': {
                'type': 'string',
                'label': 'Name',
                'min': 1,
                'tooltip': 'The name of the section (must be unique)',
            },
            'description': {
                'type': 'string',
                'label': 'Description',
                'required': False,
                'tooltip': 'A description for personal records',
            },
            'reflections_file_path_str': {
                'type': 'file',
                'label': 'Reflections File',
                'extensions': ['h5', 'hdf5'],
                'required': False,
                'tooltip': (
                    'Path to PolyLaue reflections file (HDF5).\n\n'
                    'The file will be copied into the section directory as '
                    '"reflections.h5". If one is not provided, this file will '
                    'be generated automatically when predicting reflections.'
                ),
            },
        }
