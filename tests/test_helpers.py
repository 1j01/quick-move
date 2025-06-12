import pytest
from quick_move.helpers import merge_ranges

@pytest.mark.parametrize("input_ranges, expected_output", [
    ([], []),  # empty input
    ([(1, 2)], [(1, 2)]),  # single range
    ([(0, 0)], [(0, 0)]),  # single empty range
    ([(1, 2), (3, 4)], [(1, 2), (3, 4)]),  # non-overlapping
    ([(1, 3), (2, 5)], [(1, 5)]),  # overlapping
    ([(1, 2), (2, 4)], [(1, 4)]),  # adjacent
    ([(5, 6), (1, 2), (2, 4)], [(1, 4), (5, 6)]),  # unsorted input
    ([(1, 5), (2, 3)], [(1, 5)]),  # range fully contained within another
    ([(1, 4), (2, 6), (8, 10), (9, 12)], [(1, 6), (8, 12)]),  # multiple merges
    ([(1, 4), (5, 5)], [(1, 4), (5, 5)]),  # non-overlapping with empty range
    ([(1, 1), (1, 2)], [(1, 2)]),  # zero-length range adjacent before
    ([(1, 2), (2, 2)], [(1, 2)]),  # zero-length range adjacent after
    ([(1, 3), (2, 2), (4, 5)], [(1, 3), (4, 5)]),  # zero-length range in the middle
    ([(1, 10), (2, 3), (4, 5), (6, 7)], [(1, 10)]),  # multiple ranges within a larger range
    ([(1, 3), (1, 3), (1, 3)], [(1, 3)]),  # duplicate ranges
    ([(1, 1), (1, 1), (1, 1)], [(1, 1)]),  # duplicate empty ranges
])
def test_merge_ranges(input_ranges: list[tuple[int, int]], expected_output: list[tuple[int, int]]):
    result = merge_ranges(input_ranges)
    assert result == expected_output
