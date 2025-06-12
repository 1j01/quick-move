"""Utility functions."""

import time
from pathlib import Path
from typing import Generator

import pyperclip


# pyperclip.waitForPaste() was removed in v1.9.0, although PyperclipTimeoutException is still there.
# https://github.com/asweigart/pyperclip/issues/272
def waitForPaste(timeout: float | None = None) -> str:
    """This function call blocks until a non-empty text string exists on the
    clipboard. It returns this text.

    This function raises PyperclipTimeoutException if timeout was set to
    a number of seconds that has elapsed without non-empty text being put on
    the clipboard."""
    startTime = time.time()
    while True:
        clipboardText = pyperclip.paste()
        if clipboardText != '':
            return clipboardText
        time.sleep(0.01)

        if timeout is not None and time.time() > startTime + timeout:
            raise pyperclip.PyperclipTimeoutException('waitForPaste() timed out after ' + str(timeout) + ' seconds.')


def merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    """Merge overlapping or adjacent ranges."""

    merged_ranges: list[tuple[int, int]] = []

    for start, end in sorted(ranges):
        if not merged_ranges or merged_ranges[-1][1] < start:
            merged_ranges.append((start, end))
        else:
            merged_ranges[-1] = (merged_ranges[-1][0], max(merged_ranges[-1][1], end))

    return merged_ranges


# prefix components:
space =  '    '
branch = '│   '
# pointers:
tee =    '├── '
last =   '└── '


def tree(dir_path: Path, prefix: str='') -> Generator[str, None, None]:
    """A recursive generator, given a directory Path object
    will yield a visual tree structure line by line
    with each line prefixed by the same characters
    """
    contents = list(dir_path.iterdir())
    # contents each get pointers that are ├── with a final └── :
    pointers = [tee] * (len(contents) - 1) + [last]
    for pointer, path in zip(pointers, contents):
        yield prefix + pointer + path.name
        if path.is_dir(): # extend the prefix and recurse:
            extension = branch if pointer == tee else space
            # i.e. space because last, └── , above so no more |
            yield from tree(path, prefix=prefix+extension)
