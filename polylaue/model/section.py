from polylaue.model.serializable import Serializable
from polylaue.model.series import Series


class Section(Serializable):
    """A section contains a set of series"""

    def __init__(
        self,
        name: str = 'Section',
        series: list[Series] = [],
        description: str = 'Description',
    ):
        self.name = name
        self.series = series
        self.description = description

    @property
    def num_series(self):
        return len(self.series)

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
        self.series = [Series.from_serialized(x) for x in v]
