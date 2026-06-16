# DiffStory

**Transform Git diffs into rich, interactive, self-contained HTML reports.**

DiffStory turns any `git diff` into a beautiful, portable HTML report that answers not just *what* changed, but *who* changed it, *when*, and *why* — all offline, in a single file.

```bash
pip install diffstory
cd my-repo
diffstory --staged -o report.html
# Open report.html in any browser
```

---

## Features

### Phase 1 (MVP)
- **Unified View** — Classic git-style diff with syntax highlighting
- **Side-by-Side View** — Original and modified columns, synchronized
- **Inline Edit View** — Word-level diff showing exact token changes
- **Syntax Highlighting** — 30+ languages via Pygments, light + dark themes
- **Statistics Dashboard** — Files changed, +/-, authors breakdown
- **File Sidebar** — Navigate files with search, collapse/expand
- **Keyboard Shortcuts** — `U`/`S`/`I` to switch views, `D` for theme, `Esc` to close
- **Theme Toggle** — Light/dark with system preference detection and persistence
- **Export Formats** — HTML, JSON, Markdown, CSV

### Phase 2 (Blame Integration)
- **Blame Tooltips** — Hover any changed line to see author, commit, date, and message
- **Commit Drawer** — Click a line to open a detailed side panel with full commit metadata
- **Relative Time** — "2h ago", "3d ago" for at-a-glance recency

### Future Phases
- Search across filename, author, commit message, and code content
- Filtering by author, date range, file type, change type
- Commit evolution viewer and timeline
- Deep linking to specific lines and files

---

## Installation

### From PyPI (once published)
```bash
pip install diffstory
```

### From source
```bash
git clone https://github.com/user/diffstory.git
cd diffstory
pip install -e .
```

**Requirements:** Python 3.10+, Git

---

## Usage

### Basic Commands

```bash
# Working tree diff
diffstory

# Staged changes
diffstory --staged

# Compare commits
diffstory HEAD~3 HEAD

# Compare branches
diffstory main feature

# Custom output file
diffstory -o my-report.html

# Multiple export formats
diffstory --staged --json --md --csv -o report
```

### Keyboard Shortcuts (in the HTML report)

| Key | Action |
|---|---|
| `U` | Unified view |
| `S` | Side-by-side view |
| `I` | Inline edit view |
| `D` | Toggle theme |
| `Esc` | Close drawer / stats panel |
| `F` | Focus file search |

---

## Report Features

### Three View Modes

| Mode | Description |
|---|---|
| **Unified** | Classic git diff format with line numbers |
| **Side-by-Side** | Two-column layout — original on left, modified on right |
| **Inline Edit** | Word-level diff showing additions (green) and removals (red strikethrough) within the same line |

### Blame Tooltips (Phase 2)

Hover over any changed line to see:
- **Author** name
- **Commit hash** (short, 7 chars)
- **Commit subject**
- **Date** with relative time ("2h ago")

Click any line to open the **Commit Drawer** with full metadata: body, committer, parents, files changed, insertions/deletions.

### Statistics

The statistics panel shows:
- Files changed, additions, deletions
- Added / deleted / modified / renamed file counts
- Top 10 most-changed files with per-file breakdown

---

## Output

Reports are fully self-contained single HTML files:
- All CSS inlined
- All JavaScript inlined
- All data embedded as JSON
- No external dependencies
- Works offline in any modern browser
- Safe to email or archive

---

## Project Structure

```
diffstory/
├── pyproject.toml              # Build config & entry point
├── requirements.md             # Full product requirements
├── .gitignore
├── src/diffstory/
│   ├── __init__.py             # Package version
│   ├── __main__.py             # python -m diffstory
│   ├── cli.py                  # CLI argument parsing & orchestration
│   ├── git_utils.py            # Git subprocess wrappers
│   ├── diff_parser.py          # Unified diff → structured data
│   ├── syntax.py               # Pygments syntax highlighting
│   └── html_generator.py       # Self-contained HTML report generation
└── tests/
    └── __init__.py
```

---

## Development

```bash
# Install in editable mode
pip install -e .

# Run against a test repo
cd /tmp && mkdir test && cd test
git init
echo "hello" > test.py
git add -A && git commit -m "init"
echo "world" >> test.py
diffstory
```

---

## Security

DiffStory is designed for air-gapped, audit-safe use:
- Never uploads code
- Never transmits data
- No telemetry
- No accounts required
- No external API calls
- Never modifies your repository

---

## License

MIT
