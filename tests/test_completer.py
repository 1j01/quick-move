# - Input is "/home/io/Sync/"
#   - Should list contents of that folder for completion
# - Input is "/home/io/Sync/Project Stuff"
#   - Should list contents of that folder for completion
# - Input is "/home/io/Sync/Project Stuff/"
#   - Should list contents of that folder for completion
# - Input is "/home/io/Sync/prjstff"
#   - Should suggest Project Stuff first, and other contents of Sync folder
# - Input is "/home/io/Sync/prjstff/"
#   - Should suggest Project Stuff first, and other contents of Sync folder
#   - Or maybe should implicitly accept Project Stuff and start autocompleting stuff within it
#   - Maybe even update the input field?? but probably not
# - Input is "/home/io/Sync/prjstff/tiam"
#   - Should suggest Project Stuff/Tiamblia
# - Input is "/home/io/Sync/tiam"
#   - Should suggest Project Stuff/Tiamblia
# - Input is "tiam"
#   - Should suggest Project Stuff/Tiamblia, keeping the input field relative to the destination scope of "/home/io/Sync/" (which will be changeable and persistent)

import os
from pathlib import Path

import pyfakefs
import pyfakefs.fake_filesystem
import pytest
from pyfakefs.fake_filesystem_unittest import Patcher

from quick_move.completer import get_completions
from quick_move.helpers import tree
from tests import accept


@pytest.fixture
def my_fs():
    with Patcher(additional_skip_names=[accept]) as patcher:
        yield patcher.fs


# TODO: Test that crumbs that match exactly are consumed (special handling of prefixes that are real directories).
# Take this with a grain of salt as I'm probably mixing some things up here, but:
# - the input path (i.e. "/real/dir/foo" shouldn't match "/foo/real/dir" IF /real/dir exists; otherwise it should match)
# - the input path (i.e. for search "/real/dir/foo", it shouldn't highlight the second "dir" in "/real/dir/dir" as a match)
# - the fs paths (i.e. for search "/real/dir/dir", it shouldn't highlight the first "dir" in "/real/dir/foo" as a match because it's already matched)
# - it shouldn't sort "/some/dir/boring-dir" above "/some/dir/blah" for search "/some/dir" just because "dir" appears twice
#   - or highlight the "s" in "C:\Users\..." for every path for a search "foo/s"

# TODO: Test ~/ ~user/ and maybe even %USERPROFILE% expansions, although the latter is less likely to be typed by a user.

# TODO: Test prioritization, e.g.
# - total matched characters
# - larger contiguous matches:
#   - "foobar" should match "foobar" before "foo/bar" or "foo bar"
#   - "foo/bar" should match "foo/bar" before "foobar" or "foo bar"
# - match ordering:
#   - "prjstff/foo" should match "Project Stuff/Foobar" before "Foobar/Project Stuff"
#   - "foo/prjstff" should match "Foobar/Project Stuff" before "Project Stuff/Foobar"

# TODO: Maybe special ignore rules for:
# - long hexadecimal strings, which may contain a lot of tiny matches that are not meaningful
# - hidden folders (e.g. .git, .svn, etc.)
# - common "bloat" folders like "node_modules" and other package directories
# - maybe follow gitignore rules, where present
# - (these should still be matched if the user explicitly types them, but can be deprioritized in suggestions)

@pytest.mark.parametrize("input_path, expected", [
    # Exact folder paths (with or without trailing slash)
    ("/home/io/Sync/", ["/home/io/Sync/Project Stuff", "/home/io/Sync/Misc"]),
    ("/home/io/Sync/Project Stuff", ["/home/io/Sync/Project Stuff/Tiamblia", "/home/io/Sync/Project Stuff/OtherProject"]),
    ("/home/io/Sync/Project Stuff/", ["/home/io/Sync/Project Stuff/Tiamblia", "/home/io/Sync/Project Stuff/OtherProject"]),
    # Fuzzy matching
    ("/home/io/Sync/prjstff", ["/home/io/Sync/Project Stuff"]),
    ("/home/io/Sync/prjstff/", ["/home/io/Sync/Project Stuff"]),
    ("/home/io/Sync/prjstff/tiam", ["/home/io/Sync/Project Stuff/Tiamblia"]),
    ("/home/io/Sync/tiam", ["/home/io/Sync/Project Stuff/Tiamblia"]),
    # Relative path stays relative
    ("tiam", ["Project Stuff/Tiamblia"])
])
def test_get_completions(input_path: str, expected: list[str], my_fs: pyfakefs.fake_filesystem.FakeFilesystem):
    # Create a temporary directory structure for testing
    my_fs.create_dir("/home/io/Sync")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_dir("/home/io/Sync/Misc")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_file("/home/io/Sync/Project Stuff/Tiamblia/file1.txt", contents="Content of file1")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_file("/home/io/Sync/Project Stuff/OtherProject/file2.txt", contents="Content of file2")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_file("/home/io/Sync/Misc/file3.txt", contents="Content of file3")  # pyright: ignore[reportUnknownMemberType]

    print("Created test filesystem with structure:")
    for line in tree(Path("/")):
        print(line)

    if os.name == 'nt':
        def normalize_path(path: str) -> str:
            # print(f"Normalizing path: {path}, is_absolute: {Path(path).is_absolute()}")
            # if Path(path).is_absolute():
            # ugh, Path(path).is_absolute() is False for paths like "/home/io/Sync/" on Windows
            # because the only thing that makes a path absolute on Windows is a drive letter (or maybe UNC path or whatever, but it doesn't do what I want is the point)
            if path.startswith("/"):
                path = f"C:{path}"
            return path.replace("/", "\\")
        input_path = normalize_path(input_path)
        expected = [normalize_path(path) for path in expected]

    completions = get_completions(input_path, "/home/io/Sync/")
    result = [completion.display_text for completion in completions]
    assert result == expected, f"Expected {expected} but got {result} for input '{input_path}'"
