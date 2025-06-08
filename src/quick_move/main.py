"""Main module for the Quick Move application."""

import os.path
import signal
import sys

from PyQt6 import uic
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import (QApplication, QDialog, QMainWindow,
                             QPushButton, QSlider)

from quick_move import __version__

# Allow Ctrl+C to exit the application. Qt doesn't handle interrupts by default.
signal.signal(signal.SIGINT, signal.SIG_DFL)

UI_FILE = os.path.join(os.path.dirname(__file__), "main_window.ui")

ABOUT_UI_FILE = os.path.join(os.path.dirname(__file__), "about_window.ui")

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the .ui file
        # TODO: try compiling the .ui file to a .py file; it might help with type checking
        # Pyright gives "reportPrivateImportUsage" because it doesn't find anything in the PyQt6 module,
        # I guess because it uses pkgutil.extend_path rather than explicit imports?
        # Although, `from PyQt6.uic import loadUi` (equally functional) gives the same error.
        uic.loadUi(UI_FILE, self)  # pyright: ignore[reportUnknownMemberType, reportPrivateImportUsage]

        self.importButton: QPushButton
        self.exportButton: QPushButton
        self.autoJoinSizeSlider: QSlider
        self.threshold1Slider: QSlider
        self.threshold2Slider: QSlider
        self.apertureSizeSlider: QSlider

        self.actionOpen: QAction
        self.actionSave: QAction
        self.actionQuit: QAction
        self.actionZoom_In: QAction
        self.actionZoom_Out: QAction
        self.actionAbout_Quick_Move: QAction
        self.actionAbout_Qt: QAction

        # Handle button clicks
        # self.importButton.clicked.connect(self.import_documents)  # pyright: ignore[reportUnknownMemberType]
        # self.exportButton.clicked.connect(self.export_doodles)  # pyright: ignore[reportUnknownMemberType]

        # Handle menu actions
        self.actionQuit.triggered.connect(self.close)  # pyright: ignore[reportUnknownMemberType]
        self.actionAbout_Quick_Move.triggered.connect(self.show_about)  # pyright: ignore[reportUnknownMemberType]
        self.actionAbout_Qt.triggered.connect(QApplication.aboutQt)  # pyright: ignore[reportUnknownMemberType]

    # Argument is named generically as `a0` in PyQt6, hence the "incompatibility"
    # Also the event type is Optional. I don't know why yet.
    def keyPressEvent(self, event: QKeyEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle key presses."""
        # key = event.key()
        # if key == Qt.Key.Key_O and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        #     self.import_documents()
        # elif key == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
        #     self.export_doodles()
        # elif key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
        #     self.segmentationArea.zoom(True)
        # elif key == Qt.Key.Key_Minus:
        #     self.segmentationArea.zoom(False)


        super(MainWindow, self).keyPressEvent(event)

    def show_about(self):
        """Show the about dialog."""
        dialog: QDialog = uic.loadUi(ABOUT_UI_FILE)  # type: ignore
        dialog.version_label.setText(f"{__version__}")  # pyright: ignore[reportUnknownMemberType, reportGeneralTypeIssues]
        dialog.exec()

def main():
    """Run the application. This is defined in `setup.cfg` as the entry point for the `quick-move` command."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
