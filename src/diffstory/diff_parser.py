"""Parse unified diff output into structured Python data."""

from __future__ import annotations

import difflib
import re
from typing import Optional


# Image extensions that can be previewed inline
IMAGE_EXTENSIONS = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".bmp", ".ico"})


class DiffFile:
    """Represents a single file in a diff."""

    def __init__(
        self,
        old_path: str,
        new_path: str,
        status: str = "modified",
        old_mode: Optional[str] = None,
        new_mode: Optional[str] = None,
        similarity: Optional[int] = None,
    ):
        self.old_path = old_path
        self.new_path = new_path
        self.display_path = new_path if new_path != "/dev/null" else old_path
        self.status = status  # added, deleted, modified, renamed
        self.old_mode = old_mode
        self.new_mode = new_mode
        self.similarity = similarity
        self.hunks: list[Hunk] = []
        self.is_binary_file = False  # set True when binary, no hunks

    @property
    def is_binary(self) -> bool:
        return not self.hunks and self.status != "added"

    @property
    def is_image(self) -> bool:
        """Check if the file path looks like a known image type."""
        ext = "." + self.display_path.rsplit(".", 1)[-1].lower() if "." in self.display_path else ""
        return ext in IMAGE_EXTENSIONS


class Hunk:
    """Represents a single hunk (@@ ... @@ section) in a diff."""

    def __init__(
        self,
        old_start: int,
        old_count: int,
        new_start: int,
        new_count: int,
        header: str = "",
    ):
        self.old_start = old_start
        self.old_count = old_count
        self.new_start = new_start
        self.new_count = new_count
        self.header = header
        self.lines: list[DiffLine] = []


class DiffLine:
    """Represents a single line in a diff."""

    TYPE_CONTEXT = "context"
    TYPE_ADDITION = "addition"
    TYPE_DELETION = "deletion"

    def __init__(
        self,
        line_type: str,
        content: str,
        old_lineno: Optional[int] = None,
        new_lineno: Optional[int] = None,
    ):
        self.line_type = line_type
        self.content = content
        self.old_lineno = old_lineno
        self.new_lineno = new_lineno
        self.word_diff: Optional[WordDiff] = None


class WordDiff:
    """Word-level diff for inline edit mode."""

    def __init__(self, parts: list[dict]):
        self.parts = parts  # [{"text": "...", "type": "equal|add|delete"}, ...]


def parse_diff(diff_text: str) -> list[DiffFile]:
    """Parse a unified diff string into a list of DiffFile objects."""
    files: list[DiffFile] = []
    current_file: Optional[DiffFile] = None
    current_hunk: Optional[Hunk] = None

    old_lineno = 0
    new_lineno = 0

    for line in diff_text.splitlines():
        # Check for file headers
        if line.startswith("diff --git "):
            current_file = _parse_diff_header(line)
            files.append(current_file)
            current_hunk = None
            old_lineno = 0
            new_lineno = 0
            continue

        if current_file is None:
            continue

        # Check for rename/copy info
        if line.startswith("rename from "):
            current_file.old_path = line[12:]
            current_file.status = "renamed"
            continue
        if line.startswith("rename to "):
            current_file.new_path = line[10:]
            current_file.display_path = current_file.new_path
            current_file.status = "renamed"
            continue

        # Similarity index
        if line.startswith("similarity index "):
            try:
                current_file.similarity = int(line[17:].rstrip("%"))
            except ValueError:
                pass
            continue

        # Binary files
        if line.startswith("Binary files ") or line == "Binary files differ":
            current_file.is_binary_file = True
            continue

        # New file mode
        if line.startswith("new file mode "):
            current_file.status = "added"
            current_file.new_mode = line[14:]
            continue

        # Deleted file mode
        if line.startswith("deleted file mode "):
            current_file.status = "deleted"
            current_file.old_mode = line[18:]
            continue

        # Old mode / new mode
        if line.startswith("old mode "):
            current_file.old_mode = line[9:]
            continue
        if line.startswith("new mode "):
            current_file.new_mode = line[9:]
            continue

        # Index line
        if line.startswith("index "):
            continue

        # --- / +++ lines
        if line.startswith("--- "):
            continue
        if line.startswith("+++ "):
            continue

        # Hunk header
        if line.startswith("@@"):
            current_hunk = _parse_hunk_header(line)
            current_file.hunks.append(current_hunk)
            old_lineno = current_hunk.old_start
            new_lineno = current_hunk.new_start
            continue

        if current_hunk is None:
            continue

        # Diff content lines
        if line.startswith("+"):
            diff_line = DiffLine(DiffLine.TYPE_ADDITION, line[1:], new_lineno=new_lineno)
            current_hunk.lines.append(diff_line)
            new_lineno += 1
        elif line.startswith("-"):
            diff_line = DiffLine(DiffLine.TYPE_DELETION, line[1:], old_lineno=old_lineno)
            current_hunk.lines.append(diff_line)
            old_lineno += 1
        else:
            # Context line (starts with space)
            content = line[1:] if len(line) > 1 else ""
            diff_line = DiffLine(DiffLine.TYPE_CONTEXT, content, old_lineno, new_lineno)
            current_hunk.lines.append(diff_line)
            old_lineno += 1
            new_lineno += 1

    return files


def _parse_diff_header(line: str) -> DiffFile:
    """Parse 'diff --git a/path b/path' header.

    Git uses 'dev/null' (no leading slash) in the diff --git header
    for added/deleted files. We normalize this to '/dev/null' to
    match the convention used in ---/+++ lines and throughout the
    rest of the codebase.
    """
    # Extract paths after 'diff --git '
    rest = line[11:]
    parts = rest.split(" b/", 1)
    if len(parts) == 2:
        old_path = parts[0][2:] if parts[0].startswith("a/") else parts[0]
        new_path = parts[1]
        # Git uses 'dev/null' (no leading slash) in the diff --git header.
        # Normalize to '/dev/null' for consistency with our checks.
        if old_path == "dev/null":
            old_path = "/dev/null"
        if new_path == "dev/null":
            new_path = "/dev/null"
    else:
        old_path = rest
        new_path = rest
    return DiffFile(old_path, new_path)


HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)")


def _parse_hunk_header(line: str) -> Hunk:
    """Parse @@ -old,count +new,count @@ header."""
    match = HUNK_HEADER_RE.match(line)
    if match:
        old_start = int(match.group(1))
        old_count = int(match.group(2) or 1)
        new_start = int(match.group(3))
        new_count = int(match.group(4) or 1)
        header = match.group(5).strip()
        return Hunk(old_start, old_count, new_start, new_count, header)
    return Hunk(0, 0, 0, 0)


def compute_word_diff(old_line: str, new_line: str) -> WordDiff:
    """Compute word-level diff between two lines for inline edit mode."""
    # Tokenize words (split on word boundaries, preserving whitespace)
    old_tokens = _tokenize(old_line)
    new_tokens = _tokenize(new_line)

    matcher = difflib.SequenceMatcher(None, old_tokens, new_tokens)
    parts: list[dict] = []

    for op, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if op == "equal":
            for t in old_tokens[old_start:old_end]:
                parts.append({"text": t, "type": "equal"})
        elif op == "replace":
            # Show deleted tokens then added tokens
            for t in old_tokens[old_start:old_end]:
                parts.append({"text": t, "type": "delete"})
            for t in new_tokens[new_start:new_end]:
                parts.append({"text": t, "type": "add"})
        elif op == "delete":
            for t in old_tokens[old_start:old_end]:
                parts.append({"text": t, "type": "delete"})
        elif op == "insert":
            for t in new_tokens[new_start:new_end]:
                parts.append({"text": t, "type": "add"})

    return WordDiff(parts)


def _tokenize(text: str) -> list[str]:
    """Tokenize text into words, preserving whitespace."""
    tokens: list[str] = []
    current = ""
    for char in text:
        if char.isspace():
            if current:
                tokens.append(current)
                current = ""
            tokens.append(char)
        else:
            current += char
    if current:
        tokens.append(current)
    return tokens


def compute_word_diffs(file: DiffFile) -> None:
    """Compute word-level diffs for all applicable lines in a file."""
    for hunk in file.hunks:
        additions: list[DiffLine] = []
        deletions: list[DiffLine] = []

        for line in hunk.lines:
            if line.line_type == DiffLine.TYPE_ADDITION:
                additions.append(line)
            elif line.line_type == DiffLine.TYPE_DELETION:
                deletions.append(line)

        # Pair additions with deletions (simple approach: match by position)
        add_idx = 0
        del_idx = 0
        while add_idx < len(additions) and del_idx < len(deletions):
            add_line = additions[add_idx]
            del_line = deletions[del_idx]
            word_diff = compute_word_diff(del_line.content, add_line.content)
            add_line.word_diff = word_diff
            del_line.word_diff = word_diff
            add_idx += 1
            del_idx += 1
