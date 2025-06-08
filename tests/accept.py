#!/usr/bin/env python3
"""Updates expectations in tests to accept the current output.

This allows for an ad-hoc form of snapshot testing,
where snapshots are stored in the test code itself,
and there need be no distinction between snapshot tests and regular tests.

Pass --update-expected to pytest to update expectations for any failing tests.
This will affect only tests that are run, as filtered by pytest options like -k.
If you DO want to distinguish between snapshot tests and regular tests,
you can define a custom marker and use -m to select only snapshot tests.

A convention of `assert <actual> == <expected>` must be followed for this to work,
as it will try to update the right-hand side of the assertion.
It will try to warn you if the assertion is reversed, but it can't detect all cases.

If the assertion uses a variable, it will follow the variable to its definition.
If the variable refers to a parameter, it will follow the parameter to the call site,
and examine the argument expression, and so on.
Subscript is supported, with a literal index, to update expectations stored in tuples.
Subscript can be present anywhere from the assertion to the variable definition.

If the assertion uses an expression other than a simple variable or subscript,
it will update the expression directly in the assert statement.

If a variable refers to a parameter of the test function,
it will look for a @pytest.mark.parametrize decorator, as a special case,
and update expectations within the decorator's arguments.
(It doesn't work with the whole pytest fixture system, though.)

It works with multiple expectation variables followed by assertions in the same function.
This works by ignoring variables defined after the current line of code in a function.
(This is a simplified view of the execution timeline, but it works for linear code.)

Comments and formatting are preserved (although not when displaying expressions in errors),
and custom formatting can specified for updated values by passing a pretty_print function.

Once a value is formatted, before inserting it into the source code,
it is verified to be a valid Python expression, to avoid syntax errors,
and then it is actually evaluated in the context of the failing test, to check for runtime errors,
such as a NameError when the representation of an object uses its class name, which isn't imported.
The formatted and re-parsed "actual" value is then compared to the original "actual" value,
to check for equality problems, such as a __repr__ that doesn't include all parameters,
which would fail the test when the expectation is updated.

Files are modified at exit, to handle line numbers coherently when making multiple replacements,
and to avoid mismatched line numbers when using a debugger, as well as for performance.
If the program crashes, the files won't be modified.

For safety, only files in a tests*/ folder will be modified.

TODO: for extra safety, ensure modifications reside in the currently executing test function,
using os.environ.get("PYTEST_CURRENT_TEST"),
or pytest hooks: pytest_runtest_setup (or pytest_runtest_call) and pytest_runtest_teardown
Also, could store a backup of the file before modifying it, and log the location of the backup to the console.
Although it's unclear when the backup should be deleted.
NOTE: see tests in test_accept.py for examples of what this can handle (and what it can't, marked @xfail),
or if you're interested in how one tests code that modifies tests' code :)
NOTE: some code is duplicated from dynamic_comment.py
IDEA: if you don't like the convention of `assert <actual> == <expected>`,
or the idea that it could be reversed by accident,
a feature could be added to mark an expression for updating, with a function that merely returns its argument,
similar to `typing.cast`, called something like `expected` or `updatable` or `hole` or `snapshot`.
That said, especially with the name "snapshot", it does call into question why not use a snapshot testing library. :)
The advantage to using a "real" snapshot testing library is avoiding bloating the test code with long values.
OOH: what if it supported updating files — only within a snapshots folder, for safety —
by writing Path("something.png").read_bytes() or Path("something.txt").read_text()?
It would then do write_bytes or write_text to update the snapshot file.
Slightly bizarre, but what do you think? Good magical or bad magical?
"""

import ast
import atexit
import inspect
import pprint
import re
from collections import defaultdict
from pathlib import Path
from types import FrameType
from typing import Callable, cast

class _LineColSpan:
    """A range of line/column indices within some text."""
    def __init__(self, start_line: int, start_column: int, end_line: int, end_column: int):
        self.start_line = start_line
        self.start_column = start_column
        self.end_line = end_line
        self.end_column = end_column

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.start_line}, {self.start_column}, {self.end_line}, {self.end_column})"

def _any_overlap(range1: _LineColSpan, range2: _LineColSpan) -> bool:
    """Check if two line/column ranges overlap."""
    if (range1.end_line < range2.start_line) or (range1.start_line > range2.end_line):
        return False
    if (range1.end_line == range2.start_line) and (range1.end_column < range2.start_column):
        return False
    if (range1.start_line == range2.end_line) and (range1.start_column > range2.end_column):
        return False
    return True

_replacements: dict[str, list[tuple[_LineColSpan, str]]] = defaultdict(list)
"""Maps file paths to a list of line/column ranges and replacement strings."""

_modified_files: set[str] = set()
"""File paths that have been modified by this module."""

class UpdateExpectedError(Exception):
    """Raised when a test's expectation can't be updated, when using `pytest --update-expected`."""
    # Note: sometimes NotImplementedError is used instead.


def _find_function_def(tree: ast.AST, func_name: str, file: str) -> ast.FunctionDef:
    """Find a function definition AST node by name."""
    func_defs: list[ast.FunctionDef] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == func_name:
            func_defs.append(node)

    if not func_defs:
        raise UpdateExpectedError(f"Function {func_name!r} not found in AST for {file!r}")
    elif len(func_defs) > 1:
        raise UpdateExpectedError(f"Multiple functions named {func_name!r} found in AST for {file!r}")

    return func_defs[0]

def _trace_expression_origin(frame: FrameType, func_def: ast.FunctionDef, expression: ast.expr) -> tuple[ast.AST | None, FrameType, list[str | int], ast.Name | None]:
    """Parse an expression AST node, tracing a variable back to its definition, with field accessors.

    Args:
        - frame: The frame of the function execution corresponding to the function definition.
        - func_def: The function definition AST node to search within.
        - expression: The expression AST node to inspect and trace.

    Returns a tuple of:
        - the AST node ultimately found to be replaced,
        - the frame the variable was ultimately found in,
        - field accessors used along the way,
        - and the Name node initially found in the expression.
    """
    if isinstance(expression, ast.Name):
        name_node = expression
        field_accessors = []
    elif isinstance(expression, ast.Attribute):
        name_node = expression.value
        field_accessors = [expression.attr]
    elif isinstance(expression, ast.Subscript):
        name_node = expression.value
        try:
            field_accessors = [int(ast.unparse(expression.slice))]
        except ValueError:
            raise NotImplementedError(f"Cannot handle subscript slice in expression")
    else:
        return (expression, frame, [], None)
    if not isinstance(name_node, ast.Name):
        return (expression, frame, [], None)

    # arg_value = frame.f_locals[name_node.id]
    # if isinstance(expression, ast.Name):
    #     print(f"Parameter {identifier!r} (with index {arg_index}) of function {callee.co_name!r} was passed a variable {name_node.id!r} (with value {arg_value!r}) at {call_site_loc!r}")
    # else:
    #     print(f"Parameter {identifier!r} (with index {arg_index}) of function {callee.co_name!r} was passed an expression {ast.unparse(expression)!r}) at {call_site_loc!r}")
    #     access_str = "".join([f"[{access!r}]" if isinstance(access, int) else "." + access for access in field_accessors])
    #     print(f"  The expression evaluates to {arg_value!r}{access_str}")

    # Find what the variable part of the argument expression refers to
    node_with_node_to_replace, frame_with_node_to_replace, further_field_accessors = _trace_origin(func_def, frame, func_def, name_node.id)
    return (node_with_node_to_replace, frame_with_node_to_replace, field_accessors + further_field_accessors, name_node)



def _trace_origin(node: ast.AST, frame: FrameType, other_func_def: ast.FunctionDef, identifier: str) -> tuple[ast.AST | None, FrameType, list[str | int]]:
    """Locate the declaration of an identifier in the AST, or if it's an argument, trace it back through the call stack."""

    file = frame.f_globals['__file__']
    if isinstance(node, (ast.Assign, ast.AnnAssign)):
        # Handle variable assignments
        if node.lineno > frame.f_lineno:
            # The variable definition is after the current line,
            # so it's not relevant to the current line.
            return (None, frame, [])
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if len(targets) > 1:
            # Is this possible, or is this just when the AST is hand-crafted?
            # "Multiple nodes in targets represents assigning the same value to each. Unpacking is represented by putting a Tuple or List within targets."
            print(f"Warning: Cannot handle multiple assignment targets in {ast.unparse(node)!r} at {file}:{node.lineno}")
        for target in targets:
            if isinstance(target, ast.Name):
                if target.id == identifier:
                    if node.value is None:
                        print(f"Skipping variable type declaration without value: {ast.unparse(node)!r} at {file}:{node.lineno}")
                        continue
                    return (node.value, frame, [])
            elif isinstance(target, ast.Tuple):
                skip = False
                for i, elt in enumerate(target.elts):
                    if isinstance(elt, ast.Name):
                        if elt.id == identifier:
                            if node.value is None:
                                print(f"Skipping variable type declaration without value: {ast.unparse(node)!r} at {file}:{node.lineno}")
                                # I'm not sure this complexity is necessary
                                skip = True
                                break
                            return (node.value, frame, [i])
                    else:
                        print(f"Warning: Cannot handle assignment to {ast.unparse(elt)!r} in {ast.unparse(node)!r} at {file}:{node.lineno}")
                if skip:
                    continue
            else:
                print(f"Warning: Cannot handle assignment to {ast.unparse(target)!r} in {ast.unparse(node)!r} at {file}:{node.lineno}")
    elif isinstance(node, ast.FunctionDef):
        # Handle function definitions
        if node.lineno > frame.f_lineno:
            # The function definition is after the current line,
            # so it's not relevant to the current line.
            return (None, frame, [])
        if node.name == identifier:
            return (node, frame, [])
    elif isinstance(node, ast.arguments):
        # Handle function parameters
        for arg_index, arg in enumerate(node.args):
            if arg.arg == identifier:
                callee_frame = frame
                callee = callee_frame.f_code

                if frame.f_back is None:
                    raise UpdateExpectedError(f"Cannot get caller frame")
                frame = frame.f_back
                file = frame.f_globals['__file__']
                print(f"{identifier!r} refers to a parameter (with index {arg_index}) of {callee.co_name!r}; searching in caller's frame ({frame.f_code.co_name!r}) at {file}:{frame.f_lineno}")

                # Read the entire source file
                # Perf: cache this, to avoid reading the same file multiple times
                with open(file, 'r') as f:
                    source_code = f.read()
                    # source_lines = source_code.splitlines(keepends=True)

                # Parse the source code
                tree = ast.parse(source_code)
                # print(ast.dump(tree))

                # Find the function in the AST
                func_def = _find_function_def(tree, frame.f_code.co_name, file)

                # Find call site of the inner function in the AST
                call_site_loc = f"{file}:{frame.f_lineno}"
                call_site: ast.Call | None = None
                for node in ast.walk(func_def):
                    if isinstance(node, ast.Call) and node.lineno == frame.f_lineno:
                        call_site = node
                        break

                if call_site is None:
                    raise UpdateExpectedError(f"Call site of function {callee.co_name!r} not found in AST within function {func_def.name!r} at {call_site_loc!r}")

                # Special case to handle pytest parametrized tests
                # pytest_pyfunc_call calls the test function with a variable number of arguments.
                if frame.f_code.co_name == "pytest_pyfunc_call":
                    print(f"Parameter {identifier!r} (with index {arg_index}) of function {callee.co_name!r} may be generated by fixtures or parametrization")
                    other_func_call_loc = "(?)"
                    print(f"Checking for parameterization decorators on the test function {other_func_def.name!r} at {other_func_call_loc!r}")
                    decorator_call_node, accessors = _trace_pytest_parameter(other_func_def, arg_index, identifier, other_func_call_loc)
                    return (decorator_call_node, callee_frame, accessors)

                # Find the argument in the call site
                if arg_index >= len(call_site.args):
                    raise UpdateExpectedError(f"Argument {identifier!r} not found in AST for call of function {callee.co_name!r} at {call_site_loc!r} (not enough arguments; is it a default value?)")
                arg_expr = call_site.args[arg_index]

                try:
                    node_with_node_to_replace, frame_with_node_to_replace, field_accessors, name_node = _trace_expression_origin(frame, func_def, arg_expr)
                except NotImplementedError as e:
                    raise NotImplementedError(f"{str(e).replace('expression', 'argument expression')} {ast.unparse(arg_expr)!r} for parameter {arg_index} ({identifier!r}) of function {callee.co_name!r} at {call_site_loc!r}") from e

                if node_with_node_to_replace is None or name_node is None:
                    raise UpdateExpectedError(f"Couldn't find what {identifier!r} refers to in the call of function {callee.co_name!r} at {call_site_loc!r}")

                arg_value = frame.f_locals[name_node.id]
                if isinstance(arg_expr, ast.Name):
                    print(f"Parameter {identifier!r} (with index {arg_index}) of function {callee.co_name!r} was passed a variable {name_node.id!r} (with value {arg_value!r}) at {call_site_loc!r}")
                else:
                    print(f"Parameter {identifier!r} (with index {arg_index}) of function {callee.co_name!r} was passed an expression {ast.unparse(arg_expr)!r}) at {call_site_loc!r}")
                    access_str = "".join([f"[{access!r}]" if isinstance(access, int) else "." + access for access in field_accessors])
                    print(f"  The expression evaluates to {arg_value!r}{access_str}")

                return (node_with_node_to_replace, frame_with_node_to_replace, field_accessors)


    candidates: list[tuple[ast.AST, FrameType, list[str | int]]] = []
    for child_node in ast.iter_child_nodes(node):
        node_with_node_to_replace, frame_with_node_to_replace, field_accessors = _trace_origin(child_node, frame, other_func_def, identifier)
        if node_with_node_to_replace is not None:
            candidates.append((node_with_node_to_replace, frame_with_node_to_replace, field_accessors))

    candidates.sort(key=lambda x: x[0].lineno, reverse=True)
    if candidates:
        return candidates[0]

    return (None, frame, [])

_test_counters: dict[str, int] = defaultdict(int)
def _trace_pytest_parameter(func_def: ast.FunctionDef, arg_index: int, identifier: str, func_def_loc: str) -> tuple[ast.expr | None, list[str | int]]:
    """Find the parameter in the annotation of a pytest parametrized test.

    Args:
        - func_def: The test's function def AST node.
        - arg_index: The index of the parameter in the call site.
        - identifier: The name of the parameter.
        - func_def_loc: The location of test function def, in the form `/path/file.py:line`.

    Returns a tuple of:
        - the `pytest.mark.parametrize()` call AST node
        - field accessors for the specific parameter in the decoration
    """
    # TODO: record real location
    file_with_decorator = "(?)"
    print("Found decorators:", [ast.unparse(decorator) for decorator in func_def.decorator_list])
    # TODO: handle or reject multiple decorators
    for decorator in func_def.decorator_list:
        decorator_loc = f"{file_with_decorator}:{decorator.lineno}"
        if isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "parametrize":
            print("Found parametrize() decorator")
            param_names: list[str]
            if isinstance(decorator.args[0], ast.Str):
                param_names = decorator.args[0].value.split(",")
                param_names = [param_name.strip() for param_name in param_names]
            elif isinstance(decorator.args[0], (ast.List, ast.Tuple)):
                param_names = []
                for param_name_node in decorator.args[0].elts:
                    if isinstance(param_name_node, ast.Str):
                        param_names.append(param_name_node.value)
                    else:
                        raise NotImplementedError(f"Cannot handle parametrization with parameter names that are not string literals, at {decorator_loc!r}")
            else:
                raise NotImplementedError(f"Cannot handle parametrization with parameter names list of type {type(decorator.args[0])}; only List, Tuple, and Str nodes are supported, at {decorator_loc!r}")
            # This bit may or may not be un-vetted AI code, and may or may not have basis in reality.
            if identifier not in param_names:
                raise UpdateExpectedError(f"Parameter {identifier!r} not found in pytest parametrize decorator at {decorator_loc!r}")
            param_index = param_names.index(identifier)
            if param_index != arg_index:
                raise UpdateExpectedError(f"Parameter {identifier!r} has index {param_index} in pytest parametrize decorator at {decorator_loc!r}, but index {arg_index} in call of function {func_def.name!r} at {func_def_loc!r}")
            list_node = decorator.args[1]
            # BEGIN HACK
            # This will not work with randomized test execution order.
            # (Nor will it work if this function is called multiple times. It's no longer pure.)
            # This will fail if multiple tests with the same name are run, even if they're in different files,
            # due to the string key. A function key would be better, but the FunctionDef will not work,
            # as the AST is re-parsed multiple times, so it will be a different object each time.
            test_index = _test_counters[func_def.name]
            _test_counters[func_def.name] += 1
            # END HACK
            if len(param_names) == 1:
                return (list_node, [test_index])
            else:
                return (list_node, [test_index, param_index])

    raise UpdateExpectedError(f"Couldn't find pytest.mark.parametrize() decorator call in AST for call of function {func_def.name!r} at {func_def_loc!r}")

def update_expected(actual: object, pretty_print: Callable[[object], str] | None = None) -> None:
    """Update assertion values in the source code once the program exits, found by looking up the stack."""

    if pretty_print is None:
        # I'm guessing it doesn't support a separate max width for the first line,
        # which would have the assignment before the value.
        pretty_print = pprint.PrettyPrinter(indent=4, width=80, compact=False, sort_dicts=False).pformat

    # Get the current frame, which is of this function, since this function is executing.
    # NOTE: variables here are named after what they'll hopefully end up as.
    frame_with_assert = inspect.currentframe()
    assert frame_with_assert is not None, "Cannot get current frame"

    # Find the `assert` statement that caused a test failure.
    # Could optimize by looking for "_call_reprcompare" in the stack,
    # which is what pytest rewrites assertions to, but that's an implementation detail.
    # Reference: https://github.com/pytest-dev/pytest/blob/dd68f9c95aed1dbad6d07766b0a1906a1a1e1f55/src/_pytest/assertion/rewrite.py#L1105-L1162
    while frame_with_assert.f_back is not None:
        frame_with_assert = frame_with_assert.f_back
        file_with_assert = frame_with_assert.f_globals['__file__']
        # print("frame.f_code.co_name:", frame.f_code.co_name, f"\n  {file}:{frame.f_lineno}")

        # Read the entire source file
        with open(file_with_assert, 'r') as f:
            source_code_with_assert = f.read()
            source_lines_with_assert = source_code_with_assert.splitlines(keepends=True)

        # Check for an assertion on the current line
        # TODO: make this robust by checking just `"assert" in ...` and then parsing with ast
        # An assert could be on a line with other code, not that I would recommend it.
        if source_lines_with_assert[frame_with_assert.f_lineno - 1].lstrip().startswith("assert"):
            break

    else:
        print(f"`assert` statement not found in any frame in the stack")
        return

    assert_loc = f"{file_with_assert}:{frame_with_assert.f_lineno}"
    print(f"Found `assert` statement: {assert_loc!r}")

    # Find the function name
    func_name = frame_with_assert.f_code.co_name

    # Parse the source code
    tree = ast.parse(source_code_with_assert)
    # print(ast.dump(tree))

    # Find the function in the AST
    func_def = _find_function_def(tree, func_name, file_with_assert)

    # Find the assertions in the AST
    assert_stmts: list[ast.Assert] = []
    for node_to_replace in ast.walk(func_def):
        if isinstance(node_to_replace, ast.Assert):
            assert_stmts.append(node_to_replace)

    if not assert_stmts:
        raise UpdateExpectedError(f"No assertions found within function {func_name!r} in AST; expected one at this line: {assert_loc!r}")

    # Find the assertion matching the current line
    assert_stmt = None
    for stmt in assert_stmts:
        if stmt.lineno == frame_with_assert.f_lineno:
            assert_stmt = stmt
            break
    else:
        raise UpdateExpectedError(f"No assertion found in AST within function {func_name!r} at line: {assert_loc!r}")

    # Check that the assertion's expression is a comparison
    if not isinstance(assert_stmt.test, ast.Compare):
        raise UpdateExpectedError(f"Assertion at {assert_loc!r} within function {func_name!r} is not an equality comparison")

    # Check for reversed actual/expected
    # The convention `assert <actual> == <expected>` must be followed;
    # this check doesn't ensure that, since arbitrary expressions are allowed,
    # but it should catch some common cases.
    compare = assert_stmt.test
    left_str = ast.unparse(compare.left)
    right_str = ast.unparse(compare.comparators[0])
    ACTUAL_NAMES = {"actual", "result", "got", "received", "real", "reality"}
    EXPECTED_NAMES = {"expected", "wanted", "desired", "correct", "expectation"}
    print(f"Left part of the assert: {left_str!r} (should be e.g. {ACTUAL_NAMES!r})")
    print(f"Right part of the assert: {right_str!r} (should be e.g. {EXPECTED_NAMES!r})")

    def split_identifier(identifier: str) -> list[str]:
        # Split camelCase using regular expressions
        words = re.findall(r"[A-Z][a-z]*|\d+|\w+", identifier)
        words = cast(list[str], words)
        # Join the camelCase segments and split snake_case
        words = "_".join(words).split("_")
        return words

    def matching_name(identifier: str, names: set[str]) -> str:
        words = split_identifier(identifier)
        for word in words:
            if word in names:
                return word
        return ""

    wrong_left_match = matching_name(left_str, EXPECTED_NAMES)
    wrong_right_match = matching_name(right_str, ACTUAL_NAMES)

    if wrong_left_match:
        raise UpdateExpectedError(f"Assertion at {assert_loc!r} uses actual/expected in the wrong order ({wrong_left_match!r} was found on the left of the comparison, whereas it should likely be on the right.)\nMust use convention `assert <actual> == <expected>` to work with --update-expected.\nIf this error is not relevant, just rename the variable.")
    if wrong_right_match:
        raise UpdateExpectedError(f"Assertion at {assert_loc!r} uses actual/expected in the wrong order ({wrong_right_match!r} was found on the right of the comparison, whereas it should likely be on the left.)\nMust use convention `assert <actual> == <expected>` to work with --update-expected.\nIf this error is not relevant, just rename the variable.")

    # Check for too many operands
    if len(compare.ops) > 1:
        raise UpdateExpectedError(f"Assertion at {assert_loc!r} within function {func_name!r} uses an unsupported compound comparison")

    # Check for unsupported comparison operators
    if not isinstance(compare.ops[0], (ast.Eq, ast.NotEq)):
        raise UpdateExpectedError(f"Assertion at {assert_loc!r} within function {func_name!r} uses an unsupported comparison operator")

    # Search for the variable definition, within the function definition,
    # and further in the call stack if refers to a parameter.
    right_expr = compare.comparators[0]
    try:
        node_to_replace, frame_with_node_to_replace, field_accessors, name_node = _trace_expression_origin(frame_with_assert, func_def, right_expr)
    except NotImplementedError as e:
        raise NotImplementedError(f"{e} {ast.unparse(right_expr)!r} {ast.unparse(right_expr)!r} in assert at {assert_loc!r}") from e

    if node_to_replace is None:
        raise UpdateExpectedError(f"Couldn't find what {name_node.id if name_node else ast.unparse(right_expr)!r} refers to in the assert at {assert_loc!r} within function {func_name!r}")

    # Get the file where the replacement will be made
    # TODO: perf: use a cache to avoid reading the same file multiple times
    file_with_node_to_replace = frame_with_node_to_replace.f_globals['__file__']
    with open(file_with_node_to_replace, 'r') as f:
        source_lines_with_node_to_replace = f.read().splitlines(keepends=True)

    # Format the replacement
    value_str = pretty_print(actual)
    line_with_indent = source_lines_with_node_to_replace[node_to_replace.lineno - 1]
    indent = line_with_indent[:len(line_with_indent) - len(line_with_indent.lstrip())]
    value_str = value_str.replace("\n", f"\n{indent}") # Note: this will not work for multiline strings!
    # TODO: preserve whitespace in multiline strings by parsing the AST for the value,
    # and avoiding adding indents within string nodes.
    # value_ast = ast.parse(value_str, mode="eval")

    if name_node is not None:
        var_value = frame_with_assert.f_locals[name_node.id]
        if isinstance(right_expr, ast.Name):
            print(f"Assert uses a variable {name_node.id!r} (with value {var_value!r}) at {assert_loc!r}")
        else:
            print(f"Assert uses an expression ({ast.unparse(right_expr)!r}) at {assert_loc!r}")
            access_str = "".join([f"[{access!r}]" if isinstance(access, int) else "." + access for access in field_accessors])
            print(f"  The expression evaluates to {var_value!r}{access_str}")

        print(f"{right_str!r} refers to a variable defined at {file_with_node_to_replace}:{node_to_replace.lineno} ({ast.unparse(node_to_replace)!r}) with field accessors {field_accessors!r}")
    else:
        print(f"Assert uses an expression ({ast.unparse(right_expr)!r}) which will be replaced directly in the assert at {assert_loc!r}")
        node_to_replace = right_expr

    if field_accessors:
        # Update part of the value, not the whole value
        for field_accessor in field_accessors:
            if isinstance(field_accessor, int):
                # Update an item within a list or tuple
                if not isinstance(node_to_replace, (ast.List, ast.Tuple)):
                    raise UpdateExpectedError(f"Cannot update item {field_accessor!r} within {ast.dump(node_to_replace)}")
                if field_accessor >= len(node_to_replace.elts):
                    raise UpdateExpectedError(f"Cannot update item {field_accessor!r} within {ast.dump(node_to_replace)} (not enough items)")
                node_to_replace = node_to_replace.elts[field_accessor]
            else:
                raise NotImplementedError(f"Cannot update {field_accessor!r} within {ast.dump(node_to_replace)}")

    # Verify the formatted value is valid Python
    try:
        ast.parse(value_str, mode="eval")
    except SyntaxError as e:
        raise UpdateExpectedError(f"Formatted value {value_str!r} is not a valid Python expression. You'll need to define formatting for all relevant types in `pretty_print`.") from e

    # Evaluate the formatted value code in the frame where it will be placed,
    # to make sure it doesn't reference any constructors that aren't in scope,
    # then compare it to the actual value to make sure the test will pass as expected.
    # Since the function is still in the call stack,
    # we're actually very well equipped to test the construction in context!
    try:
        new_actual = eval(value_str, frame_with_node_to_replace.f_globals, frame_with_node_to_replace.f_locals)
    except Exception as e:
        raise UpdateExpectedError(f"Failed to evaluate {value_str!r} in the context of failing test {func_name} in {file_with_node_to_replace!r}\nGot: {e!r}") from e

    if new_actual != actual:
        # TODO: make context more up-front clear
        raise UpdateExpectedError(f"""Formatted value {value_str!r} evaluated to {new_actual!r} does not match original actual value from test failure {actual!r}
1. You may need to define formatting for object types in `pretty_print` if information is lost during construction, or
2. Equality comparison may not work for this test
({func_name} in {file_with_assert!r})")""")

    # Store the replacement
    assert node_to_replace.end_lineno is not None, f"Cannot get end line number for {ast.dump(node_to_replace)}"
    assert node_to_replace.end_col_offset is not None, f"Cannot get end column offset for {ast.dump(node_to_replace)}"
    line_col_span = _LineColSpan(node_to_replace.lineno - 1, node_to_replace.col_offset, node_to_replace.end_lineno - 1, node_to_replace.end_col_offset)
    _replacements[file_with_node_to_replace].append((line_col_span, value_str))


def _commit_replacements(target_file: str | None = None) -> None:
    """
    Apply all source code replacements. This is called automatically when the program exits.

    This is a separate step to avoid line number conflicts.
    If files were written to immediately when update_expected was called,
    the next call to update_expected would have line numbers that no longer
    correspond to the source file, since the running program
    would still be using the original lines of code.

    NOTE: This still affects line numbers when the replacements are applied,
    so you may need to re-run the program to see correct line numbers
    in error messages, or to use a debugger sensibly.
    """

    for file, file_replacements in _replacements.items():
        # Safeguard against modifying unexpected files.
        # Do not modify files outside the tests directory,
        # as this could be dangerous.
        # Note that during testing of this module,
        # test files will be saved to a temporary directory,
        # such as /tmp/pytest-of-io/pytest-83/tests0/test_update_expected_var.py
        # (Note the number after "tests" in the path.)
        if not any(part.startswith("tests") for part in Path(file).parts):
            raise UpdateExpectedError(f"File {file!r} is not in the tests directory")

        # Do not modify files that have already been modified,
        # as mismatched line numbers could lead to incorrect replacements.
        if file in _modified_files:
            raise UpdateExpectedError(f"File {file!r} has already been modified by this module")

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
        # and then by decreasing column number, using a tuple
        file_replacements = sorted(file_replacements, reverse=True, key=lambda x: (x[0].end_line, x[0].start_line, x[0].end_column, x[0].start_column))

        # Raise an error if any replacements overlap
        for i, (span1, content1) in enumerate(file_replacements):
            for span2, content2 in file_replacements[i + 1:]:
                if _any_overlap(span1, span2):
                    raise UpdateExpectedError(f"Replacements overlap in file {file!r}:\n  {span1!r} {content1!r}\n  {span2!r} {content2!r}\non line {span1.start_line + 1}:\n{source_lines[span1.start_line].rstrip()}\n{' ' * span1.start_column}{'A' * (span1.end_column - span1.start_column)}\n{' ' * span2.start_column}{'B' * (span2.end_column - span2.start_column)}\n")

        # Replace the lines with the new content
        for span, new_content in file_replacements:
            new_lines = new_content.splitlines(keepends=True)
            new_lines[0] = source_lines[span.start_line][:span.start_column] + new_lines[0]
            new_lines[-1] = new_lines[-1] + source_lines[span.end_line][span.end_column:]
            print("Replacing", span, repr(source_lines[span.start_line:span.end_line + 1]), "with", repr(new_lines))
            source_lines[span.start_line:span.end_line + 1] = new_lines

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

            print(f"""Updated `expected` in {file!r}
Note: Line numbers in this file (after {first_modified_line}) may have changed.
You may need to re-run the program to see correct line numbers in error messages, or use a debugger.""")

            _modified_files.add(file)
        _replacements[file].clear()


def _exit_handler():
    """Commit all source code replacements when the program exits."""
    _commit_replacements()

atexit.register(_exit_handler)

__all__ = ["update_expected"]
