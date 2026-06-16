# Phase 2 Context — Blame Integration, Tooltips, Commit Metadata, Search, Filtering, Statistics

## What Phase 1 Delivered

| Requirement | Status |
|---|---|
| HTML generation | ✅ Self-contained single-file HTML |
| Unified view | ✅ Server-rendered |
| Side-by-side view | ✅ Server-rendered |
| Inline edit view | ✅ Word-level diffing via `difflib.SequenceMatcher` |
| Syntax highlighting | ✅ Pygments with light/dark theme scoping |
| CLI packaging | ✅ `diffstory` entry point, installed via `pip install -e .` |
| Export formats | ✅ HTML, JSON, Markdown, CSV |
| Offline reports | ✅ All CSS/JS inline, no external dependencies |

## Current Project Structure

```
/home/lakshayj/Documents/project/diff-to-html/
├── pyproject.toml              # Build config, entry point
├── README.md                   # Empty
├── PHASE2_CONTEXT.md           # This file
├── src/diffstory/
│   ├── __init__.py             # Version
│   ├── __main__.py             # python -m diffstory
│   ├── cli.py                  # Argparse CLI, export orchestration
│   ├── git_utils.py            # Subprocess wrappers for git commands
│   ├── diff_parser.py          # Unified diff → DiffFile/Hunk/DiffLine objects
│   ├── syntax.py               # Pygments-based syntax highlighting
│   └── html_generator.py       # Self-contained HTML report generation
└── tests/
    └── __init__.py             # Empty
```

## Phase 2 Requirements (from requirements.md)

1. **Blame Integration** — Each changed line should expose author, commit hash, commit title, date, relative age, email (optional), branch reference
2. **Tooltips** — Hover over a changed line reveals: Author, Commit Title, Commit Hash, Date, Relative Time, Email (configurable), Files Changed, Branch
3. **Commit Metadata** — Clicking a line opens a detailed side panel with: commit title, body, hash, author, committer, date, parents, files changed, insertions, deletions, patch summary
4. **Search** — Searchable by filename, author, commit message, commit hash, code content with instant filtering and highlight matches, keyboard shortcut support
5. **Filtering** — Filters by: authors, date range, extensions, change type, files. Combinable filters, persistent during navigation, clear-all functionality
6. **Statistics** — Already partially implemented (statistics dashboard in Phase 1). Expand with: authors, commits, contribution breakdown, change distribution

## Existing Code That Supports Phase 2

### `git_utils.py` — Already Has These Functions (unused)
- `get_blame(filepath)` — returns `list[dict]` with commit, author, author-mail, date, summary (parses `git blame --line-porcelain` output)
- `get_log_for_file(filepath)` — returns `list[dict]` with commit, author, email, date, summary
- `get_file_content(commit, filepath)` — returns file content at a specific commit

### `html_generator.py` — Data Model Supports Phase 2
- `DiffLine` objects have `old_lineno` and `new_lineno` — can be correlated with blame output
- `DiffFile` objects have `display_path` — can be used for file-level lookup
- The HTML already has `data-old` and `data-new` attributes on each diff line, which can be used for blame tooltip lookup
- JavaScript `switchView()`, `toggleTheme()`, `toggleStats()`, `toggleSidebar()` functions exist

## Implementation Strategy for Phase 2

### Approach A: Embed Blame Data in HTML (Recommended)
1. Run `git blame` for each changed file as part of report generation
2. Embed the blame data as a JSON object in the HTML (e.g., `<script id="blame-data" type="application/json">...</script>`)
3. JavaScript reads this data and shows tooltips on hover via `data-old`/`data-new` line number matching
4. Keep Phase 1 architecture: all data is in the single HTML file, works offline

### Approach B: Lazy Load on Report Open
1. The HTML report includes a mechanism to read blame data from a sidecar file or git
2. More complex, requires the report to know where the git repo is
3. Not recommended — violates "works offline" and "portable" requirements

## Key Implementation Details Needed

### Blame ↔ Line Correlation
- `git blame --line-porcelain` outputs one entry per line in the file
- Need to correlate blame entries with diff lines by line number
- For additions: use `new_lineno` to look up the blame for the current file version
- For deletions: use `old_lineno` to look up the blame for the previous file version (use `git blame <commit>~1 -- filepath`)

### Tooltip Implementation
- Use a single tooltip element that repositions on hover
- Show: Author · Commit hash (short) · Date · Title
- Position near the mouse cursor
- Debounce to avoid flicker

### Commit Drawer (Side Panel)
- Slide-in panel from the right side
- Contains full commit details: title, body, hash, author, date, files changed, stats
- Close with ESC or click outside

### Search Implementation
- Filter files by name (already have `filterFiles()`)
- Search across: filename, author name, commit message, code content
- Highlight matching text in the diff content
- Add a global search bar in the toolbar

## Open Questions for Phase 2

1. Should tooltip data be embedded as a JSON blob, or as HTML data attributes on each line?
2. Should the commit drawer load data from embedded JSON or make a separate request?
3. How to handle blame for deleted lines (need old file version)?
4. Should filtering be purely CSS-based (show/hide) or data-driven (re-render)?
5. Branch information requires `git branch --contains <commit>` — should this be run for each unique commit?

## Dependencies
- No new Python packages required beyond Pygments
- All frontend work is vanilla JavaScript (no framework)
- Phase 2 adds more data to the HTML, which may increase file size
- Consider lazy rendering for large blame datasets

## Testing Phase 2
- Test with repos that have 100+ files and many authors
- Test tooltip rendering with long commit messages and author names
- Verify blame accuracy for:
  - Lines that were moved
  - Files that were renamed
  - Binary files (no blame data)
  - New files (no previous blame)
