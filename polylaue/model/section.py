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

    @property
    def overlapping_scan_region(self) -> tuple[tuple[int, int], tuple[int, int]]:
        """Compute the overlapping scan region of the series

        This looks at the scan_shift of each series to compute the common
        region that all series will contain.

        This function returns (i_offsets, j_offsets), where each is comprised
        of a (start_offset, stop_offset).

        For example, if one series is shifted +1 in i, and one series is
        shifted -1 in j, then this function will return ((1, 0), (0, -1)),
        indicating that the overlapping region is offset at the start by
        `i == 1` and `j == 0`, and offset at the end by `i == 0` and `j == -1`.
        If the scan shape is (21, 21), then the overlapping scan region will
        have a shape of (20, 20), which is offset by 1 from the start in `i`
        and 1 from the end in `j`.
        """
        i_min = 0
        i_max = 0
        j_min = 0
        j_max = 0
        for series in self.series:
            i, j = series.scan_shift
            i_min = min(i_min, i)
            i_max = max(i_max, i)
            j_min = min(j_min, j)
            j_max = max(j_max, j)

        i_offsets = (i_max, i_min)
        j_offsets = (j_max, j_min)
        print(f'{i_offsets=} {j_offsets=}')
        return i_offsets, j_offsets

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
        self.overlapping_scan_region
