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

from pathlib import Path

import pytest
from pyfakefs.fake_filesystem import FakeFilesystem, OSType
from pyfakefs.fake_filesystem_unittest import Patcher

from quick_move.completer import get_completions
from quick_move.helpers import tree
from tests import accept


# The "accept" module provides an --update-expected option to pytest to update expected results within tests.
# It needs to modify the test files, so it shouldn't use the fake filesystem.
# This fixture sets up a fake filesystem for testing, excluding the "accept" module.
@pytest.fixture
def my_fs():
    with Patcher(additional_skip_names=[accept]) as patcher:
        yield patcher.fs

@pytest.fixture
def my_fs_1(my_fs: FakeFilesystem):
    my_fs.os = OSType.LINUX
    my_fs.create_dir("/home/io/Sync")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_dir("/home/io/Sync/Misc")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_file("/home/io/Sync/Project Stuff/Tiamblia/file1.txt", contents="Content of file1")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_file("/home/io/Sync/Project Stuff/OtherProject/file2.txt", contents="Content of file2")  # pyright: ignore[reportUnknownMemberType]
    my_fs.create_file("/home/io/Sync/Misc/file3.txt", contents="Content of file3")  # pyright: ignore[reportUnknownMemberType]

    print("Created test filesystem with structure:")
    for line in tree(Path("/")):
        print(line)

    yield my_fs


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
# - overlapping matches:
#   - "IsaiahOdhner\ia" should match "C:\Users\IsaiahOdhner\Sync\Project Stuff\Tiamblia" before "C:\Users\IsaiahOdhner\Sync\Project Stuff\OtherProject"
#     even though "ia" is in "IsaiahOdhner" and could conceivably be merged into a single match range
#   - "IsaiahOdhner\er" should match "C:\Users\IsaiahOdhner\Sync\Project Stuff\OtherProject" before "C:\Users\IsaiahOdhner\Sync\Project Stuff\Tiamblia"
#     even though "er" is in "IsaiahOdhner" and could conceivably be merged into a single match range
#   - implementation might mean keeping looking for matches until one is found that would extend the match range
#     (preferably disjoint from existing ranges, but falling back to overlapping ranges that still add new overall character coverage?)
#     (and maybe still falling back to completely overlapping ranges, if range count contributes to prioritization...
#      but wait, it currently contributes negatively to prioritization, to penalize discontiguity, but maybe in this case (overlapping matches) it should contribute positively?
#      idk maybe it should be neutral in this case; maybe the prioritization should count the merged ranges instead of individual matches;
#      I'd have to see some real cases, but I think it should be neutral, since if something is already matched, if you type something that also matches it,
#      you're probably trying to match something else)

# TODO: Maybe special ignore rules for:
# - long hexadecimal strings, which may contain a lot of tiny matches that are not meaningful
# - hidden folders (e.g. .git, .svn, etc.)
# - common "bloat" folders like "node_modules" and other package directories
# - maybe follow gitignore rules, where present
# - (these should still be matched if the user explicitly types them, but can be deprioritized in suggestions)

# TODO: Test completions for adding paths, where part of the input is fuzzy, but part is user-defined folders to create.
# e.g. "prjstff/New Project" should suggest "Project Stuff/New Project" since "prjstff" is a good match for an existing folder,
# but "New Project" isn't.

def test_exact_path_prefix_1(my_fs_1: FakeFilesystem):
    # Exact folder paths (with or without trailing slash)
    expect_completions(my_fs_1, "/home/io/Sync/", [
        # Top-down, alphabetical ordering
        "/home/io/Sync/Misc",
        "/home/io/Sync/Project Stuff",
        "/home/io/Sync/Project Stuff/OtherProject",
        "/home/io/Sync/Project Stuff/Tiamblia",
    ])

def test_exact_path_prefix_2(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "/home/io/Sync/Project Stuff", [
        "/home/io/Sync/Project Stuff/OtherProject",
        "/home/io/Sync/Project Stuff/Tiamblia",
    ])

def test_exact_path_prefix_3(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "/home/io/Sync/Project Stuff/", [
        "/home/io/Sync/Project Stuff/OtherProject",
        "/home/io/Sync/Project Stuff/Tiamblia",
    ])

# Fuzzy matching
# (These might also match subfolders)
@pytest.mark.xfail(reason="Fuzzy matching not yet implemented")
def test_fuzzy_matching_1(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "/home/io/Sync/prjstff", ["/home/io/Sync/Project Stuff"])

@pytest.mark.xfail(reason="Fuzzy matching not yet implemented")
def test_fuzzy_matching_2(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "/home/io/Sync/prjstff/", ["/home/io/Sync/Project Stuff"])

def test_fuzzy_matching_3(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "/home/io/Sync/prjstff/tiam", [
        "/home/io/Sync/Project Stuff/Tiamblia",
        "/home/io/Sync/Project Stuff",
        "/home/io/Sync/Project Stuff/OtherProject",
        "/home/io/Sync/Misc",
    ])

def test_fuzzy_matching_4(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "/home/io/Sync/tiam", [
        "/home/io/Sync/Project Stuff/Tiamblia",
        "/home/io/Sync/Misc",
        "/home/io/Sync/Project Stuff",
        "/home/io/Sync/Project Stuff/OtherProject",
    ])

@pytest.mark.xfail(reason="Currently gives absolute paths always")
def test_relative_path_stays_relative(my_fs_1: FakeFilesystem):
    expect_completions(my_fs_1, "tiam", ["Project Stuff/Tiamblia"])

def expect_completions(my_fs: FakeFilesystem, input_path: str, expected: list[str]):
    completions = get_completions(input_path, "/home/io/Sync/")
    result = [completion.display_text for completion in completions]
    assert result == expected, f"Expected {expected} but got {result} for input '{input_path}'"
