"""Tests for the accept module, which updates expectations in tests to accept the current output.

Run with `pytest tests/test_accept.py`, or `pytest` to run all tests.
"""

from pathlib import Path
import pytest
import subprocess

CONFTEST_CONTENT = f"""
import sys
sys.path.append({str(Path(__file__).parent)!r})
import pytest
from accept import update_expected

update_expected_arg: bool = False

def pytest_addoption(parser: pytest.Parser) -> None:
    # Or should it be "--accept-actual"?
    parser.addoption("--update-expected", action="store_true", help="update `expected` variable in tests to match actual results")

@pytest.fixture(scope="session", autouse=True)
def record_update_expected_arg(pytestconfig: pytest.Config) -> None:
    global update_expected_arg
    update_expected_arg = pytestconfig.getoption("update_expected", default=False)  # type: ignore

def pytest_assertrepr_compare(op: str, left: object, right: object) -> list[str] | None:
    if update_expected_arg:
        update_expected(left)
"""


@pytest.fixture(scope="session")
def tests_folder(tmp_path_factory: pytest.TempPathFactory) -> Path:
    tests_dir = tmp_path_factory.mktemp("tests")
    conftest_file = tests_dir / "conftest.py"
    conftest_file.write_text(CONFTEST_CONTENT)
    return tests_dir

# NOTE: don't rename this "test_file" or pytest will try to run it as a test (unless fixtures are exempt I guess?)
@pytest.fixture
def tests_folder_file(request: pytest.FixtureRequest, tests_folder: Path) -> Path:
    """Gives a Path to a file in the temporary tests folder, named after the test."""
    test_name = request.node.name  # type: ignore
    return tests_folder / f"{test_name}.py"

def test_update_expected_var(tests_folder_file: Path) -> None:
    """Test that update_expected works with a variable named `expected`."""
    tests_folder_file.write_text("""
def test_something():
    expected = 1
    actual = 9001
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    expected = 9001
    actual = 9001
    assert actual == expected
"""

def test_update_correct_expected_var(tests_folder_file: Path) -> None:
    """Test that update_expected handles multiple `expected` variables and asserts."""
    tests_folder_file.write_text("""
def test_something():
    expected = 1
    actual = 1
    assert actual == expected
    expected = 2
    actual = 9001
    assert actual == expected
    expected = 3
    actual = 3
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    expected = 1
    actual = 1
    assert actual == expected
    expected = 9001
    actual = 9001
    assert actual == expected
    expected = 3
    actual = 3
    assert actual == expected
"""

@pytest.mark.xfail(reason="""The order of lines of code is used as a heuristic proxy for execution order.
Nearly all tests are linear, executing top to bottom, so this works well.
Making this robust would mean reverse-executing Python code similar to a time travel debugger, vastly complicating the system.
By contrast, handling linear code takes a single line of code.
It only needs to compare the line number of the assert to the line number of the variable.""")
def test_update_correct_expected_var_non_linear(tests_folder_file: Path) -> None:
    """Test that update_expected finds the correct variable to update within a loop."""
    tests_folder_file.write_text("""
def test_something():
    for i in range(3):
        if i == 0:
            expected = 1
        elif i == 1:
            expected = 2
        else:
            expected = 3
        actual = 9000 + i
        assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    for i in range(3):
        if i == 0:
            expected = 9000
        elif i == 1:
            expected = 9001
        else:
            expected = 9002
        actual = 9000 + i
        assert actual == expected
"""

def test_update_arbitrarily_named_var(tests_folder_file: Path) -> None:
    """Test that update_expected works with a variable identified by the assertion."""
    tests_folder_file.write_text("""
def test_something():
    expected = 1
    actual = 9001
    preferred_value = 1
    assert actual == preferred_value
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    expected = 1
    actual = 9001
    preferred_value = 9001
    assert actual == preferred_value
"""

def test_chained_assignment(tests_folder_file: Path) -> None:
    """Test that update_expected handles updating part of a line, not just whole lines."""
    tests_folder_file.write_text("""
def test_something():
    input = expected = 1
    actual = 9001
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    input = expected = 9001
    actual = 9001
    assert actual == expected
"""

def test_unpacking_assignment(tests_folder_file: Path) -> None:
    """Test that update_expected handles updating tuples unpacked in assignment."""
    tests_folder_file.write_text("""
def test_something():
    input, expected = 1, 2
    actual = 9001
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    input, expected = 1, 9001
    actual = 9001
    assert actual == expected
"""

@pytest.mark.xfail(reason="not sure if this behavior is desired")
def test_unpacking_assignment_indirect(tests_folder_file: Path) -> None:
    """Test that update_expected searches beyond an unpacking assignment."""
    tests_folder_file.write_text("""
def test_something():
    a, b, c, d, e = 1, 2, 3, 4, 5
    a, expected = 1, c
    actual = 9001
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    a, b, c, d, e = 1, 2, 9001, 4, 5
    a, expected = 1, c
    actual = 9001
    assert actual == expected
"""

def test_update_assert_directly(tests_folder_file: Path) -> None:
    """Test that update_expected can update the expression in an assert line."""
    tests_folder_file.write_text("""
def test_something():
    assert 9001 == 1
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    assert 9001 == 9001
"""

def test_update_tuple(tests_folder_file: Path) -> None:
    """Test that update_expected can update a value in a tuple."""
    tests_folder_file.write_text("""
def test_something():
    expectations = (1, 2, 3)
    actualities = (9001, 2, 3)
    assert actualities[0] == expectations[0]
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    expectations = (9001, 2, 3)
    actualities = (9001, 2, 3)
    assert actualities[0] == expectations[0]
"""

def test_assert_in_function(tests_folder_file: Path) -> None:
    """Test that update_expected can handle helper functions, updating outside."""
    tests_folder_file.write_text("""
def assert_something(actual: object, expected: object) -> None:
    assert actual == expected
def test_something():
    expected = 1
    actual = 9001
    assert_something(actual, expected)
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def assert_something(actual: object, expected: object) -> None:
    assert actual == expected
def test_something():
    expected = 9001
    actual = 9001
    assert_something(actual, expected)
"""

def test_argument_indirection(tests_folder_file: Path) -> None:
    """Test that update_expected can handle multiple levels of indirection in argument names."""
    tests_folder_file.write_text("""
def assert_inner(expected_value: object, received_value: object) -> None:
    assert received_value == expected_value
def assert_outer(actual_obj: object, expected_obj: object) -> None:
    assert_inner(expected_obj, actual_obj)
def test_something():
    e = 1
    a = 9001
    assert_outer(a, e)
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def assert_inner(expected_value: object, received_value: object) -> None:
    assert received_value == expected_value
def assert_outer(actual_obj: object, expected_obj: object) -> None:
    assert_inner(expected_obj, actual_obj)
def test_something():
    e = 9001
    a = 9001
    assert_outer(a, e)
"""

def test_assert_in_separate_file(tests_folder: Path) -> None:
    """Test that the correct file is modified."""
    test_file_a = tests_folder / "test_a.py"
    test_file_b = tests_folder / "test_b.py"
    test_file_a.write_text("""
def assert_something(actual: object, expected: object) -> None:
    assert actual == expected
""")
    test_file_b.write_text("""
from test_a import assert_something
def test_something():
    expected = 1
    actual = 9001
    assert_something(actual, expected)
""")
    subprocess.run(["pytest", str(test_file_b), "--update-expected"], check=False)
    assert test_file_b.read_text() == """
from test_a import assert_something
def test_something():
    expected = 9001
    actual = 9001
    assert_something(actual, expected)
"""

def test_eval_in_separate_file(tests_folder: Path) -> None:
    """Test that the formatted value is evaluated in the correct file/function context."""
    test_file_a = tests_folder / "test_a.py"
    test_file_b = tests_folder / "test_b.py"
    test_file_a.write_text("""
def assert_something(actual: object, expected: object) -> None:
    assert actual == expected
""")
    test_file_b.write_text("""
from test_a import assert_something

def test_something():

    class ReprValue:
        def __init__(self, value: int) -> None:
            self.value = value
        def __repr__(self) -> str:
            return f"ReprValue({self.value!r})"
        def __eq__(self, other: object) -> bool:
            return self.value == other.value

    expected = ReprValue(1)
    actual = ReprValue(9001)
    assert_something(actual, expected)
""")
    subprocess.run(["pytest", str(test_file_b), "--update-expected"], check=False)
    assert test_file_b.read_text() == """
from test_a import assert_something

def test_something():

    class ReprValue:
        def __init__(self, value: int) -> None:
            self.value = value
        def __repr__(self) -> str:
            return f"ReprValue({self.value!r})"
        def __eq__(self, other: object) -> bool:
            return self.value == other.value

    expected = ReprValue(9001)
    actual = ReprValue(9001)
    assert_something(actual, expected)
"""

def test_update_tuple_via_parameter(tests_folder_file: Path) -> None:
    """Test that update_expected can update a value in a tuple."""
    tests_folder_file.write_text("""
def assert_something(actual: object, expected: object) -> None:
    assert actual == expected
def test_something():
    expectations = (1, 2, 3)
    actualities = (9001, 2, 3)
    assert_something(actualities[0], expectations[0])
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def assert_something(actual: object, expected: object) -> None:
    assert actual == expected
def test_something():
    expectations = (9001, 2, 3)
    actualities = (9001, 2, 3)
    assert_something(actualities[0], expectations[0])
"""

def test_annotated_assignment(tests_folder_file: Path) -> None:
    """Test that update_expected can handle AnnAssign, also ignoring the version without a value."""
    tests_folder_file.write_text("""
from typing import NamedTuple
class Expectations(NamedTuple):
    a: int
    b: int
def assert_something(actual: object, expected: Expectations) -> None:
    assert actual == expected
def test_something():
    expectations: Expectations
    expectations: Expectations = (1, 2)
    expectations: Expectations
    actualities = (9001, 2)
    assert_something(actualities[0], expectations[0])
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
from typing import NamedTuple
class Expectations(NamedTuple):
    a: int
    b: int
def assert_something(actual: object, expected: Expectations) -> None:
    assert actual == expected
def test_something():
    expectations: Expectations
    expectations: Expectations = (9001, 2)
    expectations: Expectations
    actualities = (9001, 2)
    assert_something(actualities[0], expectations[0])
"""

@pytest.mark.xfail(reason="Not implemented: magically rewriting PyQt6.QtCore.QPointF -> QPointF")
def test_match_import_style(tests_folder_file: Path) -> None:
    """Test that update_expected can use already imported symbols when repr gives fully qualified function name."""
    tests_folder_file.write_text("""
from PyQt6.QtCore import QPointF
def test_something():
    expected = QPointF(0, 1)
    actual = QPointF(0, 9001)
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
from PyQt6.QtCore import QPointF
def test_something():
    expected = QPointF(0, 9001)
    actual = QPointF(0, 9001)
    assert actual == expected
"""

@pytest.mark.xfail(reason="Probably beyond scope: magically rewriting PosixPath -> Path, or auto-importing PosixPath. Ideally this would be an 'ask the user' situation. But software isn't flexibly interactive these days.")
def test_use_generic_path_class(tests_folder_file: Path) -> None:
    """Test that update_expected can use already imported Path when PosixPath or WindowsPath is returned."""
    tests_folder_file.write_text("""
from pathlib import Path
def test_something():
    expected = Path("a")
    actual = Path("b")
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
from pathlib import Path
def test_something():
    expected = Path("b")
    actual = Path("b")
    assert actual == expected
"""

def test_parameterized_test_names_in_string(tests_folder_file: Path) -> None:
    """Test updating expectation in a parametrize decorator with the parameter names in a string."""
    tests_folder_file.write_text("""
import pytest
@pytest.mark.parametrize("input, expected", [(1, 11), (2, 12)])
def test_something(input: int, expected: int):
    output = input + 9000
    assert output == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
import pytest
@pytest.mark.parametrize("input, expected", [(1, 9001), (2, 9002)])
def test_something(input: int, expected: int):
    output = input + 9000
    assert output == expected
"""

def test_parameterized_test_names_in_list(tests_folder_file: Path) -> None:
    """Test updating expectation in a parametrize decorator with the parameter names in a list."""
    tests_folder_file.write_text("""
import pytest
@pytest.mark.parametrize(["input", "expected"], [(1, 11), (2, 12)])
def test_something(input: int, expected: int):
    output = input + 9000
    assert output == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
import pytest
@pytest.mark.parametrize(["input", "expected"], [(1, 9001), (2, 9002)])
def test_something(input: int, expected: int):
    output = input + 9000
    assert output == expected
"""

def test_parameterized_test_names_in_tuple(tests_folder_file: Path) -> None:
    """Test updating expectation in a parametrize decorator with the parameter names in a tuple."""
    tests_folder_file.write_text("""
import pytest
@pytest.mark.parametrize(("input", "expected"), [(1, 11), (2, 12)])
def test_something(input: int, expected: int):
    output = input + 9000
    assert output == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
import pytest
@pytest.mark.parametrize(("input", "expected"), [(1, 9001), (2, 9002)])
def test_something(input: int, expected: int):
    output = input + 9000
    assert output == expected
"""

@pytest.mark.xfail(reason="bug with indices, maybe order of field accessors")
def test_parameterized_test_single_name_in_string(tests_folder_file: Path) -> None:
    """Test updating expectation in a parametrize decorator with a single parameter, and accompanying flat list."""
    tests_folder_file.write_text("""
import pytest
@pytest.mark.parametrize("a_b_sum", [(1, 2, 3), (4, 5, 6)])
def test_something(a_b_sum: tuple[int, int, int]):
    output = a_b_sum[0] + a_b_sum[1]
    assert output == a_b_sum[2]
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
import pytest
@pytest.mark.parametrize("a_b_sum", [(1, 2, 3), (4, 5, 9)])
def test_something(a_b_sum: tuple[int, int, int]):
    output = a_b_sum[0] + a_b_sum[1]
    assert output == a_b_sum[2]
"""

@pytest.mark.xfail(reason="assert is only matched at start of line")
def test_multiple_statements_on_one_line(tests_folder_file: Path) -> None:
    """Test that the correct assert statement is targeted within a line."""
    tests_folder_file.write_text("""
def test_something():
    a = 1; assert 2 == 0; c = 3
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    a = 1; assert 2 == 2; c = 3
"""

@pytest.mark.xfail(reason="first assert is assumed")
def test_multiple_asserts_on_one_line(tests_folder_file: Path) -> None:
    """Test that the correct assert statement is targeted within a line."""
    tests_folder_file.write_text("""
def test_something():
    assert 1 == 1; assert 2 == 0; assert 3 == 3
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    assert 1 == 1; assert 2 == 2; assert 3 == 3
"""

@pytest.mark.xfail(reason="string representation escapes newlines; need different pretty-printing to test this")
def test_multi_line_string(tests_folder_file: Path) -> None:
    """Test that multi-line strings are indented as given."""
    tests_folder_file.write_text("""
def test_something():
    expected = ''
    actual = '''9001
9002
9003'''
    assert actual == expected
""")
    subprocess.run(["pytest", str(tests_folder_file), "--update-expected"], check=False)
    assert tests_folder_file.read_text() == """
def test_something():
    expected = '''9001
9002
9003'''
    actual = '''9001
9002
9003'''
    assert actual == expected
"""


def check_error(test_code: str, tests_folder: Path, error_message: str) -> None:
    """Check that running the test code raises an error with the given message.

    NOTE: Can't check for multiple line strings, because pytest inserts "E" followed by whitespace.
    Either test one line [at a time] of the message, or extend this function, possibly using regex.

    If the error isn't found, gee, it sure would be nice to see a diff.
    Maybe look for the error message markers ("E") and use python's difflib?
    Looks like pytest's diffing is here: https://github.com/pytest-dev/pytest/blob/cdddd6d69533c07092c64445a0d42d1fc75c8299/src/_pytest/assertion/util.py#L263
    and it's private, but the function could be copied, as it's mostly just a wrapper around difflib.
    But is it worth copying? The whitespace-only scenario doesn't seem likely, for one thing.
    """
    test_file = tests_folder / "test_error.py"
    test_file.write_text(test_code)
    command_args = ["pytest", str(test_file), "--update-expected"]
    result = subprocess.run(command_args, check=False, capture_output=True)
    assert result.returncode == pytest.ExitCode.TESTS_FAILED
    # assert error_message in result.stderr.decode() # Pytest doesn't show the binary string well
    # error_output = result.stderr.decode() # Error is in stdout, not stderr
    output = result.stdout.decode()
    if error_message not in output:
        print(output)
        assert False, f"Expected error message ({error_message!r}) not found in output of command {command_args!r}"

def test_error_broken_comparison(tests_folder: Path) -> None:
    """Test the error message when the updated expectation can't pass."""
    check_error("""
class SusValue:
    def __init__(self, value: int) -> None:
        self.value = value
    def __repr__(self) -> str:
        return f"SusValue({self.value!r})"
    def __eq__(self, other: object) -> bool:
        return self.value == other.value + 1 # pretty sus
def test_something():
    expected = SusValue(1)
    actual = SusValue(9001)
    assert actual == expected
""", tests_folder, "Equality comparison may not work for this test")

@pytest.mark.xfail(reason="repr(float('nan')) == 'nan'")
def test_error_broken_comparison_nan(tests_folder: Path) -> None:
    """Test the error message when the updated expectation can't pass."""
    check_error("""
def test_something():
    expected = 1
    actual = float('nan')
    assert actual == expected
""", tests_folder, "Equality comparison may not work for this test")

def test_error_reversed_expected_actual(tests_folder: Path) -> None:
    """Test the error message when actual/expected are reversed."""
    check_error("""
def test_something():
    expected = 1
    actual = 2
    assert expected == actual
""", tests_folder, "uses actual/expected in the wrong order ('expected' was found on the left of the comparison, whereas it should likely be on the right.)")

def test_error_reversed_expected_received(tests_folder: Path) -> None:
    """Test the error message when received/expected are reversed."""
    check_error("""
def test_something():
    _ = 1
    received = 2
    assert _ == received
""", tests_folder, "uses actual/expected in the wrong order ('received' was found on the right of the comparison, whereas it should likely be on the left.)")

def test_error_unsupported_comparison(tests_folder: Path) -> None:
    """Test the error message when greater/less than operators are used."""
    check_error("""
def test_something():
    expected = 1
    actual = 2
    assert actual < expected
""", tests_folder, "unsupported comparison operator")

def test_error_unsupported_compound_comparison(tests_folder: Path) -> None:
    """Test the error message when greater/less than operators are used."""
    check_error("""
def test_something():
    expected = 1
    actual = 2
    assert actual == expected == 3
""", tests_folder, "unsupported compound comparison")

@pytest.mark.xfail(reason="pytest_assertrepr_compare is not called except for comparisons, which is perfectly fine and good")
def test_error_unsupported_assert_expression(tests_folder: Path) -> None:
    """Test the error message when assert expression is not a comparison."""
    check_error("""
def test_something():
    expected = True
    actual = False
    assert actual  # (test must fail to test the error message)
""", tests_folder, "not an equality comparison")

@pytest.mark.xfail(reason="only considers first failing assert")
def test_error_conflicting_updates_to_same_target(tests_folder: Path) -> None:
    """Test the error message when replacements would overlap."""
    check_error("""
def test_something():
    for i in range(3):
        expected = 1
        actual = 9000 + i
        assert actual == expected
""", tests_folder, "Can't update `expected` at <location> to both `9000`, `9001, and `9002` wanted by asserts at <location>, <same location>, and <same location> respectively")
    # The above error message is a mix of what would be nice and practical concerns; it's neither ideal nor easy to implement.
    # More likely practicable would be to report about just two conflicting updates.
    # How this might work is to re-run the test somehow (maybe look at plugins for retrying flaky tests)
    # and if it fails in a way where this system would want to update the same variable to something else,
    # inject a message into the report.
    # If it fails for another reason, such as a later assert, well,
    # there could be a recursive updating feature, with some limit that you can set,
    # or it could simply require you to re-run the test with --update-expected again.
