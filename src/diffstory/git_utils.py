"""Git interaction via subprocess — zero external dependency on GitPython."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Raised when a git command fails."""


def _run_git(args: list[str], cwd: Optional[Path] = None) -> str:
    """Run a git command and return stdout.

    Raises GitError on non-zero exit.
    """
    if cwd is None:
        cwd = Path.cwd()

    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        msg = e.stderr.strip() or f"git command failed: git {' '.join(args)}"
        raise GitError(msg) from e
    except FileNotFoundError as e:
        raise GitError("Git executable not found. Is Git installed?") from e


def check_git_repo(cwd: Optional[Path] = None) -> bool:
    """Check if the current directory is inside a Git repository."""
    try:
        _run_git(["rev-parse", "--git-dir"], cwd=cwd)
        return True
    except GitError:
        return False


def get_diff(
    staged: bool = False,
    commit_a: Optional[str] = None,
    commit_b: Optional[str] = None,
    paths: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
) -> str:
    """Get a unified diff from Git.

    Mimics:
        git diff
        git diff --cached
        git diff COMMIT_A COMMIT_B
        git diff COMMIT_A COMMIT_B -- paths
    """
    args: list[str] = ["diff", "--no-color"]

    if staged:
        args.append("--cached")

    if commit_a is not None and commit_b is not None:
        args.append(f"{commit_a}..{commit_b}")
    elif commit_a is not None:
        args.append(commit_a)

    if paths:
        args.append("--")
        args.extend(paths)

    return _run_git(args, cwd=cwd)


def get_diff_with_renames(
    staged: bool = False,
    commit_a: Optional[str] = None,
    commit_b: Optional[str] = None,
    paths: Optional[list[str]] = None,
    cwd: Optional[Path] = None,
) -> str:
    """Get diff with rename detection enabled."""
    args: list[str] = ["diff", "--no-color", "--find-renames"]

    if staged:
        args.append("--cached")

    if commit_a is not None and commit_b is not None:
        args.append(f"{commit_a}..{commit_b}")
    elif commit_a is not None:
        args.append(commit_a)

    if paths:
        args.append("--")
        args.extend(paths)

    return _run_git(args, cwd=cwd)


def get_file_content(commit: str, filepath: str, cwd: Optional[Path] = None) -> str:
    """Get the content of a file at a specific commit."""
    return _run_git(["show", f"{commit}:{filepath}"], cwd=cwd)


def get_blame(
    filepath: str,
    cwd: Optional[Path] = None,
) -> list[dict]:
    """Get blame information for a file using --line-porcelain.

    Returns a list of dicts with keys: commit, author, author-mail, date, summary
    """
    try:
        output = _run_git(
            ["blame", "--line-porcelain", filepath],
            cwd=cwd,
        )
    except GitError:
        return []

    return _parse_blame_porcelain(output)


def _parse_blame_porcelain(output: str) -> list[dict]:
    """Parse git blame --line-porcelain output.

    Each entry starts with a header line:
        <commit> <orig_lineno> <final_lineno> <group>
    Followed by key-value metadata lines and a tab-prefixed content line.
    """
    lines = output.splitlines()
    results: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1

        # Skip blank lines and content lines
        if not line or line.startswith("\t"):
            continue

        parts = line.split()
        if len(parts) < 4:
            continue

        # Verify this looks like a commit header (hex hash or all zeros)
        commit = parts[0]
        if not _looks_like_commit(commit) and not parts[2].isdigit():
            continue

        if not parts[2].isdigit():
            continue

        lineno = int(parts[2])
        group = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 1

        entry: dict = {
            "commit": commit,
            "line": lineno,
            "group": group,
            "author": "",
            "author-mail": "",
            "date": "",
            "summary": "",
        }

        # Read metadata lines until we hit a tab-prefixed content line
        while i < len(lines):
            line = lines[i]
            if line.startswith("\t"):
                i += 1  # skip past the content line
                break
            if line.startswith("author ") and len(line) > 7:
                entry["author"] = line[7:]
            elif line.startswith("author-mail ") and len(line) > 12:
                entry["author-mail"] = line[12:]
            elif line.startswith("author-time ") and len(line) > 12:
                entry["date"] = line[12:]
            elif line.startswith("summary ") and len(line) > 8:
                entry["summary"] = line[8:]
            i += 1

        results.append(entry)

    return results


def get_repo_name(cwd: Optional[Path] = None) -> str:
    """Get the repository name from the remote or directory name."""
    try:
        remote_url = _run_git(["remote", "get-url", "origin"], cwd=cwd).strip()
        name = Path(remote_url).stem
        if name:
            return name
    except GitError:
        pass
    return Path.cwd().name if cwd is None else cwd.name
