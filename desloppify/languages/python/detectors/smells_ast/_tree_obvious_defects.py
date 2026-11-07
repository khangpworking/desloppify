# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Conservative checks for explicit debug output and discarded control flow."""

from __future__ import annotations

import ast
import re


def _detect_constant_condition(filepath, tree, all_nodes):
    return [
        {
            "file": filepath,
            "line": node.lineno,
            "content": f"constant condition: {node.test.value}",
        }
        for node in all_nodes
        if isinstance(node, (ast.If, ast.IfExp))
        and isinstance(node.test, ast.Constant)
        and isinstance(node.test.value, bool)
    ]


def _detect_debug_print(filepath, tree, all_nodes):
    matches = []
    for node in all_nodes:
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "print"
            and node.args
        ):
            continue
        first = node.args[0]
        if isinstance(first, ast.JoinedStr) and first.values:
            first = first.values[0]
        if (
            isinstance(first, ast.Constant)
            and isinstance(first.value, str)
            and re.match(r"^\s*(?:DEBUG\b|\[DEBUG\])", first.value)
        ):
            matches.append(
                {
                    "file": filepath,
                    "line": node.lineno,
                    "content": "explicit debug print: " + first.value[:100],
                }
            )
    return matches


def _detect_function_redefinition(filepath, tree, all_nodes):
    matches = []
    # Each statement list is a separate execution branch. Decorators may
    # register overloads, properties or handlers, so leave them alone.
    for parent in all_nodes:
        for _, block in ast.iter_fields(parent):
            if not isinstance(block, list):
                continue
            definitions = {}
            for statement in block:
                if not isinstance(statement, ast.stmt):
                    continue
                if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    previous = definitions.pop(statement.name, None)
                    if statement.decorator_list:
                        continue
                    if previous is not None:
                        matches.append(
                            {
                                "file": filepath,
                                "line": statement.lineno,
                                "content": f"redefinition of {statement.name} from line {previous}",
                            }
                        )
                    definitions[statement.name] = statement.lineno
                else:
                    # A reference or assignment between definitions can retain
                    # the original function or deliberately change its binding.
                    for node in ast.walk(statement):
                        if isinstance(node, ast.Name):
                            definitions.pop(node.id, None)
    return matches
