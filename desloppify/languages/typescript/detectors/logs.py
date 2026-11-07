# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Tagged console.log('[Tag]') detection.

Catches:
- Direct tags: console.log('[Tag] ...')
- Emoji-prefixed tags: console.log('🔍 [Tag] ...')
- Template-literal tags: console.log(`${TAG_VAR} ...`) where TAG_VAR = '[Tag]'
"""

import argparse
import json
import logging
import re
from collections import defaultdict
from pathlib import Path

from desloppify.base.discovery.file_paths import rel, resolve_path
from desloppify.base.discovery.source import find_ts_and_tsx_files
from desloppify.base.output.fallbacks import log_best_effort_failure
from desloppify.base.output.terminal import colorize, print_table
from desloppify.languages.typescript.detectors.contracts import DetectorResult
from desloppify.languages.typescript.detectors.logs_syntax import tagged_log_calls

logger = logging.getLogger(__name__)


TAG_EXTRACT_RE = re.compile(r"\[([^\]]+)\]")


def detect_logs(path: Path) -> DetectorResult[dict]:
    """Detect tagged logs with explicit population semantics."""
    ts_files = find_ts_and_tsx_files(path)
    total_files = len(ts_files)

    entries = []
    for filepath in ts_files:
        file_path = Path(resolve_path(filepath))
        try:
            source = file_path.read_bytes()
            source.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            log_best_effort_failure(logger, f"read logs from {filepath}", exc)
            continue
        grammar = "tsx" if file_path.suffix == ".tsx" else "typescript"
        for node, tag in tagged_log_calls(source, grammar):
            entries.append(
                {
                    "file": filepath,
                    "line": node.start_point.row + 1,
                    "column": node.start_point.column + 1,
                    "tag": tag,
                    "content": source[node.start_byte : node.end_byte].decode("utf-8"),
                }
            )

    return DetectorResult(
        entries=entries, population_kind="files", population_size=total_files
    )


def cmd_logs(args: argparse.Namespace) -> None:
    result = detect_logs(Path(args.path))
    entries = result.entries
    if args.json:
        print(json.dumps({"count": len(entries), "entries": entries}, indent=2))
        return

    if not entries:
        print(colorize("No tagged console.logs found.", "green"))
        return

    by_file: dict[str, list] = defaultdict(list)
    for e in entries:
        by_file[e["file"]].append(e)
    sorted_files = sorted(by_file.items(), key=lambda x: -len(x[1]))

    by_tag: dict[str, int] = defaultdict(int)
    for e in entries:
        by_tag[e["tag"]] += 1

    print(
        colorize(
            f"\nTagged console.logs: {len(entries)} across {len(by_file)} files\n",
            "bold",
        )
    )

    print(colorize("Top tags:", "cyan"))
    for tag, count in sorted(by_tag.items(), key=lambda x: -x[1])[:10]:
        print(f"  [{tag}] × {count}")
    print()

    print(colorize("Top files:", "cyan"))
    rows = []
    for filepath, file_entries in sorted_files[: args.top]:
        rows.append([rel(filepath), str(len(file_entries))])
    print_table(["File", "Count"], rows, [70, 6])

    if args.fix:
        print(
            colorize(f"\n--fix: Will remove {len(entries)} tagged log lines.", "yellow")
        )
        confirm = input("Proceed? [y/N] ").strip().lower()
        if confirm == "y":
            _fix_logs(by_file)
        else:
            print("Aborted.")


def _fix_logs(by_file: dict[str, list]):
    from desloppify.languages.typescript.fixers.logs import fix_debug_logs

    result = fix_debug_logs(
        [entry for entries in by_file.values() for entry in entries]
    )
    print(colorize(f"Updated {len(result.entries)} files.", "green"))
