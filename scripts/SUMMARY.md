# GitHub Issues Import - Quick Summary

**Created:** 2026-06-04  
**Purpose:** Import 100 user stories from user-stories.md to GitHub Issues

---

## 📁 Files Created

| File | Purpose |
|------|---------|
| `import_user_stories_to_github.py` | Main Python script (13KB) |
| `config.example.json` | Configuration template (2.7KB) |
| `README.md` | Complete documentation (13KB) |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Prevent committing tokens |
| `quick_start.sh` | Linux/Mac quick start script |
| `quick_start.bat` | Windows quick start script |

---

## 🚀 Quick Start (3 Steps)

### 1. Setup
```bash
cd scripts
cp config.example.json config.json
# Edit config.json with your GitHub token and repo details
```

### 2. Install
```bash
pip install -r requirements.txt
```

### 3. Import
```bash
# Test first (dry run)
python import_user_stories_to_github.py --dry-run --story-range 1-5

# Import MVP stories
python import_user_stories_to_github.py --story-range 1-57

# Or use quick start script
./quick_start.sh  # Linux/Mac
quick_start.bat   # Windows
```

---

## ⚙️ Configuration Required

Edit `config.json`:

```json
{
  "github_token": "ghp_YOUR_TOKEN_HERE",
  "repo_owner": "your-username",
  "repo_name": "ValueX-Code",
  "user_stories_file": "../Documents/user-stories.md"
}
```

**Get GitHub Token:**
1. GitHub → Settings → Developer settings → Personal access tokens
2. Generate new token (classic)
3. Select `repo` scope
4. Copy token to config.json

---

## 📊 What Gets Imported

### Story Format
Each issue contains:
- ✅ User story (As a / I want / So that)
- ✅ Acceptance criteria (checkboxes)
- ✅ Edge cases
- ✅ Validation rules
- ✅ Error scenarios
- ✅ Auto-assigned labels (category + priority)

### All 100 Stories
- **US-001 to US-057:** MVP Core (57 stories) - `priority: critical`
- **US-058 to US-059:** Critical Additions (2 stories) - `priority: high`
- **US-060 to US-067:** Enhancement Backlog (8 stories) - `priority: low`
- **US-068 to US-087:** New Features (20 stories) - `priority: high/medium`
- **US-088 to US-096:** Lifecycle States (9 stories) - `priority: medium`
- **US-097 to US-100:** Compliance (4 stories) - `priority: medium`

---

## 🏷️ Auto-Generated Labels

### Category Labels (16 total)
Based on story ranges:
- `authentication` (US-001 to 003)
- `listing` (US-004 to 010)
- `search` (US-011 to 012)
- `communication` (US-013 to 016)
- `negotiation` (US-017 to 020)
- `payment` (US-021 to 025)
- `shipping` (US-026 to 032)
- `returns` (US-033 to 035)
- `ratings` (US-036 to 037)
- `premium` (US-038 to 042)
- `support` (US-043 to 047)
- `trust-safety` (US-048 to 052)
- `admin` (US-053 to 059)
- `new-features` (US-068 to 087)
- `lifecycle` (US-088 to 096)
- `compliance` (US-097 to 100)

### Priority Labels
- `priority: critical` - MVP must-haves
- `priority: high` - Essential features
- `priority: medium` - Important features
- `priority: low` - Future enhancements

### Default Labels
- `user-story` - All stories tagged
- `PRD-v1.3` - Based on PRD version 1.3

---

## 🎯 Recommended Import Strategy

### Phase 1: Test (5 stories)
```bash
python import_user_stories_to_github.py --dry-run --story-range 1-5
python import_user_stories_to_github.py --story-range 1-5
```
**Verify:** Check GitHub for correct formatting

### Phase 2: MVP Core (57 stories)
```bash
python import_user_stories_to_github.py --story-range 1-57
```
**Time:** ~2-3 minutes

### Phase 3: Critical Additions (2 stories)
```bash
python import_user_stories_to_github.py --story-range 58-59
```

### Phase 4: New Features (20 stories)
```bash
python import_user_stories_to_github.py --story-range 68-87
```

### Phase 5: Lifecycle (9 stories)
```bash
python import_user_stories_to_github.py --story-range 88-96
```

### Phase 6: Compliance (4 stories)
```bash
python import_user_stories_to_github.py --story-range 97-100
```

### Phase 7: Backlog (8 stories)
```bash
python import_user_stories_to_github.py --story-range 60-67
```

**OR Import All at Once:**
```bash
python import_user_stories_to_github.py
```

---

## 🛡️ Safety Features

✅ **Dry Run Mode** - Preview before creating  
✅ **Skip Existing** - Avoid duplicates  
✅ **Range Selection** - Import in batches  
✅ **API Verification** - Test connection first  
✅ **Error Handling** - Graceful failure recovery  
✅ **Token Security** - .gitignore prevents commits  

---

## 📖 Usage Examples

### Preview First 10 Stories
```bash
python import_user_stories_to_github.py --dry-run --story-range 1-10
```

### Import Authentication Stories
```bash
python import_user_stories_to_github.py --story-range 1-3
```

### Import All Payment Stories
```bash
python import_user_stories_to_github.py --story-range 21-25
```

### Skip Already Imported
```bash
python import_user_stories_to_github.py --skip-existing
```

### Custom Config
```bash
python import_user_stories_to_github.py --config my-config.json
```

---

## ⚠️ Important Notes

### Before Running
1. ✅ Create GitHub Personal Access Token with `repo` scope
2. ✅ Copy config.example.json to config.json
3. ✅ Edit config.json with your token and repo details
4. ✅ Test with --dry-run first
5. ✅ Never commit config.json to git

### Rate Limits
- GitHub allows 5,000 API requests/hour
- Script creates 1 issue per story
- Safe to import all 100 stories at once
- If you hit limit, wait 1 hour or import in batches

### Security
- **Never** commit config.json
- **Never** share your GitHub token
- Use tokens with minimal required permissions
- Rotate tokens periodically
- .gitignore already configured

---

## 🐛 Troubleshooting

### "Config file not found"
```bash
cp config.example.json config.json
```

### "Failed to connect to GitHub"
- Verify token is correct
- Check token has `repo` scope
- Confirm repo_owner and repo_name are correct

### "User stories file not found"
- Verify path in config.json
- Default: `../Documents/user-stories.md`

### Duplicate Issues
```bash
python import_user_stories_to_github.py --skip-existing
```

---

## 📚 Documentation

### Full Documentation
Read `README.md` for complete guide with:
- Detailed setup instructions
- All configuration options
- Label mapping reference
- Advanced usage
- FAQ and troubleshooting

### Config Reference
See `config.example.json` for:
- All available settings
- Label mapping rules
- Priority mapping rules
- Examples

---

## ✅ Success Criteria

After import, you should see:
- ✅ 100 GitHub issues created
- ✅ Each issue has proper title (US-XXX: Title)
- ✅ Each issue has structured body with sections
- ✅ Each issue has appropriate labels
- ✅ Issues are searchable and filterable
- ✅ Acceptance criteria are checkboxes

---

## 🔗 Related Files

- **user-stories.md** (124KB) - Source document (100 stories)
- **PRD_ValueX_v1.3.md** (27KB) - Product requirements
- **PRD_to_UserStory_Mapping.md** (9.7KB) - Requirement mapping

---

## 🎉 What's Next

After importing:
1. Review issues on GitHub
2. Organize into milestones
3. Assign to team members
4. Start sprint planning
5. Link issues to pull requests
6. Track progress

---

**Script Version:** 1.0  
**Compatible With:** user-stories.md v2.0 (100 stories)  
**Python Required:** 3.7+  
**Dependencies:** requests  

---

## Quick Command Reference

| Command | Purpose |
|---------|---------|
| `--dry-run` | Preview without creating |
| `--story-range 1-10` | Import specific range |
| `--skip-existing` | Avoid duplicates |
| `--config path.json` | Use custom config |

---

**Status:** ✅ Ready to Use  
**Tested:** ✅ Yes  
**Documentation:** ✅ Complete
