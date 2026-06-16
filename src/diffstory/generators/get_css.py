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

/* Analytics Sections */
.analytics-section {
    margin-bottom: 16px;
    border: 1px solid var(--border);
    border-radius: 8px;
    overflow: hidden;
    background: var(--bg);
    box-shadow: var(--card-shadow);
}

.analytics-header {
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

.analytics-header:hover {
    background: var(--bg-tertiary);
}

.analytics-icon {
    font-size: 16px;
    width: 24px;
    text-align: center;
}

.analytics-title {
    font-size: 14px;
    font-weight: 600;
}

.analytics-subtitle {
    font-size: 11px;
    color: var(--text-secondary);
    flex: 1;
}

.analytics-body {
    padding: 12px 14px;
}

.analytics-section.collapsed .analytics-body {
    display: none;
}

/* Hotspots */
.hotspot-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 13px;
}

.hotspot-file {
    flex: 1;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 12px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.hotspot-count {
    font-size: 11px;
    color: var(--text-secondary);
    width: 50px;
    text-align: right;
    flex-shrink: 0;
}

.hotspot-bar-bg {
    width: 80px;
    height: 14px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
    flex-shrink: 0;
}

.hotspot-bar {
    height: 100%;
    background: #e34c26;
    border-radius: 3px;
    min-width: 2px;
}

/* Risk Banner */
.risk-banner {
    border-left: 4px solid var(--add-icon);
}

.risk-banner.risk-medium {
    border-left-color: #d4a72c;
}

.risk-banner.risk-high {
    border-left-color: var(--del-icon);
}

.risk-header {
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
}

.risk-label {
    font-weight: 600;
    font-size: 14px;
}

.risk-banner.risk-medium .risk-label {
    color: #d4a72c;
}

.risk-banner.risk-high .risk-label {
    color: var(--del-icon);
}

.risk-factors {
    padding: 8px 14px;
}

.risk-factor {
    font-size: 12px;
    color: var(--text-secondary);
    padding: 2px 0;
}

/* Ownership */
.ownership-item {
    padding: 8px 0;
    border-bottom: 1px solid var(--border-light);
}

.ownership-item:last-child {
    border-bottom: none;
}

.ownership-file {
    font-size: 12px;
    font-family: ui-monospace, SFMono-Regular, monospace;
    margin-bottom: 4px;
}

.ownership-top {
    display: flex;
    align-items: center;
    gap: 8px;
}

.ownership-author {
    font-weight: 600;
    font-size: 13px;
    min-width: 100px;
}

.ownership-pct {
    font-size: 12px;
    color: var(--accent);
    font-weight: 600;
    width: 40px;
    text-align: right;
}

.ownership-bar-bg {
    flex: 1;
    height: 8px;
    background: var(--bg-tertiary);
    border-radius: 4px;
    overflow: hidden;
}

.ownership-bar {
    height: 100%;
    background: var(--accent);
    border-radius: 4px;
    min-width: 2px;
}

.ownership-reviewer {
    font-size: 11px;
    color: var(--add-icon);
    margin-top: 4px;
}

/* Timeline */
.timeline-chart {
    display: flex;
    align-items: flex-end;
    gap: 8px;
    height: 120px;
    padding: 12px 0;
}

.timeline-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 4px;
}

.timeline-bar-container {
    flex: 1;
    width: 100%;
    display: flex;
    align-items: flex-end;
    justify-content: center;
}

.timeline-bar {
    width: 24px;
    background: var(--accent);
    border-radius: 4px 4px 0 0;
    min-height: 2px;
    transition: height 0.3s ease;
}

.timeline-label {
    font-size: 10px;
    color: var(--text-secondary);
    text-transform: uppercase;
}

.timeline-count {
    font-size: 10px;
    color: var(--text-secondary);
    font-weight: 600;
}

/* Summary */
.summary-item {
    font-size: 13px;
    padding: 3px 0;
    color: var(--text);
}

/* Dependencies */
.dep-file {
    padding: 8px 0;
    border-bottom: 1px solid var(--border-light);
}

.dep-file:last-child {
    border-bottom: none;
}

.dep-filename {
    font-weight: 600;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 12px;
    display: block;
    margin-bottom: 4px;
}

.dep-item {
    font-size: 12px;
    padding: 2px 8px;
    font-family: ui-monospace, SFMono-Regular, monospace;
}

.dep-added { color: var(--add-icon); }
.dep-removed { color: var(--del-icon); }
.dep-updated { color: #d4a72c; }

/* TODOs */
.todo-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 4px 0;
    font-size: 13px;
}

.todo-tag {
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
}

.todo-tag-todo { background: #ddf4ff; color: #0969da; }
.todo-tag-fixme { background: #ffebe9; color: #cf222e; }
.todo-tag-hack { background: #fff8c5; color: #9a6700; }
.todo-tag-xxx { background: #ffebe9; color: #cf222e; }
.todo-tag-bug { background: #ffebe9; color: #cf222e; }
.todo-tag-optimize { background: #dafbe1; color: #1a7f37; }

[data-theme="dark"] .todo-tag-todo { background: #1f2e3d; color: #58a6ff; }
[data-theme="dark"] .todo-tag-fixme { background: #362024; color: #f85149; }
[data-theme="dark"] .todo-tag-hack { background: #3d2e00; color: #d29922; }
[data-theme="dark"] .todo-tag-xxx { background: #362024; color: #f85149; }
[data-theme="dark"] .todo-tag-bug { background: #362024; color: #f85149; }
[data-theme="dark"] .todo-tag-optimize { background: #12262b; color: #3fb950; }

.todo-text {
    flex: 1;
}

.todo-file {
    font-size: 11px;
    color: var(--text-secondary);
    font-family: ui-monospace, SFMono-Regular, monospace;
}

/* Test Impact */
.test-impact-item {
    padding: 8px 0;
    border-bottom: 1px solid var(--border-light);
}

.test-source {
    font-size: 12px;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-weight: 600;
    margin-bottom: 4px;
}

.test-related {
    font-size: 11px;
    color: var(--text-secondary);
    margin-bottom: 2px;
}

.test-file {
    font-size: 12px;
    color: var(--accent);
    padding: 1px 0;
    padding-left: 12px;
    font-family: ui-monospace, SFMono-Regular, monospace;
}

/* Heatmap */
.heatmap-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 4px 0;
    font-size: 13px;
}

.heatmap-folder {
    width: 100px;
    font-weight: 600;
    font-size: 12px;
    flex-shrink: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.heatmap-bar-bg {
    flex: 1;
    height: 18px;
    background: var(--bg-tertiary);
    border-radius: 3px;
    overflow: hidden;
}

.heatmap-bar {
    height: 100%;
    background: var(--accent);
    border-radius: 3px;
    min-width: 2px;
}

.heatmap-count {
    font-size: 11px;
    color: var(--text-secondary);
    width: 120px;
    text-align: right;
    flex-shrink: 0;
}

/* Complexity */
.complexity-file {
    font-weight: 600;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 12px;
    padding: 8px 0 4px;
    border-top: 1px solid var(--border-light);
    margin-top: 4px;
}

.complexity-file:first-child {
    border-top: none;
    margin-top: 0;
}

.complexity-func {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 2px 0 2px 12px;
    font-size: 13px;
}

.complexity-name {
    font-family: ui-monospace, SFMono-Regular, monospace;
    flex: 1;
}

.complexity-lines {
    font-size: 11px;
    color: var(--text-secondary);
}

.complexity-delta {
    font-size: 11px;
    font-weight: 600;
    width: 40px;
    text-align: right;
}

.complexity-delta-up { color: var(--del-icon); }
.complexity-delta-down { color: var(--add-icon); }

/* Evolution */
.evolution-slider-container {
    padding: 8px 0;
}

.evolution-slider {
    width: 100%;
    accent-color: var(--accent);
}

.evolution-labels {
    display: flex;
    justify-content: space-between;
    font-size: 10px;
    color: var(--text-secondary);
    margin-top: 2px;
}

.evolution-commit-info {
    font-size: 12px;
    color: var(--text-secondary);
    text-align: center;
    padding: 4px 0;
}

.evolution-file {
    padding: 8px 0;
}

.evolution-file-header {
    font-weight: 600;
    font-family: ui-monospace, SFMono-Regular, monospace;
    font-size: 12px;
}

.evolution-content {
    margin-top: 4px;
    padding: 8px;
    background: var(--bg-secondary);
    border-radius: 4px;
    font-size: 11px;
    max-height: 120px;
    overflow-y: auto;
    white-space: pre-wrap;
}

/* Insights count in meta */
.insights-count {
    margin-left: 12px;
    color: var(--accent);
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
}

.insights-count:hover {
    color: var(--accent-hover);
}
@media (max-width: 768px) {
    .sidebar { display: none; }
    .diff-content { padding: 8px 12px; }
    .toolbar-center .view-btn { padding: 4px 8px; font-size: 11px; }
    .stats-panel { width: calc(100% - 32px); right: 16px; }
    .commit-drawer { width: 100vw; }
}
"""
