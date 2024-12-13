# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from __future__ import annotations
from pathlib import Path
from typing import TYPE_CHECKING

from polylaue.model.series import Series
from polylaue.model.editable import Editable, ParameterDescription

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

    def series_with_scan_index(self, scan_index: int) -> Series | None:
        # Return the first series we can find that contains the scan
        # index.
        for series in self.series:
            if scan_index in series.scan_range:
                return series

        # Did not find it. Returning None...
        return None

    # Serialization code
    _attrs_to_serialize = [
        'name',
        'description',
        'series_serialized',
    ]

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
            },
            'description': {
                'type': 'string',
                'label': 'Description',
                'required': False,
            },
        }
