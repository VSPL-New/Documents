#!/bin/bash
# Quick Start Script for GitHub Issues Import

set -e

echo "=================================================="
echo "  ValueX User Stories → GitHub Issues Importer"
echo "=================================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.7+"
    exit 1
fi
echo "✅ Python found: $(python3 --version)"

# Check if config exists
if [ ! -f "config.json" ]; then
    echo ""
    echo "⚠️  config.json not found"
    echo ""
    read -p "Would you like to create it from template? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp config.example.json config.json
        echo "✅ Created config.json"
        echo ""
        echo "📝 Please edit config.json with your details:"
        echo "   - github_token: Your GitHub Personal Access Token"
        echo "   - repo_owner: Your GitHub username or organization"
        echo "   - repo_name: Your repository name"
        echo ""
        echo "Press Enter when done..."
        read
    else
        echo "❌ Cannot proceed without config.json"
        exit 1
    fi
fi

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip3 install -q -r requirements.txt
echo "✅ Dependencies installed"

# Verify user stories file exists
USER_STORIES_FILE="../Documents/user-stories.md"
if [ ! -f "$USER_STORIES_FILE" ]; then
    echo "❌ User stories file not found: $USER_STORIES_FILE"
    exit 1
fi
echo "✅ User stories file found"

# Dry run test
echo ""
echo "🧪 Running test (dry run with first 5 stories)..."
echo ""
python3 import_user_stories_to_github.py --dry-run --story-range 1-5

echo ""
echo "=================================================="
echo "  Ready to import!"
echo "=================================================="
echo ""
echo "What would you like to do?"
echo ""
echo "  1. Import MVP Core stories (US-001 to US-057)"
echo "  2. Import all stories (US-001 to US-100)"
echo "  3. Import specific range"
echo "  4. Exit (import manually later)"
echo ""
read -p "Choose option (1-4): " -n 1 -r
echo ""

case $REPLY in
    1)
        echo "🚀 Importing MVP Core stories..."
        python3 import_user_stories_to_github.py --story-range 1-57
        ;;
    2)
        echo "🚀 Importing all stories..."
        python3 import_user_stories_to_github.py
        ;;
    3)
        read -p "Enter range (e.g., 1-10): " RANGE
        echo "🚀 Importing stories $RANGE..."
        python3 import_user_stories_to_github.py --story-range "$RANGE"
        ;;
    4)
        echo "👋 Exiting. Run the script manually when ready."
        exit 0
        ;;
    *)
        echo "❌ Invalid option"
        exit 1
        ;;
esac

echo ""
echo "✅ Import complete!"
echo "🔗 Check your GitHub repository for issues"
