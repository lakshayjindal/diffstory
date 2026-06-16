"""CLI entry point for DiffStory — parse arguments, gather diffs, generate reports."""

from __future__ import annotations

import argparse
import sys
import webbrowser
from pathlib import Path
from typing import Optional

from diffstory import __version__
from diffstory.diff_parser import parse_diff
from diffstory.git_utils import (
    GitError,
    check_git_repo,
    get_diff,
    get_diff_with_renames,
    get_git_root,
)
from diffstory.html_generator import generate_report


# ---------------------------------------------------------------------------
# Config file (.diffstory.toml) loader
# ---------------------------------------------------------------------------
DEFAULT_CONFIG_PATH = Path.home() / ".diffstory.toml"
LOCAL_CONFIG_PATH = Path.cwd() / ".diffstory.toml"


def _load_config() -> dict:
    """Load .diffstory.toml config from project or home directory.

    Returns a dict with keys that serve as defaults for CLI flags.
    """
    config: dict = {}

    for cfg_path in (LOCAL_CONFIG_PATH, DEFAULT_CONFIG_PATH):
        if cfg_path.exists():
            try:
                text = cfg_path.read_text(encoding="utf-8")
                config.update(_parse_toml_like(text))
            except Exception:
                pass  # ignore broken config files
    return config


def _parse_toml_like(text: str) -> dict:
    """Minimal TOML parser — enough for our trivial config schema."""
    result: dict = {}
    current_section: Optional[str] = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            current_section = stripped[1:-1].strip().lower()
            continue
        if "=" in stripped:
            key, _, val = stripped.partition("=")
            key = key.strip().lower()
            val = val.strip().strip('"').strip("'")
            # Lower-case boolean-ish strings
            if val.lower() in ("true", "yes", "on"):
                val = True
            elif val.lower() in ("false", "no", "off"):
                val = False
            else:
                try:
                    val = int(val)
                except ValueError:
                    pass
            full_key = f"{current_section}.{key}" if current_section else key
            result[full_key] = val
    return result


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

    parser.add_argument(
        "--diff",
        metavar="FILE",
        help="Generate report from a diff file directly (no git repository needed)",
    )

    parser.add_argument(
        "--no-open",
        action="store_true",
        default=False,
        help="Do not open the report in a browser after generation",
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=None,
        help="Show git commands and timing information",
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        default=None,
        help="Show detailed debug output including stack traces",
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


def _open_in_browser(path: str) -> None:
    """Open the generated report in the default browser."""
    try:
        file_url = "file://" + path
        webbrowser.open(file_url)
        print(f"  Opened in browser: {file_url}")
    except Exception as e:
        print(f"  Could not open browser: {e}", file=sys.stderr)


def _read_diff_from_file(path: str) -> str:
    """Read diff content from a file."""
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        print(f"Error: Diff file not found: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error reading diff file: {e}", file=sys.stderr)
        sys.exit(1)


def _resolve_output_path(given_path: str) -> str:
    """Resolve the output file path.

    If the given path is the default and we're inside a git repo,
    place it in a 'stories/' directory outside the git working tree
    so that git does not track it.
    """
    given = Path(given_path)
    # Only redirect the default path — if the user explicitly passed -o, use as-is
    if given.name != "diffstory-report.html":
        return str(given.resolve())

    try:
        git_root = get_git_root()
        if git_root:
            git_root = Path(git_root).resolve()
            stories_dir = git_root.parent / "stories"
            stories_dir.mkdir(parents=True, exist_ok=True)
            return str(stories_dir / given.name)
    except Exception:
        pass

    return str(given.resolve())


def main() -> None:
    """Main entry point for the diffstory CLI."""
    parser = build_parser()
    args = parser.parse_args()

    # Load config file for defaults
    config = _load_config()
    verbose = args.verbose if args.verbose is not None else config.get("cli.verbose", False)
    debug = args.debug if args.debug is not None else config.get("cli.debug", False)

    if debug:
        verbose = True  # debug implies verbose

    # Resolve output path — for the default, put it outside the git repo
    output_path = _resolve_output_path(args.output)

    # Handle --diff flag (read diff from file, no git needed)
    if args.diff:
        if verbose:
            print(f"  Reading diff file: {args.diff}")
        diff_text = _read_diff_from_file(args.diff)
        commit_a = None
        commit_b = None
        files = parse_diff(diff_text)
        if not files:
            print("No parseable diff files found.")
            sys.exit(0)
        has_exports = args.json or args.md or args.csv
        if has_exports:
            generate_exports(files, output_path, args.json, args.md, args.csv)
        try:
            report_path = generate_report(files, output_path=output_path, repo_name="diff", verbose=verbose)
        except Exception as e:
            if debug:
                import traceback
                traceback.print_exc()
            print(f"Error generating report: {e}", file=sys.stderr)
            sys.exit(1)
        print(f"\\n  HTML: {report_path}")
        print("  Report generated successfully!")

        # Open in browser unless --no-open
        if not args.no_open:
            _open_in_browser(report_path)
        return

    # Validate Git repository
    if not check_git_repo():
        print("Error: Not inside a Git repository.", file=sys.stderr)
        sys.exit(1)

    # Parse revisions
    commit_a, commit_b, paths = _parse_revisions(args)

    if verbose:
        rev_desc = "staged" if args.staged else "working tree"
        if commit_a and commit_b:
            rev_desc = f"{commit_a}..{commit_b}"
        elif commit_a:
            rev_desc = commit_a
        print(f"  Diff: {rev_desc}")

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

    if verbose:
        print(f"  Diff size: {len(diff_text)} bytes")

    # Parse diff
    files = parse_diff(diff_text)

    if not files:
        print("No parseable diff files found.")
        sys.exit(0)

    if verbose:
        print(f"  Files changed: {len(files)}")

    # Generate exports if requested
    has_exports = args.json or args.md or args.csv
    if has_exports:
        generate_exports(files, output_path, args.json, args.md, args.csv)

    # Always generate HTML report
    try:
        report_path = generate_report(
            files,
            output_path=output_path,
            staged=args.staged,
            commit_a=commit_a,
            commit_b=commit_b,
            verbose=verbose,
        )
    except Exception as e:
        if debug:
            import traceback
            traceback.print_exc()
        print(f"Error generating report: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"\\n  HTML: {report_path}")
    print("  Report generated successfully!")

    # Open in browser unless --no-open
    if not args.no_open:
        _open_in_browser(report_path)
