#!/usr/bin/env python3
"""
Audit script for quality-evaluation artifacts.

Generates a markdown report listing:
- Python packages/modules under `quality_evaluation/`
- Test suites under `tests/quality_evaluation/`
- CI configuration snippets referencing quality evaluation
- Identified gaps (missing implementation files, failing tests placeholder)
"""

import pathlib
import re
import sys


def find_files(pattern: str):
    """Return a sorted list of Path objects matching *pattern* relative to the repo root."""
    return sorted(p for p in pathlib.Path('.').rglob(pattern) if p.is_file())


def main():
    report_lines = ["# Quality Evaluation Audit Report", ""]

    # 1. Discover package files
    qe_modules = find_files("quality_evaluation/**/*.py")
    report_lines.append("## Discovered `quality_evaluation` package files")
    if qe_modules:
        for p in qe_modules:
            report_lines.append(f"- `{p}`")
    else:
        report_lines.append("- *None found*")
    report_lines.append("")

    # 2. Discover test files
    test_files = find_files("tests/quality_evaluation/**/*.py")
    report_lines.append("## Discovered test files")
    if test_files:
        for p in test_files:
            report_lines.append(f"- `{p}`")
    else:
        report_lines.append("- *None found*")
    report_lines.append("")

    # 3. CI configuration snippets referencing quality evaluation
    ci_files = find_files(".github/workflows/*.yml") + find_files(".github/workflows/*.yaml")
    ci_matches = []
    for p in ci_files:
        try:
            content = p.read_text()
        except Exception:
            continue
        if re.search(r"quality[-_]evaluation", content, re.IGNORECASE):
            ci_matches.append(p)
    report_lines.append("## CI configuration referencing quality evaluation")
    if ci_matches:
        for p in ci_matches:
            report_lines.append(f"- `{p}`")
    else:
        report_lines.append("- *None found*")
    report_lines.append("")

    # 4. Identify gaps
    report_lines.append("## Identified gaps")
    gaps = []
    if not qe_modules:
        gaps.append("- Missing `quality_evaluation` package.")
    else:
        init_path = pathlib.Path("quality_evaluation/__init__.py")
        if not init_path.is_file():
            gaps.append("- Missing `quality_evaluation/__init__.py`.")
        core_path = pathlib.Path("quality_evaluation/evaluator.py")
        if not core_path.is_file():
            gaps.append("- Missing core evaluator implementation (`evaluator.py`).")
    if not test_files:
        gaps.append("- No test suite for quality evaluation.")
    if not ci_matches:
        gaps.append("- CI does not run quality evaluation tests.")
    if gaps:
        report_lines.extend(gaps)
    else:
        report_lines.append("- No obvious gaps detected.")

    sys.stdout.write("\n".join(report_lines))


if __name__ == "__main__":
    main()
