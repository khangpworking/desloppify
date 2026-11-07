# Modified by khangpworking on 2026-11-08 for benchmark repairs. See PATCHES.md.
"""Python language security + coverage wiring helpers."""

from __future__ import annotations

import shutil
from importlib.util import find_spec

from desloppify.base.config import load_config
from desloppify.base.discovery.source import collect_exclude_dirs
from desloppify.languages._framework.base.types import (
    DetectorCoverageStatus,
    LangSecurityResult,
)
from desloppify.languages.python.detectors.bandit_adapter import detect_with_bandit
from desloppify.languages.python._helpers import scan_root_from_files


def missing_bandit_coverage() -> DetectorCoverageStatus:
    return DetectorCoverageStatus(
        detector="security",
        status="reduced",
        confidence=0.6,
        summary="bandit is not installed — Python-specific security checks will be skipped.",
        impact=(
            "Python-specific security coverage is reduced; clean security output may "
            "miss shell injection, unsafe deserialization, and risky SQL/subprocess patterns."
        ),
        remediation="Install Bandit: pip install bandit",
        tool="bandit",
        reason="missing_dependency",
    )


def python_scan_coverage_prerequisites() -> list[DetectorCoverageStatus]:
    coverage = []
    if shutil.which("bandit") is None:
        coverage.append(missing_bandit_coverage())
    if shutil.which("ruff") is None and find_spec("ruff") is None:
        coverage.append(
            DetectorCoverageStatus(
                detector="smells",
                status="reduced",
                confidence=0.6,
                summary="Ruff is not installed; Ruff-backed Python checks are unavailable.",
                impact="Code-quality scores omit checks and can rise without code improvements.",
                remediation="Install Ruff: pip install ruff",
                tool="ruff",
                reason="missing_dependency",
            )
        )
        if find_spec("pyflakes") is None:
            coverage.append(
                DetectorCoverageStatus(
                    detector="unused",
                    status="reduced",
                    confidence=0.0,
                    summary="Neither Ruff nor Pyflakes is installed; unused-code checks are unavailable.",
                    impact="An empty unused-code result does not establish clean code.",
                    remediation="Install Ruff: pip install ruff",
                    tool="ruff",
                    reason="missing_dependency",
                )
            )
    return coverage


def _load_bandit_skip_tests() -> list[str] | None:
    """Read ``languages.python.bandit_skip_tests`` from project config."""
    cfg = load_config()
    lang_cfg = cfg.get("languages", {})
    py_cfg = lang_cfg.get("python", {}) if isinstance(lang_cfg, dict) else {}
    raw = py_cfg.get("bandit_skip_tests") if isinstance(py_cfg, dict) else None
    if isinstance(raw, list) and all(isinstance(t, str) for t in raw):
        return raw
    return None


def detect_python_security(files, zone_map) -> LangSecurityResult:
    scan_root = scan_root_from_files(files)
    if scan_root is None:
        return LangSecurityResult(entries=[], files_scanned=0)

    exclude_dirs = collect_exclude_dirs(scan_root)
    skip_tests = _load_bandit_skip_tests()
    result = detect_with_bandit(
        scan_root,
        zone_map,
        exclude_dirs=exclude_dirs,
        skip_tests=skip_tests,
    )
    coverage = result.status.coverage()
    return LangSecurityResult(
        entries=result.entries,
        files_scanned=result.files_scanned,
        coverage=coverage,
    )


__all__ = [
    "detect_python_security",
    "missing_bandit_coverage",
    "python_scan_coverage_prerequisites",
]
