from polylaue.model.serializable import Serializable
from polylaue.model.series import Series


class Section(Serializable):
    """A section contains a set of series"""

    def __init__(
        self,
        name: str = 'Section',
        series: list[Series] | None = None,
        description: str = 'Description',
        parent: Serializable | None = None,
    ):
        if series is None:
            series = []

        self.name = name
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
    def series_serialized(self) -> list[dict]:
        return [x.serialize() for x in self.series]

    @series_serialized.setter
    def series_serialized(self, v: list[dict]):
        self.series = [Series.from_serialized(x, parent=self) for x in v]
