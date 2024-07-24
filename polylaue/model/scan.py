from polylaue.model.serializable import Serializable


class Scan(Serializable):
    def __init__(
        self,
        shift_x: int = 0,
        shift_y: int = 0,
        parent: Serializable | None = None,
    ):
        self.shift_x = shift_x
        self.shift_y = shift_y
        self.parent = parent

    @property
    def number(self) -> int:
        # This is based upon the scan info from the parent
        series = self.parent
        if series is None:
            return -1

        return series.scan_number(self)

    # Serialization code
    _attrs_to_serialize = [
        'shift_x',
        'shift_y',
    ]
