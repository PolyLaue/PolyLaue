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

    def generatePicture(self):
        # pre-computing a QPicture object allows paint() to run much quicker,
        # rather than re-drawing the shapes every time.
        self.picture = QtGui.QPicture()
        p = QtGui.QPainter(self.picture)

        # Disable drawing axis text for now

        # n_ticks = len(self.x_ticks)

        # if n_ticks > 1:
        #    fontsize = round(
        #       0.5 * (self.x_ticks[n_ticks - 1] - self.x_ticks[0]) / len(self.x_ticks)
        #    )
        # else:
        #     fontsize = 16

        # font = p.font()
        # font.setPixelSize(fontsize)
        # p.setFont(font)

        # padding = fontsize / 2

        p.setPen(pg.mkPen('w'))

        for i, x in enumerate(self.x_ticks):
            # p.drawText(QtCore.QPointF(x, self.y_limits[0] - padding), str(i))
            # p.drawText(QtCore.QPointF(x, self.y_limits[1] + padding + fontsize), str(i))
            p.drawLine(
                QtCore.QPointF(x, self.y_limits[0]),
                QtCore.QPointF(x, self.y_limits[1]),
            )

        for i, y in enumerate(self.y_ticks):
            # p.drawText(QtCore.QPointF(self.x_limits[0] - padding - fontsize, y), str(i))
            # p.drawText(QtCore.QPointF(self.x_limits[1] + padding, y), str(i))
            p.drawLine(
                QtCore.QPointF(self.x_limits[0], y),
                QtCore.QPointF(self.x_limits[1], y),
            )

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
