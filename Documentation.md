# DiffStory Documentation

> **Transform Git diffs into rich, interactive, self-contained HTML reports.**

DiffStory turns any `git diff` into a beautiful, portable HTML report that answers not just *what* changed, but *who* changed it, *when*, and *why* — all offline, in a single file you can share, archive, or email.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [HTML Report Features](#html-report-features)
- [Configuration](#configuration)
- [Export Formats](#export-formats)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Design Philosophy](#design-philosophy)
- [Security & Privacy](#security--privacy)
- [Project Structure](#project-structure)
- [Development](#development)
- [Architecture](#architecture)
- [License](#license)

---

## Features

### Three Diff Views

| View | Description |
|---|---|
| **Unified** | Classic git-style diff with line numbers and syntax highlighting |
| **Side-by-Side** | Original (left) and modified (right) columns, visually aligned |
| **Inline Edit** | Word-level diff — shows exact token changes inline, with green additions and red strikethrough removals. No more mental diffing. |

Switch between views instantly with the toolbar or keyboard shortcuts — no regeneration needed.

### Blame & Provenance

Every changed line carries its history. **Hover** any line to see a tooltip with:

- Author name
- Commit hash (short)
- Commit subject
- Date and relative time (e.g. "2h ago")
- Click hint for more details

**Click** any changed line to open the **commit drawer** — a side panel with full metadata:

- Full commit hash
- Commit subject and body
- Author name, email, and date
- Committer name, email, and date
- Parent commits
- Files changed, insertions, and deletions

### Search & Filtering

- **Global search** — find files by name, author, commit subject, or code content with live results. Press `F` or `/` to focus the search bar.
- **Filter chips** — narrow the view by file extension (`.py`, `.js`, `.html`, etc.) or change type (added, deleted, modified, renamed).
- **File sidebar** — searchable file list with add/delete indicators and collapse/expand.

### Statistics Dashboard

A floating panel (accessible via toolbar button) showing:

- Files changed, additions, deletions
- Added / deleted / modified / renamed file counts
- Author count and commit count (from blame data)
- Contributor breakdown with commit counts
- Top 10 most-changed files

### Keyboard Navigation

| Key | Action |
|---|---|
| `J` / `K` | Next / previous file |
| `F` or `/` | Focus global search |
| `U` / `S` / `I` | Unified / Side-by-side / Inline view |
| `D` | Toggle light/dark theme |
| `Esc` | Close drawer → close search → close stats |

### Deep Linking

Link directly to specific files and lines with stable, shareable anchors:

- `#file-0` — scrolls to the first file
- `#L-0-42` — scrolls to line 42 in the first file

These anchors are stable across regenerations and can be shared or bookmarked.

### Binary File Support

Binary files are detected and displayed with meaningful placeholders:

- **Image files** (`.png`, `.jpg`, `.gif`, `.svg`, etc.) — show a preview icon with filename
- **Other binaries** — show a file icon with metadata
- Prevents crashes and keeps the report clean

### Themes

- **Light** and **Dark** themes — toggle instantly with the toolbar button or `D` key
- Persists across sessions via `localStorage`

### Config File

Set defaults via `~/.diffstory.toml` or `.diffstory.toml` in your project root for:

- `verbose` mode
- `debug` output
- Additional configuration options

### Export Formats

Export structured data alongside the HTML report:

- **JSON** — full diff data with file metadata, hunks, and lines
- **Markdown** — readable diff summary with file status and hunk details
- **CSV** — per-file stats (file, status, additions, deletions)

---

## Advanced Features

### 1. Output Directory (`--output-dir`)

Generate all report files into a specific directory. When combined with `-o`, uses the output name as the stem.

```bash
diffstory --output-dir reviews/
# Generates:
#   reviews/
#   ├── diffstory-report.html
#   ├── diffstory-report.json
#   ├── diffstory-report.md
#   └── diffstory-report.csv

diffstory --output-dir reviews/ -o sprint-17
# Generates:
#   reviews/
#   ├── sprint-17.html
#   ├── sprint-17.json
#   ├── sprint-17.md
#   └── sprint-17.csv
```

### 2. Hotspot Detection 🔥

Shows files that have been historically unstable (modified most frequently in the last 500 commits).

```bash
diffstory --staged
# In the report: Hotspots section
# authentication.py     47 modifications
# payment.py            39 modifications
# invoice.py            32 modifications
```

Computed via `git log --name-only` over the last 500 commits. Helps reviewers identify files that change every week.

### 3. Risk Analysis ⚠

Heuristic risk scoring based on:
- Files touched
- Total LOC changed
- Core module edits (payment, billing, auth, security)
- Migration file modifications
- Hotspot file modifications

Displays a color-coded banner: **Low** 🟢, **Medium** 🟡, or **High** 🔴.

### 4. Ownership Analysis 👤

Using blame data, computes the top contributor per file as a percentage. Includes a suggested reviewer recommendation.

```
File Ownership

auth.py
Lakshay    92%  ████████████████

✓ Suggested reviewer: Lakshay Jindal
```

### 5. Change Timeline 📈

Mini bar chart showing commit distribution by day of week. Quickly identifies if work was rushed.

```
Mon ██
Tue ██████████
Wed ███
Thu ███████████████
Fri ██
```

### 6. Semantic Summaries 📝

Deterministic summary generated from filenames, commit messages, and hunk headers. No AI involved.

```
Summary
• Added authentication checks.
• Refactored invoice calculation.
• Removed deprecated endpoint.
```

### 7. Test Impact Detection 🧪

Maps changed files to their likely test files using path heuristics.

```
Testing Impact
Modified: src/auth/auth.py
Related tests:
  ▶ tests/test_auth.py
  ▶ tests/test_login.py
```

### 8. Dependency Diff 📦

Auto-detects changes to dependency manifests and shows added/updated/removed packages.

Supported files: `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, `pyproject.toml`, `Gemfile`, `Pipfile`, `composer.json`, `build.gradle`.

```
Dependencies Changed

requirements.txt:
  ↑ requests 2.31 → 2.33
  + flask 3.0
  − deprecated-package
```

### 9. TODO/FIXME Detection 📌

Scans added lines for annotations (TODO, FIXME, HACK, XXX, BUG, OPTIMIZE).

```
New TODOs & FIXMEs

TODO    Remove temporary workaround        auth.py
FIXME   Investigate race condition          payment.py
```

### 10. Folder Heatmap 📂

Bar chart showing change distribution across top-level directories.

```
Heatmap

backend/  ██████████████  12 files, +47/-23
frontend/ ██               3 files, +8/-4
docs/     █                 1 file, +2/-1
```

### 11. Complexity Delta 🔬

Tracks function-size changes in Python files using lightweight analysis of diff hunks.

```
Function Complexity

login()          7 → 14  (+7)
calculate_tax()  4 → 2   (-2)
```

### 12. Commit Evolution ⏳

When comparing commit ranges, scrub through commits with a slider to see how files evolved over time. "GitHub review meets replay."

```bash
diffstory HEAD~10 HEAD
```

### 13. Review Mode ✅

Per-file checkboxes with comments, persisted in `localStorage`. Resume reviews later.

```bash
diffstory --review
# In the report:
# ☐ auth.py reviewed
# ☐ invoice.py reviewed
# ☐ tests reviewed
```

### 14. CI Badge Mode 🏷

Print a one-line summary suitable for CI pipelines:

```bash
diffstory HEAD~1 HEAD --summary-only
# Files Changed: 14 | LOC: +233/-98 | Risk: Medium | Hotspots: 3
```

---

## Installation

### From PyPI (recommended)

```bash
pip install diffstory
```

**Requires:** Python 3.10+ and Git.

### From source

```bash
git clone https://github.com/lakshayjindal/diffstory.git
cd diffstory
pip install -e .
```

### Verify installation

```bash
diffstory --version
```

---

## Usage

### Working tree diff

Show changes in the working tree (unstaged changes):

```bash
diffstory
```

Equivalent to `git diff`.

### Staged changes

Show changes that are staged for commit:

```bash
diffstory --staged
```

Equivalent to `git diff --cached`.

### Commit comparison

Compare two commits:

```bash
diffstory HEAD~3 HEAD
```

### Branch comparison

Compare two branches:

```bash
diffstory main feature-branch
```

### Path restriction

Restrict the diff to a specific directory or path:

```bash
diffstory HEAD~3 HEAD src/
```

### Custom output file

```bash
diffstory -o my-review.html
```

Default output path: `diffstory-report.html`. When inside a git repo, the report is saved to a `stories/` directory outside the repo to prevent git from tracking it.

### Generate from a diff file

Generate a report from an existing patch/diff file without needing a git repository:

```bash
diffstory --diff /path/to/patch.diff
```

### Multiple export formats

Generate HTML, JSON, Markdown, and CSV exports simultaneously:

```bash
diffstory --staged --json --md --csv -o release-v2.0
```

This creates `release-v2.0.html`, `release-v2.0.json`, `release-v2.0.md`, and `release-v2.0.csv`.

### Suppress browser auto-open

Prevent the report from automatically opening in the browser:

```bash
diffstory --staged --no-open
```

### Verbose and debug modes

```bash
diffstory --staged --verbose
diffstory --staged --debug
```

Verbose shows git commands and timing. Debug implies verbose and also shows stack traces on errors.

### Show version

```bash
diffstory --version
```

---

## HTML Report Features

Once generated, the HTML report is a fully self-contained single file with:

- **All CSS inlined** — no external stylesheets
- **All JavaScript inlined** — no external scripts
- **All data embedded** — blame info, commit metadata, and search index as JSON
- **Works offline** — in any modern browser
- **Zero external dependencies at runtime**

### Report layout

1. **Toolbar** — view switcher (Unified / Side-by-Side / Inline), search button, theme toggle, stats button, file sidebar toggle
2. **Search bar** — hidden by default, activated via toolbar button or keyboard shortcut
3. **Filter bar** — filter chips for file extensions and change types
4. **File sidebar** — searchable, scrollable list of all changed files
5. **Diff content** — file sections with collapsible headers, hunk headers, and syntax-highlighted diff lines

### Blame tooltips

Hover over any changed line (addition, deletion, or context) to see:

- **Author** — the person who last modified that line
- **Commit** — shortened commit hash
- **Subject** — the commit message title
- **Date** — formatted date and relative time

### Commit drawer

Click any changed line to open a side panel with full commit details:

- Full commit hash (clickable, copyable)
- Commit subject and full body message
- Author name, email, and date
- Committer name, email, and date
- Parent commit hashes
- Files changed, insertions, deletions stats

Close the drawer by clicking the overlay, the close button, or pressing `Esc`.

---

## Configuration

DiffStory supports a TOML-based configuration file. The tool looks for `.diffstory.toml` in the current project directory first, then falls back to `~/.diffstory.toml` in your home directory.

### Example config

```toml
[cli]
verbose = true
debug = false
```

### Supported settings

| Setting | Type | Default | Description |
|---|---|---|---|
| `cli.verbose` | boolean | `false` | Show git commands and timing information |
| `cli.debug` | boolean | `false` | Show detailed debug output including stack traces |

CLI flags override config file settings. For example, `--debug` on the command line will enable debug mode even if the config has `debug = false`.

---

## Export Formats

### JSON

Exports the full diff data as structured JSON:

```json
[
  {
    "old_path": "src/foo.py",
    "new_path": "src/foo.py",
    "status": "modified",
    "hunks": [
      {
        "old_start": 1,
        "old_count": 5,
        "new_start": 1,
        "new_count": 7,
        "lines": [
          {"type": "context", "content": "def foo():", "old_lineno": 1, "new_lineno": 1},
          {"type": "addition", "content": "    return bar()", "old_lineno": null, "new_lineno": 2}
        ]
      }
    ]
  }
]
```

### Markdown

Exports a readable diff summary with file status, hunk headers, and line content:

```markdown
# DiffStory Report

## ~ `src/foo.py`
- **Status:** modified
- **Additions:** 3
- **Deletions:** 1
```

### CSV

Exports per-file statistics:

```csv
file,status,additions,deletions
src/foo.py,modified,3,1
src/bar.py,added,10,0
```

---

## Keyboard Shortcuts

| Key | Context | Action |
|---|---|---|
| `J` | Any (not input) | Scroll to next file |
| `K` | Any (not input) | Scroll to previous file |
| `F` or `/` | Any (not input) | Focus the global search bar |
| `D` | Any (not input) | Toggle light/dark theme |
| `U` | Any (not input) | Switch to Unified view |
| `S` | Any (not input) | Switch to Side-by-Side view |
| `I` | Any (not input) | Switch to Inline Edit view |
| `Esc` | Any | Close drawer → close search → close stats panel (in that order) |

---

## Design Philosophy

DiffStory was built to answer five questions about every changed line:

> **What changed? Who changed it? When? Why? How did it evolve?**

Traditional tools answer only the first question (`git diff` shows *what* changed). DiffStory consolidates `git diff`, `git blame`, `git log`, and GitHub-style review UX into a single, portable artifact — no server, no accounts, no data leaving your machine.

### Key principles

| Principle | Implementation |
|---|---|
| **Portability** | Single HTML file with everything inline |
| **Offline-first** | No network requests, no external dependencies |
| **Privacy** | No telemetry, no analytics, no accounts |
| **Completeness** | Every line answers the five questions above |
| **Performance** | Efficient rendering, lazy data loading |
| **Simplicity** | Vanilla JavaScript, no build process, no frameworks |

---

## Security & Privacy

- **Never uploads code** or transmits data
- **No telemetry**, no analytics, no accounts
- **No external API calls** by default
- **Never modifies your repository**
- Reports are safe for **air-gapped environments**, client deliverables, and compliance audits
- All processing happens locally via native `git` subprocess calls — no dependency on GitPython or any third-party service

---

## Project Structure

```
diffstory/
├── pyproject.toml                  # Build config, dependencies, CLI entry point
├── Documentation.md                # This file
├── README.md                       # Quick-start overview
├── requirements.md                 # Full product requirements & spec
├── deploy.sh                       # Build & publish script
├── .github/workflows/publish.yml   # CI/CD for PyPI publishing
├── src/diffstory/
│   ├── __init__.py                 # Package version
│   ├── __main__.py                 # python -m diffstory support
│   ├── cli.py                      # CLI argument parsing & orchestration
│   ├── git_utils.py                # Git subprocess wrappers (diff, blame, log)
│   ├── diff_parser.py              # Unified diff parser → structured data
│   ├── syntax.py                   # Pygments syntax highlighting
│   ├── html_generator.py           # Self-contained HTML report generation
│   └── loader.py                   # Animated CLI spinner
└── tests/
    └── __init__.py                 # Test suite (placeholder)
```

### Module responsibilities

| Module | Role |
|---|---|
| `cli.py` | Parses CLI arguments, loads config, orchestrates diff fetching, blame collection, report generation, and exports |
| `git_utils.py` | Wraps `git diff`, `git blame --line-porcelain`, `git log`, `git show` via subprocess. Detects repo root and caches it. |
| `diff_parser.py` | Parses unified diff output into structured `DiffFile`, `Hunk`, `DiffLine` objects. Computes word-level diffs for inline edit mode. |
| `syntax.py` | Uses Pygments for offline syntax highlighting with automatic language detection. Provides both light and dark theme CSS scoped by `data-theme`. |
| `html_generator.py` | Generates the self-contained HTML report with all CSS/JS/data inlined. Collects blame data, computes stats, builds search index. |
| `loader.py` | Animated CLI spinner with step tracking and elapsed time display. |

---

## Development

### Setup

```bash
# Clone the repository
git clone https://github.com/lakshayjindal/diffstory.git
cd diffstory

# Install in editable mode
pip install -e .
```

### Quick test

```bash
cd /tmp && mkdir test-diffstory && cd test-diffstory
git init && echo "hello" > test.py && git add -A && git commit -m "init"
echo "world" >> test.py
diffstory --staged
```

### Build the package

```bash
python -m build
```

### Deploy

```bash
./deploy.sh           # patch version bump
./deploy.sh minor     # minor version bump
./deploy.sh major     # major version bump
```

The deploy script:
1. Bumps the version in `pyproject.toml` and `src/diffstory/__init__.py`
2. Builds the package with `python -m build`
3. Uploads to PyPI with `twine upload`
4. Commits and tags the release in git

---

## Architecture

### Data flow

```
Git repository
      │
      ▼
  git diff (via subprocess) ───► Raw diff text
      │
      ▼
  diff_parser.py ───────────────► Structured DiffFile objects
      │
      ├──► git_utils.py ──────► Blame data (per-line provenance)
      │                             │
      │                             ▼
      │                        Commit metadata (author, date, stats)
      │
      ├──► syntax.py ──────────► Pygments highlighting
      │
      ▼
  html_generator.py ───────────► Self-contained HTML report
      │
      ├──► JSON / Markdown / CSV exports (optional)
      │
      ▼
  Browser or file share
```

### Key design decisions

| Decision | Rationale |
|---|---|
| **Subprocess-based git** | Zero dependency on GitPython; closer parity with actual git behavior; lower maintenance burden |
| **Vanilla JavaScript** | No build process, no framework dependencies, smaller report size |
| **Single-file HTML** | Portable, can be emailed, archived, or attached to PRs |
| **All data embedded as JSON** | Fast JavaScript access without additional network requests |
| **Server-rendered diffs** | Faster initial paint; all three views rendered at generation time |
| **Pygments for highlighting** | Mature, offline-capable, supports 100+ languages |

---

## License

MIT
