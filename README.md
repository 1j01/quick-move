# Quick Move

Quickly move files by typing where you want them to go.

The fastest workflow for reorganizing thousands of files.

- [ ] Move files to a folder by typing its name
- [ ] Fuzzy folder name completion
- [ ] Create folders on the fly
- [ ] AI suggestions for where to move files
- [ ] Works with any file manager via a global hotkey
- [ ] File manager integration (e.g. Nautilus, Nemo, Thunar, Dolphin, etc.) for a window-local hotkey

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

