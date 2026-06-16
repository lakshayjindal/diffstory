"""CLI entry point for DiffStory — parse arguments, gather diffs, generate reports."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from diffstory import __version__
from diffstory.diff_parser import parse_diff
from diffstory.git_utils import (
    GitError,
    check_git_repo,
    get_diff,
    get_diff_with_renames,
)
from diffstory.html_generator import generate_report


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="diffstory",
        description="Transform Git diffs into rich, interactive, self-contained HTML reports.",
        epilog=(
            "Examples:\\n"
            "  diffstory                    # working tree diff\\n"
            "  diffstory --staged           # staged changes\\n"
            "  diffstory HEAD~3 HEAD        # commit comparison\\n"
            "  diffstory main feature       # branch comparison\\n"
            "  diffstory -o report.html     # custom output file\\n"
            "  diffstory --json             # JSON export\\n"
            "  diffstory HEAD~3 HEAD src/   # restrict to path"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"diffstory {__version__}",
    )

    parser.add_argument(
        "--staged",
        action="store_true",
        help="Show staged changes (equivalent to git diff --cached)",
    )

    parser.add_argument(
        "revisions",
        nargs="*",
        metavar="REVISION",
        help="Optional commit range: REVISION [REVISION] [-- path]",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="diffstory-report.html",
        metavar="FILE",
        help="Output file path (default: diffstory-report.html)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Export diff data as JSON",
    )

    parser.add_argument(
        "--md",
        action="store_true",
        help="Export diff summary as Markdown",
    )

    parser.add_argument(
        "--csv",
        action="store_true",
        help="Export diff stats as CSV",
    )

    return parser


def _parse_revisions(args: argparse.Namespace) -> tuple[Optional[str], Optional[str], Optional[list[str]]]:
    """Extract commit range and optional path restriction from positional args.

    Supports:
        []                        -> working tree
        [COMMIT_A, COMMIT_B]      -> commit comparison
        [COMMIT_A, COMMIT_B, --, path] -> restricted comparison
        [COMMIT]                  -> comparison with HEAD
    """
    revisions = args.revisions
    paths: Optional[list[str]] = None
    commit_a: Optional[str] = None
    commit_b: Optional[str] = None

    if not revisions:
        return None, None, None

    # Check for path separator
    if "--" in revisions:
        sep_idx = revisions.index("--")
        revisions = revisions[:sep_idx]
        paths = revisions[sep_idx + 1:]

    if len(revisions) == 1:
        commit_a = revisions[0]
    elif len(revisions) >= 2:
        commit_a = revisions[0]
        commit_b = revisions[1]

    return commit_a, commit_b, paths


def generate_exports(
    files,
    output_path: str,
    json_export: bool = False,
    md_export: bool = False,
    csv_export: bool = False,
) -> None:
    """Generate non-HTML export formats."""
    base = Path(output_path)
    stem = base.stem

    if json_export:
        _export_json(files, base.with_name(stem + ".json"))
    if md_export:
        _export_markdown(files, base.with_name(stem + ".md"))
    if csv_export:
        _export_csv(files, base.with_name(stem + ".csv"))


def _export_json(files, output_path: Path) -> None:
    """Export diff data as JSON."""
    import json

    data = []
    for f in files:
        file_data = {
            "old_path": f.old_path,
            "new_path": f.new_path,
            "status": f.status,
            "hunks": [],
        }
        for hunk in f.hunks:
            hunk_data = {
                "old_start": hunk.old_start,
                "old_count": hunk.old_count,
                "new_start": hunk.new_start,
                "new_count": hunk.new_count,
                "lines": [],
            }
            for line in hunk.lines:
                hunk_data["lines"].append({
                    "type": line.line_type,
                    "content": line.content,
                    "old_lineno": line.old_lineno,
                    "new_lineno": line.new_lineno,
                })
            file_data["hunks"].append(hunk_data)
        data.append(file_data)

    output_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"  JSON: {output_path}")


def _export_markdown(files, output_path: Path) -> None:
    """Export diff summary as Markdown."""
    lines = ["# DiffStory Report\n"]
    for f in files:
        adds = sum(1 for h in f.hunks for l in h.lines if l.line_type == "addition")
        dels = sum(1 for h in f.hunks for l in h.lines if l.line_type == "deletion")
        status_icon = {"added": "+", "deleted": "-", "renamed": "→", "modified": "~"}.get(f.status, "~")
        lines.append(f"## {status_icon} `{f.display_path}`")
        lines.append(f"- **Status:** {f.status}")
        lines.append(f"- **Additions:** {adds}")
        lines.append(f"- **Deletions:** {dels}\n")
        for hunk in f.hunks:
            lines.append(f"### @@ {hunk.old_start},{hunk.old_count} {hunk.new_start},{hunk.new_count} @@")
            if hunk.header:
                lines.append(f"_{hunk.header}_\n")
            for line in hunk.lines:
                prefix = {"context": " ", "addition": "+", "deletion": "-"}[line.line_type]
                lines.append(f"    {prefix} {line.content}")
            lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Markdown: {output_path}")


def _export_csv(files, output_path: Path) -> None:
    """Export diff stats as CSV."""
    rows = ["file,status,additions,deletions"]
    for f in files:
        adds = sum(1 for h in f.hunks for l in h.lines if l.line_type == "addition")
        dels = sum(1 for h in f.hunks for l in h.lines if l.line_type == "deletion")
        rows.append(f"{f.display_path},{f.status},{adds},{dels}")

    output_path.write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"  CSV: {output_path}")


def main() -> None:
    """Main entry point for the diffstory CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # Validate Git repository
    if not check_git_repo():
        print("Error: Not inside a Git repository.", file=sys.stderr)
        sys.exit(1)

    # Parse revisions
    commit_a, commit_b, paths = _parse_revisions(args)

    try:
        # Get diff
        diff_text = get_diff_with_renames(
            staged=args.staged,
            commit_a=commit_a,
            commit_b=commit_b,
            paths=paths,
        )
    except GitError as e:
        print(f"Error fetching diff: {e}", file=sys.stderr)
        sys.exit(1)

    if not diff_text.strip():
        print("No changes detected.")
        sys.exit(0)

    # Parse diff
    files = parse_diff(diff_text)

    if not files:
        print("No parseable diff files found.")
        sys.exit(0)

    # Generate exports if requested
    has_exports = args.json or args.md or args.csv
    if has_exports:
        generate_exports(files, args.output, args.json, args.md, args.csv)

    # Always generate HTML report
    try:
        report_path = generate_report(
            files,
            output_path=args.output,
            staged=args.staged,
            commit_a=commit_a,
            commit_b=commit_b,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\\n  HTML: {report_path}")
    print("  Report generated successfully!")
