"""Git interaction via subprocess — zero external dependency on GitPython."""

from __future__ import annotations

import re
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


def _looks_like_commit(s: str) -> bool:
    """Check if a string looks like a commit hash (hex or all-zeros placeholder)."""
    if len(s) < 6:
        return False
    return all(c in "0123456789abcdef" for c in s)


def get_log_for_file(
    filepath: str,
    follow: bool = False,
    max_count: int = 10,
    cwd: Optional[Path] = None,
) -> list[dict]:
    """Get commit log for a file."""
    args = ["log", f"--max-count={max_count}", "--format=%H|%an|%ae|%ai|%s"]
    if follow:
        args.append("--follow")
    args.append("--")
    args.append(filepath)

    try:
        output = _run_git(args, cwd=cwd)
    except GitError:
        return []

    entries = []
    for line in output.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            entries.append({
                "commit": parts[0],
                "author": parts[1],
                "email": parts[2],
                "date": parts[3],
                "summary": parts[4],
            })
    return entries


def get_commit_info(commit_hash: str, cwd: Optional[Path] = None) -> dict:
    """Get rich commit metadata for a given commit hash.

    Returns dict with: hash, author, author_email, author_date,
    committer, committer_email, committer_date, subject, body,
    parents, files_changed, insertions, deletions.
    """
    # Handle all-zero hash (uncommitted/staged changes)
    if all(c == "0" for c in commit_hash):
        return {
            "hash": commit_hash,
            "author": "Uncommitted",
            "author_email": "",
            "author_date": "",
            "committer": "Uncommitted",
            "committer_email": "",
            "committer_date": "",
            "parents": [],
            "subject": "Uncommitted change (staged or working tree)",
            "body": "",
            "files_changed": 0,
            "insertions": 0,
            "deletions": 0,
        }

    try:
        output = _run_git(
            ["log", "-1", "--format=%H|%an|%ae|%ai|%cn|%ce|%ci|%P|%s|%b", commit_hash],
            cwd=cwd,
        )
    except GitError:
        return {"hash": commit_hash, "subject": "unknown"}

    lines = output.strip().split("\n", 1)
    header_line = lines[0]
    body = lines[1] if len(lines) > 1 else ""

    parts = header_line.split("|", 9)
    if len(parts) < 9:
        return {"hash": commit_hash, "subject": "unknown"}

    # Count files changed, insertions, deletions (skip for all-zero/uncommitted)
    files_changed = 0
    insertions = 0
    deletions = 0
    if not all(c == "0" for c in commit_hash):
        try:
            stat_output = _run_git(
                ["diff", "--stat", f"{commit_hash}~1..{commit_hash}", "--"],
                cwd=cwd,
            )
            stat_lines = stat_output.strip().split("\n") if stat_output.strip() else []
            for line in stat_lines:
                m = re.search(r"(\d+) file[s]? changed", line)
                if m:
                    files_changed = int(m.group(1))
                m = re.search(r"(\d+) insertion", line)
                if m:
                    insertions += int(m.group(1))
                m = re.search(r"(\d+) deletion", line)
                if m:
                    deletions += int(m.group(1))
        except GitError:
            pass

    return {
        "hash": parts[0],
        "author": parts[1],
        "author_email": parts[2],
        "author_date": parts[3],
        "committer": parts[4],
        "committer_email": parts[5],
        "committer_date": parts[6],
        "parents": parts[7].split() if parts[7] else [],
        "subject": parts[8],
        "body": body.strip(),
        "files_changed": files_changed,
        "insertions": insertions,
        "deletions": deletions,
    }


def get_blame_for_revision(
    filepath: str,
    revision: Optional[str] = None,
    cwd: Optional[Path] = None,
) -> dict[int, dict]:
    """Get blame info for a file at a specific revision.

    Returns a dict mapping line numbers to blame entries.
    Each entry has: commit, author, author_mail, date, summary
    Handles group lengths: an entry with lineno=5, group=3 covers lines 5,6,7.

    If revision is None, blame the working tree version.
    """
    entries = get_blame(filepath, cwd=cwd) if revision is None else _get_blame_at_revision(filepath, revision, cwd)
    result: dict[int, dict] = {}
    for entry in entries:
        lineno = entry["line"]
        group = entry.get("group", 1)
        blame_info = {
            "commit": entry["commit"],
            "author": entry["author"],
            "author_mail": entry.get("author-mail", ""),
            "date": entry.get("date", ""),
            "summary": entry.get("summary", ""),
        }
        for offset in range(group):
            result[lineno + offset] = blame_info
    return result


def _get_blame_at_revision(filepath: str, revision: str, cwd: Optional[Path] = None) -> list[dict]:
    """Run git blame on a file at a specific revision."""
    try:
        output = _run_git(
            ["blame", "--line-porcelain", revision, "--", filepath],
            cwd=cwd,
        )
    except GitError:
        return []
    return _parse_blame_porcelain(output)


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
