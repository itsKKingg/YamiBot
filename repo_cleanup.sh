#!/bin/bash
# Repository Cleanup Script
# This script reorganizes the YamiBot repository according to security audit recommendations

set -e

echo "🧹 Starting repository cleanup..."

# Create docs directory structure
echo "📁 Creating docs/ directory structure..."
mkdir -p docs/implementation
mkdir -p docs/deployment

# Move documentation files
echo "📄 Moving documentation files to docs/..."
mv CHANGELOG.md docs/ 2>/dev/null || echo "  - CHANGELOG.md not found or already moved"
mv CHANGES.md docs/ 2>/dev/null || echo "  - CHANGES.md not found or already moved"
mv SECURITY.md docs/ 2>/dev/null || echo "  - SECURITY.md not found or already moved"

# Move implementation notes to docs/implementation/
echo "📝 Moving implementation notes to docs/implementation/..."
mv IMPLEMENTATION_SUMMARY.md docs/implementation/ 2>/dev/null || echo "  - IMPLEMENTATION_SUMMARY.md not found or already moved"
mv IMPROVEMENTS.md docs/implementation/ 2>/dev/null || echo "  - IMPROVEMENTS.md not found or already moved"
mv MUSIC_INTEGRATION_IMPLEMENTATION.md docs/implementation/ 2>/dev/null || echo "  - MUSIC_INTEGRATION_IMPLEMENTATION.md not found or already moved"
mv PROVIDER_ARCHITECTURE_REFACTOR_SUMMARY.md docs/implementation/ 2>/dev/null || echo "  - PROVIDER_ARCHITECTURE_REFACTOR_SUMMARY.md not found or already moved"
mv IMPLEMENTATION_VERIFICATION.md docs/implementation/ 2>/dev/null || echo "  - IMPLEMENTATION_VERIFICATION.md not found or already moved"
mv VERIFICATION.md docs/implementation/ 2>/dev/null || echo "  - VERIFICATION.md not found or already moved"
mv GRACEFUL_INIT_SUMMARY.md docs/implementation/ 2>/dev/null || echo "  - GRACEFUL_INIT_SUMMARY.md not found or already moved"
mv DEPLOYMENT_FIX_SUMMARY.md docs/implementation/ 2>/dev/null || echo "  - DEPLOYMENT_FIX_SUMMARY.md not found or already moved"

# Move deployment docs to docs/deployment/
echo "📋 Moving deployment documentation to docs/deployment/..."
mv DEPLOYMENT_CHECKLIST.md docs/deployment/ 2>/dev/null || echo "  - DEPLOYMENT_CHECKLIST.md not found or already moved"

# Move test file to tests/
echo "🧪 Creating tests/ directory and moving test file..."
mkdir -p tests
mv test_basic.py tests/ 2>/dev/null || echo "  - test_basic.py not found or already moved"

# Create tests/__init__.py
echo "📄 Creating tests/__init__.py..."
touch tests/__init__.py

# Move Procfile to deployment/
echo "🚀 Moving Procfile to deployment/..."
mv Procfile deployment/ 2>/dev/null || echo "  - Procfile not found or already moved"

echo ""
echo "✅ Repository cleanup complete!"
echo ""
echo "Next steps:"
echo "1. Review the changes with: git status"
echo "2. Commit the changes with: git add . && git commit -m 'Reorganize repository structure per security audit'"
echo "3. Update any hardcoded paths in deployment scripts to reflect new structure"
echo ""
echo "New repository structure:"
echo "  docs/"
echo "    ├── CHANGELOG.md"
echo "    ├── CHANGES.md"
echo "    ├── SECURITY.md"
echo "    ├── implementation/ (implementation notes)"
echo "    └── deployment/ (deployment docs)"
echo "  tests/"
echo "    └── test_basic.py"
echo "  deployment/"
echo "    ├── Dockerfile"
echo "    ├── Procfile"
echo "    └── koyeb-deploy.md"
