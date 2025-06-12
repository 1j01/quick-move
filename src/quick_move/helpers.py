"""Utility functions."""

import time

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
