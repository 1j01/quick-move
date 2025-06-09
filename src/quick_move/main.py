"""Main module for the Quick Move application."""

import os.path
import signal
import sys

from PyQt6 import uic
from PyQt6.QtCore import QStringListModel, Qt
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit, QListView, QMainWindow,
                             QPushButton)

from quick_move import __version__
from PyQt6.QtWidgets import QMessageBox

# Allow Ctrl+C to exit the application. Qt doesn't handle interrupts by default.
signal.signal(signal.SIGINT, signal.SIG_DFL)

UI_FILE = os.path.join(os.path.dirname(__file__), "main_window.ui")

ABOUT_UI_FILE = os.path.join(os.path.dirname(__file__), "about_window.ui")

# Get payload from command line arguments
payload = sys.argv[1:] if len(sys.argv) > 1 else []
# Get selection with desktop automation
if payload and payload[0] == '--from-clipboard':
    # import keyboard
    import pyperclip
    original_clipboard = pyperclip.paste()
    # keyboard.send('ctrl+x')
    # Instead of keyboard, use xdotool to avoid needing root permissions
    import subprocess
    subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+x'], check=True)
    # Does pyperclip.paste() wait for the clipboard to change at all, or is it dumb?
    new_clipboard = pyperclip.paste()
    pyperclip.copy(original_clipboard)
    # More robust might be to set the clipboard to empty, then ctrl+x, then wait for the clipboard to change,
    # with some timeout.
    # Currently, if you run the program after copying/cutting the selection, it will be identical to the original clipboard,
    # and the payload will be considered empty.
    if new_clipboard == original_clipboard:
        print("new_clipboard is the same as original_clipboard, assuming no selection was made.")
        print(f"original_clipboard: {original_clipboard}")
        payload = []
    else:
        print("new_clipboard is different from original_clipboard, assuming selection was made.")
        print(f"new_clipboard: {new_clipboard}")
        print(f"original_clipboard: {original_clipboard}")
        # TODO: split on spaces, handle quoting
        payload = new_clipboard.splitlines()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Load the .ui file
        # TODO: try compiling the .ui file to a .py file; it might help with type checking
        # Pyright gives "reportPrivateImportUsage" because it doesn't find anything in the PyQt6 module,
        # I guess because it uses pkgutil.extend_path rather than explicit imports?
        # Although, `from PyQt6.uic import loadUi` (equally functional) gives the same error.
        uic.loadUi(UI_FILE, self)  # pyright: ignore[reportUnknownMemberType, reportPrivateImportUsage]

        self.payloadLabel: QLabel
        self.destinationEdit: QLineEdit
        self.suggestionsListView: QListView  # NOTE: There's also QCompleter which could be used for suggestions
        self.moveButton: QPushButton

        self.actionQuit: QAction
        self.actionAbout_Quick_Move: QAction
        self.actionAbout_Qt: QAction

        # Handle button clicks
        # (could do this with an action, for consistency...)
        self.moveButton.clicked.connect(self.move_files)

        # Handle menu actions
        self.actionQuit.triggered.connect(self.close) # type: ignore
        self.actionAbout_Quick_Move.triggered.connect(self.show_about)
        self.actionAbout_Qt.triggered.connect(QApplication.aboutQt)

        # Populate info about selected files
        self.payloadLabel.setText(f"Moving {len(payload)} files: {', '.join(payload)}" if payload else '⚠️ No files selected. The quick-move program should be run with files as arguments.')

        # Handle destination directory input
        self.destinationEdit.textChanged.connect(self.update_suggestions)

    # Argument is named generically as `a0` in PyQt6, hence the "incompatibility"
    # Also the event type is Optional. I don't know why yet.
    def keyPressEvent(self, event: QKeyEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle key presses."""
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.move_files()
        elif key == Qt.Key.Key_F1:
            self.show_about()

        super(MainWindow, self).keyPressEvent(event)

    def move_files(self):
        """Move selected files to the target directory."""
        # TODO: Implement file moving logic
        QMessageBox.information(self, "Move Files", "This feature is not implemented yet.")

    def update_suggestions(self):
        """Update the suggestions list based on the destination directory input."""
        destination = self.destinationEdit.text()
        if not destination:
            self.suggestionsListView.setModel(None)
            return
        # TODO: Implement suggestions based on the destination directory
        suggestions = [f"{destination}/suggestion_{i}" for i in range(5)]  # Dummy suggestions
        model = QStringListModel(suggestions)
        self.suggestionsListView.setModel(model)

    def show_about(self):
        """Show the about dialog."""
        dialog: QDialog = uic.loadUi(ABOUT_UI_FILE)  # type: ignore
        dialog.version_label.setText(f"{__version__}")  # type: ignore
        dialog.exec()

def main():
    """Run the application. This is defined in `setup.cfg` as the entry point for the `quick-move` command."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
