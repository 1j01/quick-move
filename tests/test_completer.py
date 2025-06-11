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

import pytest
from quick_move.completer import get_completions

# TODO: Actually test relative paths instead of concatenating a temporary path with the input path.
# Might need a proper FS mock. Or to abstract the core algorithm away from the filesystem.

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
def test_get_completions(input_path: str, expected: list[str], tmp_path_factory: pytest.TempPathFactory):
    # Create a temporary directory structure for testing
    tmp_path = tmp_path_factory.mktemp("test_completer")
    (tmp_path / "home").mkdir()
    (tmp_path / "home" / "io").mkdir()
    (tmp_path / "home" / "io" / "Sync").mkdir()
    scope_path = tmp_path / "home" / "io" / "Sync"
    (scope_path / "Project Stuff").mkdir()
    (scope_path / "Project Stuff" / "Tiamblia").mkdir()
    (scope_path / "Project Stuff" / "OtherProject").mkdir()
    (scope_path / "Misc").mkdir()
    (scope_path / "Project Stuff" / "Tiamblia" / "file1.txt").write_text("Content of file1")
    (scope_path / "Project Stuff" / "OtherProject" / "file2.txt").write_text("Content of file2")
    (scope_path / "Misc" / "file3.txt").write_text("Content of file3")

    completions = get_completions(scope_path.as_posix() + input_path, scope_path.as_posix())
    result = [completion.display_text for completion in completions]
    assert result == expected, f"Expected {expected} but got {result} for input '{input_path}'"
