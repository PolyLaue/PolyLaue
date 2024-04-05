import signal
import sys

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import QApplication

from polylaue.ui.main_window import MainWindow
from polylaue.utils import resource_loader
import polylaue.resources.icons


def main():
    # For now, the only argument parsing we do is assume that
    # the file right after the script is to be loaded...
    load_file = None
    if len(sys.argv) > 1:
        load_file = sys.argv[1]

    # Kill the program when ctrl-c is used
    signal.signal(signal.SIGINT, signal.SIG_DFL)

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

    if load_file:
        # Load a file that was provided on the command-line
        window.load_image_file(load_file)

    # Run the application
    app.exec()


if __name__ == '__main__':
    main()
