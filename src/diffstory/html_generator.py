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
from diffstory.generators import _get_css, _get_javascript

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
    review_mode: bool = False,
    hotspots: Optional[list] = None,
    timeline: Optional[dict] = None,
    folder_stats: Optional[dict] = None,
    dependency_diffs: Optional[list] = None,
    todos: Optional[list] = None,
    test_impact: Optional[list] = None,
    complexity_delta: Optional[list] = None,
    semantic_summaries: Optional[list] = None,
    evolution_commits: Optional[list] = None,
    evolution_files: Optional[dict] = None,
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

    # Build analytics HTML sections
    hotspots_html = _build_hotspots_html(hotspots)
    risk_html = _build_risk_analysis_html(files, hotspots, stats)
    ownership_html = _build_ownership_html(blame_data_dict["line_blame"], files)
    timeline_html = _build_timeline_html(timeline)
    summaries_html = _build_summaries_html(semantic_summaries)
    deps_html = _build_dependency_html(dependency_diffs)
    todos_html = _build_todos_html(todos)
    test_impact_html = _build_test_impact_html(test_impact)
    heatmap_html = _build_heatmap_html(folder_stats)
    complexity_html = _build_complexity_html(complexity_delta)
    evolution_html = _build_evolution_html(evolution_commits, evolution_files)
    review_mode_js = "true" if review_mode else "false"

    # Build review checkboxes for file headers
    review_checkboxes_html = ""
    if review_mode:
        for i, file in enumerate(files):
            review_checkboxes_html += (
                '<div class="review-checkbox" id="review-checkbox-' + str(i) + '">'
                '<input type="checkbox" id="review-chk-' + str(i) + '" onclick="toggleReviewFile(' + str(i) + ')">'
                '<label for="review-chk-' + str(i) + '">Reviewed</label>'
                '</div>\n'
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
        hotspots_html=hotspots_html,
        risk_html=risk_html,
        ownership_html=ownership_html,
        timeline_html=timeline_html,
        summaries_html=summaries_html,
        deps_html=deps_html,
        todos_html=todos_html,
        test_impact_html=test_impact_html,
        heatmap_html=heatmap_html,
        complexity_html=complexity_html,
        evolution_html=evolution_html,
        review_checkboxes_html=review_checkboxes_html,
        review_mode=review_mode,
    )

    output = Path(output_path)
    output.write_text(html, encoding="utf-8")
    return str(output.resolve())


# ---------------------------------------------------------------------------
# Analytics section builders
# ---------------------------------------------------------------------------

def _build_hotspots_html(hotspots: Optional[list]) -> str:
    if not hotspots:
        return ""
    items = ""
    for h in hotspots[:10]:
        bar_width = max(2, int(h["modifications"] / max(1, hotspots[0]["modifications"]) * 100))
        items += (
            '<div class="hotspot-item">'
            '<span class="hotspot-file">' + escape(h["file"]) + '</span>'
            '<span class="hotspot-count">' + str(h["modifications"]) + ' mods</span>'
            '<div class="hotspot-bar-bg"><div class="hotspot-bar" style="width:' + str(bar_width) + '%"></div></div>'
            '</div>'
        )
    return (
        '<div class="analytics-section" id="hotspots-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128293;</span>'
        '<span class="analytics-title">Hotspots</span>'
        '<span class="analytics-subtitle">Files modified most frequently in recent history</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_risk_analysis_html(files: list, hotspots: Optional[list], stats: dict) -> str:
    file_count = len(files)
    additions = stats.get("additions", 0)
    deletions = stats.get("deletions", 0)
    total_loc = additions + deletions

    # Heuristics
    risk_factors = []
    risk_score = 0

    if file_count > 15:
        risk_factors.append(f"{file_count} files touched")
        risk_score += 2
    elif file_count > 8:
        risk_factors.append(f"{file_count} files touched")
        risk_score += 1

    if total_loc > 1000:
        risk_factors.append(f"{total_loc} LOC changed")
        risk_score += 2
    elif total_loc > 300:
        risk_factors.append(f"{total_loc} LOC changed")
        risk_score += 1

    # Check for migration files, core modules
    core_modules = ["payment", "billing", "auth", "security", "core", "db", "database"]
    for f in files:
        path_lower = f.display_path.lower()
        if any(m in path_lower for m in core_modules):
            if "migration" in path_lower or "migrate" in path_lower:
                risk_factors.append("Migrations affected")
                risk_score += 2
                break
        if any(m in path_lower for m in core_modules[:4]):
            risk_factors.append(f"Core module edited: {f.display_path}")
            risk_score += 1

    if hotspots:
        hotspot_files = {h["file"] for h in hotspots[:5]}
        for f in files:
            if f.display_path in hotspot_files:
                risk_factors.append(f"Hotspot file modified: {f.display_path}")
                risk_score += 1
                break

    if risk_score == 0:
        risk_factors.append("Low-risk change")

    risk_level = "low"
    risk_label = "Low"
    if risk_score >= 5:
        risk_level = "high"
        risk_label = "⚠ High"
    elif risk_score >= 3:
        risk_level = "medium"
        risk_label = "◆ Medium"

    factors_html = "".join(
        '<div class="risk-factor">&#8226; ' + escape(f) + '</div>'
        for f in risk_factors
    )

    return (
        '<div class="analytics-section risk-banner risk-' + risk_level + '" id="risk-section">'
        '<div class="risk-header">'
        '<span class="risk-label">' + risk_label + ' Risk Changes</span>'
        '</div>'
        '<div class="risk-factors">' + factors_html + '</div>'
        '</div>'
    )


def _build_ownership_html(blame_data: dict, files: list) -> str:
    if not blame_data or not files:
        return ""

    # Compute ownership per file
    file_ownership: dict[str, dict] = {}
    file_line_counts: dict[str, int] = {}

    for key, entry in blame_data.items():
        file_idx = key.split(":")[0]
        try:
            fi = int(file_idx)
            if fi < len(files):
                filepath = files[fi].display_path
            else:
                continue
        except (ValueError, IndexError):
            continue

        if filepath not in file_ownership:
            file_ownership[filepath] = {}
            file_line_counts[filepath] = 0

        author = entry.get("author", "Unknown")
        file_ownership[filepath][author] = file_ownership[filepath].get(author, 0) + 1
        file_line_counts[filepath] += 1

    items = ""
    for filepath in sorted(file_ownership.keys())[:10]:
        authors = file_ownership[filepath]
        total = file_line_counts[filepath]
        if total == 0:
            continue
        sorted_authors = sorted(authors.items(), key=lambda x: -x[1])
        top_author = sorted_authors[0][0]
        top_pct = int(sorted_authors[0][1] / total * 100)

        # Reviewer recommendation
        reviewer = f"Suggested reviewer: {top_author}"

        items += (
            '<div class="ownership-item">'
            '<div class="ownership-file">' + escape(filepath) + '</div>'
            '<div class="ownership-top">'
            '<span class="ownership-author">' + escape(top_author) + '</span>'
            '<span class="ownership-pct">' + str(top_pct) + '%</span>'
            '<div class="ownership-bar-bg"><div class="ownership-bar" style="width:' + str(top_pct) + '%"></div></div>'
            '</div>'
            '<div class="ownership-reviewer">&#10003; ' + escape(reviewer) + '</div>'
            '</div>'
        )

    if not items:
        return ""

    return (
        '<div class="analytics-section" id="ownership-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128100;</span>'
        '<span class="analytics-title">File Ownership</span>'
        '<span class="analytics-subtitle">Top contributor per file with reviewer suggestion</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_timeline_html(timeline: Optional[dict]) -> str:
    if not timeline or not timeline.get("counts"):
        return ""
    days = timeline["days"]
    counts = timeline["counts"]
    max_count = max(counts) if counts else 1

    bars = ""
    for i, day in enumerate(days):
        c = counts[i]
        bar_height = max(2, int(c / max_count * 100)) if max_count > 0 else 0
        bars += (
            '<div class="timeline-col">'
            '<div class="timeline-bar-container">'
            '<div class="timeline-bar" style="height:' + str(bar_height) + '%"></div>'
            '</div>'
            '<div class="timeline-label">' + day + '</div>'
            '<div class="timeline-count">' + str(c) + '</div>'
            '</div>'
        )

    return (
        '<div class="analytics-section" id="timeline-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128200;</span>'
        '<span class="analytics-title">Change Timeline</span>'
        '<span class="analytics-subtitle">Commits by day of week (recent ' + str(sum(counts)) + ' commits)</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">'
        '<div class="timeline-chart">' + bars + '</div>'
        '</div>'
        '</div>'
    )


def _build_summaries_html(summaries: Optional[list]) -> str:
    if not summaries:
        return ""
    items = "".join(
        '<div class="summary-item">&#8226; ' + escape(s) + '</div>'
        for s in summaries
    )
    return (
        '<div class="analytics-section" id="summaries-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128196;</span>'
        '<span class="analytics-title">Summary</span>'
        '<span class="analytics-subtitle">What changed in this diff</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_dependency_html(deps: Optional[list]) -> str:
    if not deps:
        return ""
    items = ""
    for dep in deps:
        items += '<div class="dep-file"><span class="dep-filename">' + escape(dep["file"]) + '</span>'
        if dep.get("updated"):
            for u in dep["updated"]:
                items += '<div class="dep-item dep-updated">&#8593; ' + escape(u["name"]) + ' ' + escape(u["from"]) + ' &#8594; ' + escape(u["to"]) + '</div>'
        if dep.get("added"):
            for a in dep["added"]:
                items += '<div class="dep-item dep-added">&#43; ' + escape(a) + '</div>'
        if dep.get("removed"):
            for r in dep["removed"]:
                items += '<div class="dep-item dep-removed">&#8722; ' + escape(r) + '</div>'
        items += '</div>'

    return (
        '<div class="analytics-section" id="deps-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128230;</span>'
        '<span class="analytics-title">Dependencies Changed</span>'
        '<span class="analytics-subtitle">Added, updated, or removed packages</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_todos_html(todos: Optional[list]) -> str:
    if not todos:
        return ""
    items = ""
    for t in todos:
        tag_class = "todo-tag-" + t["tag"].lower()
        items += (
            '<div class="todo-item">'
            '<span class="todo-tag ' + tag_class + '">' + t["tag"] + '</span>'
            '<span class="todo-text">' + escape(t["text"]) + '</span>'
            '<span class="todo-file">' + escape(t["file"]) + '</span>'
            '</div>'
        )
    return (
        '<div class="analytics-section" id="todos-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128221;</span>'
        '<span class="analytics-title">New TODOs &amp; FIXMEs</span>'
        '<span class="analytics-subtitle">Annotations added in this diff</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_test_impact_html(test_impact: Optional[list]) -> str:
    if not test_impact:
        return ""
    items = ""
    for ti in test_impact[:10]:
        tests_html = "".join(
            '<div class="test-file">&#9654; ' + escape(t) + '</div>'
            for t in ti["tests"][:5]
        )
        items += (
            '<div class="test-impact-item">'
            '<div class="test-source">Modified: ' + escape(ti["source"]) + '</div>'
            '<div class="test-related">Related tests:</div>'
            + tests_html +
            '</div>'
        )
    return (
        '<div class="analytics-section" id="test-impact-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128220;</span>'
        '<span class="analytics-title">Testing Impact</span>'
        '<span class="analytics-subtitle">Related tests to run</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_heatmap_html(folder_stats: Optional[dict]) -> str:
    if not folder_stats:
        return ""
    max_changes = max(fs["changes"] for fs in folder_stats.values()) if folder_stats else 1

    items = ""
    for folder in sorted(folder_stats.keys()):
        fs = folder_stats[folder]
        bar_width = max(2, int(fs["changes"] / max_changes * 100))
        items += (
            '<div class="heatmap-item">'
            '<span class="heatmap-folder">' + escape(folder) + '</span>'
            '<div class="heatmap-bar-bg"><div class="heatmap-bar" style="width:' + str(bar_width) + '%"></div></div>'
            '<span class="heatmap-count">' + str(fs["changes"]) + ' files, +' + str(fs["additions"]) + '/-' + str(fs["deletions"]) + '</span>'
            '</div>'
        )

    return (
        '<div class="analytics-section" id="heatmap-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128202;</span>'
        '<span class="analytics-title">Folder Heatmap</span>'
        '<span class="analytics-subtitle">Change distribution across directories</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_complexity_html(complexity_delta: Optional[list]) -> str:
    if not complexity_delta:
        return ""
    items = ""
    for cd in complexity_delta[:10]:
        items += '<div class="complexity-file">' + escape(cd["file"]) + '</div>'
        for fn in cd["functions"][:5]:
            delta = fn["new_lines"] - fn["old_lines"]
            delta_str = ("+" if delta >= 0 else "") + str(delta)
            delta_class = "complexity-delta-up" if delta > 0 else ("complexity-delta-down" if delta < 0 else "")
            items += (
                '<div class="complexity-func">'
                '<span class="complexity-name">' + escape(fn["name"]) + '()</span>'
                '<span class="complexity-lines">' + str(fn["old_lines"]) + ' &#8594; ' + str(fn["new_lines"]) + '</span>'
                '<span class="complexity-delta ' + delta_class + '">(' + delta_str + ')</span>'
                '</div>'
            )

    return (
        '<div class="analytics-section" id="complexity-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128300;</span>'
        '<span class="analytics-title">Complexity Delta</span>'
        '<span class="analytics-subtitle">Function size changes in Python files</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">' + items + '</div>'
        '</div>'
    )


def _build_evolution_html(evolution_commits: Optional[list], evolution_files: Optional[dict]) -> str:
    if not evolution_commits or not evolution_files:
        return ""

    # Build commit list for the slider
    commits_json_str = json.dumps([{
        "hash": c["hash"][:8],
        "subject": c.get("subject", ""),
        "author": c.get("author", ""),
    } for c in evolution_commits])

    # Build evolution content for each file
    file_evo_html = ""
    for filepath, evo in evolution_files.items():
        # Store content snippets in data attributes
        file_evo_html += (
            '<div class="evolution-file" data-file="' + escape(filepath) + '">'
            '<div class="evolution-file-header">' + escape(filepath) + '</div>'
            '<pre class="evolution-content" id="evo-content-' + escape(filepath.replace("/", "-")) + '">'
            + (escape(evo[0]["content"][:500]) if evo else "No content") +
            '</pre>'
            '</div>'
        )

    return (
        '<div class="analytics-section" id="evolution-section">'
        '<div class="analytics-header" onclick="toggleAnalytics(this)">'
        '<span class="analytics-icon">&#128257;</span>'
        '<span class="analytics-title">Commit Evolution</span>'
        '<span class="analytics-subtitle">Scrub through commits to see how files evolved</span>'
        '<span class="file-toggle">&#9660;</span>'
        '</div>'
        '<div class="analytics-body">'
        '<div class="evolution-slider-container">'
        '<input type="range" class="evolution-slider" id="evolution-slider" min="0" max="' + str(len(evolution_commits) - 1) + '" value="0" oninput="onEvolutionSlide(this.value)">'
        '<div class="evolution-labels" id="evolution-labels">'
        '<span>' + escape(evolution_commits[0]["subject"][:50]) + '</span>'
        '<span>' + escape(evolution_commits[-1]["subject"][:50]) + '</span>'
        '</div>'
        '<div class="evolution-commit-info" id="evolution-commit-info"></div>'
        '</div>'
        '<div id="evolution-files">' + file_evo_html + '</div>'
        '<div class="evolution-data" id="evolution-data" style="display:none">' + commits_json_str + '</div>'
        '</div>'
        '</div>'
    )


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
    hotspots_html: str = "",
    risk_html: str = "",
    ownership_html: str = "",
    timeline_html: str = "",
    summaries_html: str = "",
    deps_html: str = "",
    todos_html: str = "",
    test_impact_html: str = "",
    heatmap_html: str = "",
    complexity_html: str = "",
    evolution_html: str = "",
    review_checkboxes_html: str = "",
    review_mode: bool = False,
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
                + hotspots_html + '\n'        + risk_html + '\n'        + ownership_html + '\n'        + timeline_html + '\n'        + summaries_html + '\n'        + deps_html + '\n'        + todos_html + '\n'        + test_impact_html + '\n'        + heatmap_html + '\n'        + complexity_html + '\n'        + evolution_html + '\n'+ file_sections_html + '\n'
        '        </main>\n'
        '    </div>\n'
        '</div>\n'
        '<script>\n'
        + js + '\n'
        '</script>\n'
        '</body>\n'
        '</html>'
    )
