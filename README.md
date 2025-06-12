# <img src="src/quick_move/folder-with-arrow.svg" height="32"> Quick Move

Quickly move files by typing where you want them to go.

The fastest workflow for reorganizing thousands of files.

- [x] Move files to a folder by typing its name
- [x] Fuzzy folder name completion
- [x] Create folders on the fly
- [ ] AI suggestions for where to move files
  - [ ] Looks at destination folder (configured scope) structure as well as a history of recent moves
  - [ ] Looks at file names and contents
- [ ] Works with any file manager via a global hotkey
  - [x] Experimental desktop automation with a flag `quick-move --from-clipboard` which triggers <kbd>Ctrl+X</kbd> or <kbd>Ctrl+Shift+C</kbd> and reads the clipboard to get the selected files
- [x] File manager integration (e.g. Nautilus, Nemo, Thunar, Dolphin, etc.) for a window-local hotkey
  - [x] Tested with Thunar, should work with others, as long as you can set a custom action to run `quick-move` with the selected files as arguments
  - [x] AutoHotKey wrapper script to integrate with Windows Explorer
- [x] Limit destination suggestions to a specific folder
  - currently hard-coded to the home directory, or if present `~/Sync` (default Syncthing folder)
- [ ] Move history
  - [ ] Undo recent moves from a list
  - [ ] Open the destination folder of a move
  - [ ] Default destination input to the last used folder (or include it as a suggestion)
  - [ ] Option to clear the history

## Bugs and Issues

If you encounter any bugs or issues with the app, please report them in the [Issues section](https://github.com/1j01/quick-move/issues) of the project on GitHub.

Known issues:
- Pressing Enter will always accept a suggestion, even if you want to create a new folder, or use the currently typed path. You can only create a new folder if nothing matches.
- If you want to move files to the root of the configured destination scope, right now I guess it'll say "Please specify a destination directory."
  I haven't needed to do this yet, and haven't tried it.
- (If you press the shortcut in Thunar with nothing selected, it will consider the current directory as the selected item. This is not a bug, but it may be unexpected. There doesn't seem to be a way in Thunar to disable the custom action if nothing is selected, while still allowing it on folders.)
- **Experimental**: `quick-move --from-clipboard` may go haywire and spam Ctrl+Z instead of pressing Ctrl+X once; this may just be a bad interaction between xdotool and Synergy, though.

## License

Copyright © 2025 Isaiah Odhner

This project is licensed under the GNU General Public License, version 3. See [`LICENSE.txt`](https://github.com/1j01/quick-move/blob/main/LICENSE.txt) for more information.

## Development

- Clone the repository, and `cd` into it.
- Create a virtual environment with `python -m venv .venv`
- Activate the virtual environment with `source .venv/bin/activate` or on Windows `.venv/Scripts/activate` (without `source`)
- Install dependencies with `pip install -r requirements.txt`
- Install `quick-move` with `pip install -e .`
- Run the app with `quick-move`
- Optionally, expose the CLI globally (i.e. outside the virtual environment) with `link_cli_globally.sh`; this is useful for testing integration with file managers, or global hotkeys
  - This script is tested on Linux, as well as Windows with Git Bash. It may not work when run from a different shell, such as PowerShell or Command Prompt on Windows.

A VS Code launch configuration is included for debugging. Press F5 to run the app in debug mode.

The app is built with PyQt6. Qt Designer is used to scaffold the UI with drag and drop. It edits `.ui` files, which are then loaded by a widget class.
I hear there's also a way to compile `.ui` files to Python code.

To avoid version conflicts, you may want to install `pyqt6-tools` (which includes Qt Designer) outside of the virtual environment. This may need to change if it's used for compiling `.ui` files in the future, but for now it's not included as a dependency, and the version of `pyqt6` is not set to match it.

Run tests with:
```bash
pytest -vv
```
or continuously with:
```bash
pytest-watch -- -vv
```

