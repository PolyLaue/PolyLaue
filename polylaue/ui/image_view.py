from PySide6.QtCore import QEvent, QPointF, Qt, Signal

from polylaue.model.reflections.base import BaseReflections
from polylaue.ui.reflections_style import ReflectionsStyle

import numpy as np
import pyqtgraph as pg

Key = Qt.Key


class PolyLaueImageView(pg.ImageView):
    """Override some of the pyqtgraph behavior in our own ImageView"""

    """Emitted when the scan number should be shifted"""
    shift_scan_number = Signal(int)

    """Emitted when the scan position should be shifted"""
    shift_scan_position = Signal(int, int)

    """Emitted when the mouse is moved

    The argument is a message that can be displayed in the status bar.
    """
    mouse_move_message = Signal(str)

    def __init__(self, *args, **kwargs):
        frame_tracker = kwargs.pop('frame_tracker')
        super().__init__(*args, **kwargs)

        self._last_mouse_position = None

        self.frame_tracker = frame_tracker
        self._reflections = None
        self.reflection_pens = []
        self.lock_reflections_array = False

        # FIXME: load this from the settings
        self._reflections_style = ReflectionsStyle()
        self.reflection_artist = artist = pg.ScatterPlotItem(
            pxMode=False,
            symbol=self.reflections_style.symbol,
            pen=None,
            brush=None,
            size=self.reflections_style.size,
            hoverable=True,
            tip=self._create_reflection_tooltip,
        )
        self.addItem(artist)
        self.reflection_status_message = ''

        # Add an action to reverse the cmap
        self.add_cmap_reverse_menu_action()

        self.setup_connections()

    def setup_connections(self):
        self.reflection_artist.sigHovered.connect(self.on_reflection_hovered)
        self.scene.sigMouseMoved.connect(self.on_mouse_move)

    def auto_level_colors(self):
        # These levels appear to work well for the data we have
        data = self.image_data
        lower = np.nanpercentile(data, 1.0)
        upper = np.nanpercentile(data, 99.75)
        self.setLevels(lower, upper)

    def auto_level_histogram_range(self):
        # Make the histogram range a little bigger than the auto level colors
        data = self.image_data
        lower = np.nanpercentile(data, 0.5)
        upper = np.nanpercentile(data, 99.8)
        self.setHistogramRange(lower, upper)

    @property
    def reflections(self) -> BaseReflections | None:
        return self._reflections

    @reflections.setter
    def reflections(self, v: BaseReflections | None):
        self._reflections = v
        self.reset_reflection_pens()
        self.update_reflection_overlays()

    @property
    def reflections_style(self) -> ReflectionsStyle:
        return self._reflections_style

    @reflections_style.setter
    def reflections_style(self, v: ReflectionsStyle):
        self._reflections_style = v
        self.on_reflections_style_modified()

    def on_reflections_style_modified(self):
        # Update all styles that need to be updated.
        self.reset_reflection_pens()
        self.update_reflection_overlays()

        plot = self.reflection_artist
        style = self.reflections_style

        plot.setSize(style.size)
        plot.setSymbol(style.symbol)

    def reset_reflection_pens(self):
        self.reflection_pens = []
        if self.reflections is None:
            return

        num_crystals = self.reflections.num_crystals
        width = self.reflections_style.pen_width
        pens = []
        for i in range(num_crystals):
            pens.append(pg.mkPen(i, num_crystals, width=width))
        self.reflection_pens = np.array(pens)

    def _create_reflection_tooltip(self, x, y, data):
        # The data will contain the index into the reflections array.
        # We will extract anything we need from there.
        row = self.reflections_array[data]
        tip = self.format_reflection_metadata(row[np.newaxis], delim='\n')

        # Remove the leading delimiter
        return tip[1:]

    def clear_reflection_overlays(self):
        self.reflection_artist.clear()

        if not self.lock_reflections_array:
            # Only clear the array if we are not locked (which usually
            # means we are searching for a matching prediction).
            self.reflections_array = None

        # This fixes a bug where off-image overlays would stick around
        # after changing frames when they shouldn't be (but they would
        # disappear immediately after any interaction). I'm guessing
        # pyqtgraph should be doing this.
        self.reflection_artist.prepareGeometryChange()

    def update_reflection_overlays(self):
        self.clear_reflection_overlays()
        if self.reflections is None:
            # Nothing to do...
            return

        # Verify we aren't locking the reflections array (which usually
        # means we are searching for a matching prediction).
        if not self.lock_reflections_array:
            reflections = self.reflections.reflections_table(
                *self.frame_tracker.scan_pos, self.frame_tracker.scan_num
            )
            if reflections is None:
                # Nothing to do...
                return

            self.reflections_array = reflections
        else:
            reflections = self.reflections_array

        crystal_ids = reflections[:, 9].astype(int)
        pens = self.reflection_pens[crystal_ids]

        style = self.reflections_style
        if style.use_brush:
            brush = [pen.brush() for pen in pens]
        else:
            brush = None

        offsets = [style.offset_x, style.offset_y]
        self.reflection_artist.setData(
            *(reflections[:, :2] + offsets).T,
            data=np.arange(len(reflections), dtype=int),
            pen=pens,
            brush=brush,
        )

    def on_reflection_hovered(self, points, ev):
        if len(ev) == 0:
            self.reflection_status_message = ''
            return

        indices = [x.index() for x in ev]
        hovered_rows = self.reflections_array[indices]

        self.reflection_status_message = self.format_reflection_metadata(
            hovered_rows, delim=', '
        )

        # Trigger this again so we have an updated status bar
        # FIXME: it would be nice if we didn't have to trigger this twice
        # for every mouse move
        self.on_mouse_move()

    def on_mouse_move(self, pos: QPointF | None = None):
        if self.image_data is None:
            # No data
            return

        if pos is None:
            # If no position is provided, the last mouse position will be used
            pos = self._last_mouse_position

            if pos is None:
                # We cannot proceed without a position
                return

        # Keep a record of the last position in case we change frames,
        # so we can call this function again.
        self._last_mouse_position = pos

        # First, map the scene coordinates to the view
        pos = self.view.mapSceneToView(pos)

        # We get the correct pixel coordinates by flooring these
        j, i = np.floor(pos.toTuple()).astype(int)

        data_shape = self.image_data.shape
        if not 0 <= i < data_shape[0] or not 0 <= j < data_shape[1]:
            # The mouse is out of bounds
            self.mouse_move_message.emit('')
            return

        # For display, x and y are the same as j and i, respectively
        x, y = j, i

        intensity = self.image_data[i, j]
        # Unfortunately, if we do f'{x=}', it includes the numpy
        # dtype, which we don't want.
        message = f'x={x}, y={y}, intensity={intensity}'
        message += self.reflection_status_message
        self.mouse_move_message.emit(message)

    def format_reflection_metadata(
        self, rows: np.ndarray, delim: str = ', '
    ) -> str:
        # Convert some of these to lists, so that we get native
        # types instead of numpy types. Otherwise, they will
        # be printed like `np.int64(1)`.
        hkls = np.asarray(rows[:, 2:5].astype(int))
        d_spacings = rows[:, 8].tolist()
        crystal_ids = rows[:, 9].astype(int).tolist()

        # Convert hkls to list of strings
        hkls = [' '.join(str(y) for y in x) for x in hkls]

        if len(hkls) == 1:
            hkl = hkls[0]
            d_spacing = d_spacings[0]
            crystal_id = crystal_ids[0]
            return f'{delim}{hkl=}{delim}{d_spacing=}{delim}{crystal_id=}'

        hkls = f'[{", ".join(hkls)}]'
        d_spacings = f'[{", ".join(map(str, d_spacings))}]'
        crystal_ids = f'[{", ".join(map(str, crystal_ids))}]'
        return f'{delim}{hkls=}{delim}{d_spacings=}{delim}{crystal_ids=}'

    @property
    def image_data(self) -> np.ndarray:
        return self.image_item.image

    @property
    def image_item(self) -> pg.ImageItem:
        return self.getImageItem()

    def keyPressEvent(self, event: QEvent):
        """Override the key press event to navigate between scan numbers"""

        def shift_position(i, j):
            self.shift_scan_position.emit(i, j)
            event.accept()

        def shift_scan_number(i):
            self.shift_scan_number.emit(i)
            event.accept()

        match event.key():
            case Key.Key_Right:
                # Move right one column
                return shift_position(0, 1)
            case Key.Key_Left:
                # Move left one column
                return shift_position(0, -1)
            case Key.Key_Down:
                # Move down one row
                return shift_position(1, 0)
            case Key.Key_Up:
                # Move up one row
                return shift_position(-1, 0)
            case Key.Key_PageUp:
                # Move up one scan
                return shift_scan_number(1)
            case Key.Key_PageDown:
                # Move down one scan
                return shift_scan_number(-1)

        return super().keyPressEvent(event)

    def add_cmap_reverse_menu_action(self):
        """Add a 'reverse' action to the pyqtgraph colormap menu

        This assumes pyqtgraph won't change its internal attribute structure.
        If it does change, then this function just won't work...
        """
        w = self.getHistogramWidget()
        if not w:
            # There should be a histogram widget. Not sure why it's missing...
            return

        try:
            gradient = w.item.gradient
            menu = gradient.menu
        except AttributeError:
            # pyqtgraph must have changed its attribute structure
            return

        if not menu:
            return

        def reverse():
            cmap = gradient.colorMap()
            cmap.reverse()
            gradient.setColorMap(cmap)

        menu.addSeparator()
        action = menu.addAction('reverse')
        action.triggered.connect(reverse)
