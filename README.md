# DiffStory

**Transform Git diffs into rich, interactive, self-contained HTML reports.**

DiffStory turns any `git diff` into a beautiful, portable HTML report that answers not just *what* changed, but *who* changed it, *when*, and *why* — all offline, in a single file you can share, archive, or email.

```bash
pip install diffstory
cd my-repo
diffstory --staged -o review.html
# Open review.html in any browser — zero setup required
```

---

## Features

### Three Diff Views

| View | Description |
|---|---|
| **Unified** | Classic git-style diff with line numbers and syntax highlighting |
| **Side-by-Side** | Original (left) and modified (right) columns, visually aligned |
| **Inline Edit** | Word-level diff — shows exact token changes inline, green additions and red strikethrough removals. No more mental diffing. |

Switch between views instantly with the toolbar or keyboard shortcuts — no regeneration needed.

### Blame & Provenance

Every changed line carries its history. **Hover** any line to see a tooltip with author name, commit hash, subject, date, and relative time (e.g. "2h ago"). **Click** any line to open the commit drawer — a side panel with full metadata: commit body, author, committer, parents, files changed, insertions, and deletions.

### Search & Filtering

- **Global search** — find files by name, author, commit subject, or code content with live results
- **Filter chips** — narrow the view by file extension (`.py`, `.js`, `.html`, etc.) or change type (added, deleted, modified, renamed)
- **File sidebar** — searchable file list with add/delete indicators and collapse/expand

### Statistics Dashboard

A floating panel showing:
- Files changed, additions, deletions
- Added / deleted / modified / renamed file counts
- Author count and commit count (from blame)
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

Link directly to specific files and lines: `#file-0` scrolls to the first file, `#L-0-42` scrolls to line 42 in the first file. Shareable, stable anchors.

### Binary File Support

Binary files are detected and displayed with meaningful placeholders — image files get a preview icon, other binaries show metadata — preventing crashes and keeping the report clean.

### Customization

- **Light/Dark themes** — toggle instantly, persists across sessions
- **Config file** — `~/.diffstory.toml` or `.diffstory.toml` in your project sets defaults for verbose mode, debug output, and more
- **`--verbose` / `--debug` flags** — see what's happening under the hood

### Export Formats

Alongside the HTML report, export structured data:

```bash
diffstory --staged --json --md --csv
```

### Analytics & Insights

Every report now includes rich analytics computed from git history:

- **🔥 Hotspots** — Files modified most frequently in recent history
- **⚠ Risk Analysis** — Heuristic risk scoring based on LOC, files touched, core modules, and hotspots
- **👤 Ownership Analysis** — Top contributor per file with suggested reviewer
- **📈 Change Timeline** — Commit distribution by day of week
- **📝 Semantic Summary** — Deterministic summary from filenames and commit messages
- **📦 Dependency Diff** — Auto-detects changes to `requirements.txt`, `package.json`, `Cargo.toml`, `go.mod`, etc.
- **📌 TODO/FIXME Detection** — Scans added lines for annotations
- **🧪 Test Impact** — Maps changed files to their likely test files
- **📂 Folder Heatmap** — Change distribution across directories
- **🔬 Complexity Delta** — Function-size changes in Python files
- **⏳ Commit Evolution** — Slider to scrub through commits in a range
- **✅ Review Mode** — Per-file checkboxes with localStorage persistence (`--review`)

### CI Badge Mode

```bash
diffstory HEAD~1 HEAD --summary-only
# Files Changed: 14 | LOC: +233/-98 | Risk: Medium | Hotspots: 3
```

### Output Directory

```bash
diffstory --output-dir reviews/
diffstory --output-dir reviews/ -o sprint-17
```

---

## Installation

```bash
pip install diffstory
```

**Requires:** Python 3.10+ and Git.

To install from source:

```bash
git clone https://github.com/lakshayjindal/diffstory.git
cd diffstory
pip install -e .
```

---

## Usage

```bash
# Working tree diff
diffstory

# Staged changes (what will be committed)
diffstory --staged

# Compare commits
diffstory HEAD~3 HEAD

# Compare branches
diffstory main feature-branch

# Compare revisions with path restriction
diffstory HEAD~3 HEAD src/

# Generate from a diff file directly (no git repo needed)
diffstory --diff /path/to/patch.diff

# Custom output file
diffstory -o my-review.html

# Multiple export formats at once
diffstory --staged --json --md --csv -o release-v2.0

# Verbose mode
diffstory --staged --verbose

# Show version
diffstory --version
```

### Config File Example

Create `~/.diffstory.toml` or `.diffstory.toml` in your project:

```toml
[cli]
verbose = true
debug = false
```

---

## HTML Report

Every generated HTML report is **fully self-contained**:

- All CSS inlined — no external stylesheets
- All JavaScript inlined — no external scripts
- All data (blame, commits, search index) embedded as JSON
- Works offline in any modern browser
- Safe to email, archive, or include in audit evidence
- Zero external dependencies at runtime

Open it, share it, attach it to a PR, or file it for compliance. It just works.

---

## Project Structure

```
diffstory/
├── pyproject.toml              # Build config & CLI entry point
├── README.md
├── requirements.md             # Full product requirements & spec
├── deploy.sh                   # Build & publish script
├── .github/workflows/publish.yml  # CI/CD for PyPI publishing
├── src/diffstory/
│   ├── __init__.py             # Package version
│   ├── __main__.py             # python -m diffstory support
│   ├── cli.py                  # CLI argument parsing & orchestration
│   ├── git_utils.py            # Git subprocess wrappers (diff, blame, log)
│   ├── diff_parser.py          # Unified diff parser → structured data
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

# Test with a quick repo
cd /tmp && mkdir test-diffstory && cd test-diffstory
git init && echo "hello" > test.py && git add -A && git commit -m "init"
echo "world" >> test.py
diffstory --staged

# Build the package
python -m build

# Deploy (version bump, build, publish)
./deploy.sh           # patch bump
./deploy.sh minor     # minor bump
```

---

## Design Philosophy

DiffStory was built to answer five questions about every changed line:

> **What changed? Who changed it? When? Why? How did it evolve?**

It consolidates `git diff`, `git blame`, `git log`, and GitHub-style review UX into a single, portable artifact — no server, no accounts, no data leaving your machine.

### Security

- Never uploads code or transmits data
- No telemetry, no analytics, no accounts
- No external API calls by default
- Never modifies your repository
- Generated reports are safe for air-gapped environments, client deliverables, and compliance audits

---

## License

MIT
