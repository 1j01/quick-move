"""This file is loaded by pytest automatically. Fixtures defined here are available to all tests in the folder.

https://docs.pytest.org/en/7.1.x/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

Also pytest_assertrepr_compare hook only seems to work in here.
"""


import pytest

from tests.accept import update_expected


def pretty_print(obj: object, level: int = 1) -> str:
    """Format any object used in test assertions as source code to insert into the test when using --update-expected."""
    def bracketed(brackets: tuple[str, str], representations: list[str]) -> str:
        # MAX_LEN = 15
        INDENT = " " * 4
        multiline = True #any("\n" in representation or len(representation) > MAX_LEN for representation in representations)
        if multiline:
            return brackets[0] + "\n" + f",\n".join(f"{INDENT * level}{representation}" for representation in representations) + ",\n" + f"{INDENT * (level - 1)}{brackets[1]}"
        return brackets[0] + ", ".join(representations) + brackets[1]

    if isinstance(obj, list):
        return bracketed(("[", "]"), [pretty_print(item, level + 1) for item in obj])  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    elif isinstance(obj, tuple):
        return bracketed(("(", ")"), [pretty_print(item, level + 1) for item in obj])  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    elif isinstance(obj, dict):
        return bracketed(("{", "}"), [f"{pretty_print(key, level + 1)}: {pretty_print(value, level + 1)}" for key, value in obj.items()])  # pyright: ignore[reportUnknownArgumentType, reportUnknownVariableType]
    else:
        return repr(obj)

update_expected_arg: bool = False

def pytest_addoption(parser: pytest.Parser) -> None:
    # Or should it be "--accept-actual"?
    parser.addoption("--update-expected", action="store_true", help="update `expected` variable in tests to match actual results")

@pytest.fixture(scope="session", autouse=True)
def record_update_expected_arg(pytestconfig: pytest.Config) -> None:
    global update_expected_arg
    update_expected_arg = pytestconfig.getoption("update_expected", default=False)  # type: ignore

def pytest_assertrepr_compare(op: str, left: object, right: object) -> list[str] | None:
    """Custom comparison for QPolygonF instances and lists, for when pytest assertions fail.

    Also handles the --update-expected option, to accept actual results as new expectations.
    """
    if update_expected_arg:
        # Protect against recursion; only update based on root value, not inner values being compared.
        # If I had control over the function signature, I would just add a "recursed" argument.
        # An alternative way to do this would be a global flag, but I'm vibing with the inspect module.
        # Oh, I guess another way to do this would be to split out a function that I have control over the signature of.
        import inspect
        frame = inspect.currentframe()
        assert frame is not None
        recursed = False
        while frame.f_back:
            frame = frame.f_back
            if frame.f_code.co_name == "pytest_assertrepr_compare":
                recursed = True
                break
        if not recursed:
            update_expected(left, pretty_print)

    return None
