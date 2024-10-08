# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from dataclasses import dataclass


@dataclass
class FrameTracker:
    # FIXME: change these to `y` and `z`
    scan_pos_x: int = 1
    scan_pos_y: int = 1
    scan_num: int = 3

    @property
    def scan_pos(self) -> tuple[int, int]:
        return (self.scan_pos_x, self.scan_pos_y)

    @scan_pos.setter
    def scan_pos(self, v: tuple[int, int]):
        self.scan_pos_x = v[0]
        self.scan_pos_y = v[1]
