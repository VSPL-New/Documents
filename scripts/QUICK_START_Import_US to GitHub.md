# Quick Start Guide

## 1. Install Python Requirements

```bash
pip install requests
```

## 2. Configure

```bash
cd Documents/scripts
```

Edit `config.json` (already created) and update:

```json
{
  "github_token": "ghp_YOUR_GITHUB_TOKEN",
  "repo_owner": "your-github-username",
  "repo_name": "ValueX-Code"
}
```

Get GitHub token: https://github.com/settings/tokens (needs `repo` scope)

## 3. Test (Dry Run)

Preview what will be created:

```bash
python import_user_stories_to_github.py --dry-run --sprint 1
```

## 4. Import Stories

### Option A: Import by Sprint (Recommended)

**Sprint 0 - Foundation:**
```bash
python import_user_stories_to_github.py --sprint 0
```

**Sprint 1 - User Management:**
```bash
python import_user_stories_to_github.py --sprint 1
```

**Sprint 2 - Listings:**
```bash
python import_user_stories_to_github.py --sprint 2
```

Continue with other sprints as needed.

### Option B: Import by Range

**Core MVP (US-001 to US-057):**
```bash
python import_user_stories_to_github.py --story-range 1-57
```

**New Features (US-068 to US-100):**
```bash
python import_user_stories_to_github.py --story-range 68-100
```

### Option C: Import All

```bash
python import_user_stories_to_github.py --skip-existing
```

## What Gets Created

Each issue includes:
- ✅ Sprint info (sprint number, goal, story points)
- ✅ Repository mapping (backend, mobile, web, AI, infra)
- ✅ Dependencies (blocked by which stories)
- ✅ Full user story (As a / I want to / So that)
- ✅ Acceptance criteria with checkboxes
- ✅ Edge cases
- ✅ Validation rules
- ✅ Error scenarios
- ✅ Comprehensive labels (sprint, repo, size, category, priority)

## Common Commands

```bash
# Preview before creating
--dry-run

# Import specific sprint
--sprint 1

# Import story range
--story-range 1-10

# Skip if already exists
--skip-existing

# Combine options
--sprint 0 --dry-run
--story-range 1-20 --skip-existing
```

## Example Workflow

```bash
# 1. Test connection
python import_user_stories_to_github.py --dry-run --sprint 0

# 2. Import Sprint 0 (foundation)
python import_user_stories_to_github.py --sprint 0

# 3. Import Sprint 1 (user management)
python import_user_stories_to_github.py --sprint 1

# 4. Continue with other sprints...
python import_user_stories_to_github.py --sprint 2
```

## Troubleshooting

**Error: "Config file not found"**
- Make sure you're in `Documents/scripts` directory
- Check `config.json` exists

**Error: "Failed to connect to GitHub"**
- Verify your GitHub token is correct
- Check `repo_owner` and `repo_name` are correct
- Ensure token has `repo` scope

**Error: "Rate limit exceeded"**
- GitHub allows 5000 requests/hour
- Wait or import in smaller batches

## Need More Details?

See [README.md](README.md) for complete documentation.

## Security Warning

⚠️ **Never commit config.json to git!**

Add to .gitignore:
```bash
echo "Documents/scripts/config.json" >> .gitignore
```
