"""Main module for the Quick Move application."""

import os.path
import signal
import sys

from PyQt6 import uic
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QAction, QKeyEvent
from PyQt6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow,
                             QPushButton)

from quick_move import __version__
from PyQt6.QtWidgets import QMessageBox

from quick_move.completer import get_completions

# Allow Ctrl+C to exit the application. Qt doesn't handle interrupts by default.
signal.signal(signal.SIGINT, signal.SIG_DFL)

UI_FILE = os.path.join(os.path.dirname(__file__), "main_window.ui")

ABOUT_UI_FILE = os.path.join(os.path.dirname(__file__), "about_window.ui")

# I want to move files to ~/Sync (syncthing default folder), mainly, for now.
# TODO: persistent destination scope config that you can change easily, perhaps with the Home key (using the same destination input field)
destination_scope = os.path.expanduser('~/Sync/')
if not os.path.exists(destination_scope):
    destination_scope = os.path.expanduser('~/')

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
        self.suggestionsListWidget: QListWidget
        self.moveButton: QPushButton

        self.actionQuit: QAction
        self.actionAbout_Quick_Move: QAction
        self.actionAbout_Qt: QAction

        # Handle button clicks
        # (could do this with an action, for consistency...)
        self.moveButton.clicked.connect(self.move_files)  # pyright: ignore[reportUnknownMemberType]

        # Handle menu actions
        self.actionQuit.triggered.connect(self.close)  # pyright: ignore[reportUnknownMemberType]
        self.actionAbout_Quick_Move.triggered.connect(self.show_about)  # pyright: ignore[reportUnknownMemberType]
        self.actionAbout_Qt.triggered.connect(QApplication.aboutQt)  # pyright: ignore[reportUnknownMemberType]

        # Populate info about selected files
        self.payloadLabel.setText(f"Moving {len(payload)} files: {', '.join(payload)}" if payload else '⚠️ No files selected. The quick-move program should be run with files as arguments.')

        # Handle destination directory input
        self.destinationEdit.textChanged.connect(self.update_suggestions)  # pyright: ignore[reportUnknownMemberType]
        self.destinationEdit.setText(destination_scope)
        self.destinationEdit.focusNextPrevChild = lambda next: True

        # Keep the destinationEdit input field focused if you click on the suggestions list widget.
        self.suggestionsListWidget.setFocusProxy(self.destinationEdit)

    def event(self, event: QEvent | None) -> bool:
        if isinstance(event, QKeyEvent):
            # If Tab is pressed, accept the current suggestion
            # This has to be handled specially because Tab is handled specially by Qt
            # and doesn't propagate to the keyPressEvent handler.
            # There may be a much cleaner way to do this. Who knows!
            if event.key() == Qt.Key.Key_Tab and event.type() == QEvent.Type.ShortcutOverride:
                self.accept_suggestion()
                return True
        return super(MainWindow, self).event(event)

    # Argument is named generically as `a0` in PyQt6, hence the "incompatibility"
    # Also the event type is Optional. I don't know why yet.
    def keyPressEvent(self, event: QKeyEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle key presses."""
        key = event.key()
        # print(f"Key pressed: {key} (Qt.Key.{Qt.Key(key).name}, {event.text()})")
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_Return or key == Qt.Key.Key_Enter:
            self.accept_suggestion()
            self.move_files()
        elif key == Qt.Key.Key_Up:
            self.suggestionsListWidget.setCurrentRow(max(0, self.suggestionsListWidget.currentRow() - 1))
        elif key == Qt.Key.Key_Down:
            self.suggestionsListWidget.setCurrentRow(min(self.suggestionsListWidget.count() - 1, self.suggestionsListWidget.currentRow() + 1))
        # See event() method for Tab handling.
        # elif key == Qt.Key.Key_Tab:
        #     self.accept_suggestion()

        super(MainWindow, self).keyPressEvent(event)

    def accept_suggestion(self):
        """Accept the currently selected suggestion and update the destination input field."""
        item = self.suggestionsListWidget.currentItem()
        if item is not None:
            label = self.suggestionsListWidget.itemWidget(item)
            if label is not None:
                # Use tooltip() instead of text() to avoid HTML in the input field
                # Could alternatively store a custom property on the label with the full path.
                # Do we want a tooltip? Maybe, so I've done it this way.
                self.destinationEdit.setText(label.toolTip())

    def move_files(self):
        """Move selected files to the target directory, and exit if successful."""
        import shutil
        destination = self.destinationEdit.text().strip()
        if not destination:
            # There's a potential UX issue if you want to move files to the root of the configured destination scope.
            # Right now I guess it'll just give you this error message.
            QMessageBox.warning(self, "Warning", "Please specify a destination directory.")
            return
        if not os.path.exists(destination):
            # QMessageBox.warning(self, "Warning", f"The destination '{destination}' does not exist.")
            # return
            if QMessageBox.question(self, "Create Directory", f"The destination '{destination}' does not exist. Do you want to create it?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
                try:
                    os.makedirs(destination, exist_ok=True)
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to create directory '{destination}': {e}")
                    return
            else:
                return
        if not os.path.isdir(destination):
            QMessageBox.warning(self, "Warning", f"The destination '{destination}' is not a directory.")
            return
        # TODO: Can we do this atomically?
        for file in payload:
            try:
                shutil.move(file, destination)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to move '{file}' to '{destination}': {e}")

        self.close()

    def update_suggestions(self):
        """Update the suggestions list based on the destination directory input."""
        suggestions = get_completions(self.destinationEdit.text(), destination_scope)
        # TODO: icons/styling for directories to be created, AI suggestions
        self.suggestionsListWidget.clear()
        self.suggestionsListWidget.clear()
        for suggestion in suggestions:
            # suggestion.match_highlights is a list of (start, end) tuples
            text = suggestion.display_text
            html = ""
            last_idx = 0
            for start, end in suggestion.match_highlights:
                # TODO: escape HTML characters in text
                html += text[last_idx:start]
                # TODO: escape HTML characters in text
                html += f"<span style='background-color: rgba(255, 255, 0, 0.5); font-weight: bold'>{text[start:end]}</span>"
                last_idx = end
            # TODO: escape HTML characters in text
            html += text[last_idx:]
            label = QLabel()
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText(html)
            label.setToolTip(text)  # Show the full path in the tooltip (ALSO USED FOR READING BACK FOR AUTO-COMPLETE)
            # label.setStyleSheet("QLabel { padding: 2px; }")  # this doesn't expand the label size, so it doesn't work
            item = QListWidgetItem()
            self.suggestionsListWidget.addItem(item)
            self.suggestionsListWidget.setItemWidget(item, label)
        self.suggestionsListWidget.setCurrentRow(0)

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
