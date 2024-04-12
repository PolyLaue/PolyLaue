from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal

from pyqtgraph import ImageView

Key = Qt.Key

if TYPE_CHECKING:
    from PySide6.QtCore import QEvent


class PolyLaueImageView(ImageView):
    """Override some of the pyqtgraph behavior in our own ImageView"""

    """Emitted when the scan position should be shifted"""
    shift_scan_position = Signal(int, int)

    def keyPressEvent(self, event: 'QEvent'):
        """Override the key press event to navigate between scan numbers"""

        def shift_position(i, j):
            self.shift_scan_position.emit(i, j)
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

        return super().keyPressEvent(event)
