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
from quick_move.completer import list_dir_for_completion

@pytest.mark.parametrize("input_path, expected", [
    ("/home/io/Sync/", ["Project Stuff", "OtherProject"]),
    ("/home/io/Sync/Project Stuff", ["Tiamblia", "readme.txt"]),
    ("/home/io/Sync/Project Stuff/", ["Tiamblia", "readme.txt"]),
    ("/home/io/Sync/prjstff", ["Project Stuff", "OtherProject"]),
    ("/home/io/Sync/prjstff/", ["Project Stuff", "OtherProject"]),
    ("/home/io/Sync/prjstff/tiam", ["Tiamblia"]),
    ("/home/io/Sync/tiam", ["Project Stuff"]),
    ("tiam", ["Project Stuff/Tiamblia"])
])
def test_list_dir_for_completion(input_path, expected):
    result = list_dir_for_completion(input_path)
    assert result == expected, f"Expected {expected} but got {result} for input '{input_path}'"
