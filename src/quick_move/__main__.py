"""Main module for the Quick Move application."""

import os.path
import shutil
import signal
import sys
from html import escape
from typing import cast

from PyQt6 import uic
from PyQt6.QtCore import QEvent, QSettings, Qt, QTimer, QUrl
from PyQt6.QtGui import QAction, QDesktopServices, QKeyEvent
from PyQt6.QtWidgets import (QApplication, QDialog, QLabel, QLineEdit,
                             QListWidget, QListWidgetItem, QMainWindow, QMenu,
                             QMessageBox, QPushButton)

from quick_move import __version__
from quick_move.completer import get_completions
from quick_move.desktop_automation import get_selected_files

UI_FILE = os.path.join(os.path.dirname(__file__), "main_window.ui")
ABOUT_UI_FILE = os.path.join(os.path.dirname(__file__), "about_window.ui")
RECENT_MOVE_UI_FILE = os.path.join(os.path.dirname(__file__), "recent_move_dialog.ui")

MAX_HISTORY = 100

class MainWindow(QMainWindow):
    def __init__(self, payload: list[str], destination_scope: str):
        super().__init__()

        self.payload = payload
        self.destination_scope = destination_scope

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
        self.menuHistory: QMenu

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
        # Create recent move actions
        self.historyActions: list[QAction] = []
        # self.separatorAct = self.menuHistory.addSeparator()
        # TODO: placeholder disabled item (empty menu is confusing)
        for _i in range(MAX_HISTORY):
            act = QAction(self)
            act.setVisible(False)
            act.triggered.connect(self.historyItemClicked)  # pyright: ignore[reportUnknownMemberType]
            self.historyActions.append(act)

        # Add recent move actions to the menu
        self.menuHistory.addActions(self.historyActions)  # pyright: ignore[reportUnknownMemberType]
        self.updateHistoryActions()
        # Add Clear History action
        clear_history_action = QAction("Clear History", self)
        clear_history_action.triggered.connect(self.clearHistory)  # pyright: ignore[reportUnknownMemberType]
        self.menuHistory.addSeparator()
        self.menuHistory.addAction(clear_history_action)  # pyright: ignore[reportUnknownMemberType]

        # Populate info about selected files
        self.payloadLabel.setTextFormat(Qt.TextFormat.PlainText)
        self.payloadLabel.setText(f"Moving {len(payload)} file{'' if len(payload) == 1 else 's'}: {', '.join([os.path.basename(file) for file in payload])}" if payload else '⚠️ No files selected. The quick-move program should be run with files as arguments.')

        # Handle destination directory input
        self.destinationEdit.textChanged.connect(self.update_suggestions)  # pyright: ignore[reportUnknownMemberType]
        self.destinationEdit.setText(destination_scope)
        self.destinationEdit.focusNextPrevChild = lambda next: True
        self.destinationEdit.setFocus()

        def handle_destination_edit_event(a0: QEvent | None) -> bool:
            """Handle events on the destination input field."""
            event = a0
            if isinstance(event, QKeyEvent):
                # print(f"DestinationEdit key event: {event.key()} (Qt.Key.{Qt.Key(event.key()).name}), modifiers: {event.modifiers()} (Qt.KeyboardModifier.{Qt.KeyboardModifier(event.modifiers()).name}), type: {event.type()} (QEvent.Type.{QEvent.Type(event.type()).name})")
                if (
                    event.key() == Qt.Key.Key_Z and
                    (event.modifiers() & ~Qt.KeyboardModifier.ShiftModifier) == Qt.KeyboardModifier.ControlModifier and
                    event.type() != QEvent.Type.KeyRelease
                ):
                    # Place cursor at end of the field if Ctrl+Z or Ctrl+Shift+Z is pressed
                    # and everything is selected.
                    # This works around the selectAll()+insert() leaving everything selected in the undo state
                    # when accepting a suggestion.

                    def place_cursor_at_end():
                        # print("Text matches selection?", self.destinationEdit.selectedText() == self.destinationEdit.text(),
                        #     "Text:", self.destinationEdit.text(),
                        #     "Selected text:", self.destinationEdit.selectedText(),
                        #     "Cursor position:", self.destinationEdit.cursorPosition(),
                        #     "Selection start:", self.destinationEdit.selectionStart(),
                        #     "Selection end:", self.destinationEdit.selectionEnd(),
                        #     "Selection length:", self.destinationEdit.selectionLength(),
                        #     "Text length:", len(self.destinationEdit.text()))

                        # if self.destinationEdit.selectedText() == self.destinationEdit.text():
                        if self.destinationEdit.selectionLength() == len(self.destinationEdit.text()):
                            # print("Placing cursor at end of destinationEdit.")
                            self.destinationEdit.end(False)

                    QTimer.singleShot(0, place_cursor_at_end)  # pyright: ignore[reportUnknownMemberType]

            return super(QLineEdit, self.destinationEdit).event(event)

        self.destinationEdit.event = handle_destination_edit_event

        # Keep the destinationEdit input field focused if you click on the suggestions list widget.
        self.suggestionsListWidget.setFocusProxy(self.destinationEdit)

    def event(self, event: QEvent | None) -> bool:
        if isinstance(event, QKeyEvent):
            # print(f"Key event: {event.key()} (Qt.Key.{Qt.Key(event.key()).name}), modifiers: {event.modifiers()} (Qt.KeyboardModifier.{Qt.KeyboardModifier(event.modifiers()).name}), type: {event.type()} (QEvent.Type.{QEvent.Type(event.type()).name})")
            # If Tab is pressed, accept the current suggestion
            # This has to be handled specially because Tab is handled specially by Qt
            # and doesn't propagate to the keyPressEvent handler.
            # There may be a much cleaner way to do this. Who knows!
            if event.key() == Qt.Key.Key_Tab and event.type() == QEvent.Type.ShortcutOverride:
                self.accept_suggestion()
                return True
            # elif event.key() == Qt.Key.Key_Z and event.modifiers() == Qt.KeyboardModifier.ControlModifier: # and event.type() == QEvent.Type.ShortcutOverride:
            #     # Place cursor at end of the field
            #     print("Ctrl+Z pressed, placing cursor at end of destinationEdit.")
            #     self.destinationEdit.setCursorPosition(len(self.destinationEdit.text()))

        return super(MainWindow, self).event(event)

    # Argument is named generically as `a0` in PyQt6, hence the "incompatibility"
    # Also the event type is Optional. I don't know why yet.
    def keyPressEvent(self, event: QKeyEvent) -> None:  # pyright: ignore[reportIncompatibleMethodOverride]
        """Handle key presses."""
        key = event.key()
        # print(f"Key pressed: {key} (Qt.Key.{Qt.Key(key).name})")
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
                # Don't use text() because it will include the HTML from match_highlights
                # (not to mention we might want it to display a relative path)
                new_text = str(label.property("suggestion").path) + os.path.sep
                # Instead of self.destinationEdit.setText, which will erase undo history,
                # use the QTextCursor API to set the text in an undoable way.
                # ...textCursor method doesn't seem to exist on QLineEdit...

                # cursor = self.destinationEdit.textCursor()
                # cursor.joinPreviousEditBlock()
                # cursor.setPosition(0, QTextCursor.MoveAnchor)
                # cursor.setPosition(len(new_text), QTextCursor.KeepAnchor)
                # cursor.removeSelectedText()
                # cursor.insertText(new_text)
                # cursor.endEditBlock()

                # This works, although when you undo, text is selected that you didn't select.
                # I've worked around that by deselecting when you press Ctrl+Z if everything is selected.
                # (See handle_destination_edit_event.)
                self.destinationEdit.selectAll()
                # self.destinationEdit.clear()  # would create an unnecessary undo step with the field empty
                self.destinationEdit.insert(new_text)



    def move_files(self):
        """Move selected files to the target directory, and exit if successful."""
        destination = self.destinationEdit.text().strip()
        if not destination:
            # There's a potential UX issue if you want to move files to the root of the configured destination scope.
            # Right now I guess it'll just give you this error message.
            QMessageBox.warning(self, "Warning", "Please specify a destination directory.")
            return
        if not os.path.exists(destination):
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

        self.record_move(self.payload, destination)

        # TODO: Can we do this atomically?
        # Or make this more flexible, like prompt to undo, retry, skip, or (if applicable) overwrite
        # (Would be easier if we could reuse a file manager / OS dialog for this, either with an API or desktop automation.)
        for file in self.payload:
            try:
                shutil.move(file, destination)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to move '{file}' to '{destination}': {e}")

        self.close()

    def update_suggestions(self):
        """Update the suggestions list based on the destination directory input."""
        suggestions = get_completions(self.destinationEdit.text(), self.destination_scope)
        # TODO: icons/styling for directories to be created, AI suggestions
        self.suggestionsListWidget.clear()
        self.suggestionsListWidget.clear()
        for suggestion in suggestions:
            text = suggestion.display_text
            html = ""
            last_idx = 0
            for start, end in suggestion.match_highlights:
                html += escape(text[last_idx:start])
                html += f"<span style='background-color: rgba(255, 255, 0, 0.5); font-weight: bold'>{escape(text[start:end])}</span>"
                last_idx = end
            html += escape(text[last_idx:])
            label = QLabel()
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setText(html)
            label.setToolTip(str(suggestion.path) + "\n\nSort info (for debugging):\n" + repr(suggestion.sort_info))
            label.setProperty("suggestion", suggestion)
            # label.setStyleSheet("QLabel { padding: 2px; }")  # this doesn't expand the label size, so it doesn't work
            item = QListWidgetItem()
            self.suggestionsListWidget.addItem(item)
            self.suggestionsListWidget.setItemWidget(item, label)
        self.suggestionsListWidget.setCurrentRow(0)

    def record_move(self, files: list[str], destination: str):
        """Record the move operation for the History menu."""
        settings = QSettings('Isaiah Odhner', 'Quick Move')
        moves = settings.value('recentMoves', [])

        moves.insert(0, {
            'files': files,
            'destination': destination,
        })
        del moves[MAX_HISTORY:]

        settings.setValue('recentMoves', moves)

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                widget.updateHistoryActions()

    def updateHistoryActions(self):
        settings = QSettings('Isaiah Odhner', 'Quick Move')
        moves = settings.value('recentMoves', [])

        numRecentMoves = min(len(moves), MAX_HISTORY)

        for i in range(numRecentMoves):
            text = moves[i]['destination']
            if i < 9:
                text = f"&{i + 1} {text}"
            self.historyActions[i].setText(text)
            self.historyActions[i].setData(moves[i])
            self.historyActions[i].setVisible(True)

        for j in range(numRecentMoves, MAX_HISTORY):
            self.historyActions[j].setVisible(False)

        # self.separatorAct.setVisible((numRecentMoves > 0))

    def historyItemClicked(self):
        """Show a dialog with options to undo the move or open the destination directory."""
        action = cast(QAction, self.sender())
        move = cast(dict[str, str|list[str]], action.data())

        # TODO: ensure destination label is fully readable, with scrollbar if necessary

        # Should it close the dialog after undoing the move or opening the destination?
        # or gray out the move button (now implemented), maybe both buttons, after undoing the move?
        # I don't know, there's a lot of design possibilities here.
        # If you undo the move, you might want to open the SOURCE directory to see the files,
        # but this may actually be MULTIPLE directories; or you may want to REDO the move.
        # You may even want to REDO the move without undoing it first, re-applying it with new files (recreated from some process).
        # And in any case, some of the files or folders may have been moved or deleted externally,
        # or failed to move (either existing in the destination, which could lead to confusion when trying to undo, or due to other errors),
        # so there's a lot of situations to consider.
        # We should probably include more information in the history, like which files moved successfully or failed,
        # and what directories were created if any, in order to free up the design, and make it easier to present a fuller picture.
        # I'm also considering a sort of two pane layout with source and destination,
        # with "<- Undo" and "Redo ->" buttons, and "Open Source Directories" and "Open Destination Directory" buttons,
        # with two text areas showing which files are currently in either folder (usually one or the other, but both in the case of partial failure)

        dialog: QDialog = uic.loadUi(RECENT_MOVE_UI_FILE)  # type: ignore
        dialog.setWindowTitle("Recent Move")
        dialog.movedFilesTextBrowser.setText("\n".join(move['files']))  # type: ignore
        dialog.destinationLabel.setText(f"Destination: {move['destination']}")  # type: ignore
        def undo_and_disable():
            self.undoMove(move)
            dialog.undoMoveButton.setDisabled(True)  # type: ignore
        dialog.undoMoveButton.clicked.connect(undo_and_disable)  # type: ignore
        dialog.openDestinationButton.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(cast(str, move['destination']))))  # type: ignore
        dialog.exec()

    def undoMove(self, move: dict[str, str|list[str]]):
        """Undo a move operation by moving the files back to their original locations."""
        # TODO: Can we do this atomically?
        # Or make this more flexible, like prompt to undo, retry, skip, or (if applicable) overwrite
        # (Would be easier if we could reuse a file manager / OS dialog for this, either with an API or desktop automation.)
        # TODO: can we type check this better? values have different types depending on the key... TypedDict?
        files = cast(list[str], move['files'])
        destination = cast(str, move['destination'])
        for original_path in files:
            path_in_destination = os.path.join(destination, os.path.basename(original_path))
            try:
                shutil.move(path_in_destination, original_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to move file '{path_in_destination}' back to '{original_path}': {e}")

        # Remove the move from the history
        # Not sure this is a good idea, might be better to mark it as undone instead.
        settings = QSettings('Isaiah Odhner', 'Quick Move')
        moves = settings.value('recentMoves', [])
        moves = [m for m in moves if m != move]
        settings.setValue('recentMoves', moves)

        for widget in QApplication.topLevelWidgets():
            if isinstance(widget, MainWindow):
                widget.updateHistoryActions()

    def clearHistory(self):
        """Clear the history of recent moves."""
        # In the future this might mention how this history can be used for improving suggestions, as well as undoing moves.
        if QMessageBox.question(self, "Clear History", "Are you sure you want to clear the history of recent moves?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
            return
        settings = QSettings('Isaiah Odhner', 'Quick Move')
        settings.setValue('recentMoves', [])
        self.updateHistoryActions()

    def show_about(self):
        """Show the about dialog."""
        dialog: QDialog = uic.loadUi(ABOUT_UI_FILE)  # type: ignore
        dialog.version_label.setText(f"{__version__}")  # type: ignore
        dialog.exec()

def main():
    """Run the application. This is defined in `setup.cfg` as the entry point for the `quick-move` command."""

    # Allow Ctrl+C to exit the application. Qt doesn't handle interrupts by default.
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)

    # I want to move files to ~/Sync (syncthing default folder), mainly, for now.
    # TODO: persistent destination scope config that you can change easily, perhaps with the Home key (using the same destination input field)
    destination_scope = os.path.expanduser('~/Sync/')
    if not os.path.exists(destination_scope):
        destination_scope = os.path.expanduser('~/')
    # Normalize to native path separators (/ on Linux, \ on Windows)
    destination_scope = os.path.abspath(destination_scope) + os.path.sep

    # Get payload from command line arguments
    payload = sys.argv[1:] if len(sys.argv) > 1 else []
    # Get selection with desktop automation
    if payload and payload[0] == '--from-clipboard':
        payload = get_selected_files()

    window = MainWindow(payload, destination_scope)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
