import os
import sys

from PyQt6.QtWidgets import QMessageBox

from quick_move.helpers import waitForPaste

def get_selected_files() -> list[str]:
    """
    Get the currently selected files in the file manager.

    Note that this function currently may exit the process.
    Also it assumes QApplication is running, in order to show an error message box.
    TODO: improve this error handling.
    """
    import pyperclip
    original_clipboard = pyperclip.paste()
    # Clear the clipboard in order to wait for it to be populated (even if the same data is copied that was there originally).
    pyperclip.copy('')

    if os.name == 'nt':
        import keyboard
        # keyboard.send('ctrl+x')
        keyboard.send('ctrl+shift+c')  # Copy As Path in Windows Explorer
    else:
        # import keyboard
        # keyboard.send('ctrl+x')
        # Instead of keyboard, use xdotool to avoid needing root permissions
        import subprocess
        subprocess.run(['xdotool', 'key', '--clearmodifiers', 'ctrl+x'], check=True)
    # This may look like a race condition, where if the clipboard is updated before we start waiting for it to change, it will not be detected.
    # However, waitForPaste does not compare against a snapshot of the clipboard, it waits for a non-empty clipboard.
    # We should get the new clipboard content even if it's already changed before calling waitForPaste.
    # We just have to make sure to empty the clipboard before attempting to copy the selection.
    try:
        new_clipboard = waitForPaste(timeout=5)
    except pyperclip.PyperclipTimeoutException as e:
        # Show a message box and exit
        pyperclip.copy(original_clipboard)
        message = f"Error: {e}\n\nThe program may not have permission to send keyboard events to Windows Explorer."
        print(message)
        QMessageBox.critical(None, "Quick Move", message)
        sys.exit(1)

    pyperclip.copy(original_clipboard)

    if new_clipboard == '':
        payload = []
    else:
        # Need to handle splitting, quoting, and escaping according to the OS and file manager
        # Windows Explorer (with Ctrl+Shift+C) copies paths separated by newlines, surrounded by double quotes.
        # Windows Explorer (with Ctrl+C or Ctrl+X) copies paths separated by spaces, unquoted. Spaces are ambiguous, so this is not suitable.
        # Thunar (with Ctrl+C or Ctrl+X) copies paths separated by newlines, unquoted.
        payload = new_clipboard.splitlines()
        # TODO: handle escaping? What would be escaped?
        # Since paths are absolute, double quotes can't appear at the START of a path unless the path is quoted.
        # However, a path can END with a double quote that is part of the file name.
        # Also, we only want to strip ONE double quote at the start and end of the path, if it's quoted, otherwise we might remove a quote that is part of the file name.
        # payload = [file.strip('"') for file in payload] ; naive
        payload = [file[1:-1] if file.startswith('"') and file.endswith('"') else file for file in payload]

    return payload
