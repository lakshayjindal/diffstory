"""Git interaction via subprocess — zero external dependency on GitPython."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Raised when a git command fails."""


# Cache the git repo root once discovered to avoid repeated rev-parse calls.
# This is safe because the cwd doesn't change during a single diffstory run.
_GIT_ROOT_CACHE: Optional[str] = None


def _get_repo_root(cwd: Path) -> Optional[str]:
    """Detect and cache the git repository root directory.

    Returns None if cwd is not inside a git repository.
    """
    global _GIT_ROOT_CACHE
    if _GIT_ROOT_CACHE is not None:
        return _GIT_ROOT_CACHE
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
        _GIT_ROOT_CACHE = result.stdout.strip()
        return _GIT_ROOT_CACHE
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _run_git(args: list[str], cwd: Optional[Path] = None) -> str:
    """Run a git command and return stdout.

    Automatically resolves cwd to the git repository root so that all
    git commands execute from the top-level directory. This is critical
    because paths from git diff are always repo-relative, but git blame,
    git log, etc. resolve paths relative to the current working directory.
    Without this, running diffstory from a subdirectory would cause
    "fatal: cannot stat path 'src/foo.py'" errors.

    Raises GitError on non-zero exit.
    """
    if cwd is None:
        cwd = Path.cwd()

    # Resolve to repo root so that repo-relative paths (from diff output)
    # work correctly with all git commands (blame, log, diff, etc.)
    repo_root = _get_repo_root(cwd)
    if repo_root is not None:
        cwd = Path(repo_root)

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


def get_git_root(cwd: Optional[Path] = None) -> Optional[str]:
    """Get the absolute path to the root of the Git repository."""
    try:
        return _run_git(["rev-parse", "--show-toplevel"], cwd=cwd).strip()
    except GitError:
        return None


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

    Handles root commits (no parent), merge commits, and
    the all-zero hash (uncommitted/staged changes).
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

    parents_list = parts[7].split() if parts[7] else []

    # Count files changed, insertions, deletions (skip for all-zero/uncommitted)
    files_changed = 0
    insertions = 0
    deletions = 0
    if not all(c == "0" for c in commit_hash):
        try:
            if parents_list:
                # Has parents — use diff with first parent
                parent_ref = parents_list[0]
                stat_output = _run_git(
                    ["diff", "--stat", f"{parent_ref}..{commit_hash}", "--"],
                    cwd=cwd,
                )
            else:
                # Root commit — count files via log --name-status
                stat_output = _run_git(
                    ["log", "-1", "--format=", "--name-status", commit_hash],
                    cwd=cwd,
                )
                # Parse added files from root commit
                for line in stat_output.strip().splitlines():
                    if line.strip():
                        files_changed += 1
                        if line.startswith("A"):
                            insertions += 1  # approximate
                return {
                    "hash": parts[0],
                    "author": parts[1],
                    "author_email": parts[2],
                    "author_date": parts[3],
                    "committer": parts[4],
                    "committer_email": parts[5],
                    "committer_date": parts[6],
                    "parents": parents_list,
                    "subject": parts[8],
                    "body": body.strip(),
                    "files_changed": files_changed,
                    "insertions": insertions,
                    "deletions": deletions,
                }

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
        "parents": parents_list,
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


def get_hotspots(max_files: int = 20, cwd: Optional[Path] = None) -> list[dict]:
    """
    Identify hotspot files — files modified most frequently in recent history.

    Runs `git log --name-only` over the last 500 commits and counts
    how many times each file appears.

    Returns a list of dicts sorted by modification count descending:
        [{"file": "src/auth.py", "modifications": 47}, ...]
    """
    try:
        output = _run_git(["log", "--max-count=500", "--format=", "--name-only", "--diff-filter=AM"], cwd=cwd)
    except GitError:
        return []

    counts: dict[str, int] = {}
    for line in output.splitlines():
        line = line.strip()
        if line and not line.startswith("commit"):
            counts[line] = counts.get(line, 0) + 1

    sorted_files = sorted(counts.items(), key=lambda x: -x[1])
    return [{"file": f, "modifications": c} for f, c in sorted_files[:max_files]]


def get_change_timeline(max_commits: int = 200, cwd: Optional[Path] = None) -> dict:
    """
    Get commit counts grouped by day of week for a change timeline chart.

    Returns a dict with day names as keys and commit counts as values:
        {"Mon": 5, "Tue": 12, "Wed": 8, "Thu": 15, "Fri": 3, "Sat": 1, "Sun": 0}
    """
    try:
        output = _run_git(["log", f"--max-count={max_commits}", "--format=%ad", "--date=format:%a"], cwd=cwd)
    except GitError:
        return {}

    day_order = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    counts: dict[str, int] = {d: 0 for d in day_order}

    for line in output.splitlines():
        line = line.strip()
        if line in counts:
            counts[line] += 1

    max_count = max(counts.values()) if counts else 1
    return {"days": day_order, "counts": [counts[d] for d in day_order], "max": max_count}


def scan_diff_for_todos(diff_text: str) -> list[dict]:
    """
    Scan diff text for TODO, FIXME, HACK, XXX, BUG, OPTIMIZE annotations
    that appear in added lines (prefixed with +).

    Returns a list of dicts:
        [{"file": "src/auth.py", "line": 42, "tag": "TODO", "text": "Remove temporary workaround"}]
    """
    import re
    results: list[dict] = []
    current_file = "unknown"
    # Match + lines with TODO/FIXME/HACK/XXX/BUG/OPTIMIZE (with optional colon/space after)
    pattern = re.compile(r"^\+.*?\b(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE)\b[\s:]*\.?(.*)", re.IGNORECASE)

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            # Extract new file path
            parts = line[11:].split(" b/", 1)
            if len(parts) == 2:
                current_file = parts[1]
            continue
        if line.startswith("+++"):
            path = line[6:] if line.startswith("+++ b/") else ""
            if path:
                current_file = path
            continue

        match = pattern.match(line)
        if match:
            results.append({
                "file": current_file,
                "tag": match.group(1).upper(),
                "text": match.group(2).strip(),
            })

    return results


def get_dependency_files_for_diff(files: list, cwd: Optional[Path] = None) -> list[dict]:
    """
    Detect which of the changed files are dependency manifests
    and try to parse added/removed dependencies.

    Returns a list of dicts:
        [{
            "file": "requirements.txt",
            "added": ["requests>=2.33"],
            "removed": ["flask"],
            "updated": [{"name": "django", "from": "5.2", "to": "5.3"}]
        }]
    """
    DEPENDENCY_FILES = {
        "requirements.txt": "pip",
        "pyproject.toml": "pep621",
        "Pipfile": "pipenv",
        "Pipfile.lock": "pipenv-lock",
        "package.json": "npm",
        "yarn.lock": "yarn",
        "pnpm-lock.yaml": "pnpm",
        "Cargo.toml": "cargo",
        "Cargo.lock": "cargo-lock",
        "go.mod": "go",
        "go.sum": "go-lock",
        "Gemfile": "bundler",
        "Gemfile.lock": "bundler-lock",
        "composer.json": "composer",
        "composer.lock": "composer-lock",
        "build.gradle": "gradle",
        "pom.xml": "maven",
        "Makefile": "make",
    }

    import re
    results: list[dict] = []

    for f in files:
        filename = Path(f.display_path).name
        if filename not in DEPENDENCY_FILES:
            continue

        pkg_type = DEPENDENCY_FILES[filename]
        dep_info = {"file": f.display_path, "type": pkg_type, "added": [], "removed": [], "updated": []}

        # Get the diff content for this file from hunks
        added_lines: list[str] = []
        removed_lines: list[str] = []
        for hunk in f.hunks:
            for line in hunk.lines:
                if line.line_type == "addition":
                    added_lines.append(line.content)
                elif line.line_type == "deletion":
                    removed_lines.append(line.content)

        # Parse based on file type
        if filename == "requirements.txt":
            dep_info["added"] = [l.strip() for l in added_lines if l.strip() and not l.startswith("#") and not l.startswith("-r")]
            dep_info["removed"] = [l.strip() for l in removed_lines if l.strip() and not l.startswith("#")]
            # Detect updates
            added_names = {_extract_pip_package(l) for l in dep_info["added"]}
            removed_names = {_extract_pip_package(l) for l in dep_info["removed"]}
            overlap = added_names & removed_names
            for name in overlap:
                old_ver = next((l for l in dep_info["removed"] if l.startswith(name)), "")
                new_ver = next((l for l in dep_info["added"] if l.startswith(name)), "")
                dep_info["updated"].append({"name": name, "from": old_ver, "to": new_ver})
            # Don't list updates in added/removed
            updated_names = {u["name"] for u in dep_info["updated"]}
            dep_info["added"] = [a for a in dep_info["added"] if _extract_pip_package(a) not in updated_names]
            dep_info["removed"] = [r for r in dep_info["removed"] if _extract_pip_package(r) not in updated_names]

        elif filename == "package.json":
            dep_info["added"] = added_lines
            dep_info["removed"] = removed_lines

        elif filename == "Cargo.toml":
            dep_info["added"] = [l.strip() for l in added_lines if "=" in l and not l.strip().startswith("[")]
            dep_info["removed"] = [l.strip() for l in removed_lines if "=" in l and not l.strip().startswith("[")]

        elif filename == "go.mod":
            dep_info["added"] = [l.strip() for l in added_lines if l.strip() and not l.startswith("module ") and not l.startswith("go ")]
            dep_info["removed"] = [l.strip() for l in removed_lines if l.strip() and not l.startswith("module ") and not l.startswith("go ")]

        elif filename == "pyproject.toml":
            dep_info["added"] = [l.strip() for l in added_lines if "=" in l and not l.strip().startswith("[")]
            dep_info["removed"] = [l.strip() for l in removed_lines if "=" in l and not l.strip().startswith("[")]

        results.append(dep_info)

    return results


def _extract_pip_package(line: str) -> str:
    """Extract the package name from a pip-style requirements line."""
    import re
    # Handle: package==1.0, package>=1.0, package~=1.0, package!=1.0, package
    m = re.match(r"^([a-zA-Z0-9._-]+)", line)
    return m.group(1) if m else line


def get_folder_stats(files: list) -> dict:
    """
    Group changed files by folder and compute change counts per folder.

    Returns a dict:
        {"backend/": {"changes": 47, "additions": 30, "deletions": 17},
         "frontend/": {"changes": 12, "additions": 8, "deletions": 4}}
    """
    folders: dict[str, dict] = {}

    for f in files:
        path = f.display_path
        parts = path.split("/")
        if len(parts) > 1:
            folder = parts[0] + "/"
        else:
            folder = "/"  # root

        adds = sum(1 for h in f.hunks for l in h.lines if l.line_type == "addition")
        dels = sum(1 for h in f.hunks for l in h.lines if l.line_type == "deletion")

        if folder not in folders:
            folders[folder] = {"changes": 0, "additions": 0, "deletions": 0}
        folders[folder]["changes"] += 1
        folders[folder]["additions"] += adds
        folders[folder]["deletions"] += dels

    return folders


def map_related_tests(files: list) -> list[dict]:
    """
    Map changed files to their likely test files using path heuristics.

    Heuristics:
      - src/auth/auth.py → tests/auth/test_auth.py, tests/test_auth.py
      - app/models/user.py → tests/models/test_user.py, tests/test_user.py
      - foo.py → test_foo.py, tests/test_foo.py
      - src/foo/bar.py → tests/foo/test_bar.py

    Returns a list of dicts:
        [{"source": "src/auth.py", "tests": ["tests/test_auth.py", "tests/test_login.py"]}]
    """
    results: list[dict] = []

    for f in files:
        path = f.display_path
        basename = Path(path).stem if "." in path else path
        parent = str(Path(path).parent) if "/" in path else ""

        # Build test file candidates
        candidates = set()
        candidates.add(f"test_{basename}.py")
        candidates.add(f"tests/test_{basename}.py")

        # Mirror the source path under tests/
        if parent and parent != ".":
            candidates.add(f"tests/{parent}/test_{basename}.py")

            # Also try without src/ prefix
            if parent.startswith("src/"):
                sub = parent[4:]
                candidates.add(f"tests/{sub}/test_{basename}.py")
                candidates.add(f"tests/test_{basename}.py")

        results.append({
            "source": path,
            "tests": sorted(candidates),
        })

    return results


def get_complexity_delta(files: list, cwd: Optional[Path] = None) -> list[dict]:
    """
    Compute function complexity delta for Python files using the `ast` module.

    For each changed .py file, parse the old and new content (if available)
    and count function bodies (def/async def, class methods).

    Returns a list of dicts:
        [{"file": "src/auth.py", "functions": [{"name": "login", "old_lines": 7, "new_lines": 14}], ...}]
    """
    results: list[dict] = []

    for f in files:
        if not f.display_path.endswith(".py"):
            continue

        # We can estimate complexity from the diff itself
        func_changes: list[dict] = []
        current_func = None

        for hunk in f.hunks:
            for line in hunk.lines:
                content = line.content.strip()
                # Detect function/method definitions
                if content.startswith("def ") or content.startswith("async def "):
                    func_name = content.split("(")[0].replace("def ", "").replace("async def ", "").strip()
                    if func_name:
                        if current_func:
                            func_changes.append(current_func)
                        current_func = {"name": func_name, "old_lines": 0, "new_lines": 0, "old_complexity": 0, "new_complexity": 0}

                if current_func:
                    if line.line_type == "addition":
                        current_func["new_lines"] += 1
                    elif line.line_type == "deletion":
                        current_func["old_lines"] += 1
                    elif line.line_type == "context":
                        current_func["old_lines"] += 1
                        current_func["new_lines"] += 1

            if current_func:
                func_changes.append(current_func)
                current_func = None

        if func_changes:
            results.append({"file": f.display_path, "functions": func_changes})

    return results


def get_file_content_at_commit(filepath: str, commit: str, cwd: Optional[Path] = None) -> str:
    """Get the full content of a file at a specific commit."""
    try:
        return _run_git(["show", f"{commit}:{filepath}"], cwd=cwd)
    except GitError:
        return ""


def get_commits_for_evolution(limit: int = 10, base_commit: Optional[str] = None, head_commit: Optional[str] = None, cwd: Optional[Path] = None) -> list[dict]:
    """
    Get a list of commits for the commit evolution slider.

    Returns a list of dicts:
        [{"hash": "abc123", "subject": "Fix bug", "author": "Lakshay", "date": "..."}]
    """
    try:
        if base_commit and head_commit:
            output = _run_git(
                ["log", "--reverse", f"--max-count={limit}", "--format=%H|%an|%ae|%ai|%s", f"{base_commit}..{head_commit}"],
                cwd=cwd,
            )
        else:
            output = _run_git(["log", "--reverse", f"--max-count={limit}", "--format=%H|%an|%ae|%ai|%s"], cwd=cwd)
    except GitError:
        return []

    commits: list[dict] = []
    for line in output.strip().splitlines():
        parts = line.split("|", 4)
        if len(parts) == 5:
            commits.append({
                "hash": parts[0],
                "author": parts[1],
                "author_email": parts[2],
                "date": parts[3],
                "subject": parts[4],
            })
    return commits


def get_commit_range_files(base_commit: str, head_commit: str, cwd: Optional[Path] = None) -> list[str]:
    """Get the list of files changed between two commits."""
    try:
        output = _run_git(["diff", "--name-only", f"{base_commit}..{head_commit}"], cwd=cwd)
    except GitError:
        return []
    return [l.strip() for l in output.splitlines() if l.strip()]


def compute_file_evolution(filepath: str, commits: list[dict], cwd: Optional[Path] = None) -> list[dict]:
    """
    For a given file, fetch its content at each commit in the range.

    Returns a list of dicts with commit info and file content:
        [{"commit": {...}, "content": "...", "exists": True}]
    """
    evolution: list[dict] = []
    for commit in commits:
        content = get_file_content_at_commit(filepath, commit["hash"], cwd=cwd)
        evolution.append({
            "commit": commit,
            "content": content,
            "exists": bool(content),
        })
    return evolution


def compute_semantic_summary(files: list, commits_data: Optional[dict] = None) -> list[str]:
    """
    Generate a deterministic semantic summary from filenames, commit messages,
    and hunk headers. No AI involved.

    Returns a list of summary strings:
        ["Added authentication checks.", "Refactored invoice calculation."]
    """
    summaries: list[str] = []
    seen: set[str] = set()

    # From commit messages
    if commits_data:
        for chash, info in commits_data.items():
            subject = info.get("subject", "")
            if subject and subject not in seen:
                # Clean up common prefixes for natural reading
                cleaned = subject
                for prefix in ["feat: ", "fix: ", "chore: ", "refactor: ", "docs: ", "test: "]:
                    if cleaned.lower().startswith(prefix):
                        cleaned = cleaned[len(prefix):]
                        break
                summary = cleaned[0].upper() + cleaned[1:] if cleaned else cleaned
                summaries.append(f"{summary}." if not summary.endswith(".") else summary)
                seen.add(subject)

    # From file names (for files without commit messages)
    seen_files: set[str] = set()
    for f in files:
        path = f.display_path
        if path in seen_files:
            continue
        seen_files.add(path)

        basename = Path(path).stem
        parent = Path(path).parent
        status = f.status

        # Generate summary from file name
        readable = basename.replace("_", " ").replace("-", " ").title()

        if status == "added":
            summary = f"Added {readable}."
        elif status == "deleted":
            summary = f"Removed {readable}."
        elif status == "renamed":
            summary = f"Renamed {readable}."
        else:
            summary = f"Updated {readable}."

        if summary not in seen:
            summaries.append(summary)
            seen.add(summary)

    # From hunk headers
    for f in files:
        for hunk in f.hunks:
            if hunk.header:
                header_text = hunk.header.strip()
                # Filter out generic headers
                if header_text and not header_text.startswith("@@"):
                    summary = header_text[0].upper() + header_text[1:] if header_text else header_text
                    summary = summary.rstrip(".") + "."
                    if summary not in seen:
                        summaries.append(summary)
                        seen.add(summary)

    return summaries[:15]  # Limit to 15 summaries
