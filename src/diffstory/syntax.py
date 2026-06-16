"""Syntax highlighting using Pygments, works entirely offline."""

from __future__ import annotations

from typing import Optional

from pygments import highlight
from pygments.lexers import (
    get_lexer_by_name,
    get_lexer_for_filename,
    ClassNotFound,
)
from pygments.formatters import HtmlFormatter


# Mapping of file extensions to language names for quick lookup
EXTENSION_MAP: dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".cs": "csharp",
    ".go": "go",
    ".rs": "rust",
    ".php": "php",
    ".rb": "ruby",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".sql": "sql",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".yml": "yaml",
    ".yaml": "yaml",
    ".json": "json",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".md": "markdown",
    ".markdown": "markdown",
    ".xml": "xml",
    ".svg": "xml",
    ".toml": "ini",
    ".cfg": "ini",
    ".ini": "ini",
    ".txt": "text",
    ".dockerfile": "docker",
    ".tf": "terraform",
    ".vue": "html",
    ".svelte": "html",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".hpp": "cpp",
    ".swift": "swift",
    ".scala": "scala",
    ".ex": "elixir",
    ".exs": "elixir",
    ".erl": "erlang",
    ".hrl": "erlang",
    ".hs": "haskell",
    ".lua": "lua",
    ".r": "r",
    ".R": "r",
    ".m": "matlab",
    ".mm": "matlab",
}

def get_lexer_for_file(filepath: str) -> object:
    """Get the appropriate Pygments lexer for a file path."""
    # Try by extension first
    ext = "." + filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    if ext in EXTENSION_MAP:
        try:
            return get_lexer_by_name(EXTENSION_MAP[ext])
        except ClassNotFound:
            pass

    # Try by full filename
    try:
        return get_lexer_for_filename(filepath)
    except ClassNotFound:
        pass

    # Try to guess from common filenames
    basename = filepath.rsplit("/", 1)[-1].lower()
    if basename in ("dockerfile",):
        try:
            return get_lexer_by_name("docker")
        except ClassNotFound:
            pass
    if basename in ("makefile", "gnumakefile"):
        try:
            return get_lexer_by_name("make")
        except ClassNotFound:
            pass

    return None


def get_highlighted_line(line: str, filepath: str, lexer_cache: dict) -> str:
    """Highlight a single line of code using a cached lexer."""
    from html import escape
    lexer = lexer_cache.get(filepath)
    if lexer is None:
        lexer = get_lexer_for_file(filepath)
        lexer_cache[filepath] = lexer

    if lexer is None:
        return escape(line)

    try:
        formatter = HtmlFormatter(nowrap=True, style="default")
        return highlight(line, lexer, formatter)
    except Exception:
        return escape(line)


def get_syntax_css(style: str = "default") -> str:
    """Get the CSS for syntax highlighting."""
    formatter = HtmlFormatter(style=style)
    return formatter.get_style_defs(".highlight")


def _scope_css(css: str, theme: str) -> str:
    """Scope every .highlight rule under a data-theme attribute selector."""
    lines = css.splitlines()
    result = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(".highlight"):
            indent = line[:len(line) - len(line.lstrip())]
            line = indent + '[data-theme="' + theme + '"] ' + stripped
        result.append(line)
    return "\n".join(result)


def get_syntax_styles() -> str:
    """Get both light and dark syntax highlight CSS, scoped by data-theme."""
    light_css = get_syntax_css("default")
    dark_css = get_syntax_css("monokai")
    return "\n" + _scope_css(light_css, "light") + "\n\n" + _scope_css(dark_css, "dark") + "\n"
