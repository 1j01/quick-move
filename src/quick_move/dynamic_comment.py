#!/usr/bin/env python3
"""Adds/updates generated comments in source files at runtime."""

import atexit
import inspect
import re
from collections import defaultdict

special_comment_delimiter = "#<#"
"""Denotes a generated comment, and is used to replace the comment."""

replacements: dict[str, list[tuple[range, str]]] = defaultdict(list)
"""Maps file paths to a list of line ranges and their replacement content."""

modified_files: set[str] = set()
"""File paths that have been modified by this module."""

def generate_comment(new_comment_content: str, *, above: bool = True, stack_depth: int = 1, trim: bool = True):
    """
    Insert or replace a comment above (or below) the call site, once the program exits.

    Comment syntax does not need to be included in the passed string.
    A special comment delimiter will be used to identify the comment
    as generated, and only a generated comment will be replaced.

    `stack_depth` is the number of stack frames to look above for the call site.
    This allows for composition. You can define a function that calls `generate_comment`,
    and pass `stack_depth=2` to generate the comment at the call site of that function,
    rather than the call site of `generate_comment` inside that function.
    It's recommended to add `stack_depth` as a (keyword-only) parameter of
    the function (with a default value), to allow further composition.
    """

    # Get the caller's frame and source file name
    current_frame = inspect.currentframe()
    assert current_frame is not None, "Cannot get current frame"
    caller_frame = current_frame
    for i in range(stack_depth):
        assert caller_frame.f_back is not None, f"Cannot get caller's frame (frame {i} of {stack_depth}: {caller_frame})"
        caller_frame = caller_frame.f_back
    caller_file = caller_frame.f_globals['__file__']

    # Read the entire source file
    with open(caller_file, 'r') as f:
        source_lines = f.readlines()

    # Find the function call line
    call_line = caller_frame.f_lineno
    assert isinstance(call_line, int), "Line number must be an integer"

    # Look above or below for any comment lines
    search_range = range(call_line - 2, -1, -1) if above else range(call_line, len(source_lines))
    for i in search_range:
        if not source_lines[i].lstrip().startswith(special_comment_delimiter):
            break

    # Format the comment replacement
    comment_indent = re.match(r'\s*', source_lines[call_line - 1]).group(0)  # pyright: ignore[reportOptionalMemberAccess]
    comment_line_start = f"{comment_indent}{special_comment_delimiter} "
    new_comment_content = comment_line_start + f"\n{comment_line_start}".join(new_comment_content.splitlines())
    if trim:
        new_comment_content = "\n".join(line.rstrip() for line in new_comment_content.splitlines())

    # Store the replacement
    old_comment_range = range(i + 1, call_line - 1) if above else range(call_line, i)  # pyright: ignore[reportUnboundVariable]
    replacements[caller_file].append((old_comment_range, new_comment_content))

def commit_comment_replacements(target_file: str | None = None):
    """
    Apply all comment replacements. This is called automatically when the program exits.

    This is a separate step to avoid line number conflicts.
    If files were written to immediately when generate_comment was called,
    the next call to generate_comment would have line numbers that no longer
    correspond to the source file, since the running program
    would still be using the original lines of code.

    NOTE: This still affects line numbers when the replacements are applied,
    so you may need to re-run the program to see correct line numbers
    in error messages, or to use a debugger sensibly.
    """

    for file, file_replacements in replacements.items():
        # Do not modify files that have already been modified,
        # as mismatched line numbers could lead to incorrect replacements.
        if file in modified_files:
            raise RuntimeError(f"File {file!r} has already been modified by this module")

        # Filter to just the target file, if specified.
        # Would a better default be to look at the caller's frame
        # for the target file (__file__)?
        if target_file is not None and file != target_file:
            continue

        # Read the entire source file
        with open(file, 'r') as f:
            source_lines = f.readlines()
            original_source_lines = source_lines.copy()

        # Sort the replacements by decreasing line number
        file_replacements = sorted(file_replacements, reverse=True, key=lambda x: x[0].start)

        # Merge replacements that overlap, to support
        # calling generate_comment in a loop, or multiple times on one line.
        # Only need to merge exactly matching ranges, in either case,
        # and since the list is sorted, only need to check adjacent items.
        i = 0
        while i < len(file_replacements) - 1:
            current_item = file_replacements[i]
            next_item = file_replacements[i + 1]

            if current_item[0] == next_item[0]:
                file_replacements[i] = (current_item[0], current_item[1] + "\n" + next_item[1])
                del file_replacements[i + 1]
            else:
                i += 1

        # Replace the comment lines with the new content
        for line_range, new_comment_content in file_replacements:
            source_lines[line_range.start:line_range.stop] = f"{new_comment_content}\n".splitlines(keepends=True)

        # Write the source file back out
        if tuple(source_lines) != tuple(original_source_lines):
            # first_modified_line = min(line_range.start for line_range in replacements[file])
            first_modified_line = 0
            for a, b in zip(source_lines, original_source_lines):
                if a != b:
                    # print("first modified line:", first_modified_line, repr(a), repr(b))
                    break
                first_modified_line += 1

            with open(file, 'w') as f:
                f.writelines(source_lines)

            print(f"""Updated generated comments ({special_comment_delimiter!r}) in {file!r}
Note: Line numbers in this file (after {first_modified_line}) may have changed.
You may need to re-run the program to see correct line numbers in error messages, or use a debugger.""")

            modified_files.add(file)
        replacements[file].clear()


def _exit_handler():
    """Commit all comment replacements when the program exits."""
    commit_comment_replacements()

atexit.register(_exit_handler)


if __name__ == '__main__':
    # Example usage:

    #<# This is a generated comment.
    #<# It can span multiple lines.
    generate_comment("This is a generated comment.\nIt can span multiple lines.")

    import random

    lines = random.randint(1, 10)
    #<# This is a generated comment with 3 line(s).
    #<# Line 1
    #<# Line 2
    #<# Line 3
    generate_comment(f"This is a generated comment with {lines} line(s).\n" + "\n".join(f"Line {i + 1}" for i in range(lines)))

    #<# This is a generated comment after the variable number of lines.
    #<# A random number: 0.5704587074408937
    generate_comment(f"This is a generated comment after the variable number of lines.\nA random number: {random.random()}")

    generate_comment(f"Look out below!"[0:5] + "here!", above=False)
    #<# Look here!

    for i in range(5):
        #<# Counting to five with one generate_comment call site: 1
        #<# Counting to five with one generate_comment call site: 2
        #<# Counting to five with one generate_comment call site: 3
        #<# Counting to five with one generate_comment call site: 4
        #<# Counting to five with one generate_comment call site: 5
        generate_comment(f"Counting to five with one generate_comment call site: {i + 1}")

    def generate_hello_comment(name: str, *, stack_depth: int = 2):
        """This wraps generate_comment to specialize it.

        By using `stack_depth > 1`, the comment will be generated outside this function,
        rather than next to `generate_comment()` inside this function.
        Making `stack_depth` a parameter of this function allows it to be
        used in other supporting functions.
        """
        generate_comment(f"Hello, {name}!", stack_depth=stack_depth)

    def generate_hello_world_comment(*, stack_depth: int = 3):
        """This wraps `generate_hello_comment` to further specialize it."""
        generate_hello_comment("world", stack_depth=stack_depth)

    #<# Hello, everyone!
    generate_hello_comment("everyone")

    #<# Hello, world!
    generate_hello_world_comment()


    # --------------------------------------------------------

    # I just thought of a weird edge case:

    # generate_comment("Foo!", above=False)
    #
    # generate_comment("Bar!", above=True)

    # The result is not idempotent. At first it ends up like this:

    # generate_comment("Foo!", above=False)

    # #<# Bar!
    # #<# Foo!
    # generate_comment("Bar!", above=True)

    # Then resolves to this:

    # generate_comment("Foo!", above=False)
    # #<# Foo!

    # #<# Bar!
    # generate_comment("Bar!", above=True)

    # I probably need to break out the replacement logic into a separate function,
    # in order to test this well, because modifying source code... seems hard to test.
    # I mean what would you do? I guess you could write a test that writes
    # code to a file and then executes it and checks the modified file.
    # That wouldn't be too bad, now that I think about it.
    # TODO: test & fix
    # I could also differentiate the comment delimiter for above/below.
    # Something like "#^#" for comments below, and "#v#" for comments above.
    # Or embrace Unicode and use "#↑#" and "#↓#" or similar.
    # Maybe corner arrows... ↰ ↱ ↲ ↳ ↴ ↵
    # Oh yeah, Unicode is weirdly deficient when it comes to corner arrows.
    # It doesn't have the ones I want.
    # I could use ⮡ and ⮣, but to point from the output to the source,
    # there's no arrows coming from the right. There's one from the left,
    # just to make things more confusing.
    # There's these stubby ones ⬐ ⬑ I could use.
    # But of course ASCII feels "safer"
    # (Would be cute to use ↬ if in a loop, but the only mirror (↫) is not in the right direction.)

    # --------------------------------------------------------

    # There are of course plenty of other edge cases, since it's
    # not using the AST to decide where to insert the comment.
    # For example:
    string = f"""
    #<# This is a generated comment in a string literal. Oops.
    {generate_comment("This is a generated comment in a string literal. Oops.")}
    """
    # Then again, maybe you want it in a string sometimes:
    some_complex_pattern = re.compile(rf"""
        # group 1
        (foo[0-9]+)
        # group 2
        (
            #<# Generated comment in verbose regular expression
            {generate_comment("Generated comment in verbose regular expression")}
            bar|baz
        )
    """, re.VERBOSE)

    # Multiple calls on one line works fine, because I have merging logic,
    # and it's searching for the special comments from the same line,
    # so the ranges to merge are identical, same as for one call site in a loop.
    # A happy accident!
    #<#   A
    #<#  AAA
    #<# AAAAA
    #<#   B
    generate_comment("  A\n AAA\nAAAAA"); generate_comment("  B")
    # This works fine as well:
    #<# A
    generate_comment("A"); generate_comment("B", above=False)
    #<# B
    #<# B
    generate_comment("A", above=False); generate_comment("B")
    #<# A

    # This is a weird logical construction:
    if random.random() < 0.5:
        #<# One of these will update: 0.6176558109481572
        generate_comment(f"One of these will update: {random.random()}")
    else:
        #<# One of these will update: 0.5696855573011381
        generate_comment(f"One of these will update: {random.random()}")
    # It won't remove the comment when the code path isn't taken.
    # TODO: maybe add "STALE" markings like I did for the ASCII diagram comments?
    # Of course the file will need to be processed for it to be marked,
    # and there could be scenarios where it's STALE but the file isn't run.

    # If you want to remove a generated comment conditionally,
    # you can't use an empty string currently:
    #<#
    generate_comment("")
    # TODO: maybe None should be supported to remove the comment?
    # Or an empty string should remove the comment?
    # The use case I guess would be something like `note_warnings()`
    # which would generate a comment if there were any warnings,
    # and remove the comment if there were no warnings.

    # --------------------------------------------------------

    # This is no longer needed, since it's called automatically at exit:

    # commit_comment_replacements()

    # # Committing multiple times is not allowed
    # try:
    #     commit_comment_replacements()
    # except RuntimeError as e:
    #     pass
    # else:
    #     raise Exception("Expected RuntimeError was not raised")

