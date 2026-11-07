# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Removing diagnostics must preserve JavaScript evaluation and application state."""

import json
import shutil
import subprocess

import pytest

from desloppify.languages.typescript.detectors.logs import detect_logs
from desloppify.languages.typescript.fixers.logs import fix_debug_logs


def test_missing_parser_leaves_source_unchanged_and_reports_reduced_coverage(
    tmp_path, set_project_root, monkeypatch
):
    from desloppify.languages.typescript import TypeScriptConfig
    from desloppify.languages.typescript.detectors import logs_syntax

    monkeypatch.setattr(logs_syntax, "_parser", lambda grammar: None)
    path = tmp_path / "main.ts"
    source = "let n = 0; console.log('[DEBUG]', ++n);\n"
    path.write_text(source, encoding="utf-8")
    fix_debug_logs([{"file": str(path), "line": 1, "tag": "DEBUG"}])
    assert path.read_text(encoding="utf-8") == source
    coverage = TypeScriptConfig().scan_coverage_prerequisites()
    assert any(
        c.detector == "logs" and c.status == "reduced" and c.confidence == 0
        for c in coverage
    )


@pytest.mark.skipif(
    shutil.which("node") is None, reason="Node is required for behavioral proof"
)
@pytest.mark.parametrize(
    "source,expression,expected_logs",
    [
        ("let n = 0;\nconsole.log('[DEBUG]', ++n);", "n", 1),
        ("let n = 0;\nconst value = ++n;\nconsole.log('[DEBUG]', value);", "n", 1),
        ("function value() { console.log('[DEBUG]'); return 7; }", "value()", 1),
        ("let n = 0;\nif (++n) {\nconsole.log('[DEBUG]');\n}", "n", 1),
        ("const n = 12;\nconsole.log(\n'[DEBUG]',\nn\n);", "n", 1),
        ("const text = `\nconsole.log('[DEBUG] example');\n`;", "text", 0),
        ("const text = /console.log('[DEBUG]')/;", "text.source", 0),
        ("// console.log('[DEBUG] example');\nconst n = 4;", "n", 0),
        (
            "const events = [];\nconsole.log('[DEBUG]', ...{*[Symbol.iterator]() {events.push(1); yield 2;}});",
            "events",
            1,
        ),
        (
            "const events = [];\nconst obj = {get value() {events.push('read');return 1;}};\nconsole.log('[DEBUG]', obj.value);",
            "events",
            1,
        ),
        (
            "let n = 0;\nconst result = console.log('[DEBUG]', ++n);",
            "[n, result === undefined]",
            1,
        ),
        ("let n = 0;\nconsole.log('[DEBUG]', console.log('[INNER]', ++n));", "n", 2),
        ("let n = 0;\nif (++n) console.log('[DEBUG]'); else n = 9;", "n", 1),
        (
            "let n = 0;\nconsole.log('[DEBUG]', ++n); console.log('[TRACE]', ++n);",
            "n",
            2,
        ),
    ],
)
def test_cleanup_preserves_evaluation(
    tmp_path, set_project_root, source, expression, expected_logs
):
    pytest.importorskip("tree_sitter_language_pack")
    path = tmp_path / "main.ts"
    code = source + "\nprocess.stderr.write(JSON.stringify(" + expression + "));\n"
    path.write_text(code, encoding="utf-8")

    def observe(text):
        result = subprocess.run(
            [shutil.which("node"), "--input-type=module"],
            input=text,
            text=True,
            capture_output=True,
            check=True,
        )
        return json.loads(result.stderr)

    before = observe(code)
    entries = detect_logs(tmp_path).entries
    assert len(entries) == expected_logs
    fix_debug_logs(entries, dry_run=True)
    assert path.read_text(encoding="utf-8") == code
    fix_debug_logs(entries)
    after = path.read_text(encoding="utf-8")
    assert observe(after) == before
    assert not detect_logs(tmp_path).entries
    fix_debug_logs(detect_logs(tmp_path).entries)
    assert path.read_text(encoding="utf-8") == after
