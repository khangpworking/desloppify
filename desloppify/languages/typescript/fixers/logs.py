# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Remove tagged logging while preserving argument evaluation and control flow."""

from __future__ import annotations

from desloppify.languages._framework.base.types import FixResult
from desloppify.languages.typescript.detectors.logs_syntax import tagged_log_calls
from desloppify.languages.typescript.fixers.fixer_io import apply_fixer
from desloppify.languages.typescript.fixers.logs_context import (
    is_logger_wrapper_context,
)


def fix_debug_logs(entries: list[dict], *, dry_run: bool = False) -> FixResult:
    def transform(lines, file_entries):
        source = "".join(lines).encode("utf-8")
        grammar = "tsx" if file_entries[0]["file"].endswith(".tsx") else "typescript"
        selected = {}
        for node, tag in tagged_log_calls(source, grammar):
            row, col = node.start_point
            if is_logger_wrapper_context(lines, row):
                continue
            if any(
                e["line"] == row + 1 and e.get("column", col + 1) == col + 1
                for e in file_entries
            ):
                selected[node.start_byte] = (node, tag)
        if not selected:
            return lines, []

        changes = {
            start: (node.end_byte, node) for start, (node, _) in selected.items()
        }
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line.encode("utf-8")))
        for node, _ in selected.values():
            row = node.start_point.row
            if (
                not source[offsets[row] : node.start_byte].strip()
                and row
                and lines[row - 1].lstrip().startswith("// DEBUG:")
            ):
                changes[offsets[row - 1]] = (offsets[row], None)
        ordered = sorted(changes.items())

        def render(start, end):
            pieces = []
            cursor = start
            for offset, (stop, node) in ordered:
                if offset < cursor or stop > end:
                    continue
                pieces.append(source[cursor:offset])
                if node is not None:
                    args = node.child_by_field_name("arguments")
                    evaluated = []
                    for arg in args.named_children:
                        if arg.type in {
                            "comment",
                            "string",
                            "number",
                            "true",
                            "false",
                            "null",
                        }:
                            continue
                        # Preserve spreads, getters, throws and calls in evaluation order.
                        evaluated.append(render(arg.start_byte, arg.end_byte))
                    pieces.append(
                        b"(void [" + b", ".join(evaluated) + b"])"
                        if evaluated
                        else b"(void 0)"
                    )
                cursor = stop
            pieces.append(source[cursor:end])
            return b"".join(pieces)

        return render(0, len(source)).decode("utf-8").splitlines(keepends=True), sorted(
            {tag for _, tag in selected.values()}
        )

    results = apply_fixer(entries, transform, dry_run=dry_run)
    return FixResult(
        entries=[
            {
                "file": r["file"],
                "removed": r["removed"],
                "tags": r["removed"],
                "lines_removed": r["lines_removed"],
                "log_count": sum(e["file"] == r["file"] for e in entries),
            }
            for r in results
        ]
    )


__all__ = ["fix_debug_logs"]
