# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Observable detector regressions, including nearby valid Python idioms."""

import pytest
import subprocess
import sys

from desloppify.languages.python.detectors.smells import detect_smells


@pytest.mark.parametrize(
    "source, expected",
    [
        ("if True:\n    value = 1\n", {"constant_condition"}),
        ("def f():\n    return 1\ndef f():\n    return 2\n", {"function_redefinition"}),
        ('print("DEBUG: value", 3)\n', {"debug_print"}),
        ("def broken(:\n    pass\n", {"syntax_error"}),
        ('print("Result:", 3)\n', set()),
        ("while True:\n    break\n", set()),
        ("if flag:\n    def f(): return 1\nelse:\n    def f(): return 2\n", set()),
        (
            "@overload\ndef f(x: int): ...\n@overload\ndef f(x: str): ...\ndef f(x): return x\n",
            set(),
        ),
        ("def f(): return 1\nold_f = f\ndef f(): return 2\n", set()),
    ],
)
def test_python_defect_detection(tmp_path, source, expected):
    (tmp_path / "example.py").write_text(source, encoding="utf-8")
    entries, checked = detect_smells(tmp_path)
    relevant = {
        "constant_condition",
        "function_redefinition",
        "debug_print",
        "syntax_error",
    }
    assert checked == 1
    assert {entry["id"] for entry in entries} & relevant == expected


def test_empty_scan_does_not_publish_a_perfect_score(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "desloppify",
            "--lang",
            "python",
            "scan",
            "--path",
            ".",
            "--profile",
            "objective",
            "--no-badge",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 2
    assert "no source files" in (result.stdout + result.stderr).lower()
    assert not (tmp_path / ".desloppify" / "state-python.json").exists()
