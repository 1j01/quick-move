"""Entry point for the Quick Move application."""

import os.path
import signal
import sys

from PyQt6.QtWidgets import QApplication

from quick_move import __version__
from quick_move.main_window import MainWindow
from quick_move.desktop_automation import get_selected_files


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
    # and handle DOS-style short filenames and symbolic links.
    # (not sure if resolving symlinks is necessary / a good idea)
    destination_scope = os.path.realpath(destination_scope) + os.path.sep

    # Get payload from command line arguments
    payload = sys.argv[1:] if len(sys.argv) > 1 else []
    # Get selection with desktop automation
    if payload and payload[0] == '--from-clipboard':
        payload = get_selected_files()

    # Handle DOS-style short filenames and symbolic links.
    # (Not sure if resolving symlinks is necessary / a good idea,
    # but handling DOS-style short filenames is important for long paths
    # on Windows, and realpath() does both.)
    payload = [os.path.realpath(p) for p in payload]

    window = MainWindow(payload, destination_scope)
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
