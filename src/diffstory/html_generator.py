"""Generate self-contained HTML reports from parsed diff data."""

from __future__ import annotations

import uuid
from datetime import datetime
from html import escape
from typing import Any, Optional

import json

from diffstory.diff_parser import DiffFile, DiffLine, Hunk, compute_word_diffs
from diffstory.syntax import get_highlighted_line, get_syntax_styles
from diffstory.git_utils import get_blame_for_revision, get_commit_info, get_repo_name


def _compute_stats(files: list[DiffFile], blame_data: Optional[dict] = None, commits_data: Optional[dict] = None) -> dict:
    """Compute summary statistics, including blame-derived stats if available."""
    total_additions = 0
    total_deletions = 0
    total_files = len(files)
    added_files = 0
    deleted_files = 0
    modified_files = 0
    renamed_files = 0
    changed_lines_per_file: list[dict] = []

    for f in files:
        adds = sum(1 for h in f.hunks for l in h.lines if l.line_type == "addition")
        dels = sum(1 for h in f.hunks for l in h.lines if l.line_type == "deletion")
        total_additions += adds
        total_deletions += dels

        if f.status == "added":
            added_files += 1
        elif f.status == "deleted":
            deleted_files += 1
        elif f.status == "renamed":
            renamed_files += 1
        else:
            modified_files += 1

        changed_lines_per_file.append({
            "file": f.display_path,
            "additions": adds,
            "deletions": dels,
            "total": adds + dels,
        })

    changed_lines_per_file.sort(key=lambda x: x["total"], reverse=True)

    # Collect author breakdown from blame data
    authors: dict = {}
    unique_commits: set = set()
    if blame_data:
        for key, entry in blame_data.items():
            auth = entry.get("author", "Unknown")
            if auth not in authors:
                authors[auth] = {"additions": 0, "deletions": 0, "commits": set()}
            # Rough estimate: count lines per author
            chash = entry.get("commit", "")
            if chash:
                unique_commits.add(chash)
                authors[auth]["commits"].add(chash)

    # If we have commit data, use it for richer stats
    if commits_data:
        for chash, info in commits_data.items():
            unique_commits.add(chash)

    author_breakdown = [
        {"name": name, "commits": len(d["commits"])}
        for name, d in sorted(authors.items(), key=lambda x: -len(x[1]["commits"]))
    ]

    return {
        "files_changed": total_files,
        "additions": total_additions,
        "deletions": total_deletions,
        "added_files": added_files,
        "deleted_files": deleted_files,
        "modified_files": modified_files,
        "renamed_files": renamed_files,
        "authors": len(authors),
        "commits": len(unique_commits),
        "author_breakdown": author_breakdown[:10],
        "largest_files": changed_lines_per_file[:10],
    }


def _hunk_header_extra(header: str) -> str:
    """Build the optional header text span for a hunk."""
    if header:
        return ' <span class="hunk-header-text">' + escape(header) + '</span>'
    return ""


def _render_unified_hunk(hunk: Hunk, filepath: str, lexer_cache: dict) -> str:
    """Render a hunk in unified view mode."""
    lines_html = ""
    for line in hunk.lines:
        line_type = line.line_type
        old_no = str(line.old_lineno or "")
        new_no = str(line.new_lineno or "")
        prefix = " " if line_type == "context" else line_type[0]
        css_class = "diff-line diff-" + line_type

        highlighted = get_highlighted_line(line.content, filepath, lexer_cache)
        lines_html += (
            '<div class="' + css_class + '" data-old="' + old_no + '" data-new="' + new_no + '">'
            '<span class="line-prefix">' + prefix + '</span>'
            '<span class="line-num line-num-old">' + old_no + '</span>'
            '<span class="line-num line-num-new">' + new_no + '</span>'
            '<span class="line-content">' + highlighted + '</span>'
            '</div>\n'
        )

    header_extra = _hunk_header_extra(hunk.header)
    hunk_html = (
        '<div class="hunk-header">@@ ' + str(hunk.old_start) + ',' + str(hunk.old_count) + ' '
        + str(hunk.new_start) + ',' + str(hunk.new_count) + ' @@'
        + header_extra
        + '</div>\n'
        + '<div class="hunk-body">' + lines_html + '</div>\n'
    )
    return hunk_html


def _render_sidebyside_hunk(hunk: Hunk, filepath: str, lexer_cache: dict) -> str:
    """Render a hunk in side-by-side view mode."""
    rows = ""
    left_lines: list[Optional[DiffLine]] = []
    right_lines: list[Optional[DiffLine]] = []

    for line in hunk.lines:
        if line.line_type == "deletion":
            left_lines.append(line)
            right_lines.append(None)
        elif line.line_type == "addition":
            left_lines.append(None)
            right_lines.append(line)
        else:
            left_lines.append(line)
            right_lines.append(line)

    max_lines = max(len(left_lines), len(right_lines))

    for i in range(max_lines):
        left = left_lines[i] if i < len(left_lines) else None
        right = right_lines[i] if i < len(right_lines) else None

        left_content = ""
        right_content = ""
        left_class = "diff-empty"
        right_class = "diff-empty"

        if left:
            left_class = "diff-" + left.line_type
            old_no = str(left.old_lineno or "")
            highlighted = get_highlighted_line(left.content, filepath, lexer_cache)
            left_content = (
                '<span class="line-num line-num-old">' + old_no + '</span>'
                '<span class="line-content">' + highlighted + '</span>'
            )

        if right:
            right_class = "diff-" + right.line_type
            new_no = str(right.new_lineno or "")
            highlighted = get_highlighted_line(right.content, filepath, lexer_cache)
            right_content = (
                '<span class="line-num line-num-new">' + new_no + '</span>'
                '<span class="line-content">' + highlighted + '</span>'
            )

        rows += (
            '<div class="sbs-row">'
            '<div class="sbs-left ' + left_class + ' diff-line" data-old="' + (str(left.old_lineno) if left and left.old_lineno else '') + '" data-new="' + (str(left.new_lineno) if left and left.new_lineno else '') + '">' + left_content + '</div>'
            '<div class="sbs-right ' + right_class + ' diff-line" data-old="' + (str(right.old_lineno) if right and right.old_lineno else '') + '" data-new="' + (str(right.new_lineno) if right and right.new_lineno else '') + '">' + right_content + '</div>'
            '</div>\n'
        )

    header_extra = _hunk_header_extra(hunk.header)
    hunk_html = (
        '<div class="hunk-header">@@ ' + str(hunk.old_start) + ',' + str(hunk.old_count) + ' '
        + str(hunk.new_start) + ',' + str(hunk.new_count) + ' @@'
        + header_extra
        + '</div>\n'
        + '<div class="sbs-hunk">' + rows + '</div>\n'
    )
    return hunk_html


def _render_inline_hunk(hunk: Hunk, filepath: str, lexer_cache: dict) -> str:
    """Render a hunk in inline edit mode (word-level diff)."""
    lines_html = ""

    for line in hunk.lines:
        if line.line_type == "context":
            old_no = str(line.old_lineno or "")
            new_no = str(line.new_lineno or "")
            highlighted = get_highlighted_line(line.content, filepath, lexer_cache)
            lines_html += (
                '<div class="diff-line diff-context" data-old="' + old_no + '" data-new="' + new_no + '">'
                '<span class="line-prefix"> </span>'
                '<span class="line-num line-num-old">' + old_no + '</span>'
                '<span class="line-num line-num-new">' + new_no + '</span>'
                '<span class="line-content">' + highlighted + '</span>'
                '</div>\n'
            )
        elif line.line_type == "deletion":
            old_no = str(line.old_lineno or "")
            lines_html += (
                '<div class="diff-line diff-deletion" data-old="' + old_no + '">'
                '<span class="line-prefix">-</span>'
                '<span class="line-num line-num-old">' + old_no + '</span>'
                '<span class="line-num line-num-new"></span>'
                '<span class="line-content">'
            )
            if line.word_diff:
                for part in line.word_diff.parts:
                    if part["type"] == "delete":
                        lines_html += '<span class="wd-removed">' + escape(part["text"]) + '</span>'
                    elif part["type"] == "equal":
                        lines_html += '<span class="wd-equal">' + escape(part["text"]) + '</span>'
            else:
                lines_html += escape(line.content)
            lines_html += '</span></div>\n'

        elif line.line_type == "addition":
            new_no = str(line.new_lineno or "")
            lines_html += (
                '<div class="diff-line diff-addition" data-new="' + new_no + '">'
                '<span class="line-prefix">+</span>'
                '<span class="line-num line-num-old"></span>'
                '<span class="line-num line-num-new">' + new_no + '</span>'
                '<span class="line-content">'
            )
            if line.word_diff:
                for part in line.word_diff.parts:
                    if part["type"] == "add":
                        lines_html += '<span class="wd-added">' + escape(part["text"]) + '</span>'
                    elif part["type"] == "equal":
                        lines_html += '<span class="wd-equal">' + escape(part["text"]) + '</span>'
            else:
                lines_html += escape(line.content)
            lines_html += '</span></div>\n'

    header_extra = _hunk_header_extra(hunk.header)
    hunk_html = (
        '<div class="hunk-header">@@ ' + str(hunk.old_start) + ',' + str(hunk.old_count) + ' '
        + str(hunk.new_start) + ',' + str(hunk.new_count) + ' @@'
        + header_extra
        + '</div>\n'
        + '<div class="hunk-body">' + lines_html + '</div>\n'
    )
    return hunk_html


def _render_file_section(file: DiffFile, file_index: int, lexer_cache: dict) -> str:
    """Render a complete file section with all three view modes."""
    file_id = "file-" + str(file_index)
    file_label = file.display_path
    file_status = file.status
    status_icon = {
        "added": "&#43;",
        "deleted": "&#8722;",
        "renamed": "&#8594;",
        "modified": "&#9679;",
    }.get(file_status, "&#9679;")

    status_class = "file-status-" + file_status

    # Compute word diffs for inline mode
    compute_word_diffs(file)

    # Render all three views
    unified_html = ""
    sbs_html = ""
    inline_html = ""

    if file.is_binary_file:
        # Binary file — show placeholder instead of diff hunks
        binary_content = escape("Binary file")
        if file.is_image:
            binary_content = (
                '<div class="binary-preview">'
                '<div class="binary-icon">&#128247;</div>'
                '<div class="binary-label">Image file &mdash; ' + escape(file_label) + '</div>'
                '<div class="binary-note">Preview requires the file to be checked out locally</div>'
                '</div>'
            )
        else:
            binary_content = (
                '<div class="binary-preview">'
                '<div class="binary-icon">&#128196;</div>'
                '<div class="binary-label">Binary file &mdash; ' + escape(file_label) + '</div>'
                '<div class="binary-note">Diff content not available for binary files</div>'
                '</div>'
            )
        unified_html = '<div class="binary-container">' + binary_content + '</div>'
        sbs_html = '<div class="binary-container">' + binary_content + '</div>'
        inline_html = '<div class="binary-container">' + binary_content + '</div>'
    else:
        for hunk in file.hunks:
            unified_html += _render_unified_hunk(hunk, file.display_path, lexer_cache)
            sbs_html += _render_sidebyside_hunk(hunk, file.display_path, lexer_cache)
            inline_html += _render_inline_hunk(hunk, file.display_path, lexer_cache)

    additions = sum(1 for h in file.hunks for l in h.lines if l.line_type == "addition")
    deletions = sum(1 for h in file.hunks for l in h.lines if l.line_type == "deletion")

    # Build the rename badge if applicable
    rename_badge = ""
    if file.status == "renamed" and file.old_path != file.new_path:
        rename_badge = ('<span class="rename-badge" title="Renamed from '
                        + escape(file.old_path) + '">'
                        + escape(file.old_path) + ' &#8594; </span>')
    elif file.status == "renamed":
        rename_badge = '<span class="rename-badge">Renamed</span>'

    return (
        '<div class="file-section" id="' + file_id + '" data-file="' + escape(file.display_path) + '">\n'
        '    <div class="file-header" onclick="toggleFile(this)">\n'
        '        <span class="file-status-icon ' + status_class + '">' + status_icon + '</span>\n'
        '        <span class="file-label">' + rename_badge + escape(file_label) + '</span>\n'
        '        <span class="file-stats">\n'
        '            <span class="stat-add">+' + str(additions) + '</span>\n'
        '            <span class="stat-del">-' + str(deletions) + '</span>\n'
        '        </span>\n'
        '        <span class="file-toggle">&#9660;</span>\n'
        '    </div>\n'
        '    <div class="file-diff-content">\n'
        '        <div class="diff-view unified-view active-view">' + unified_html + '</div>\n'
        '        <div class="diff-view sidebyside-view">' + sbs_html + '</div>\n'
        '        <div class="diff-view inline-view">' + inline_html + '</div>\n'
        '    </div>\n'
        '</div>\n'
    )


def _build_stats_table(stats: dict) -> str:
    """Build the stats table HTML rows."""
    rows = ""
    for f in stats["largest_files"]:
        rows += (
            '<tr><td>' + escape(f["file"]) + '</td>'
            '<td class="stat-add">+' + str(f["additions"]) + '</td>'
            '<td class="stat-del">-' + str(f["deletions"]) + '</td>'
            '<td>' + str(f["total"]) + '</td></tr>'
        )
    return rows


def _collect_blame_data(
    files: list[DiffFile],
    staged: bool = False,
    commit_a: Optional[str] = None,
    commit_b: Optional[str] = None,
    verbose: bool = False,
    progress_callback: Optional[callable] = None,
) -> dict:
    """Collect blame and commit metadata for all changed lines.

    Returns a dict with:
      - line_blame: dict mapping "file_idx:lineno" to blame entry
      - commits: dict mapping commit_hash to commit metadata

    Handles renamed files by using the old path for deletion blame
    and the new path for addition/context blame. Falls back to
    blaming the working tree when no revision info is available.
    """
    line_blame: dict = {}
    all_commits: set = set()
    blame_attempted = False

    for fi, file in enumerate(files):
        new_filepath = file.display_path
        old_filepath = file.old_path if file.old_path != "/dev/null" else file.display_path

        if new_filepath == "/dev/null" and old_filepath == "/dev/null":
            continue

        # Determine which revisions to blame
        new_revision = None  # None means working tree
        if commit_b:
            new_revision = commit_b
        elif staged:
            pass  # blame working tree for staged additions

        old_revision = None
        if commit_a:
            old_revision = commit_a
        elif staged:
            old_revision = "HEAD"
        elif not commit_a and not commit_b:
            # Working tree diff: blame deletions against HEAD so that
            # old_lineno lookups correctly reference the committed version
            old_revision = "HEAD"

        # File exists — attempt blame. For working tree (all None), get_blame
        # runs on the working tree. For --diff mode (no git repo), the per-file
        # try/except catches the GitError gracefully.
        blame_attempted = True

        if verbose:
            new_rev_str = str(new_revision) if new_revision else "working tree"
            old_rev_str = str(old_revision) if old_revision else "working tree"
            print(f"    Blaming {file.display_path} (new: {new_rev_str}, old: {old_rev_str})...")

        # Get blame for current (new) version — skip if file doesn't exist at revision
        blame_new: dict = {}
        new_blame_ok = False
        if new_filepath != "/dev/null":
            try:
                blame_new = get_blame_for_revision(new_filepath, revision=new_revision)
                new_blame_ok = True
                if verbose:
                    print(f"      Got {len(blame_new)} blame entries for new version")
            except Exception as e:
                if verbose:
                    print(f"      Warning: could not get blame for {new_filepath} at {new_revision}: {e}")

        # Get blame for old version if different from new (e.g. renames, different revision)
        blame_old: dict = blame_new
        old_blame_ok = new_blame_ok
        if old_revision and old_filepath != new_filepath:
            try:
                blame_old = get_blame_for_revision(old_filepath, revision=old_revision)
                old_blame_ok = True
                if verbose:
                    print(f"      Got {len(blame_old)} blame entries for old version (renamed path)")
            except Exception as e:
                blame_old = {}
                old_blame_ok = False
                if verbose:
                    print(f"      Warning: could not get blame for {old_filepath} at {old_revision}: {e}")
        elif old_revision and old_filepath == new_filepath and old_revision != new_revision:
            # Same path but different revision — re-blame
            try:
                blame_old = get_blame_for_revision(old_filepath, revision=old_revision)
                old_blame_ok = True
                if verbose:
                    print(f"      Got {len(blame_old)} blame entries for old version (different revision)")
            except Exception as e:
                old_blame_ok = new_blame_ok
                if verbose:
                    print(f"      Warning: could not get blame for {old_filepath} at {old_revision}: {e}")

        # Map blame by line number for additions and context
        mapped_count = 0
        for hunk in file.hunks:
            for line in hunk.lines:
                if line.line_type in ("addition", "context") and line.new_lineno:
                    entry = blame_new.get(line.new_lineno) if new_blame_ok else None
                    if entry:
                        key = str(fi) + ":" + str(line.new_lineno)
                        line_blame[key] = entry
                        all_commits.add(entry["commit"])
                        mapped_count += 1

                elif line.line_type == "deletion" and line.old_lineno:
                    if old_blame_ok:
                        entry = blame_old.get(line.old_lineno)
                        if entry:
                            key = str(fi) + ":" + str(line.old_lineno)
                            line_blame[key] = entry
                            all_commits.add(entry["commit"])
                            mapped_count += 1

        if verbose:
            print(f"      Mapped {mapped_count} lines to blame data")

        # Report progress after each file
        if progress_callback is not None:
            progress_callback(fi + 1, len(files), file.display_path)

    # Collect commit metadata for all unique commits
    commits: dict = {}
    if blame_attempted and all_commits:
        if verbose:
            print(f"  Collecting metadata for {len(all_commits)} unique commits...")
        for chash in all_commits:
            if chash and len(chash) == 40:
                try:
                    info = get_commit_info(chash)
                    commits[chash] = info
                except Exception as e:
                    if verbose:
                        print(f"    Warning: could not get commit info for {chash[:8]}: {e}")

    # Warn if blame was attempted but produced no data at all
    if blame_attempted and not line_blame:
        import sys as _sys
        _sys.stderr.write(
            "Warning: git blame could not collect data for any files. "
            "Try --verbose for details.\n"
        )

    return {
        "line_blame": line_blame,
        "commits": commits,
    }


def _collect_search_data(files: list[DiffFile], blame_data: dict, commits_data: dict) -> dict:
    """Collect searchable data from files, blame, and commits for frontend search."""
    file_names = [f.display_path for f in files]
    author_names = set()
    commit_subjects = []

    for entry in blame_data.values():
        if entry.get("author"):
            author_names.add(entry["author"])

    for info in commits_data.values():
        if info.get("subject"):
            commit_subjects.append(info["subject"])

    return {
        "files": file_names,
        "authors": sorted(author_names),
        "subjects": commit_subjects,
    }


def generate_report(
    files: list[DiffFile],
    output_path: str = "diffstory-report.html",
    repo_name: Optional[str] = None,
    staged: bool = False,
    commit_a: Optional[str] = None,
    commit_b: Optional[str] = None,
    verbose: bool = False,
    progress_callback: Optional[callable] = None,
) -> str:
    """Generate a self-contained HTML report.

    Args:
        files: List of parsed DiffFile objects.
        output_path: Path where the report will be saved.
        repo_name: Optional repository name override.
        staged: Whether the diff is from staged changes.
        commit_a: First commit in a range comparison.
        commit_b: Second commit in a range comparison.
        verbose: Whether to print progress messages.
    """
    if verbose:
        print(f"  Generating report for {len(files)} file(s)...")
    from pathlib import Path

    lexer_cache: dict = {}
    report_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Collect blame data
    try:
        blame_data_dict = _collect_blame_data(
            files, staged=staged, commit_a=commit_a, commit_b=commit_b, verbose=verbose,
            progress_callback=progress_callback,
        )
    except Exception as e:
        if verbose:
            print(f"  Warning: blame collection failed: {e}")
        blame_data_dict = {"line_blame": {}, "commits": {}}

    blame_line_count = len(blame_data_dict["line_blame"])
    blame_commit_count = len(blame_data_dict["commits"])
    if verbose:
        print(f"  Blame data: {blame_line_count} lines mapped, {blame_commit_count} commits")

    stats = _compute_stats(files, blame_data=blame_data_dict["line_blame"], commits_data=blame_data_dict["commits"])

    # Collect search data
    search_data = _collect_search_data(files, blame_data_dict["line_blame"], blame_data_dict["commits"])

    # Render all file sections
    file_sections_html = ""
    file_sidebar_items_html = ""

    for i, file in enumerate(files):
        file_sections_html += _render_file_section(file, i, lexer_cache)
        additions = sum(1 for h in file.hunks for l in h.lines if l.line_type == "addition")
        deletions = sum(1 for h in file.hunks for l in h.lines if l.line_type == "deletion")
        status_icon = {
            "added": "&#43;",
            "deleted": "&#8722;",
            "renamed": "&#8594;",
            "modified": "&#9679;",
        }.get(file.status, "&#9679;")
        status_class = "file-status-" + file.status
        file_sidebar_items_html += (
            '<div class="sidebar-file" onclick="scrollToFile(' + "'file-" + str(i) + "'" + ')">\n'
            '<span class="sidebar-file-icon ' + status_class + '">' + status_icon + '</span>\n'
            '<span class="sidebar-file-name">' + escape(file.display_path) + '</span>\n'
            '<span class="sidebar-file-stats">'
            '<span class="stat-add">+' + str(additions) + '</span>'
            '<span class="stat-del">-' + str(deletions) + '</span>'
            '</span>\n'
            '</div>\n'
        )

    repo = repo_name or get_repo_name()
    stats_table = _build_stats_table(stats)

    # Compute file extensions for filter chips
    all_extensions = sorted(set(
        "." + f.display_path.rsplit(".", 1)[1].lower()
        for f in files if "." in f.display_path
    ))
    change_types = sorted(set(f.status for f in files))

    # Serialize data for embedding in HTML
    blame_json = json.dumps(blame_data_dict["line_blame"])
    commits_json = json.dumps(blame_data_dict["commits"])
    search_json = json.dumps(search_data)

    # Build extension filter buttons HTML
    ext_filters_html = ""
    for ext in all_extensions:
        ext_filters_html += (
            '<button class="filter-chip filter-ext" data-ext="' + ext + '" onclick="toggleFilterExt(\'' + ext + '\')">'
            + ext + '</button>'
        )

    # Build change type filter buttons HTML
    type_filters_html = ""
    for ct in ["added", "deleted", "modified", "renamed"]:
        if ct in change_types:
            cls = "filter-chip filter-type filter-" + ct
            label = ct.capitalize()
            type_filters_html += (
                '<button class="' + cls + '" data-type="' + ct + '" onclick="toggleFilterType(\'' + ct + '\')">'
                + label + '</button>'
            )

    html = _build_html_template(
        repo=repo,
        report_time=report_time,
        stats=stats,
        stats_table=stats_table,
        file_sections_html=file_sections_html,
        file_sidebar_html=file_sidebar_items_html,
        blame_json=blame_json,
        commits_json=commits_json,
        search_json=search_json,
        ext_filters_html=ext_filters_html,
        type_filters_html=type_filters_html,
    )

    output = Path(output_path)
    output.write_text(html, encoding="utf-8")
    return str(output.resolve())


def _build_html_template(
    repo: str,
    report_time: str,
    stats: dict,
    stats_table: str,
    file_sections_html: str,
    file_sidebar_html: str,
    blame_json: str = "{}",
    commits_json: str = "{}",
    search_json: str = "{}",
    ext_filters_html: str = "",
    type_filters_html: str = "",
) -> str:
    """Build the complete self-contained HTML document."""
    css = _get_css()
    syntax_css = get_syntax_styles()
    js = _get_javascript()

    escaped_repo = escape(repo)
    escaped_time = escape(report_time)

    # Build author breakdown HTML
    author_html = ""
    for a in stats.get("author_breakdown", []):
        author_html += '<div class="stats-author"><span class="author-name">' + escape(a["name"]) + '</span><span class="author-commits">' + str(a["commits"]) + ' commits</span></div>'

    return (
        '<!DOCTYPE html>\n'
        '<html lang="en" data-theme="light">\n'
        '<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        '<title>DiffStory &mdash; ' + escaped_repo + '</title>\n'
        '<style>\n'
        + css + '\n'
        + syntax_css + '\n'
        + '</style>\n'
        '</head>\n'
        '<body>\n'
        '<!-- Embedded data -->\n'
        '<script id="diffstory-blame-data" type="application/json">' + blame_json + '</script>\n'
        '<script id="diffstory-commit-data" type="application/json">' + commits_json + '</script>\n'
        '<script id="diffstory-search-data" type="application/json">' + search_json + '</script>\n'
        '<div id="app">\n'
        '    <header id="toolbar">\n'
        '        <div class="toolbar-left">\n'
        '            <span class="toolbar-title">DiffStory</span>\n'
        '            <span class="toolbar-repo">' + escaped_repo + '</span>\n'
        '        </div>\n'
        '        <div class="toolbar-center">\n'
        '            <button class="view-btn active" data-view="unified" onclick="switchView(\'unified\')" title="Unified View (U)">Unified</button>\n'
        '            <button class="view-btn" data-view="sidebyside" onclick="switchView(\'sidebyside\')" title="Side-by-Side (S)">Side-by-Side</button>\n'
        '            <button class="view-btn" data-view="inline" onclick="switchView(\'inline\')" title="Inline Edit (I)">Inline</button>\n'
        '        </div>\n'
        '        <div class="toolbar-right">\n'
        '            <button class="tool-btn" onclick="focusSearch()" id="search-btn" title="Search (F or /)">\n'
        '                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" class="tool-icon">\n'
        '                    <path d="M10.68 11.74a6 6 0 0 1-7.922-8.982 6 6 0 0 1 8.982 7.922l3.04 3.04a.749.749 0 0 1-.326 1.275.749.749 0 0 1-.734-.215ZM11.5 7a4.499 4.499 0 1 0-8.997 0A4.499 4.499 0 0 0 11.5 7Z"/>\n'
        '                </svg>\n'
        '            </button>\n'
        '            <button class="tool-btn" onclick="toggleTheme()" id="theme-btn" title="Toggle Theme (D)">\n'
        '                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" class="tool-icon" id="theme-icon">\n'
        '                    <path d="M8 12a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0-1.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm5.657-8.157a.75.75 0 0 1 0 1.061l-1.061 1.06a.749.749 0 0 1-1.275-.326.749.749 0 0 1 .215-.734l1.06-1.06a.75.75 0 0 1 1.06 0Zm-9.193 9.193a.75.75 0 0 1 0 1.06l-1.06 1.061a.75.75 0 1 1-1.061-1.06l1.06-1.061a.75.75 0 0 1 1.061 0ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0ZM3 8a.75.75 0 0 1-.75.75H.75a.75.75 0 0 1 0-1.5h1.5A.75.75 0 0 1 3 8Zm13 0a.75.75 0 0 1-.75.75h-1.5a.75.75 0 0 1 0-1.5h1.5A.75.75 0 0 1 16 8Zm-8 5a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13Zm3.536-1.464a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.751.751 0 0 1-.018 1.042.751.751 0 0 1-1.042.018l-1.06-1.06a.75.75 0 0 1 0-1.06Z"/>\n'
        '                </svg>\n'
        '            </button>\n'
        '            <button class="tool-btn" onclick="toggleStats()" id="stats-btn" title="Statistics">\n'
        '                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" class="tool-icon">\n'
        '                    <path d="M1.5 1.75V13.5h13.75a.75.75 0 0 1 0 1.5H.75a.75.75 0 0 1-.75-.75V1.75a.75.75 0 0 1 1.5 0Zm14.28 2.53-5.25 5.25a.75.75 0 0 1-1.06 0L7 7.06 4.28 9.78a.751.751 0 0 1-1.042-.018.751.751 0 0 1-.018-1.042l3.25-3.25a.75.75 0 0 1 1.06 0L10 7.94l4.72-4.72a.751.751 0 0 1 1.042.018.751.751 0 0 1 .018 1.042Z"/>\n'
        '                </svg>\n'
        '            </button>\n'
        '            <button class="tool-btn" onclick="toggleSidebar()" id="sidebar-btn" title="File List">\n'
        '                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16" class="tool-icon">\n'
        '                    <path d="M6.823 7.823a.25.25 0 0 1 0 .354l-2.396 2.396A.25.25 0 0 1 4 10.396V5.604a.25.25 0 0 1 .427-.177Z"/>\n'
        '                    <path d="M1.75 0h12.5C15.216 0 16 .784 16 1.75v12.5A1.75 1.75 0 0 1 14.25 16H1.75A1.75 1.75 0 0 1 0 14.25V1.75C0 .784.784 0 1.75 0ZM1.5 1.75v12.5c0 .138.112.25.25.25H9.5v-13H1.75a.25.25 0 0 0-.25.25ZM11 14.5h3.25a.25.25 0 0 0 .25-.25V1.75a.25.25 0 0 0-.25-.25H11Z"/>\n'
        '                </svg>\n'
        '            </button>\n'
        '        </div>\n'
        '    </header>\n'
        '    <!-- Global Search Bar -->\n'
        '    <div id="search-bar" class="search-bar hidden">\n'
        '        <input type="text" id="global-search" placeholder="Search files, authors, commits, code... (Esc to close)" oninput="doGlobalSearch()">\n'
        '        <span id="search-count" class="search-count"></span>\n'
        '        <button class="search-clear" onclick="clearGlobalSearch()">&times;</button>\n'
        '    </div>\n'
        '    <!-- Filter Bar -->\n'
        '    <div id="filter-bar" class="filter-bar">\n'
        '        <div class="filter-group">\n'
        '            <span class="filter-label">Type:</span>\n'
        + type_filters_html + '\n'
        '        </div>\n'
        '        <div class="filter-group">\n'
        '            <span class="filter-label">Ext:</span>\n'
        + ext_filters_html + '\n'
        '        </div>\n'
        '        <button class="filter-chip filter-clear" onclick="clearFilters()">Clear all</button>\n'
        '    </div>\n'
        '    <div id="stats-panel" class="stats-panel hidden">\n'
        '        <div class="stats-header">\n'
        '            <h2>Statistics</h2>\n'
        '            <button class="close-btn" onclick="toggleStats()">&times;</button>\n'
        '        </div>\n'
        '        <div class="stats-grid">\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats["files_changed"]) + '</div>\n'
        '                <div class="stat-label">Files Changed</div>\n'
        '            </div>\n'
        '            <div class="stat-card stat-add-bg">\n'
        '                <div class="stat-value">+' + str(stats["additions"]) + '</div>\n'
        '                <div class="stat-label">Additions</div>\n'
        '            </div>\n'
        '            <div class="stat-card stat-del-bg">\n'
        '                <div class="stat-value">-' + str(stats["deletions"]) + '</div>\n'
        '                <div class="stat-label">Deletions</div>\n'
        '            </div>\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats["added_files"]) + '</div>\n'
        '                <div class="stat-label">Added</div>\n'
        '            </div>\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats["deleted_files"]) + '</div>\n'
        '                <div class="stat-label">Deleted</div>\n'
        '            </div>\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats["modified_files"]) + '</div>\n'
        '                <div class="stat-label">Modified</div>\n'
        '            </div>\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats["renamed_files"]) + '</div>\n'
        '                <div class="stat-label">Renamed</div>\n'
        '            </div>\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats.get("authors", 0)) + '</div>\n'
        '                <div class="stat-label">Authors</div>\n'
        '            </div>\n'
        '            <div class="stat-card">\n'
        '                <div class="stat-value">' + str(stats.get("commits", 0)) + '</div>\n'
        '                <div class="stat-label">Commits</div>\n'
        '            </div>\n'
        '        </div>\n'
        '        <div class="stats-table-section">\n'
        '            <h3>Most Changed Files</h3>\n'
        '            <table class="stats-table">\n'
        '                <thead>\n'
        '                    <tr><th>File</th><th>+</th><th>-</th><th>Total</th></tr>\n'
        '                </thead>\n'
        '                <tbody>\n'
        + stats_table + '\n'
        '                </tbody>\n'
        '            </table>\n'
        '        </div>\n'
        '        <div class="stats-table-section">\n'
        '            <h3>Contributors</h3>\n'
        '            <div class="stats-authors">' + author_html + '</div>\n'
        '        </div>\n'
        '    </div>\n'
        '    <!-- Tooltip -->\n'
        '    <div id="tooltip" class="tooltip hidden"></div>\n'
        '    <!-- Commit Drawer -->\n'
        '    <div id="commit-drawer" class="commit-drawer hidden">\n'
        '        <div class="drawer-header">\n'
        '            <h2>Commit Details</h2>\n'
        '            <button class="close-btn" onclick="closeDrawer()">&times;</button>\n'
        '        </div>\n'
        '        <div id="drawer-content" class="drawer-content">\n'
        '            <div class="drawer-loading">Select a changed line to view commit details...</div>\n'
        '        </div>\n'
        '    </div>\n'
        '    <div id="drawer-overlay" class="drawer-overlay hidden" onclick="closeDrawer()"></div>\n'
        '    <div id="main-content">\n'
        '        <nav id="sidebar" class="sidebar">\n'
        '            <div class="sidebar-search">\n'
        '                <input type="text" id="file-search" placeholder="Search files..." oninput="filterFiles()">\n'
        '            </div>\n'
        '            <div class="sidebar-files">\n'
        + file_sidebar_html + '\n'
        '            </div>\n'
        '        </nav>\n'
        '        <main id="diff-content" class="diff-content">\n'
        '            <div class="report-meta">\n'
        '                Generated on ' + escaped_time + '\n'
        '                <span id="active-filters" class="active-filters"></span>\n'
        '            </div>\n'
        + file_sections_html + '\n'
        '        </main>\n'
        '    </div>\n'
        '</div>\n'
        '<script>\n'
        + js + '\n'
        '</script>\n'
        '</body>\n'
        '</html>'
    )


def _get_css() -> str:
    """Get all CSS styles for the report."""
    return """\
/* Reset & Base */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root, [data-theme="light"] {
    --bg: #ffffff;
    --bg-secondary: #f6f8fa;
    --bg-tertiary: #eaeef2;
    --text: #1f2328;
    --text-secondary: #656d76;
    --border: #d0d7de;
    --border-light: #e0e4e8;
    --line-number-color: #6e7681;
    --diff-context-color: #656d76;
    --accent: #0969da;
    --accent-hover: #0550ae;
    --add-bg: #e6ffec;
    --add-text: #116329;
    --add-icon: #1a7f37;
    --del-bg: #ffebe9;
    --del-text: #82071e;
    --del-icon: #cf222e;
    --wd-add-bg: #abf2bc;
    --wd-del-bg: #fbbfbc;
    --hunk-header-bg: #f0f4f8;
    --hunk-header-text: #57606a;
    --toolbar-bg: #f6f8fa;
    --toolbar-border: #d0d7de;
    --sidebar-bg: #f6f8fa;
    --sidebar-hover: #eaeef2;
    --sidebar-active: #ddf4ff;
    --card-shadow: 0 1px 3px rgba(0,0,0,0.08);
    --line-num-color: #6e7681;
    --btn-hover: #eaeef2;
    --scrollbar-thumb: #c0c8d0;
    --stats-bg: #ffffff;
}

[data-theme="dark"] {
    --bg: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text: #e6edf3;
    --text-secondary: #8b949e;
    --border: #30363d;
    --border-light: #21262d;
    --line-number-color: #484f58;
    --diff-context-color: #8b949e;
    --accent: #58a6ff;
    --accent-hover: #79c0ff;
    --add-bg: #12262b;
    --add-text: #7ee787;
    --add-icon: #3fb950;
    --del-bg: #25171c;
    --del-text: #ffa198;
    --del-icon: #f85149;
    --wd-add-bg: #1b3626;
    --wd-del-bg: #362024;
    --hunk-header-bg: #161b22;
    --hunk-header-text: #8b949e;
    --toolbar-bg: #161b22;
    --toolbar-border: #30363d;
    --sidebar-bg: #161b22;
    --sidebar-hover: #21262d;
    --sidebar-active: #1f2e3d;
    --card-shadow: 0 1px 3px rgba(0,0,0,0.3);
    --line-num-color: #484f58;
    --btn-hover: #21262d;
    --scrollbar-thumb: #30363d;
    --stats-bg: #161b22;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif, 'Apple Color Emoji';
    font-size: 14px;
    line-height: 1.5;
    color: var(--text);
    background: var(--bg);
    overflow: hidden;
    height: 100vh;
}

#app {
    display: flex;
    flex-direction: column;
    height: 100vh;
}

.tool-icon {
    display: block;
    fill: currentColor;
}

.tool-btn svg.tool-icon {
    pointer-events: none;
}

/* Toolbar */
#toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 8px 16px;
    background: var(--toolbar-bg);
    border-bottom: 1px solid var(--toolbar-border);
    flex-shrink: 0;
    z-index: 100;
    gap: 12px;
}

.toolbar-left {
    display: flex;
    align-items: center;
    gap: 12px;
    min-width: 200px;
}

.toolbar-title {
    font-weight: 700;
    font-size: 16px;
    color: var(--accent);
}

.toolbar-repo {
    font-size: 13px;
    color: var(--text-secondary);
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.toolbar-center {
    display: flex;
    gap: 4px;
}

.view-btn {
    padding: 6px 14px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    border-radius: 6px;
    cursor: pointer;
    font-size: 13px;
    font-weight: 500;
    transition: all 0.15s ease;
}

.view-btn:hover {
    background: var(--btn-hover);
    color: var(--text);
}

.view-btn.active {
    background: var(--accent);
    color: #ffffff;
    border-color: var(--accent);
}

.toolbar-right {
    display: flex;
    gap: 4px;
    min-width: 100px;
    justify-content: flex-end;
}

.tool-btn {
    padding: 6px 10px;
    border: 1px solid var(--border);
    background: transparent;
    color: var(--text-secondary);
    border-radius: 6px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.15s ease;
    line-height: 1;
}

.tool-btn:hover {
    background: var(--btn-hover);
    color: var(--text);
}

/* Main Content Layout */
#main-content {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* Sidebar */
.sidebar {
    width: 300px;
    min-width: 300px;
    background: var(--sidebar-bg);
    border-right: 1px solid var(--border);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: margin-left 0.2s ease, min-width 0.2s ease;
}

.sidebar.hidden {
    margin-left: -300px;
    min-width: 0;
    width: 0;
    border-right: none;
}

.sidebar-search {
    padding: 12px;
    border-bottom: 1px solid var(--border);
}

.sidebar-search input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
    outline: none;
    transition: border-color 0.15s;
}

.sidebar-search input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.15);
}

.sidebar-files {
    flex: 1;
    overflow-y: auto;
    padding: 4px 0;
}

.sidebar-file {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    cursor: pointer;
    transition: background 0.1s;
    border-left: 3px solid transparent;
}

.sidebar-file:hover {
    background: var(--sidebar-hover);
}

.sidebar-file.active {
    background: var(--sidebar-active);
    border-left-color: var(--accent);
}

.sidebar-file-icon {
    font-weight: 700;
    font-size: 12px;
    width: 18px;
    text-align: center;
    flex-shrink: 0;
}

.sidebar-file-icon.file-status-added { color: var(--add-icon); }
.sidebar-file-icon.file-status-deleted { color: var(--del-icon); }
.sidebar-file-icon.file-status-modified { color: var(--accent); }
.sidebar-file-icon.file-status-renamed { color: var(--text-secondary); }

.sidebar-file-name {
    flex: 1;
    font-size: 13px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--text);
}

.sidebar-file-stats {
    font-size: 11px;
    font-weight: 600;
    flex-shrink: 0;
    display: flex;
    gap: 4px;
}

/* Diff Content */
.diff-content {
    flex: 1;
    overflow-y: auto;
    padding: 16px 24px;
}

.report-meta {
    font-size: 12px;
    color: var(--text-secondary);
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-light);
    margin-bottom: 16px;
}

/* File Section */
.file-section {
    margin-bottom: 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    background: var(--bg);
    box-shadow: var(--card-shadow);
}

.file-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 14px;
    background: var(--bg-secondary);
    cursor: pointer;
    user-select: none;
    transition: background 0.1s;
    border-bottom: 1px solid var(--border);
}

.file-header:hover {
    background: var(--bg-tertiary);
}

.file-status-icon {
    font-weight: 700;
    font-size: 13px;
    width: 20px;
    text-align: center;
}

.file-status-icon.file-status-added { color: var(--add-icon); }
.file-status-icon.file-status-deleted { color: var(--del-icon); }
.file-status-icon.file-status-modified { color: var(--accent); }
.file-status-icon.file-status-renamed { color: var(--text-secondary); }

.file-label {
    flex: 1;
    font-size: 14px;
    font-weight: 600;
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.rename-badge {
    font-size: 12px;
    color: var(--text-secondary);
    font-weight: 400;
}

.file-stats {
    font-size: 12px;
    font-weight: 600;
    display: flex;
    gap: 6px;
}

.stat-add { color: var(--add-icon); }
.stat-del { color: var(--del-icon); }

.file-toggle {
    font-size: 11px;
    color: var(--text-secondary);
    transition: transform 0.15s ease;
}

.file-section.collapsed .file-toggle {
    transform: rotate(-90deg);
}

.file-section.collapsed .file-diff-content {
    display: none;
}

/* File diff content */
.file-diff-content {
    overflow-x: auto;
}

/* Diff Views */
.diff-view {
    display: none;
}

.diff-view.active-view {
    display: block;
}

/* Hunk Header */
.hunk-header {
    padding: 6px 14px;
    background: var(--hunk-header-bg);
    color: var(--hunk-header-text);
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    font-size: 12px;
    border-bottom: 1px solid var(--border-light);
}

.hunk-header-text {
    color: var(--text-secondary);
}

/* Unified View Lines */
.diff-line {
    display: flex;
    align-items: stretch;
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    font-size: 12px;
    line-height: 1.5;
    min-height: 22px;
}

.diff-line:hover {
    background: rgba(0,0,0,0.02);
}

[data-theme="dark"] .diff-line:hover {
    background: rgba(255,255,255,0.03);
}

.diff-context { background: transparent; }
.diff-addition { background: var(--add-bg); }
.diff-deletion { background: var(--del-bg); }

.line-prefix {
    width: 20px;
    min-width: 20px;
    text-align: center;
    color: var(--text-secondary);
    user-select: none;
    flex-shrink: 0;
    padding-top: 1px;
}

.diff-addition .line-prefix { color: var(--add-icon); }
.diff-deletion .line-prefix { color: var(--del-icon); }

.line-num {
    min-width: 40px;
    text-align: right;
    padding: 0 8px;
    color: var(--line-num-color);
    user-select: none;
    flex-shrink: 0;
    font-size: 11px;
    border-right: 1px solid var(--border-light);
}

.line-num-old {
    width: 50px;
    min-width: 50px;
}

.line-num-new {
    width: 50px;
    min-width: 50px;
    border-right: 2px solid var(--border-light);
}

.line-content {
    flex: 1;
    padding: 0 10px;
    white-space: pre-wrap;
    word-break: break-all;
}

/* Side-by-Side View */
.sbs-hunk { }

.sbs-row {
    display: flex;
}

.sbs-left, .sbs-right {
    width: 50%;
    display: flex;
    align-items: stretch;
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    font-size: 12px;
    line-height: 1.5;
    min-height: 22px;
}

.sbs-left {
    border-right: 1px solid var(--border);
}

.sbs-left .line-num-old,
.sbs-right .line-num-new {
    width: 50px;
    min-width: 50px;
}

.sbs-left .line-content,
.sbs-right .line-content {
    flex: 1;
    padding: 0 10px;
    white-space: pre-wrap;
    word-break: break-all;
}

.sbs-left.diff-addition,
.sbs-right.diff-addition { background: var(--add-bg); }
.sbs-left.diff-deletion,
.sbs-right.diff-deletion { background: var(--del-bg); }
.diff-empty { background: var(--bg-secondary); }

/* Inline Edit View - Word Diff */
.wd-removed {
    background: var(--wd-del-bg);
    color: var(--del-text);
    text-decoration: line-through;
    border-radius: 3px;
    padding: 0 2px;
}

.wd-added {
    background: var(--wd-add-bg);
    color: var(--add-text);
    border-radius: 3px;
    padding: 0 2px;
}

.wd-equal {
    color: var(--text);
}

/* Statistics Panel */
.stats-panel {
    position: fixed;
    top: 50px;
    right: 16px;
    width: 420px;
    max-height: calc(100vh - 70px);
    background: var(--stats-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    z-index: 200;
    overflow-y: auto;
    padding: 20px;
    transition: opacity 0.2s, transform 0.2s;
}

.stats-panel.hidden {
    opacity: 0;
    pointer-events: none;
    transform: translateY(-8px);
}

.stats-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
}

.stats-header h2 {
    font-size: 18px;
    font-weight: 600;
}

.close-btn {
    background: none;
    border: none;
    font-size: 22px;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
}

.close-btn:hover {
    background: var(--btn-hover);
}

.stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    margin-bottom: 20px;
}

.stat-card {
    padding: 12px;
    border: 1px solid var(--border-light);
    border-radius: 8px;
    text-align: center;
    background: var(--bg);
}

.stat-card.stat-add-bg { border-color: var(--add-icon); background: var(--add-bg); }
.stat-card.stat-del-bg { border-color: var(--del-icon); background: var(--del-bg); }

.stat-value {
    font-size: 24px;
    font-weight: 700;
    color: var(--text);
}

.stat-label {
    font-size: 11px;
    color: var(--text-secondary);
    margin-top: 2px;
}

.stats-table-section h3 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 8px;
}

.stats-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 13px;
}

.stats-table th {
    text-align: left;
    padding: 6px 8px;
    border-bottom: 1px solid var(--border);
    color: var(--text-secondary);
    font-weight: 500;
}

.stats-table td {
    padding: 6px 8px;
    border-bottom: 1px solid var(--border-light);
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    font-size: 12px;
}

.stats-table td:first-child {
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

/* Scrollbar Styling */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: transparent;
}

::-webkit-scrollbar-thumb {
    background: var(--scrollbar-thumb);
    border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--text-secondary);
}

/* Syntax highlighting overrides */
.highlight { background: transparent; }
.highlight .lineno { display: none; }

/* Tooltip */
.tooltip {
    position: fixed;
    z-index: 300;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    box-shadow: 0 4px 16px rgba(0,0,0,0.15);
    padding: 10px 14px;
    font-size: 12px;
    line-height: 1.5;
    max-width: 360px;
    pointer-events: none;
    transition: opacity 0.12s ease;
}

.tooltip.hidden {
    opacity: 0;
    pointer-events: none;
}

.tooltip-author {
    font-weight: 600;
    color: var(--text);
    font-size: 13px;
}

.tooltip-commit {
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    font-size: 11px;
    color: var(--text-secondary);
}

.tooltip-subject {
    color: var(--text);
    margin-top: 2px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.tooltip-date {
    color: var(--text-secondary);
    font-size: 11px;
    margin-top: 1px;
}

.tooltip-click-hint {
    color: var(--text-secondary);
    font-size: 10px;
    margin-top: 4px;
    border-top: 1px solid var(--border-light);
    padding-top: 3px;
    font-style: italic;
}

/* Commit Drawer */
.commit-drawer {
    position: fixed;
    top: 0;
    right: 0;
    width: 460px;
    max-width: 100vw;
    height: 100vh;
    background: var(--bg);
    border-left: 1px solid var(--border);
    box-shadow: -4px 0 24px rgba(0,0,0,0.15);
    z-index: 400;
    display: flex;
    flex-direction: column;
    transition: transform 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.commit-drawer.hidden {
    transform: translateX(100%);
}

.drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
}

.drawer-header h2 {
    font-size: 16px;
    font-weight: 600;
}

.drawer-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
}

.drawer-loading {
    color: var(--text-secondary);
    text-align: center;
    padding: 40px 0;
}

.drawer-section {
    margin-bottom: 16px;
}

.drawer-section-title {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
    margin-bottom: 4px;
}

.drawer-commit-hash {
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
    font-size: 13px;
    color: var(--accent);
}

.drawer-subject {
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.4;
}

.drawer-body {
    font-size: 13px;
    color: var(--text-secondary);
    line-height: 1.6;
    white-space: pre-wrap;
    margin-top: 8px;
}

.drawer-meta-grid {
    display: grid;
    grid-template-columns: 90px 1fr;
    gap: 6px 12px;
    font-size: 13px;
}

.drawer-meta-label {
    color: var(--text-secondary);
    font-weight: 500;
}

.drawer-meta-value {
    color: var(--text);
}

.drawer-stats {
    display: flex;
    gap: 16px;
    margin-top: 8px;
}

.drawer-stat {
    text-align: center;
}

.drawer-stat-value {
    font-size: 20px;
    font-weight: 700;
}

.drawer-stat-label {
    font-size: 11px;
    color: var(--text-secondary);
}

.drawer-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0,0,0,0.3);
    z-index: 399;
    transition: opacity 0.2s;
}

.drawer-overlay.hidden {
    opacity: 0;
    pointer-events: none;
}

/* Search Bar */
.search-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    flex-shrink: 0;
    transition: all 0.15s ease;
}

.search-bar.hidden {
    display: none;
}

.search-bar input {
    flex: 1;
    padding: 7px 12px;
    border: 1px solid var(--border);
    border-radius: 6px;
    background: var(--bg);
    color: var(--text);
    font-size: 13px;
    outline: none;
}

.search-bar input:focus {
    border-color: var(--accent);
    box-shadow: 0 0 0 3px rgba(9, 105, 218, 0.15);
}

.search-count {
    font-size: 12px;
    color: var(--text-secondary);
    white-space: nowrap;
}

.search-clear {
    background: none;
    border: none;
    font-size: 18px;
    color: var(--text-secondary);
    cursor: pointer;
    padding: 2px 8px;
    border-radius: 4px;
    line-height: 1;
}

.search-clear:hover {
    background: var(--btn-hover);
    color: var(--text);
}

/* Filter Bar */
.filter-bar {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 16px;
    background: var(--bg-secondary);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
    flex-shrink: 0;
}

.filter-group {
    display: flex;
    align-items: center;
    gap: 4px;
}

.filter-label {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.3px;
    margin-right: 2px;
}

.filter-chip {
    padding: 3px 10px;
    border: 1px solid var(--border);
    background: var(--bg);
    color: var(--text-secondary);
    border-radius: 12px;
    cursor: pointer;
    font-size: 11px;
    font-weight: 500;
    transition: all 0.15s ease;
}

.filter-chip:hover {
    background: var(--btn-hover);
    color: var(--text);
}

.filter-chip.active {
    background: var(--accent);
    color: #ffffff;
    border-color: var(--accent);
}

.filter-chip.active.filter-added { background: var(--add-icon); border-color: var(--add-icon); }
.filter-chip.active.filter-deleted { background: var(--del-icon); border-color: var(--del-icon); }
.filter-chip.active.filter-modified { background: var(--accent); border-color: var(--accent); }
.filter-chip.active.filter-renamed { background: var(--text-secondary); border-color: var(--text-secondary); }

.filter-clear {
    margin-left: auto;
    font-size: 11px;
    padding: 3px 10px;
    color: var(--del-icon);
    border-color: var(--del-bg);
    background: var(--del-bg);
}

.filter-clear:hover {
    background: var(--del-bg);
    color: var(--del-text);
}

/* Active filters display */
.active-filters {
    margin-left: 12px;
    font-size: 12px;
    color: var(--text-secondary);
}

/* Hide filtered-out file sections */
.file-section.hidden-by-search,
.file-section.hidden-by-filter {
    display: none;
}

/* Search match highlight */
.search-match {
    background: #ffd70044;
    border-radius: 2px;
    padding: 0 1px;
}

[data-theme="dark"] .search-match {
    background: #ffd70033;
}

/* Binary file preview */
.binary-container {
    padding: 20px;
    text-align: center;
}

.binary-preview {
    padding: 24px;
    border: 2px dashed var(--border);
    border-radius: 8px;
    background: var(--bg-secondary);
    max-width: 400px;
    margin: 0 auto;
}

.binary-icon {
    font-size: 40px;
    margin-bottom: 8px;
}

.binary-label {
    font-size: 14px;
    font-weight: 600;
    color: var(--text);
    font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace;
}

.binary-note {
    font-size: 12px;
    color: var(--text-secondary);
    margin-top: 4px;
}

/* Diff line hover cursor for blame */
.diff-line {
    cursor: pointer;
}

/* Responsive */
@media (max-width: 768px) {
    .sidebar { display: none; }
    .diff-content { padding: 8px 12px; }
    .toolbar-center .view-btn { padding: 4px 8px; font-size: 11px; }
    .stats-panel { width: calc(100% - 32px); right: 16px; }
    .commit-drawer { width: 100vw; }
}
"""


def _get_javascript() -> str:
    """Get JavaScript for interactivity — blame tooltips, commit drawer, etc."""
    return """\
// Load blame, commit, and search data
var blameData = {};
var commitData = {};
var searchData = {};
try {
    var blameEl = document.getElementById('diffstory-blame-data');
    if (blameEl) blameData = JSON.parse(blameEl.textContent);
    var commitEl = document.getElementById('diffstory-commit-data');
    if (commitEl) commitData = JSON.parse(commitEl.textContent);
    var searchEl = document.getElementById('diffstory-search-data');
    if (searchEl) searchData = JSON.parse(searchEl.textContent);
} catch(e) {}

// Helper: format a timestamp as relative time
function relativeTime(dateStr) {
    var now = new Date();
    var d = new Date(dateStr);
    var diff = Math.floor((now - d) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 2592000) return Math.floor(diff / 86400) + 'd ago';
    if (diff < 31536000) return Math.floor(diff / 2592000) + 'mo ago';
    return Math.floor(diff / 31536000) + 'y ago';
}

// Helper: format date nicely
function formatDate(dateStr) {
    try {
        var d = new Date(dateStr);
        return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch(e) {
        return dateStr;
    }
}

// Helper: short commit hash
function shortHash(hash) {
    return hash ? hash.substring(0, 7) : '???????';
}

// Tooltip
var tooltipEl = document.getElementById('tooltip');

function getBlameKey(fileIdx, lineType, oldNo, newNo) {
    if (lineType === 'deletion' && oldNo) return fileIdx + ':' + oldNo;
    if (newNo) return fileIdx + ':' + newNo;
    return null;
}

function buildTooltipHtml(key) {
    if (!key || !blameData[key]) return null;
    var blame = blameData[key];
    var commitHash = blame.commit;
    var short = shortHash(commitHash);
    var author = blame.author || 'Unknown';
    var subject = blame.summary || '';
    var dateStr = '';
    if (blame.date && blame.date.match(/^\\d+$/)) {
        var d = new Date(parseInt(blame.date) * 1000);
        dateStr = d.toISOString();
    } else if (blame.date) {
        dateStr = blame.date;
    }

    var commitInfo = commitData[commitHash] || {};
    var fullSubject = commitInfo.subject || subject;
    var authorName = commitInfo.author || author;
    var authorDate = commitInfo.author_date || dateStr;

    var html = '';
    html += '<div class="tooltip-author">' + escapeHtml(authorName) + '</div>';
    html += '<div class="tooltip-commit">' + short + '</div>';
    if (fullSubject) {
        html += '<div class="tooltip-subject">' + escapeHtml(fullSubject) + '</div>';
    }
    if (authorDate) {
        html += '<div class="tooltip-date">' + formatDate(authorDate) + ' (' + relativeTime(authorDate) + ')</div>';
    }
    html += '<div class="tooltip-click-hint">Click for details</div>';
    return html;
}

var tooltipCurrentKey = null;

function showTooltip(event, fileIdx, lineType, oldNo, newNo) {
    var key = getBlameKey(fileIdx, lineType, oldNo, newNo);
    if (!key) { hideTooltip(); return; }

    // Rebuild HTML only if the key changed
    if (key !== tooltipCurrentKey) {
        var html = buildTooltipHtml(key);
        if (!html) { hideTooltip(); return; }
        tooltipEl.innerHTML = html;
        tooltipCurrentKey = key;
        tooltipEl.classList.remove('hidden');
    }

    // Position tooltip
    positionTooltip(event);
}

function positionTooltip(event) {
    if (tooltipEl.classList.contains('hidden')) return;
    var x = event.clientX + 14;
    var y = event.clientY - 10;
    var tw = tooltipEl.offsetWidth;
    var th = tooltipEl.offsetHeight;
    if (x + tw > window.innerWidth - 10) x = event.clientX - tw - 14;
    if (y + th > window.innerHeight - 10) y = event.clientY - th + 10;
    if (y < 5) y = 5;
    tooltipEl.style.left = x + 'px';
    tooltipEl.style.top = y + 'px';
}

function hideTooltip() {
    tooltipEl.classList.add('hidden');
    tooltipCurrentKey = null;
}

// Escape HTML for tooltip content
function escapeHtml(str) {
    if (!str) return '';
    return str
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
}

// Compute a stable file index from the DOM
function getFileIndex(lineEl) {
    var section = lineEl.closest('.file-section');
    if (!section) return -1;
    var id = section.id;
    if (id && id.startsWith('file-')) {
        return parseInt(id.substring(5));
    }
    return -1;
}

// Deep linking — scroll to file or line on page load
function handleDeepLink() {
    var hash = window.location.hash;
    if (!hash) return;
    hash = hash.substring(1); // remove #

    if (hash.startsWith('file-')) {
        setTimeout(function() {
            scrollToFile(hash);
        }, 100);
    } else if (hash.startsWith('L-')) {
        // #L-42 or #L-fileIdx-42
        var parts = hash.substring(2).split('-');
        if (parts.length === 2) {
            var fileIdx = parseInt(parts[0]);
            var lineNo = parseInt(parts[1]);
            var section = document.getElementById('file-' + fileIdx);
            if (section) {
                scrollToFile('file-' + fileIdx);
                // Try to find the line
                setTimeout(function() {
                    var lines = section.querySelectorAll('.diff-line');
                    for (var i = 0; i < lines.length; i++) {
                        var oldAttr = lines[i].getAttribute('data-old');
                        var newAttr = lines[i].getAttribute('data-new');
                        if (oldAttr == lineNo || newAttr == lineNo) {
                            lines[i].scrollIntoView({ behavior: 'smooth', block: 'center' });
                            lines[i].style.outline = '2px solid var(--accent)';
                            setTimeout(function() { lines[i].style.outline = ''; }, 2000);
                            break;
                        }
                    }
                }, 200);
            }
        }
    }
}

// Attach hover and click handlers to all diff lines
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.diff-line').forEach(function(el) {
        var fileIdx = getFileIndex(el);
        if (fileIdx < 0) return;

        var lineType = 'context';
        if (el.classList.contains('diff-addition')) lineType = 'addition';
        else if (el.classList.contains('diff-deletion')) lineType = 'deletion';

        var oldNo = el.getAttribute('data-old');
        var newNo = el.getAttribute('data-new');

        // Tooltip on hover
        el.addEventListener('mouseenter', function(e) {
            showTooltip(e, fileIdx, lineType, oldNo, newNo);
            tooltipEl.style.pointerEvents = 'none';
        });

        el.addEventListener('mousemove', function(e) {
            positionTooltip(e);
        });

        el.addEventListener('mouseleave', function() {
            hideTooltip();
        });

        // Commit drawer on click
        el.addEventListener('click', function(e) {
            var key = null;
            if (lineType === 'deletion' && oldNo) {
                key = fileIdx + ':' + oldNo;
            } else if (newNo) {
                key = fileIdx + ':' + newNo;
            }
            if (key && blameData[key]) {
                openDrawer(blameData[key].commit);
            }
        });
    });

    // Handle deep linking after all handlers are attached
    handleDeepLink();
});

// Also handle hash changes dynamically
window.addEventListener('hashchange', function() {
    handleDeepLink();
});

// View Switching
let currentView = 'unified';

function switchView(viewName) {
    currentView = viewName;
    document.querySelectorAll('.view-btn').forEach(function(btn) {
        btn.classList.toggle('active', btn.dataset.view === viewName);
    });
    document.querySelectorAll('.diff-view').forEach(function(view) {
        view.classList.toggle('active-view', view.classList.contains(viewName + '-view'));
    });
}

// Theme Toggle — swap sun/moon SVG
const sunPath = 'M8 12a4 4 0 1 1 0-8 4 4 0 0 1 0 8Zm0-1.5a2.5 2.5 0 1 0 0-5 2.5 2.5 0 0 0 0 5Zm5.657-8.157a.75.75 0 0 1 0 1.061l-1.061 1.06a.749.749 0 0 1-1.275-.326.749.749 0 0 1 .215-.734l1.06-1.06a.75.75 0 0 1 1.06 0Zm-9.193 9.193a.75.75 0 0 1 0 1.06l-1.06 1.061a.75.75 0 1 1-1.061-1.06l1.06-1.061a.75.75 0 0 1 1.061 0ZM8 0a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0V.75A.75.75 0 0 1 8 0ZM3 8a.75.75 0 0 1-.75.75H.75a.75.75 0 0 1 0-1.5h1.5A.75.75 0 0 1 3 8Zm13 0a.75.75 0 0 1-.75.75h-1.5a.75.75 0 0 1 0-1.5h1.5A.75.75 0 0 1 16 8Zm-8 5a.75.75 0 0 1 .75.75v1.5a.75.75 0 0 1-1.5 0v-1.5A.75.75 0 0 1 8 13Zm3.536-1.464a.75.75 0 0 1 1.06 0l1.061 1.06a.75.75 0 0 1-1.06 1.061l-1.061-1.06a.75.75 0 0 1 0-1.061ZM2.343 2.343a.75.75 0 0 1 1.061 0l1.06 1.061a.751.751 0 0 1-.018 1.042.751.751 0 0 1-1.042.018l-1.06-1.06a.75.75 0 0 1 0-1.06Z';
const moonPath = 'M9.598 1.591a.749.749 0 0 1 .785-.175 7.001 7.001 0 1 1-8.967 8.967.75.75 0 0 1 .961-.96 5.5 5.5 0 0 0 7.046-7.046.75.75 0 0 1 .175-.786Zm1.616 1.945a7 7 0 0 1-7.678 7.678 5.499 5.499 0 1 0 7.678-7.678Z';

function toggleTheme() {
    var html = document.documentElement;
    var isDark = html.getAttribute('data-theme') === 'dark';
    var newTheme = isDark ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('diffstory-theme', newTheme);
    // Swap icon: after toggling light→new moon, dark→new sun
    var icon = document.querySelector('#theme-btn path');
    if (icon) icon.setAttribute('d', newTheme === 'dark' ? sunPath : moonPath);
}

// Load saved theme
(function() {
    var saved = localStorage.getItem('diffstory-theme');
    if (saved) {
        document.documentElement.setAttribute('data-theme', saved);
        // Set initial icon
        var icon = document.querySelector('#theme-btn path');
        if (icon) icon.setAttribute('d', saved === 'dark' ? sunPath : moonPath);
    }
})();

// File Toggle (collapse/expand)
function toggleFile(header) {
    var section = header.closest('.file-section');
    section.classList.toggle('collapsed');
}

// Sidebar Toggle
var sidebarVisible = true;

function toggleSidebar() {
    sidebarVisible = !sidebarVisible;
    document.getElementById('sidebar').classList.toggle('hidden', !sidebarVisible);
}

// Stats Panel
function toggleStats() {
    document.getElementById('stats-panel').classList.toggle('hidden');
}

// Scroll to File
function scrollToFile(fileId) {
    var fileSection = document.getElementById(fileId);
    if (fileSection) {
        fileSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    document.querySelectorAll('.sidebar-file').forEach(function(el) {
        el.classList.remove('active');
    });
    var sidebarEl = document.querySelector('.sidebar-file[onclick*="' + fileId + '"]');
    if (sidebarEl) sidebarEl.classList.add('active');
}

// Commit Drawer
function openDrawer(commitHash) {
    var info = commitData[commitHash];
    if (!info) return;

    var drawer = document.getElementById('commit-drawer');
    var overlay = document.getElementById('drawer-overlay');
    var content = document.getElementById('drawer-content');

    var filesChanged = info.files_changed !== undefined ? info.files_changed : '?';
    var insertions = info.insertions !== undefined ? info.insertions : '?';
    var deletions = info.deletions !== undefined ? info.deletions : '?';

    var bodyHtml = '';
    if (info.body) {
        bodyHtml = '<div class="drawer-section"><div class="drawer-body">' + escapeHtml(info.body) + '</div></div>';
    }

    var parentHtml = '';
    if (info.parents && info.parents.length > 0) {
        parentHtml = '<div class="drawer-meta-grid"><div class="drawer-meta-label">Parents</div><div class="drawer-meta-value drawer-commit-hash">' +
            info.parents.map(function(p) { return shortHash(p); }).join(', ') + '</div></div>';
    }

    content.innerHTML = '' +
        '<div class="drawer-section">' +
        '    <div class="drawer-commit-hash">' + commitHash + '</div>' +
        '    <div class="drawer-subject">' + escapeHtml(info.subject || 'No subject') + '</div>' +
        bodyHtml +
        '</div>' +
        '<div class="drawer-section">' +
        '    <div class="drawer-section-title">Meta</div>' +
        '    <div class="drawer-meta-grid">' +
        '        <div class="drawer-meta-label">Author</div><div class="drawer-meta-value">' + escapeHtml(info.author || 'Unknown') + '</div>' +
        '        <div class="drawer-meta-label">Email</div><div class="drawer-meta-value">' + escapeHtml(info.author_email || '') + '</div>' +
        '        <div class="drawer-meta-label">Date</div><div class="drawer-meta-value">' + formatDate(info.author_date || '') + '</div>' +
        '        <div class="drawer-meta-label">Committer</div><div class="drawer-meta-value">' + escapeHtml(info.committer || '') + '</div>' +
        parentHtml +
        '    </div>' +
        '</div>' +
        '<div class="drawer-section">' +
        '    <div class="drawer-section-title">Stats</div>' +
        '    <div class="drawer-stats">' +
        '        <div class="drawer-stat"><div class="drawer-stat-value">' + filesChanged + '</div><div class="drawer-stat-label">Files</div></div>' +
        '        <div class="drawer-stat"><div class="drawer-stat-value stat-add">+' + insertions + '</div><div class="drawer-stat-label">Additions</div></div>' +
        '        <div class="drawer-stat"><div class="drawer-stat-value stat-del">-' + deletions + '</div><div class="drawer-stat-label">Deletions</div></div>' +
        '    </div>' +
        '</div>';

    drawer.classList.remove('hidden');
    overlay.classList.remove('hidden');
}

function closeDrawer() {
    document.getElementById('commit-drawer').classList.add('hidden');
    document.getElementById('drawer-overlay').classList.add('hidden');
}

// Global Search
function focusSearch() {
    var bar = document.getElementById('search-bar');
    bar.classList.remove('hidden');
    var input = document.getElementById('global-search');
    input.focus();
    input.select();
}

function doGlobalSearch() {
    var query = document.getElementById('global-search').value.toLowerCase().trim();
    var countEl = document.getElementById('search-count');
    var matchedFiles = [];

    document.querySelectorAll('.file-section').forEach(function(section) {
        section.classList.remove('hidden-by-search');
    });

    if (!query) {
        countEl.textContent = '';
        document.querySelectorAll('.search-match').forEach(function(el) {
            var parent = el.parentNode;
            while (el.firstChild) parent.insertBefore(el.firstChild, el);
            parent.removeChild(el);
        });
        return;
    }

    // Check each file section
    document.querySelectorAll('.file-section').forEach(function(section) {
        var fileName = section.dataset.file || '';
        var fileIdx = parseInt(section.id.replace('file-', ''));
        var match = false;

        // Check file name
        if (fileName.toLowerCase().includes(query)) match = true;

        // Check authors from search data
        if (!match && searchData.authors) {
            for (var i = 0; i < searchData.authors.length; i++) {
                if (searchData.authors[i].toLowerCase().includes(query)) { match = true; break; }
            }
        }

        // Check commit subjects from search data
        if (!match && searchData.subjects) {
            for (var i = 0; i < searchData.subjects.length; i++) {
                if (searchData.subjects[i].toLowerCase().includes(query)) { match = true; break; }
            }
        }

        // Check code content in the diff lines
        if (!match) {
            var lines = section.querySelectorAll('.line-content');
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].textContent.toLowerCase().includes(query)) {
                    match = true;
                    break;
                }
            }
        }

        if (match) {
            matchedFiles.push(fileName);
            section.classList.remove('hidden-by-search');
        } else {
            section.classList.add('hidden-by-search');
        }
    });

    countEl.textContent = matchedFiles.length + ' file' + (matchedFiles.length !== 1 ? 's' : '') + ' match';
}

function clearGlobalSearch() {
    document.getElementById('global-search').value = '';
    document.getElementById('search-count').textContent = '';
    document.querySelectorAll('.file-section').forEach(function(section) {
        section.classList.remove('hidden-by-search');
    });
}

// Filter Chips
var activeExtFilters = [];
var activeTypeFilters = [];

function applyFilters() {
    var hasExtFilter = activeExtFilters.length > 0;
    var hasTypeFilter = activeTypeFilters.length > 0;

    if (!hasExtFilter && !hasTypeFilter) {
        document.querySelectorAll('.file-section').forEach(function(s) { s.classList.remove('hidden-by-filter'); });
        document.getElementById('active-filters').textContent = '';
        return;
    }

    var visibleCount = 0;
    document.querySelectorAll('.file-section').forEach(function(section) {
        var fileName = section.dataset.file || '';
        var statusIcon = section.querySelector('.file-status-icon');
        var hide = false;

        if (hasExtFilter) {
            var ext = '';
            var dotIdx = fileName.lastIndexOf('.');
            if (dotIdx >= 0) ext = fileName.substring(dotIdx).toLowerCase();
            if (activeExtFilters.indexOf(ext) === -1) hide = true;
        }

        if (!hide && hasTypeFilter) {
            var status = 'modified';
            if (statusIcon) {
                if (statusIcon.classList.contains('file-status-added')) status = 'added';
                else if (statusIcon.classList.contains('file-status-deleted')) status = 'deleted';
                else if (statusIcon.classList.contains('file-status-renamed')) status = 'renamed';
            }
            if (activeTypeFilters.indexOf(status) === -1) hide = true;
        }

        if (hide) {
            section.classList.add('hidden-by-filter');
        } else {
            section.classList.remove('hidden-by-filter');
            visibleCount++;
        }
    });

    var label = '';
    if (hasTypeFilter) label += activeTypeFilters.join(', ');
    if (hasExtFilter) label += (label ? ' | ' : '') + activeExtFilters.join(', ');
    document.getElementById('active-filters').textContent = label ? 'Filtered: ' + label : '';
}

function toggleFilterExt(ext) {
    var btn = document.querySelector('.filter-ext[data-ext="' + ext + '"]');
    var idx = activeExtFilters.indexOf(ext);
    if (idx >= 0) {
        activeExtFilters.splice(idx, 1);
        btn.classList.remove('active');
    } else {
        activeExtFilters.push(ext);
        btn.classList.add('active');
    }
    applyFilters();
}

function toggleFilterType(type) {
    var btn = document.querySelector('.filter-type[data-type="' + type + '"]');
    var idx = activeTypeFilters.indexOf(type);
    if (idx >= 0) {
        activeTypeFilters.splice(idx, 1);
        btn.classList.remove('active');
    } else {
        activeTypeFilters.push(type);
        btn.classList.add('active');
    }
    applyFilters();
}

function clearFilters() {
    activeExtFilters = [];
    activeTypeFilters = [];
    document.querySelectorAll('.filter-chip').forEach(function(btn) { btn.classList.remove('active'); });
    document.querySelectorAll('.file-section').forEach(function(s) { s.classList.remove('hidden-by-filter'); });
    document.getElementById('active-filters').textContent = '';
}

// Keyboard Navigation
document.addEventListener('keydown', function(e) {
    // Allow typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
        if (e.key === 'Escape') {
            e.target.blur();
            document.getElementById('search-bar').classList.add('hidden');
            e.preventDefault();
        }
        return;
    }
    switch (e.key) {
        case 'j': case 'J': scrollToNextFile(1); e.preventDefault(); break;
        case 'k': case 'K': scrollToNextFile(-1); e.preventDefault(); break;
        case 'f': case 'F': focusSearch(); e.preventDefault(); break;
        case '/': focusSearch(); e.preventDefault(); break;
        case 'd': case 'D': toggleTheme(); e.preventDefault(); break;
        case 'u': case 'U': switchView('unified'); e.preventDefault(); break;
        case 's': case 'S': switchView('sidebyside'); e.preventDefault(); break;
        case 'i': case 'I': switchView('inline'); e.preventDefault(); break;
        case 'Escape':
            if (!document.getElementById('commit-drawer').classList.contains('hidden')) {
                closeDrawer();
            } else if (!document.getElementById('search-bar').classList.contains('hidden')) {
                document.getElementById('search-bar').classList.add('hidden');
                clearGlobalSearch();
            } else {
                document.getElementById('stats-panel').classList.add('hidden');
            }
            e.preventDefault();
            break;
    }
});

// J/K Scroll to next/previous file
function scrollToNextFile(direction) {
    var sections = document.querySelectorAll('.file-section:not(.hidden-by-search):not(.hidden-by-filter)');
    if (sections.length === 0) return;
    var container = document.getElementById('diff-content');
    var scrollTop = container.scrollTop;
    var containerHeight = container.clientHeight;
    var viewCenter = scrollTop + containerHeight / 2;

    var bestIdx = -1;
    if (direction > 0) {
        // Find the first section whose top is below the view center
        var minTop = Infinity;
        for (var i = 0; i < sections.length; i++) {
            var top = sections[i].offsetTop;
            if (top > viewCenter + 10 && top < minTop) {
                minTop = top;
                bestIdx = i;
            }
        }
        if (bestIdx === -1) bestIdx = 0; // wrap to first
    } else {
        // Find the last section whose top is above the view center
        var maxTop = -Infinity;
        for (var i = 0; i < sections.length; i++) {
            var top = sections[i].offsetTop;
            if (top < viewCenter - 10 && top > maxTop) {
                maxTop = top;
                bestIdx = i;
            }
        }
        if (bestIdx === -1) bestIdx = sections.length - 1; // wrap to last
    }

    if (bestIdx >= 0) {
        sections[bestIdx].scrollIntoView({ behavior: 'smooth', block: 'start' });
        scrollToFile(sections[bestIdx].id);
    }
}

// File Filtering
function filterFiles() {
    var query = document.getElementById('file-search').value.toLowerCase();
    document.querySelectorAll('.sidebar-file').forEach(function(el) {
        var name = el.querySelector('.sidebar-file-name').textContent.toLowerCase();
        el.style.display = name.includes(query) ? '' : 'none';
    });
}

// Sidebar file click tracking for active state
document.querySelectorAll('.sidebar-file').forEach(function(el) {
    el.addEventListener('click', function() {
        document.querySelectorAll('.sidebar-file').forEach(function(f) {
            f.classList.remove('active');
        });
        el.classList.add('active');
    });
});
"""
