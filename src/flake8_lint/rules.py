"""Built-in AST rule catalogue for flake8-lint."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

from .api import RuleContext, RuleViolation
from .registry import RuleRegistration


@dataclass(frozen=True)
class CallbackRule:
    """Adapt a plain callback function into a :class:`Rule`.

    :ivar code: The rule's unique code.
    :ivar description: Human-readable summary of the rule.
    :ivar callback: Function producing violations for a context.
    """

    code: str
    description: str
    callback: Callable[[RuleContext], Iterable[RuleViolation]]

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        """Delegate to the wrapped callback for *context*."""
        return self.callback(context)


def builtin_registrations() -> tuple[RuleRegistration, ...]:
    """Return the registrations for every built-in ``X###`` rule."""
    return (
        RuleRegistration(
            code="X001",
            description="Do not use bare except.",
            rule=CallbackRule("X001", "Do not use bare except.", _check_bare_except),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X002",
            description="Do not use except Exception.",
            rule=CallbackRule("X002", "Do not use except Exception.", _check_broad_exception),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X003",
            description="Reserved rule code.",
            rule=CallbackRule("X003", "Reserved rule code.", _check_reserved),
            provider="flake8_lint.builtin",
            enabled=False,
            reserved=True,
        ),
        RuleRegistration(
            code="X004",
            description="Do not silently swallow exceptions.",
            rule=CallbackRule(
                "X004",
                "Do not silently swallow exceptions.",
                _check_muted_exception,
            ),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X005",
            description="Require compliant docstrings.",
            rule=CallbackRule("X005", "Require compliant docstrings.", _check_docstrings),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X006",
            description="Do not use local imports.",
            rule=CallbackRule("X006", "Do not use local imports.", _check_local_imports),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X007",
            description="Require return annotations for value-returning functions.",
            rule=CallbackRule(
                "X007",
                "Require return annotations for value-returning functions.",
                _check_missing_return_annotation,
            ),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X008",
            description="Do not annotate returns with None.",
            rule=CallbackRule(
                "X008",
                "Do not annotate returns with None.",
                _check_none_return_annotation,
            ),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X009",
            description="Do not use percent formatting.",
            rule=CallbackRule("X009", "Do not use percent formatting.", _check_percent_formatting),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X010",
            description="Do not suppress ImportError.",
            rule=CallbackRule(
                "X010",
                "Do not suppress ImportError.",
                _check_import_error_suppression,
            ),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X011",
            description="Do not use Type | None.",
            rule=CallbackRule("X011", "Do not use Type | None.", _check_union_none_annotations),
            provider="flake8_lint.builtin",
        ),
        RuleRegistration(
            code="X012",
            description="Do not use Type1 | Type2.",
            rule=CallbackRule("X012", "Do not use Type1 | Type2.", _check_union_type_annotations),
            provider="flake8_lint.builtin",
        ),
    )


def _violation(context: RuleContext, node: ast.AST, code: str, message: str) -> RuleViolation:
    """Build a :class:`RuleViolation` at *node*'s position for *code*."""
    return RuleViolation(
        filename=context.filename,
        lineno=getattr(node, "lineno", 1),
        col_offset=getattr(node, "col_offset", 0),
        code=code,
        message=message,
    )


def _check_bare_except(context: RuleContext) -> Iterable[RuleViolation]:
    """X001: flag bare ``except:`` handlers."""
    for node in ast.walk(context.tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            yield _violation(
                context,
                node,
                "X001",
                "Do not use bare `except:`; catch specific exceptions.",
            )


def _contains_exception(exc_node: ast.expr) -> bool:
    """Return whether *exc_node* names ``Exception`` directly or in a tuple."""
    if isinstance(exc_node, ast.Name) and exc_node.id == "Exception":
        return True
    if isinstance(exc_node, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id == "Exception" for elt in exc_node.elts)
    return False


def _check_broad_exception(context: RuleContext) -> Iterable[RuleViolation]:
    """X002: flag ``except Exception:`` handlers."""
    for node in ast.walk(context.tree):
        if isinstance(node, ast.ExceptHandler) and node.type is not None and _contains_exception(node.type):
            yield _violation(
                context,
                node,
                "X002",
                "Do not use `except Exception:`; catch a more specific exception.",
            )


def _check_reserved(context: RuleContext) -> Iterable[RuleViolation]:
    """X003: reserved placeholder rule that never emits violations."""
    del context
    return ()


def _is_muting_stmt(stmt: ast.stmt) -> bool:
    """Return whether *stmt* silently mutes an exception handler."""
    if isinstance(stmt, (ast.Pass, ast.Continue, ast.Break, ast.Return)):
        return True
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis


def _check_muted_exception(context: RuleContext) -> Iterable[RuleViolation]:
    """X004: flag handlers whose body only mutes the caught exception."""
    for node in ast.walk(context.tree):
        if not isinstance(node, ast.ExceptHandler):
            continue
        if not node.body or all(_is_muting_stmt(stmt) for stmt in node.body):
            yield _violation(
                context,
                node,
                "X004",
                "Do not silently swallow exceptions; handle them or re-raise.",
            )


def _has_proper_docstring(node: ast.AST, lines: Optional[Sequence[str]]) -> bool:
    """Return whether *node*'s first statement is a triple-quoted docstring.

    When *lines* is provided, the opening quote style is verified against the
    source so that implicitly-concatenated or non-triple-quoted strings fail.
    """
    body = getattr(node, "body", None)
    if not body:
        return False
    first_stmt = body[0]
    if not isinstance(first_stmt, ast.Expr):
        return False
    value = getattr(first_stmt, "value", None)
    if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
        return False
    if lines is None:
        return True
    doc_line = lines[first_stmt.lineno - 1].lstrip()
    return doc_line.startswith(('"""', "'''"))


def _docstring_has_structured_header(doc: str) -> bool:
    """Return whether *doc* opens with a ``[Unit|Integration|...]`` header."""
    header_re = re.compile(r"^\s*\[(Unit|Integration|Local|E2E)]\s+\S.*$")
    for line in doc.splitlines():
        if line.strip():
            return bool(header_re.match(line))
    return False


def _docstring_has_section(doc: str, section_name: str) -> bool:
    """Return whether any line in *doc* starts with *section_name*."""
    return any(line.strip().startswith(section_name) for line in doc.splitlines())


def _has_test_imports(tree: ast.AST) -> bool:
    """Return whether *tree* imports ``pytest`` or ``unittest``."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in {"pytest", "unittest"}:
                    return True
        elif (
            isinstance(node, ast.ImportFrom) and node.module and node.module.split(".", 1)[0] in {"pytest", "unittest"}
        ):
            return True
    return False


def _is_test_module(context: RuleContext) -> bool:
    """Return whether *context* refers to a test module by name or imports."""
    path = Path(context.filename)
    name = path.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    if any(parent.name == "tests" for parent in path.parents):
        return True
    return _has_test_imports(context.tree)


def _iter_test_functions(tree: ast.AST) -> Iterable[ast.AST]:
    """Return the top-level ``test*`` functions inside ``Test*`` scopes."""

    class Visitor(ast.NodeVisitor):
        """Collect outermost test functions while tracking class/def nesting."""

        def __init__(self):
            """Initialise the empty class stack, depth counter, and results."""
            self.class_stack: list[ast.ClassDef] = []
            self.function_depth = 0
            self.results: list[ast.AST] = []

        def visit_ClassDef(self, node: ast.ClassDef):
            """Track the enclosing class while visiting its body."""
            self.class_stack.append(node)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef):
            """Dispatch a sync function definition to the shared handler."""
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            """Dispatch an async function definition to the shared handler."""
            self._visit_function(node)

        def _visit_function(self, node: ast.AST):
            """Record *node* when it is an outermost ``test*`` function."""
            name = getattr(node, "name", "")
            outermost = self.function_depth == 0
            if (
                outermost
                and name.startswith("test")
                and (not self.class_stack or self.class_stack[-1].name.startswith("Test"))
            ):
                self.results.append(node)
            self.function_depth += 1
            self.generic_visit(node)
            self.function_depth -= 1

    visitor = Visitor()
    visitor.visit(tree)
    return visitor.results


def _check_docstrings(context: RuleContext) -> Iterable[RuleViolation]:
    """X005: require compliant docstrings on classes, functions, and methods.

    Test modules additionally require the structured header and Scenario /
    Boundaries / On failure sections on their test functions.
    """
    lines = context.source.splitlines() if context.source is not None else None
    generic_message = (
        "Missing or improperly formatted docstring: add a coherent docstring block as the first statement in the body."
    )

    if _is_test_module(context):
        test_nodes = set(_iter_test_functions(context.tree))
        for node in ast.walk(context.tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node in test_nodes:
                if not _has_proper_docstring(node, lines):
                    yield _violation(
                        context,
                        node,
                        "X005",
                        "Missing or improperly formatted test docstring: add a "
                        "structured docstring as the first statement and include "
                        "Scenario, Boundaries, and On failure, first check "
                        "sections.",
                    )
                    continue
                raw_doc = ast.get_docstring(node, clean=False) or ""
                sections_ok = all(
                    _docstring_has_section(raw_doc, section)
                    for section in ("Scenario:", "Boundaries:", "On failure, first check:")
                )
                if not _docstring_has_structured_header(raw_doc) or not sections_ok:
                    yield _violation(
                        context,
                        node,
                        "X005",
                        "Missing or incomplete structured test docstring: include the required header and sections.",
                    )
            elif not _has_proper_docstring(node, lines):
                yield _violation(context, node, "X005", generic_message)
        return

    for node in ast.walk(context.tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef),
        ) and not _has_proper_docstring(node, lines):
            yield _violation(context, node, "X005", generic_message)


def _check_local_imports(context: RuleContext) -> Iterable[RuleViolation]:
    """X006: flag imports nested inside function or class bodies."""

    class Visitor(ast.NodeVisitor):
        """Track scope depth and record imports found below module scope."""

        def __init__(self):
            """Initialise the scope-depth counter and violation list."""
            self.depth = 0
            self.violations: list[RuleViolation] = []

        def visit_FunctionDef(self, node: ast.FunctionDef):
            """Descend into a sync function body, tracking nesting depth."""
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
            """Descend into an async function body, tracking nesting depth."""
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_ClassDef(self, node: ast.ClassDef):
            """Descend into a class body, tracking nesting depth."""
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_Import(self, node: ast.Import):
            """Record ``import`` statements found below module scope."""
            if self.depth > 0:
                self.violations.append(
                    _violation(
                        context,
                        node,
                        "X006",
                        "Do not use local imports inside function or class bodies; move imports to module scope.",
                    )
                )

        def visit_ImportFrom(self, node: ast.ImportFrom):
            """Record ``from ... import`` statements found below module scope."""
            if self.depth > 0:
                self.violations.append(
                    _violation(
                        context,
                        node,
                        "X006",
                        "Do not use local imports inside function or class bodies; move imports to module scope.",
                    )
                )

        def visit_Call(self, node: ast.Call):
            """Record ``__import__()`` calls found below module scope."""
            if self.depth > 0 and isinstance(node.func, ast.Name) and node.func.id == "__import__":
                self.violations.append(
                    _violation(
                        context,
                        node,
                        "X006",
                        "Do not use local imports inside function or class "
                        "bodies; move imports to module scope (including "
                        "__import__() calls).",
                    )
                )
            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(context.tree)
    return tuple(visitor.violations)


def _function_returns_value(node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> bool:
    """Return whether *node* has a ``return`` with a value in its own body."""
    queue: list[ast.AST] = list(node.body)
    while queue:
        current = queue.pop()
        if isinstance(current, ast.Return) and current.value is not None:
            return True
        if isinstance(
            current,
            (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda),
        ):
            continue
        queue.extend(ast.iter_child_nodes(current))
    return False


def _check_missing_return_annotation(context: RuleContext) -> Iterable[RuleViolation]:
    """X007: flag value-returning functions that lack a return annotation."""
    for node in ast.walk(context.tree):
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and _function_returns_value(node)
            and node.returns is None
        ):
            yield _violation(
                context,
                node,
                "X007",
                "Function or method returns a value but has no return type "
                "annotation; add an explicit '-> return_type' annotation.",
            )


def _expr_is_none(expr: Optional[ast.expr]) -> bool:
    """Return whether *expr* is the ``None`` literal."""
    if expr is None:
        return False
    if isinstance(expr, ast.Name) and expr.id == "None":
        return True
    return isinstance(expr, ast.Constant) and expr.value is None


def _check_none_return_annotation(context: RuleContext) -> Iterable[RuleViolation]:
    """X008: flag explicit ``-> None`` return annotations on non-stub functions."""
    for node in ast.walk(context.tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if _is_stub_body(node):
            continue
        if _expr_is_none(node.returns):
            yield _violation(
                context,
                node,
                "X008",
                "Do not use an explicit '-> None' return annotation; omit the "
                "return type instead for functions that return nothing.",
            )


def _check_percent_formatting(context: RuleContext) -> Iterable[RuleViolation]:
    """X009: flag old-style ``%`` string formatting on string literals."""
    percent_pattern = r"%(?:\(\w+\))?[-#0 +]*\d*(?:\.\d+)?[hlL]?[diouxXeEfFgGcrs]"

    def has_percent_placeholders(value: str) -> bool:
        """Return whether *value* contains a printf-style placeholder."""
        return bool(re.search(percent_pattern, value))

    for node in ast.walk(context.tree):
        if (
            isinstance(node, ast.BinOp)
            and isinstance(node.op, ast.Mod)
            and isinstance(node.left, ast.Constant)
            and isinstance(node.left.value, str)
            and has_percent_placeholders(node.left.value)
        ):
            yield _violation(
                context,
                node,
                "X009",
                "Do not use old-style '%' string formatting (e.g. '%s', '%d'); use f-strings instead.",
            )


def _except_catches_import_error(handler: ast.ExceptHandler) -> bool:
    """Return whether *handler* catches ``ImportError``/``ModuleNotFoundError``."""
    if handler.type is None:
        return False
    names = {"ImportError", "ModuleNotFoundError"}
    if isinstance(handler.type, ast.Name):
        return handler.type.id in names
    if isinstance(handler.type, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id in names for elt in handler.type.elts)
    return False


def _except_handler_has_raise(handler: ast.ExceptHandler) -> bool:
    """Return whether *handler*'s body contains a ``raise`` statement."""
    return any(isinstance(node, ast.Raise) for stmt in handler.body for node in ast.walk(stmt))


def _has_import_in_body(body: Sequence[ast.stmt]) -> bool:
    """Return whether *body* performs any import (statement or ``__import__``)."""
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return True
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "__import__":
                return True
    return False


def _check_import_error_suppression(context: RuleContext) -> Iterable[RuleViolation]:
    """X010: flag try/except blocks that swallow import failures."""
    for node in ast.walk(context.tree):
        if not isinstance(node, ast.Try):
            continue
        for handler in node.handlers:
            if (
                _except_catches_import_error(handler)
                and not _except_handler_has_raise(handler)
                and _has_import_in_body(node.body)
            ):
                yield _violation(
                    context,
                    handler,
                    "X010",
                    "Do not suppress ImportError/ModuleNotFoundError in "
                    "try/except; let import failures propagate instead of "
                    "converting them into optional dependencies.",
                )


def _is_stub_body(node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> bool:
    """Return whether *node*'s body is a single ``...`` stub statement."""
    if len(node.body) != 1:
        return False
    stmt = node.body[0]
    return isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant) and stmt.value.value is Ellipsis


def _is_union_with_none(annotation: Optional[ast.expr]) -> bool:
    """Return whether *annotation* is a top-level ``X | None`` union."""
    if not _is_top_level_union(annotation):
        return False
    members = list(_iter_union_members(annotation))
    return any(_expr_is_none(member) for member in members)


def _is_union_without_none(annotation: Optional[ast.expr]) -> bool:
    """Return whether *annotation* is a top-level union with no ``None`` member."""
    if not _is_top_level_union(annotation):
        return False
    members = list(_iter_union_members(annotation))
    return not any(_expr_is_none(member) for member in members)


def _iter_annotations(tree: ast.AST) -> Iterable[ast.AST]:
    """Yield every parameter, return, and variable annotation in *tree*."""
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in list(node.args.posonlyargs) + list(node.args.args) + list(node.args.kwonlyargs):
                if arg.annotation is not None:
                    yield arg.annotation
            if node.args.vararg and node.args.vararg.annotation is not None:
                yield node.args.vararg.annotation
            if node.args.kwarg and node.args.kwarg.annotation is not None:
                yield node.args.kwarg.annotation
            if node.returns is not None:
                yield node.returns
        elif isinstance(node, ast.AnnAssign):
            yield node.annotation


def _is_top_level_union(annotation: Optional[ast.expr]) -> bool:
    """Return whether *annotation* is a ``|`` union at its top level."""
    return isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr)


def _iter_union_members(annotation: ast.expr) -> Iterable[ast.expr]:
    """Yield the flattened member expressions of a ``|`` union annotation."""
    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        yield from _iter_union_members(annotation.left)
        yield from _iter_union_members(annotation.right)
        return
    yield annotation


def _check_union_none_annotations(context: RuleContext) -> Iterable[RuleViolation]:
    """X011: flag ``Type | None`` annotations that should use ``Optional``."""
    for annotation in _iter_annotations(context.tree):
        if _is_union_with_none(annotation):
            yield _violation(
                context,
                annotation,
                "X011",
                "Do not use `Type | None` in type hints; use `Optional[Type]` from typing instead.",
            )


def _check_union_type_annotations(context: RuleContext) -> Iterable[RuleViolation]:
    """X012: flag ``Type1 | Type2`` annotations that should use ``Union``."""
    for annotation in _iter_annotations(context.tree):
        if _is_union_without_none(annotation):
            yield _violation(
                context,
                annotation,
                "X012",
                "Do not use `Type1 | Type2` in type hints; use `Union[Type1, Type2]` from typing instead.",
            )
