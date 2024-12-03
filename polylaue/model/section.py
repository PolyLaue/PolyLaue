# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from pathlib import Path

from polylaue.model.serializable import Serializable
from polylaue.model.series import Series
from polylaue.model.editable import Editable, ParameterDescription


class Section(Editable):
    """A section contains a set of series"""

    def __init__(
        self,
        name: str = '',
        series: list[Series] | None = None,
        description: str = '',
        parent: Serializable | None = None,
    ):
        super().__init__()

        if series is None:
            series = []

        self._name = name
        self.series = series
        self.description = description
        self.parent = parent

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
    def directory(self) -> Path | None:
        dir = Section._directory(self.parent, self.name)
        if dir is not None and dir.is_dir():
            return dir
        else:
            return None

    @staticmethod
    def _directory(parent, name) -> Path | None:
        if parent is None:
            return None

        if name == "":
            return None

        root_dir = Path(parent.directory).resolve()

        return root_dir / Path(f"section_{name.lower()}")

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value):
        prev_value = self._name

        if value == prev_value:
            return

        self._name = value

        current_dir = Section._directory(self.parent, prev_value)
        destination_dir = Section._directory(self.parent, value)

        if destination_dir is None:
            return

        if current_dir is not None and current_dir.is_dir():
            Path.rename(current_dir, destination_dir)
        elif not destination_dir.exists():
            Path.mkdir(destination_dir)

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
        }
