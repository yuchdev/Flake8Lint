"""Built-in AST rule catalogue for flake8-lint."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

from .api import RuleContext, RuleViolation
from .registry import RuleRegistration


@dataclass(frozen=True)
class CallbackRule:
    code: str
    description: str
    callback: Callable[[RuleContext], Iterable[RuleViolation]]

    def check(self, context: RuleContext) -> Iterable[RuleViolation]:
        return self.callback(context)


def builtin_registrations() -> tuple[RuleRegistration, ...]:
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
    return RuleViolation(
        filename=context.filename,
        lineno=getattr(node, "lineno", 1),
        col_offset=getattr(node, "col_offset", 0),
        code=code,
        message=message,
    )


def _check_bare_except(context: RuleContext) -> Iterable[RuleViolation]:
    for node in ast.walk(context.tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            yield _violation(
                context,
                node,
                "X001",
                "Do not use bare `except:`; catch specific exceptions.",
            )


def _contains_exception(exc_node: ast.expr) -> bool:
    if isinstance(exc_node, ast.Name) and exc_node.id == "Exception":
        return True
    if isinstance(exc_node, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id == "Exception" for elt in exc_node.elts)
    return False


def _check_broad_exception(context: RuleContext) -> Iterable[RuleViolation]:
    for node in ast.walk(context.tree):
        if (
            isinstance(node, ast.ExceptHandler)
            and node.type is not None
            and _contains_exception(node.type)
        ):
            yield _violation(
                context,
                node,
                "X002",
                "Do not use `except Exception:`; catch a more specific exception.",
            )


def _check_reserved(context: RuleContext) -> Iterable[RuleViolation]:
    del context
    return ()


def _is_muting_stmt(stmt: ast.stmt) -> bool:
    if isinstance(stmt, (ast.Pass, ast.Continue, ast.Break, ast.Return)):
        return True
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and stmt.value.value is Ellipsis
    )


def _check_muted_exception(context: RuleContext) -> Iterable[RuleViolation]:
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


def _has_proper_docstring(node: ast.AST, lines: Sequence[str] | None) -> bool:
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
    return doc_line.startswith('"""')


def _docstring_has_structured_header(doc: str) -> bool:
    header_re = re.compile(r"^\s*\[(Unit|Integration|Local|E2E)]\s+\S.*$")
    for line in doc.splitlines():
        if line.strip():
            return bool(header_re.match(line))
    return False


def _docstring_has_section(doc: str, section_name: str) -> bool:
    return any(line.strip().startswith(section_name) for line in doc.splitlines())


def _has_test_imports(tree: ast.AST) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in {"pytest", "unittest"}:
                    return True
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split(".", 1)[0] in {"pytest", "unittest"}:
                return True
    return False


def _is_test_module(context: RuleContext) -> bool:
    path = Path(context.filename)
    name = path.name
    if name.startswith("test_") or name.endswith("_test.py"):
        return True
    if any(parent.name == "tests" for parent in path.parents):
        return True
    return _has_test_imports(context.tree)


def _iter_test_functions(tree: ast.AST) -> Iterable[ast.AST]:
    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.class_stack: list[ast.ClassDef] = []
            self.function_depth = 0
            self.results: list[ast.AST] = []

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            self.class_stack.append(node)
            self.generic_visit(node)
            self.class_stack.pop()

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self._visit_function(node)

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self._visit_function(node)

        def _visit_function(self, node: ast.AST) -> None:
            name = getattr(node, "name", "")
            outermost = self.function_depth == 0
            if outermost and name.startswith("test"):
                if not self.class_stack or self.class_stack[-1].name.startswith("Test"):
                    self.results.append(node)
            self.function_depth += 1
            self.generic_visit(node)
            self.function_depth -= 1

    visitor = Visitor()
    visitor.visit(tree)
    return visitor.results


def _check_docstrings(context: RuleContext) -> Iterable[RuleViolation]:
    lines = context.source.splitlines() if context.source is not None else None
    generic_message = (
        "Missing or improperly formatted docstring: add a coherent docstring block as the first "
        "statement in the body."
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
                        "Missing or incomplete structured test docstring: include "
                        "the required header and sections.",
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
    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.depth = 0
            self.violations: list[RuleViolation] = []

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            self.depth += 1
            self.generic_visit(node)
            self.depth -= 1

        def visit_Import(self, node: ast.Import) -> None:
            if self.depth > 0:
                self.violations.append(
                    _violation(
                        context,
                        node,
                        "X006",
                        "Do not use local imports inside function bodies; move "
                        "imports to module scope.",
                    )
                )

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            if self.depth > 0:
                self.violations.append(
                    _violation(
                        context,
                        node,
                        "X006",
                        "Do not use local imports inside function bodies; move "
                        "imports to module scope.",
                    )
                )

        def visit_Call(self, node: ast.Call) -> None:
            if self.depth > 0 and isinstance(node.func, ast.Name) and node.func.id == "__import__":
                self.violations.append(
                    _violation(
                        context,
                        node,
                        "X006",
                        "Do not use local imports inside function bodies; move "
                        "imports to module scope (including __import__() calls).",
                    )
                )
            self.generic_visit(node)

    visitor = Visitor()
    visitor.visit(context.tree)
    return tuple(visitor.violations)


def _function_returns_value(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    class Visitor(ast.NodeVisitor):
        def __init__(self) -> None:
            self.returns_value = False

        def visit_Return(self, ret: ast.Return) -> None:
            if ret.value is not None:
                self.returns_value = True

        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            del node
            return None

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            del node
            return None

        def visit_Lambda(self, node: ast.Lambda) -> None:
            del node
            return None

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            del node
            return None

    visitor = Visitor()
    for stmt in node.body:
        visitor.visit(stmt)
    return visitor.returns_value


def _check_missing_return_annotation(context: RuleContext) -> Iterable[RuleViolation]:
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


def _expr_is_none(expr: ast.expr | None) -> bool:
    if expr is None:
        return False
    if isinstance(expr, ast.Name) and expr.id == "None":
        return True
    return isinstance(expr, ast.Constant) and expr.value is None


def _check_none_return_annotation(context: RuleContext) -> Iterable[RuleViolation]:
    for node in ast.walk(context.tree):
        if isinstance(
            node,
            (ast.FunctionDef, ast.AsyncFunctionDef),
        ) and _expr_is_none(node.returns):
            yield _violation(
                context,
                node,
                "X008",
                "Do not use an explicit '-> None' return annotation; omit the "
                "return type instead for functions that return nothing.",
            )


def _check_percent_formatting(context: RuleContext) -> Iterable[RuleViolation]:
    percent_pattern = r"%(?:\(\w+\))?[-#0 +]*\d*(?:\.\d+)?[hlL]?[diouxXeEfFgGcrs]"

    def has_percent_placeholders(value: str) -> bool:
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
                "Do not use old-style '%' string formatting (e.g. '%s', '%d'); "
                "use f-strings instead.",
            )


def _except_catches_import_error(handler: ast.ExceptHandler) -> bool:
    if handler.type is None:
        return False
    names = {"ImportError", "ModuleNotFoundError"}
    if isinstance(handler.type, ast.Name):
        return handler.type.id in names
    if isinstance(handler.type, ast.Tuple):
        return any(isinstance(elt, ast.Name) and elt.id in names for elt in handler.type.elts)
    return False


def _except_handler_has_raise(handler: ast.ExceptHandler) -> bool:
    return any(isinstance(node, ast.Raise) for stmt in handler.body for node in ast.walk(stmt))


def _has_import_in_body(body: Sequence[ast.stmt]) -> bool:
    for stmt in body:
        for node in ast.walk(stmt):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                return True
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "__import__"
            ):
                return True
    return False


def _check_import_error_suppression(context: RuleContext) -> Iterable[RuleViolation]:
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


def _is_union_with_none(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    found_none = False
    found_union = False
    for node in ast.walk(annotation):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            found_union = True
        if _expr_is_none(node):
            found_none = True
    return found_union and found_none


def _is_union_without_none(annotation: ast.expr | None) -> bool:
    if annotation is None:
        return False
    found_none = False
    found_union = False
    for node in ast.walk(annotation):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            found_union = True
        if _expr_is_none(node):
            found_none = True
    return found_union and not found_none


def _iter_annotations(tree: ast.AST) -> Iterable[ast.AST]:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in (
                list(node.args.posonlyargs)
                + list(node.args.args)
                + list(node.args.kwonlyargs)
            ):
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


def _check_union_none_annotations(context: RuleContext) -> Iterable[RuleViolation]:
    for annotation in _iter_annotations(context.tree):
        if _is_union_with_none(annotation):
            yield _violation(
                context,
                annotation,
                "X011",
                "Do not use `Type | None` in type hints; use `Optional[Type]` from typing instead.",
            )


def _check_union_type_annotations(context: RuleContext) -> Iterable[RuleViolation]:
    for annotation in _iter_annotations(context.tree):
        if _is_union_without_none(annotation):
            yield _violation(
                context,
                annotation,
                "X012",
                "Do not use `Type1 | Type2` in type hints; use `Union[Type1, "
                "Type2]` from typing instead.",
            )
