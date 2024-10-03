# Copyright © 2024, UChicago Argonne, LLC. See "LICENSE" for full details.

from typing import Sequence

import pyqtgraph as pg
from pyqtgraph import QtCore, QtGui

Number = int | float


class CustomGridItem(pg.GraphicsObject):
    def __init__(
        self, x_ticks=None, y_ticks=None, x_limits=None, y_limits=None
    ):
        pg.GraphicsObject.__init__(self)

        if x_ticks is None:
            x_ticks = []

        if y_ticks is None:
            y_ticks = []

        if x_limits is None:
            x_limits = (0, 100)

        if y_limits is None:
            y_limits = (0, 100)

        self.x_ticks: Sequence[Number] = x_ticks
        self.y_ticks: Sequence[Number] = y_ticks
        self.x_limits: tuple[Number, Number] = x_limits
        self.y_limits: tuple[Number, Number] = y_limits
        self.picture = QtGui.QPicture()
        self.active_cell: tuple[int, int] = (0, 0)
        self._redraw_needed = True
        self.generatePicture()

    def set_x_ticks(self, x_ticks: Sequence[Number]):
        self.x_ticks = x_ticks
        self._redraw_needed = True

    def set_y_ticks(self, y_ticks: Sequence[Number]):
        self.y_ticks = y_ticks
        self._redraw_needed = True

    def set_x_limits(self, x_limits: tuple[Number, Number]):
        self.x_limits = x_limits
        self._redraw_needed = True

    def set_y_limits(self, y_limits: tuple[Number, Number]):
        self.y_limits = y_limits
        self._redraw_needed = True

    def set_active_cell(self, cell: tuple[int, int]):
        self.active_cell = cell
        self._redraw_needed = True

    def generatePicture(self):
        # pre-computing a QPicture object allows paint() to run much quicker,
        # rather than re-drawing the shapes every time.
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)

        # Draw grid
        p.setPen(pg.mkPen('w'))

        for i, x in enumerate(self.x_ticks):
            p.drawLine(
                QtCore.QPointF(x, self.y_limits[0]),
                QtCore.QPointF(x, self.y_limits[1]),
            )

        for i, y in enumerate(self.y_ticks):
            p.drawLine(
                QtCore.QPointF(self.x_limits[0], y),
                QtCore.QPointF(self.x_limits[1], y),
            )

        # Draw grid labels

        # disable for now
        draw_labels = False

        if draw_labels:
            n_ticks = len(self.x_ticks)

            if n_ticks > 1:
                fontsize = round(
                    0.3
                    * (self.x_ticks[n_ticks - 1] - self.x_ticks[0])
                    / len(self.x_ticks)
                )
            else:
                fontsize = 16

            font = p.font()
            font.setPixelSize(fontsize)
            p.setFont(font)

            padding = fontsize / 2

            for i in range(len(self.x_ticks) - 1):
                x0 = self.x_ticks[i]
                x1 = self.x_ticks[i + 1]
                x = (x1 + x0) / 2
                p.drawText(
                    QtCore.QPointF(x, self.y_limits[0] - padding), str(i + 1)
                )
                p.drawText(
                    QtCore.QPointF(x, self.y_limits[1] + padding + fontsize),
                    str(i + 1),
                )

            for i in range(len(self.y_ticks) - 1):
                y0 = self.y_ticks[i]
                y1 = self.y_ticks[i + 1]
                y = (y1 + y0) / 2
                p.drawText(
                    QtCore.QPointF(self.x_limits[0] - padding - fontsize, y),
                    str(i + 1),
                )
                p.drawText(
                    QtCore.QPointF(self.x_limits[1] + padding, y), str(i + 1)
                )

        # Highlight current cell in the grid
        if (
            len(self.x_ticks) > self.active_cell[0] + 1
            and len(self.y_ticks) > self.active_cell[1] + 1
        ):
            p.setPen(pg.mkPen('y', width=2))

            x0 = self.x_ticks[self.active_cell[0]]
            y0 = self.y_ticks[self.active_cell[1]]
            x1 = self.x_ticks[self.active_cell[0] + 1]
            y1 = self.y_ticks[self.active_cell[1] + 1]
            w = x1 - x0
            h = y1 - y0
            p.drawRect(x0, y0, w, h)

        p.end()

        self._redraw_needed = False

    def paint(self, p: QtGui.QPainter, *args):
        if self._redraw_needed:
            self.generatePicture()

        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        if self._redraw_needed:
            self.generatePicture()

        return QtCore.QRectF(self.picture.boundingRect())
