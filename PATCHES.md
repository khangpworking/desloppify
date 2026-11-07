# Patched Desloppify fork

Maintained by khangpworking. Publication and per-file change notices added on
2026-11-08. Based on upstream commit
`3a7735d531a96b6a226bfbdc9fd662b14195f857`.
The `benchmark-fixes` branch contains the locally tested changes; it is not an
upstream release. The original Open Source Native License is retained in
[LICENSE](LICENSE), including its redistribution terms.

## Changes

- Replace whole-line debug-log deletion with syntax-aware edits that preserve
  argument evaluation and surrounding control flow. Remove unsafe dead-variable
  and block cleanup; share the safe implementation with the interactive fixer.
- Detect constant boolean branches, explicit debug prints, repeated function
  definitions, and Python syntax errors without mislabeling parse diagnostics.
- Include Ruff in the full extra, constrain the language pack to the tested
  compatible series, and report reduced coverage when required tools are absent.
- Refuse to publish a score for scans that analyze no source files.
- Repair Windows path handling and portable subprocess-test assumptions.
- Detect unreferenced private helpers of any size while respecting references,
  callbacks, explicit exports and the existing eligibility safeguards.
- Resolve imports from conventional `src/` layouts, restoring the real consumers
  of public APIs such as `click.testing` without filename-specific suppressions.

## Validation

Measured on 2026-11-07 with Python 3.12.13, Node 26.4.0 and Windows.

| Check | Original | Patched |
| --- | --- | --- |
| Seeded Python defects detected | 16/20 | 20/20 |
| Targeted false positives on corrected controls | 0/20 | 0/20 |
| Log-fixer cases preserving runtime behavior | 3/8 | 8/8 |
| Click testing.py orphan warning | Present | Absent; four real importers found |
| Full suite passed / failed | 6,805 / 31 | 6,890 / 0 |

Three pre-existing Roslyn integration tests remain skipped. Lint, configured
mypy checks, the import architecture contract, distribution builds and Twine
checks passed. The built wheel was independently installed and verified.
Original suite figures use the compatible parser to make the comparison fair.
The suite improvement includes corrections to Windows-incompatible tests as
well as production repairs.

The seeded and corrected cases are a known regression corpus, not a held-out
estimate of general accuracy. Seven incidental findings remain on the corrected
corpus. The Click scan still has 200 findings requiring review, and its changed
score reflects changed analysis, not edits to Click itself. Static analysis
cannot establish every dynamic or external reference.

All three isolated repetitions per target had identical finding IDs. The latest
focused cases failed before their corresponding repairs and passed afterward.
Publication adds notices and documentation only: Python ASTs and parsed package
configuration were checked to be identical to the benchmarked source.
