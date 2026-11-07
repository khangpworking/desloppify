# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Identify actual tagged console calls, excluding comments and string contents."""

from __future__ import annotations

import re
import sys
from functools import lru_cache

_CALLEE = re.compile(rb"console\s*\.\s*(?:log|warn|info|debug)\Z")
_TAG = re.compile(r"^[\"'`].{0,4}\[([^\]]+)\]", re.DOTALL)
_VARIABLE_TAG = re.compile(r"^`\$\{\w*(?:TAG|DEBUG|LOG)\w*\}", re.IGNORECASE)


@lru_cache(maxsize=2)
def _parser(grammar):
    try:
        from tree_sitter_language_pack import get_parser

        return get_parser(grammar)
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        print(
            f"Tagged log analysis unavailable: {exc}. Install desloppify[full]; no log fixes will be applied.",
            file=sys.stderr,
        )
        return None


def logs_parser_available() -> bool:
    """Both grammars are needed to cover a mixed TS/TSX project."""
    return all(_parser(grammar) is not None for grammar in ("typescript", "tsx"))


def tagged_log_calls(
    source: bytes, grammar: str = "typescript"
) -> list[tuple[object, str]]:
    parser = _parser(grammar)
    if parser is None:
        return []
    tree = parser.parse(source)
    found = []
    stack = [tree.root_node]
    while stack:
        node = stack.pop()
        stack.extend(reversed(node.named_children))
        if node.type != "call_expression" or node.has_error:
            continue
        callee = node.child_by_field_name("function")
        args = node.child_by_field_name("arguments")
        if (
            callee is None
            or args is None
            or not _CALLEE.fullmatch(source[callee.start_byte : callee.end_byte])
        ):
            continue
        if b"?." in source[callee.end_byte : args.start_byte]:
            continue
        values = [n for n in args.named_children if n.type != "comment"]
        if not values:
            continue
        first = source[values[0].start_byte : values[0].end_byte].decode("utf-8")
        match = _TAG.match(first)
        if match or _VARIABLE_TAG.match(first):
            found.append((node, match.group(1) if match else "unknown"))
    return found


__all__ = ["tagged_log_calls", "logs_parser_available"]
