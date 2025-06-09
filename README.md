# Quick Move

Quickly move files by typing where you want them to go.

The fastest workflow for reorganizing thousands of files.

- [x] Move files to a folder by typing its name
  - technically works... but need to improve matching/autocomplete for this tool to be useful
- [ ] Fuzzy folder name completion
- [ ] Create folders on the fly
- [ ] AI suggestions for where to move files
  - [ ] Looks at destination folder (configured scope) structure as well as a history of recent moves
  - [ ] Looks at file names and contents
- [ ] Works with any file manager via a global hotkey
  - [x] Experimental desktop automation with a flag `quick-move --from-clipboard` which triggers <kbd>Ctrl+X</kbd> and reads the clipboard to get the selected files
- [x] File manager integration (e.g. Nautilus, Nemo, Thunar, Dolphin, etc.) for a window-local hotkey
  - [x] Tested with Thunar, should work with others, as long as you can set a custom action to run `quick-move` with the selected files as arguments
- [x] Limit destination suggestions to a specific folder
  - currently hard-coded to the home directory, or if present `~/Sync` (default Syncthing folder)
- [ ] Undo recent moves from a list
  - [ ] A way to clear the history

## Bugs and Issues

If you encounter any bugs or issues with the app, please report them in the [Issues section](https://github.com/1j01/quick-move/issues) of the project on GitHub.

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
- Expose the CLI globally with `link_cli_globally.sh` (tested on Linux; includes some half-hearted Windows support which presumably doesn't work)

A VS Code launch configuration is included for debugging. Press F5 to run the app in debug mode.

The app is built with PyQt6. Qt Designer is used to scaffold the UI with drag and drop. It edits `.ui` files, which are then loaded by a widget class.
I hear there's also a way to compile `.ui` files to Python code.

Run tests with:
```bash
pytest -vv
```
or continuously with:
```bash
pytest-watch -- -vv
```

