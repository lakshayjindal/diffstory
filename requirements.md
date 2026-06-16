# DiffStory — Complete Product Requirements & Implementation Specification

## Project Overview

### Product Name

DiffStory (working title)

### Package Type

Python CLI application distributed through PyPI.

### Installation

```bash
pip install diffstory
```

### Primary Command

```bash
diffstory [options]
```

---

# Vision

DiffStory transforms Git diffs into rich, interactive, self-contained HTML reports that explain not only what changed, but also who changed it, when they changed it, why it was changed, and how the code evolved over time.

Traditional diff viewers answer:

> What changed?

DiffStory should answer:

> What changed?
>
> Who changed it?
>
> When was it changed?
>
> Why was it changed?
>
> How has this line evolved?
>
> Where did this change originate?

The generated report must be portable, offline, shareable, and usable by developers, QA teams, auditors, consultants, security teams, and technical managers.

---

# Problem Statement

Current tools have limitations:

* Git diff only shows textual changes.
* diff2html generates visual reports but lacks provenance.
* git blame provides attribution but lacks review UX.
* GitHub/GitLab require server access and are tied to repositories.
* Pull requests disappear into platform silos.
* Historical investigation is slow and fragmented.

Users frequently switch between:

* git diff
* git blame
* git log
* GitHub PR pages
* IDE history tools

to answer a single question.

DiffStory consolidates all of these contexts into one report.

---

# Primary Goals

The system must:

* Generate beautiful HTML diff reports.
* Work entirely offline.
* Include blame information.
* Support multiple viewing styles.
* Scale to large repositories.
* Produce portable artifacts.
* Require minimal setup.
* Use existing Git repositories without modification.

---

# Non-Goals

The product is NOT intended to:

* Replace Git.
* Replace GitHub or GitLab.
* Edit repositories.
* Commit changes.
* Push changes.
* Modify code.
* Replace IDEs.
* Require internet access.
* Depend on hosted services.
* Become a full code review platform.

---

# Target Users

## Developers

Need:

* Better local review experience.
* Historical understanding.
* Code archaeology.

---

## QA Engineers

Need:

* Review artifacts.
* Audit evidence.
* Release validation.

---

## Consultants

Need:

* Deliverables for clients.
* Portable reports.

---

## Technical Leads

Need:

* Contributor visibility.
* Review summaries.
* Impact analysis.

---

## Security Teams

Need:

* Change investigation.
* Provenance tracking.

---

## Auditors

Need:

* Offline evidence.
* Traceability.

---

# Core User Stories

As a developer, I want to generate an HTML report from a Git diff.

As a reviewer, I want to know who modified each changed line.

As a lead, I want to understand why a line changed.

As a QA engineer, I want a report I can archive.

As an auditor, I want evidence that requires no repository access.

As an investigator, I want to trace line evolution.

---

# CLI Requirements

## Working Tree

```bash
diffstory
```

Equivalent:

```bash
git diff
```

---

## Staged Changes

```bash
diffstory --staged
```

Equivalent:

```bash
git diff --cached
```

---

## Commit Comparison

```bash
diffstory COMMIT_A COMMIT_B
```

---

## Branch Comparison

```bash
diffstory main feature/auth
```

---

## File Restriction

```bash
diffstory HEAD~3 HEAD src/
```

---

## Output File

```bash
diffstory -o report.html
```

Default:

```text
diffstory-report.html
```

---

## JSON Export

```bash
diffstory --json
```

---

## Markdown Export

```bash
diffstory --md
```

---

## CSV Export

```bash
diffstory --csv
```

---

# HTML Report Requirements

Generated reports must:

* Be a single HTML file.
* Include all CSS inline.
* Include all JavaScript inline.
* Include all metadata inline.
* Function without internet access.
* Open in any modern browser.
* Require no installation.

The report must remain functional if emailed or archived.

---

# Diff Visualization Modes

## Unified Mode

Classic Git format.

Requirements:

* Additions.
* Deletions.
* Context lines.
* Syntax highlighting.

---

## Side-by-Side Mode

Requirements:

* Original column.
* Modified column.
* Synchronized scrolling.
* Line mapping.

---

## Inline Edit Mode

This is a flagship feature.

Instead of:

```diff
- subtotal
+ subtotal + tax
```

Show:

```text
subtotal → subtotal + tax
```

Requirements:

* Word-level additions.
* Word-level removals.
* Single-line presentation.
* Reduced visual noise.

---

## View Switching

Users must switch modes without regenerating reports.

Toolbar:

* Unified
* Side-by-side
* Inline

Instant switching.

---

# Blame Integration

Each changed line must expose:

* Author name.
* Commit hash.
* Commit title.
* Commit date.
* Relative age.
* Commit email (optional).
* Branch reference if available.

Source:

```bash
git blame --line-porcelain
```

---

# Tooltip Requirements

Hovering over a changed line must reveal:

Author

Commit Title

Commit Hash

Date

Relative Time

Email (configurable)

Files Changed

Branch

PR Number (future integrations)

Tooltips must appear instantly.

---

# Commit Drawer

Clicking a line opens a detailed side panel.

Information:

Commit Title

Commit Body

Hash

Author

Committer

Date

Parents

Files Changed

Insertions

Deletions

Patch Summary

Must be dismissible.

---

# Timeline Feature

Users should understand line evolution.

Display:

How many times the line changed.

Expandable timeline.

Timeline entries:

Date

Author

Commit

Message

---

# Evolution Viewer

Users can inspect prior versions.

Example:

Version 1

↓

Version 2

↓

Version 3

Requirements:

* Chronological ordering.
* Side-by-side comparison.
* Expand on demand.

---

# Syntax Highlighting

Support:

Python

JavaScript

TypeScript

Java

C#

Go

Rust

PHP

Ruby

Kotlin

SQL

Shell

YAML

JSON

HTML

CSS

Markdown

Plain Text

Requirements:

Automatic detection.

Graceful fallback.

Offline operation.

---

# Word-Level Diffing

Requirements:

Highlight modified tokens.

Reduce duplicate lines.

Support algorithms:

* Myers
* difflib
* Patience Diff

Allow future extensibility.

---

# File Navigation

Sidebar requirements:

File names.

Counts:

* Added

- Deleted

Modified indicators.

Rename indicators.

Search capability.

Collapse support.

Sticky positioning.

---

# Search

Searchable by:

Filename

Author

Commit Message

Commit Hash

Code Content

Requirements:

Instant filtering.

Highlight matches.

Keyboard shortcut support.

---

# Filtering

Filters:

Authors

Date Range

Extensions

Change Type

Files

Requirements:

Combinable filters.

Persistent during navigation.

Clear-all functionality.

---

# Rename Detection

Requirements:

Detect renamed files.

Display:

Old Name

New Name

Similarity Score

Source:

```bash
git diff --find-renames
```

---

# Binary File Support

Requirements:

Detect binary assets.

Image preview support.

Metadata for unsupported types.

No crashes.

Display meaningful placeholders.

---

# Statistics Dashboard

Provide:

Files Changed

Insertions

Deletions

Authors

Commits

Largest Files

Most Modified Files

Contribution Breakdown

Change Distribution

---

# Theme Support

Themes:

Light

Dark

Auto

Requirements:

Persist selection.

Respect system preference.

Instant switching.

---

# Keyboard Navigation

Requirements:

J → Next Change

K → Previous Change

F → Search

D → Theme Toggle

U → Unified

S → Side-by-Side

I → Inline

ESC → Close Panels

---

# Deep Linking

Support:

#line-482

#file-auth.py

Requirements:

Direct navigation.

Stable anchors.

Shareability.

---

# Performance Requirements

Target Repository Size:

500+ files

10,000+ changed lines

Requirements:

Initial render under 2 seconds.

Minimal browser lag.

Efficient memory usage.

Lazy rendering.

Virtualized large sections.

Avoid DOM explosions.

---

# Configuration System

Configuration file:

```text
.diffstory.toml
```

Settings:

Theme

Default View

Syntax Highlighting

Email Visibility

Relative Time

Tooltip Behavior

Keyboard Shortcuts

Statistics Visibility

Evolution Depth

---

# Security Requirements

The tool must:

Never upload code.

Never transmit data.

Never perform telemetry.

Never require accounts.

Never access external APIs by default.

Never modify Git history.

Never alter repository contents.

---

# Privacy Expectations

All generated artifacts must remain local.

Generated reports must be safe for:

Internal audits.

Client sharing.

Air-gapped environments.

Regulated industries.

---

# Error Handling Requirements

Handle gracefully:

Non-Git directories.

Detached HEAD states.

Missing commits.

Corrupt repositories.

Binary files.

Encoding issues.

Huge diffs.

Permission errors.

Invalid CLI arguments.

Interrupted generation.

Provide actionable error messages.

Never expose stack traces unless debug mode is enabled.

---

# Logging Requirements

Modes:

Silent

Normal

Verbose

Debug

Debug mode may expose:

Git commands.

Execution times.

Internal processing stages.

---

# Architecture Expectations

## Backend

Language:

Python

Responsibilities:

Git interaction.

Diff extraction.

Metadata collection.

HTML generation.

Export generation.

Configuration parsing.

Statistics computation.

---

## Frontend

Technology:

Vanilla JavaScript.

Responsibilities:

Rendering.

Filtering.

Search.

Theme switching.

Tooltips.

Navigation.

View switching.

Panel interactions.

No build process.

No framework dependency.

---

# Git Integration Expectations

Preferred approach:

Python subprocess.

Reasons:

Zero dependency on GitPython.

Closer parity with Git behavior.

Predictable output.

Lower maintenance burden.

Git executable required.

---

# Export Requirements

HTML

JSON

Markdown

CSV

Requirements:

Consistent metadata.

Deterministic output.

Machine-readable formats.

Human-readable formats.

---

# Packaging Requirements

Distribution:

PyPI.

Entry Point:

```bash
diffstory
```

Requirements:

Python 3.10+

Cross-platform.

Linux support.

macOS support.

Windows support.

Reproducible builds.

Semantic versioning.

Comprehensive README.

Example screenshots.

CLI documentation.

---

# Testing Requirements

Unit Tests:

Diff parsing.

Blame parsing.

Configuration parsing.

Statistics generation.

Export generation.

CLI validation.

Integration Tests:

Real repositories.

Branch comparisons.

Staged changes.

Large repositories.

Cross-platform execution.

UI Tests:

Search.

Theme switching.

View switching.

Tooltips.

Keyboard navigation.

Performance Tests:

Large datasets.

Memory benchmarks.

Timing benchmarks.

---

# Acceptance Criteria

The MVP is considered complete when:

A user can install the package using pip.

A user can generate a standalone HTML report.

The report supports unified viewing.

The report supports side-by-side viewing.

The report supports inline edit viewing.

Changed lines expose blame metadata.

Syntax highlighting functions correctly.

The report works offline.

Large repositories remain usable.

No repository modifications occur.

---

# Negative Requirements

The system must NOT:

Require internet access.

Upload code.

Collect analytics.

Depend on Git hosting providers.

Require Node.js.

Require Docker.

Require databases.

Modify repositories.

Alter commits.

Rewrite history.

Store generated reports remotely.

Become a merge tool.

Become a code editor.

Become a hosted SaaS product.

Prioritize aesthetics over performance.

Sacrifice correctness for animations.

---

# Risks and Challenges

Inline diff generation complexity.

Large repository performance.

Blame accuracy around moved code.

Browser memory limitations.

Cross-platform Git behavior differences.

Encoding inconsistencies.

HTML size growth.

Balancing functionality with simplicity.

Avoiding feature creep.

---

# Recommended Development Phases

## Phase 1 (MVP)

HTML generation.

Unified view.

Side-by-side view.

Inline edits.

Syntax highlighting.

Offline reports.

CLI packaging.

---

## Phase 2

Blame integration.

Tooltips.

Commit metadata.

Search.

Filtering.

Statistics.

---

## Phase 3

Commit drawer.

Evolution viewer.

Timelines.

Deep links.

Keyboard shortcuts.

---

## Phase 4

Binary previews.

Advanced analytics.

Performance optimization.

Enterprise polish.

---

## Future Possibilities

GitHub integrations.

GitLab integrations.

Azure DevOps integrations.

Bitbucket integrations.

PR import.

Comment synchronization.

Hosted comparison portal.

VS Code extension.

JetBrains plugin.

Pre-commit hooks.

CI publishing actions.

---

# Success Metrics

Users can replace diff2html for daily usage.

Generated reports are adopted in QA workflows.

Reports become reusable audit artifacts.

Developers reduce context switching.

Reviewers identify change ownership faster.

Investigation time decreases significantly.

The generated HTML becomes the preferred medium for sharing change context.

---

# Final Product Philosophy

DiffStory should feel like opening a time machine for a Git diff.

It should not merely visualize changes.

It should tell the story behind those changes.

Every changed line should answer:

What changed?

Who changed it?

When did they change it?

Why was it changed?

How did it evolve?

And allow users to discover those answers in seconds, entirely offline, from a single HTML file.
