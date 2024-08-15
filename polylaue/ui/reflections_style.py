# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from dataclasses import asdict, dataclass


@dataclass
class ReflectionsStyle:
    symbol: str = 'o'
    size: float = 10.0
    pen_width: float = 3.0
    use_brush: bool = False
    offset_x: float = 0.0
    offset_y: float = 0.0

    def asdict(self) -> dict:
        return asdict(self)
