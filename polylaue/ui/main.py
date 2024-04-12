import signal
import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

import pyqtgraph

from polylaue.ui.main_window import MainWindow
from polylaue.utils import resource_loader
import polylaue.resources.icons


def main():
    # For now, the only argument parsing we do is assume that
    # the series right after the script is to be loaded...
    load_series = None
    if len(sys.argv) > 1:
        load_series = sys.argv[1]

    # Kill the program when ctrl-c is used
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # Setup config options for pyqtgraph
    pyqtgraph.setConfigOptions(
        **{
            # Use row-major for the imageAxisOrder in pyqtgraph
            'imageAxisOrder': 'row-major',
            # Use numba acceleration where we can
            'useNumba': True,
        }
    )

    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts)

    QCoreApplication.setOrganizationName('PolyLaue')
    QCoreApplication.setApplicationName('PolyLaue')

    app = QApplication(sys.argv)

    data = resource_loader.read_binary(
        polylaue.resources.icons, 'polylaue.ico'
    )
    pixmap = QPixmap()
    pixmap.loadFromData(data, 'ico')
    icon = QIcon(pixmap)
    app.setWindowIcon(icon)

    window = MainWindow()
    window.set_icon(icon)
    window.show()

    if load_series:
        # Load a file that was provided on the command-line
        window.load_series(load_series)

    # Run the application
    app.exec()


if __name__ == '__main__':
    main()
