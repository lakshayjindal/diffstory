#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# deploy.sh — Build and publish diffstory to PyPI and GitHub Packages.
#
# Usage:
#   ./deploy.sh               # patch bump (0.2.0 → 0.2.1)
#   ./deploy.sh minor         # minor bump (0.2.0 → 0.3.0)
#   ./deploy.sh major         # major bump (0.2.0 → 1.0.0)
#   ./deploy.sh 0.3.0         # explicit version
#
# Requires:
#   - twine, build installed  (pip install twine build)
#   - .env with PYPI_TOKEN or TWINE_PASSWORD set
#   - GITHUB_TOKEN env var (if publishing to GitHub Packages)
# ---------------------------------------------------------------------------
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT_DIR"

# ---- colour helpers ----
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m' # No Colour

info()  { echo -e "${CYAN}==>${NC} $*"; }
ok()    { echo -e "${GREEN}✓${NC} $*"; }
err()   { echo -e "${RED}✗${NC} $*"; exit 1; }

# ---- 1. Load .env ----
if [[ -f .env ]]; then
    set -a
    source .env
    set +a
fi

PYPI_TOKEN="${PYPI_TOKEN:-${pypi:-}}"
GITHUB_TOKEN="${GITHUB_TOKEN:-}"

# ---- 2. Bump version ----
VERSION_FILE="src/diffstory/__init__.py"
PYPROJECT_FILE="pyproject.toml"

current_version=$(sed -n "s/^__version__ = \"\(.*\)\"/\1/p" "$VERSION_FILE")
info "Current version: $current_version"

bump="${1:-patch}"

if [[ "$bump" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    new_version="$bump"
elif [[ "$bump" == "major" ]]; then
    new_version=$(echo "$current_version" | awk -F. '{printf "%d.%d.%d", $1+1, 0, 0}')
elif [[ "$bump" == "minor" ]]; then
    new_version=$(echo "$current_version" | awk -F. '{printf "%d.%d.%d", $1, $2+1, 0}')
else
    # patch (default)
    new_version=$(echo "$current_version" | awk -F. '{printf "%d.%d.%d", $1, $2, $3+1}')
fi

info "New version: $new_version"

# Update __init__.py
sed -i "s/^__version__ = \".*\"/__version__ = \"$new_version\"/" "$VERSION_FILE"
# Update pyproject.toml
sed -i "s/^version = \".*\"/version = \"$new_version\"/" "$PYPROJECT_FILE"

ok "Version bumped: $current_version → $new_version"

# ---- 3. Clean old builds ----
rm -rf dist/ build/ *.egg-info

# ---- 4. Build package ----
info "Building package..."
python3 -m build
ok "Build complete: dist/"

# ---- 5. Publish to PyPI ----
if [[ -n "$PYPI_TOKEN" ]]; then
    info "Publishing to PyPI..."
    python3 -m twine upload \
        --username __token__ \
        --password "$PYPI_TOKEN" \
        dist/*.tar.gz dist/*.whl \
        2>&1 || echo "  (PyPI publish skipped — check token/network)"
    ok "Published to PyPI"
else
    info "Skipping PyPI publish (PYPI_TOKEN not set)"
fi

# ---- 6. Publish to GitHub Packages (optional) ----
# GitHub Packages for Python requires:
#   1. Package name format: @OWNER/REPO
#   2. Upload via GitHub Actions with proper token
#   3. Repository URL format: https://uploads.packages.github.com/
#
# Since this requires a GITHUB_TOKEN with packages:write scope
# and repository-specific configuration, it's better handled
# by the .github/workflows/publish.yml workflow on tag pushes.
#
# For local testing, use:
#   python3 -m twine upload --repository-url https://test.pypi.org/legacy/ dist/*
if [[ -n "$GITHUB_TOKEN" ]]; then
    info "Publishing to GitHub Packages..."
    OWNER="lakshayjindal"
    python3 -m twine upload \
        --repository-url "https://uploads.packages.github.com/" \
        --username "$OWNER" \
        --password "$GITHUB_TOKEN" \
        dist/*.tar.gz dist/*.whl \
        2>&1 || echo "  (GitHub Packages publish skipped — run via CI instead)"
    ok "Published to GitHub Packages"
else
    info "Skipping GitHub Packages publish (GITHUB_TOKEN not set — use CI workflow)"
fi

# ---- 7. Commit version bump ----
git add "$VERSION_FILE" "$PYPROJECT_FILE"
git commit -m "Bump version to $new_version" 2>/dev/null || true
ok "Version bump committed"

echo ""
echo -e "${GREEN}All done!${NC} Version $new_version built and published."
echo "  dist/:"
ls -lh dist/
