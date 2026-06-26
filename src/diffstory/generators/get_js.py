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

// Collapse / Expand All — also toggles analytics sections (Hotspots, etc.)
function collapseAll() {
    var allSections = document.querySelectorAll('.file-section, .analytics-section');
    var allCollapsed = true;
    for (var i = 0; i < allSections.length; i++) {
        if (!allSections[i].classList.contains('collapsed')) {
            allCollapsed = false;
            break;
        }
    }
    allSections.forEach(function(s) {
        s.classList.toggle('collapsed', !allCollapsed);
    });
    var btn = document.getElementById('collapse-all-btn');
    if (btn) {
        // Label reflects the NEW state after toggle (allCollapsed is the OLD state)
        btn.textContent = allCollapsed ? 'Collapse All' : 'Expand All';
    }
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

// Analytics section toggle (collapse/expand)
function toggleAnalytics(header) {
    var section = header.closest('.analytics-section');
    section.classList.toggle('collapsed');
}

// Review mode
var reviewState = JSON.parse(localStorage.getItem('diffstory-review') || '{}');

function toggleReviewFile(fileIdx) {
    var chk = document.getElementById('review-chk-' + fileIdx);
    if (chk) {
        reviewState['file-' + fileIdx] = chk.checked;
        localStorage.setItem('diffstory-review', JSON.stringify(reviewState));
    }
}

// Restore review state on load
(function() {
    try {
        var reviewEl = document.getElementById('diffstory-review-mode');
        if (reviewEl && reviewEl.textContent === 'true') {
            for (var key in reviewState) {
                var chk = document.getElementById('review-chk-' + key.replace('file-', ''));
                if (chk && reviewState[key]) {
                    chk.checked = true;
                }
            }
        }
    } catch(e) {}
})();

document.querySelectorAll('.sidebar-file').forEach(function(el) {
    el.addEventListener('click', function() {
        document.querySelectorAll('.sidebar-file').forEach(function(f) {
            f.classList.remove('active');
        });
        el.classList.add('active');
    });
});
"""
