# User Stories to GitHub Issues Importer

This script **combines data from both files** to create comprehensive GitHub issues:
- `user-stories.md` - Full story details (acceptance criteria, edge cases, validation rules, error scenarios)
- `Sprint-plan.md` - Sprint organization (sprint number, story points, dependencies, repo mapping)

## Features

✅ **Complete Story Details** - All acceptance criteria, edge cases, validation rules, error scenarios  
✅ **Sprint Information** - Sprint number, goal, story points, dependencies from Sprint-plan.md  
✅ **Smart Merging** - Automatically combines data from both markdown files  
✅ **Comprehensive Labels** - Sprint, repo, size, category, priority, dependency tracking  
✅ **Rich Formatting** - Emoji-enhanced sections, checkboxes, highlighted error codes  
✅ **Dry Run Mode** - Preview issues before creating them  
✅ **Range Selection** - Import specific story ranges (e.g., US-001 to US-010)  
✅ **Sprint Filter** - Import specific sprints (e.g., Sprint 0, Sprint 1)  
✅ **Skip Existing** - Avoid duplicate issues  
✅ **Milestones** - Assign issues to milestones  
✅ **Assignees** - Auto-assign team members  

---

## Prerequisites

### 1. Python 3.7+

Check your Python version:
```bash
python --version
```

### 2. Install Dependencies

```bash
pip install requests
```

### 3. GitHub Personal Access Token

Create a GitHub Personal Access Token with `repo` permissions:

1. Go to GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Click "Generate new token (classic)"
3. Give it a name: "ValueX User Stories Import"
4. Select scopes:
   - ✅ `repo` (Full control of private repositories)
5. Click "Generate token"
6. **Copy the token** (you won't see it again!)

---

## Setup

### 1. Copy Configuration Template

```bash
cd Documents/scripts
cp config.example.json config.json
```

### 2. Edit config.json

```json
{
  "github_token": "ghp_YOUR_TOKEN_HERE",
  "repo_owner": "your-username-or-org",
  "repo_name": "ValueX-Code",
  "user_stories_file": "../user-stories.md",
  "sprint_plan_file": "../Sprint-plan.md",
  ...
}
```

**Important:** Never commit `config.json` with your token to git!

### 3. Add config.json to .gitignore

```bash
echo "Documents/scripts/config.json" >> .gitignore
```

---

## Usage

### Test Connection (Dry Run)

Preview what issues would be created without actually creating them:

```bash
python import_user_stories_to_github.py --dry-run
```

### Import All Stories

```bash
python import_user_stories_to_github.py
```

### Import Specific Range

Import only US-001 to US-010:
```bash
python import_user_stories_to_github.py --story-range 1-10
```

Import MVP core stories (US-001 to US-057):
```bash
python import_user_stories_to_github.py --story-range 1-57
```

Import new PRD v1.3 stories (US-068 to US-100):
```bash
python import_user_stories_to_github.py --story-range 68-100
```

### Import by Sprint (Sprint-plan.md)

Update config.json to use Sprint-plan.md:
```json
"user_stories_file": "../Documents/Sprint-plan.md"
```

Import all stories from Sprint 1:
```bash
python import_user_stories_to_github.py --sprint 1
```

Import Sprint 0 foundation stories:
```bash
python import_user_stories_to_github.py --sprint "Sprint 0"
```

### Skip Existing Issues

If you've already imported some stories and want to add new ones:
```bash
python import_user_stories_to_github.py --skip-existing
```

### Custom Config File

```bash
python import_user_stories_to_github.py --config my-config.json
```

---

## Issue Format

Each GitHub issue will be created with this structure:

### Title
```
US-001: User Registration with Aadhaar Verification
```

### Body (Combined from both files)

```markdown
## 📋 Sprint Information

**Sprint:** Sprint 1 - Identity & User Management
**Sprint Goal:** Allow users to register, verify identity and manage profiles
**Story Points:** 8
**Repositories:** `backend`, `mobile`
**Dependencies:** S0-001

## 👤 User Story

**As a** new user
**I want to** register using my Aadhaar
**So that** I can access the platform securely with verified identity

## ✅ Acceptance Criteria

- [ ] **Given** I am on the registration page **When** I enter my mobile number **Then** I receive an OTP for mobile verification
- [ ] **When** I complete Aadhaar verification **Then** my account is created successfully
- [ ] **And** I am assigned a unique user ID
- [ ] **And** my verified identity is stored securely

## ⚠️ Edge Cases

- User already registered with same Aadhaar
- Aadhaar verification fails (invalid, expired, or API timeout)
- Mobile number already linked to another account
- User cancels Aadhaar verification mid-flow
- Network interruption during verification

## 🔒 Validation Rules

- Mobile number must be 10 digits
- Mobile number must be unique per account
- Aadhaar must be valid 12-digit number
- One Aadhaar can link to only one account
- User must accept terms & conditions

## ❌ Error Scenarios

- **`ERROR_MOBILE_ALREADY_REGISTERED`**: "This mobile number is already registered"
- **`ERROR_AADHAAR_ALREADY_USED`**: "This Aadhaar is already linked to an account"
- **`ERROR_AADHAAR_VERIFICATION_FAILED`**: "Unable to verify Aadhaar. Please try again"

---
📄 **Source:** user-stories.md + Sprint-plan.md
🔖 **Story ID:** `US-001`
🔗 **Blocked by:** S0-001
```

### Labels

Issues are automatically tagged with comprehensive labels:

**Sprint Labels:**
- `sprint-0`, `sprint-1`, `sprint-2`, etc.

**Repository Labels:**
- `repo:backend`, `repo:mobile`, `repo:web`, `repo:ai`, `repo:infra`

**Size Labels** (based on story points):
- `size: small` (1-3 SP)
- `size: medium` (4-8 SP)  
- `size: large` (9+ SP)

**Category Labels:**
- `authentication`, `listing`, `search`, `communication`
- `negotiation`, `payment`, `shipping`, `returns`
- `ratings`, `premium`, `support`, `trust-safety`
- `admin`, `new-features`, `lifecycle`, `compliance`

**Priority Labels:**
- `priority: critical` - Core MVP features
- `priority: high` - Essential features
- `priority: medium` - Important features
- `priority: low` - Enhancement backlog

**Dependency Labels:**
- `has-dependency` - Story depends on other stories
- `sprint-setup` - Infrastructure setup (S0-xxx)

**Custom Labels:**
- `user-story` - All stories
- `PRD-v1.3` - Aligned with PRD v1.3

---

## Configuration Reference

### Basic Settings

| Field | Required | Description |
|-------|----------|-------------|
| `github_token` | ✅ Yes | GitHub Personal Access Token |
| `repo_owner` | ✅ Yes | GitHub username or organization |
| `repo_name` | ✅ Yes | Repository name |
| `user_stories_file` | ✅ Yes | Path to user-stories.md |

### Optional Settings

| Field | Type | Description |
|-------|------|-------------|
| `default_labels` | Array | Labels applied to all issues |
| `milestone_number` | Number | Milestone ID to assign issues |
| `default_assignees` | Array | GitHub usernames to auto-assign |
| `label_mapping` | Object | Category-based label rules |
| `priority_mapping` | Object | Priority-based label rules |

### Label Mapping

Automatically assigns category labels based on story number ranges:

```json
"label_mapping": {
  "authentication": {
    "start": 1,
    "end": 3,
    "description": "User Management & Authentication"
  },
  "listing": {
    "start": 4,
    "end": 10,
    "description": "Seller - Listing Management"
  }
}
```

### Priority Mapping

Assigns priority labels:

```json
"priority_mapping": {
  "priority: critical": {
    "start": 1,
    "end": 57,
    "description": "MVP Core Features"
  }
}
```

---

## Story Categories & Ranges

| Category | Stories | Range | Label |
|----------|---------|-------|-------|
| **User Management & Authentication** | US-001 to US-003 | 1-3 | `authentication` |
| **Seller - Listing Management** | US-004 to US-010 | 4-10 | `listing` |
| **Buyer - Discovery & Search** | US-011 to US-012 | 11-12 | `search` |
| **Communication** | US-013 to US-016 | 13-16 | `communication` |
| **Negotiation & Cart** | US-017 to US-020 | 17-20 | `negotiation` |
| **Orders & Payments** | US-021 to US-025 | 21-25 | `payment` |
| **Shipping & Logistics** | US-026 to US-032 | 26-32 | `shipping` |
| **Returns** | US-033 to US-035 | 33-35 | `returns` |
| **Ratings & Reviews** | US-036 to US-037 | 36-37 | `ratings` |
| **Premium Features** | US-038 to US-042 | 38-42 | `premium` |
| **Support & Assistance** | US-043 to US-047 | 43-47 | `support` |
| **Trust & Safety** | US-048 to US-052 | 48-52 | `trust-safety` |
| **Admin & Moderation** | US-053 to US-059 | 53-59 | `admin` |
| **Enhancement Backlog** | US-060 to US-067 | 60-67 | - |
| **New Features - PRD v1.3** | US-068 to US-087 | 68-87 | `new-features` |
| **Lifecycle State Machines** | US-088 to US-096 | 88-96 | `lifecycle` |
| **Compliance & Accessibility** | US-097 to US-100 | 97-100 | `compliance` |

---

## Recommended Import Strategy

### Option A: Import by User Stories Range

#### Phase 1: MVP Core (Critical)
```bash
python import_user_stories_to_github.py --story-range 1-57
```
**Stories:** US-001 to US-057 (57 stories)  
**Label:** `priority: critical`

### Option B: Import by Sprint (Sprint-plan.md)

First, update config.json to use Sprint-plan.md:
```json
"user_stories_file": "../Documents/Sprint-plan.md"
```

#### Sprint 0: Foundation & Architecture
```bash
python import_user_stories_to_github.py --sprint 0
```
**Stories:** S0-001 to S0-008 (8 stories)  
**Label:** `sprint-0-foundation-architecture`, `sprint-setup`

#### Sprint 1: Identity & User Management
```bash
python import_user_stories_to_github.py --sprint 1
```
**Stories:** US-001, US-002, US-003, US-077, US-088 (5 stories)  
**Goal:** Allow users to register, verify identity and manage profiles

#### Sprint 2: Seller Listing Creation
```bash
python import_user_stories_to_github.py --sprint 2
```
**Stories:** US-004 to US-010, US-084, US-089 (9 stories)  
**Goal:** Allow sellers to create and publish listings

#### Sprint 3: Discovery & Search
```bash
python import_user_stories_to_github.py --sprint 3
```
**Stories:** US-011, US-012, US-066, US-073 (4 stories)  
**Goal:** Enable buyers to discover items

#### Sprint 4: Communication & Negotiation
```bash
python import_user_stories_to_github.py --sprint 4
```
**Stories:** US-013 to US-018, US-069, US-076, US-080 (11 stories)  
**Goal:** Enable buyer-seller interaction

#### Sprint 5: Cart, Checkout & Payments
```bash
python import_user_stories_to_github.py --sprint 5
```
**Stories:** US-019 to US-023, US-025, US-072, US-090, US-091 (10 stories)  
**Goal:** Enable secure transactions and escrow

#### Sprint 6: Shipping & Delivery
```bash
python import_user_stories_to_github.py --sprint 6
```
**Stories:** US-026 to US-032, US-092 (8 stories)  
**Goal:** Enable fulfillment workflow

---

### Continued: Traditional Range-Based Phases

### Phase 2: Critical Additions
```bash
python import_user_stories_to_github.py --story-range 58-59
```
**Stories:** US-058 to US-059 (2 stories)  
**Label:** `priority: high`

### Phase 3: New Essential Features
```bash
python import_user_stories_to_github.py --story-range 68-78
```
**Stories:** US-068 to US-078 (11 stories)  
**Label:** `priority: high`

### Phase 4: Lifecycle & State Machines
```bash
python import_user_stories_to_github.py --story-range 88-96
```
**Stories:** US-088 to US-096 (9 stories)  
**Label:** `priority: medium`

### Phase 5: Additional Features
```bash
python import_user_stories_to_github.py --story-range 79-87
```
**Stories:** US-079 to US-087 (9 stories)  
**Label:** `priority: medium`

### Phase 6: Compliance & Accessibility
```bash
python import_user_stories_to_github.py --story-range 97-100
```
**Stories:** US-097 to US-100 (4 stories)  
**Label:** `priority: medium`

### Phase 7: Enhancement Backlog (Future)
```bash
python import_user_stories_to_github.py --story-range 60-67
```
**Stories:** US-060 to US-067 (8 stories)  
**Label:** `priority: low`

---

## Troubleshooting

### Error: "Config file not found"

Create `config.json` from the example:
```bash
cp config.example.json config.json
```

### Error: "Failed to connect to GitHub"

Check:
1. Is your token valid? (Try accessing GitHub manually)
2. Does token have `repo` scope?
3. Is `repo_owner` and `repo_name` correct?
4. Is repository accessible with your account?

### Error: "User stories file not found"

Check the `user_stories_file` path in config.json:
```json
"user_stories_file": "../Documents/user-stories.md"
```

### Rate Limit Exceeded

GitHub API has rate limits:
- **Authenticated:** 5,000 requests/hour
- **Creating issues:** ~100 issues safely

If you hit the limit:
1. Wait an hour
2. Import in smaller batches using `--story-range`

### Duplicate Issues

Use `--skip-existing` flag:
```bash
python import_user_stories_to_github.py --skip-existing
```

---

## Example Workflow

### Initial Setup
```bash
# 1. Navigate to scripts directory
cd scripts

# 2. Create config
cp config.example.json config.json

# 3. Edit config with your details
nano config.json

# 4. Test connection (dry run)
python import_user_stories_to_github.py --dry-run --story-range 1-5

# 5. Import first batch
python import_user_stories_to_github.py --story-range 1-10
```

### Adding More Stories Later
```bash
# Check what's already imported on GitHub

# Import remaining stories, skipping existing
python import_user_stories_to_github.py --skip-existing
```

---

## GitHub Milestones Setup

### Create Milestones (Optional)

1. Go to your GitHub repo → Issues → Milestones
2. Create milestones:
   - "MVP Core" (for US-001 to US-057)
   - "Phase 2 - Enhancements" (for US-068 to US-100)
   - "Future Backlog" (for US-060 to US-067)

3. Get milestone number from URL:
   ```
   https://github.com/owner/repo/milestone/1
                                            ^ This is the milestone_number
   ```

4. Add to config.json:
   ```json
   "milestone_number": 1
   ```

---

## GitHub Labels Setup

Create these labels in your repo (Settings → Labels):

### Category Labels
- `authentication` (blue)
- `listing` (green)
- `search` (yellow)
- `communication` (orange)
- `negotiation` (purple)
- `payment` (red)
- `shipping` (brown)
- `returns` (pink)
- `ratings` (cyan)
- `premium` (gold)
- `support` (teal)
- `trust-safety` (dark red)
- `admin` (gray)
- `new-features` (light blue)
- `lifecycle` (dark blue)
- `compliance` (dark green)

### Priority Labels
- `priority: critical` (red)
- `priority: high` (orange)
- `priority: medium` (yellow)
- `priority: low` (green)

### Other Labels
- `user-story` (blue)
- `PRD-v1.3` (purple)

---

## Advanced Usage

### Custom Label Logic

Edit `config.json` to customize label assignments:

```json
"label_mapping": {
  "my-custom-label": {
    "start": 1,
    "end": 50,
    "description": "First 50 stories"
  }
}
```

### Multiple Configs

Maintain different configs for different scenarios:

```bash
# Production repo
python import_user_stories_to_github.py --config config.prod.json

# Test repo
python import_user_stories_to_github.py --config config.test.json --dry-run
```

---

## Security Best Practices

### ⚠️ Never Commit Tokens

Add to `.gitignore`:
```
scripts/config.json
scripts/*.local.json
```

### ✅ Token Permissions

Only grant necessary permissions:
- ✅ `repo` scope (for private repos)
- ✅ `public_repo` scope (for public repos only)

### ✅ Token Rotation

Rotate tokens periodically:
1. Generate new token
2. Update config.json
3. Delete old token from GitHub

### ✅ Use Environment Variables (Alternative)

Instead of storing token in config.json:

```bash
export GITHUB_TOKEN="ghp_your_token"
```

Modify script to read from environment:
```python
config['github_token'] = os.environ.get('GITHUB_TOKEN', config.get('github_token'))
```

---

## FAQ

**Q: Can I import to multiple repositories?**  
A: Yes, create separate config files for each repo.

**Q: Can I update existing issues?**  
A: No, this script only creates new issues. Use `--skip-existing` to avoid duplicates.

**Q: What if user-stories.md format changes?**  
A: The parser uses regex patterns. If format changes significantly, parser logic needs updates.

**Q: Can I customize issue templates?**  
A: Yes, modify `_format_issue_body()` method in the script.

**Q: Does it work with GitHub Enterprise?**  
A: Yes, update `base_url` in the script to your GHE instance.

---

## Support

For issues or questions:
1. Check troubleshooting section
2. Review config.example.json
3. Run with `--dry-run` first
4. Check GitHub API status: https://www.githubstatus.com/

---

## Sprint Planning Guide (Sprint-plan.md)

The Sprint-plan.md format organizes user stories into sprints with:
- Sprint goals and exit criteria
- Repository assignments (backend, mobile, web, infra)
- Story points and dependencies
- Clear MVP release milestone

### Sprint Overview

| Sprint | Goal | Stories | Duration |
|--------|------|---------|----------|
| Sprint 0 | Foundation & Architecture | S0-001 to S0-008 | 2 weeks |
| Sprint 1 | Identity & User Management | 5 stories | 2 weeks |
| Sprint 2 | Seller Listing Creation | 9 stories | 2 weeks |
| Sprint 3 | Discovery & Search | 4 stories | 2 weeks |
| Sprint 4 | Communication & Negotiation | 11 stories | 2 weeks |
| Sprint 5 | Cart, Checkout & Payments | 10 stories | 2 weeks |
| Sprint 6 | Shipping & Delivery | 8 stories | 2 weeks |
| **MVP Release** | - | **55 stories total** | **14 weeks** |

Post-MVP sprints (7-12) cover returns, ratings, trust & safety, admin operations, premium plans, AI features, and compliance.

### Repository Label Mapping

When using Sprint-plan.md, stories are automatically tagged with repository labels:

- `repo:backend` - Backend API and services
- `repo:mobile` - Flutter mobile app
- `repo:web` - Admin web dashboard
- `repo:infra` - Infrastructure, DevOps, CI/CD
- `repo:ai` - AI/ML services

### Sprint-Specific Labels

Sprint labels are auto-generated:
- `sprint-0-foundation-architecture`
- `sprint-1-identity-user-management`
- `sprint-2-seller-listing-creation`
- `sprint-3-discovery-search`
- `sprint-4-communication-negotiation`
- `sprint-5-cart-checkout-payments`
- `sprint-6-shipping-delivery`

Special labels:
- `sprint-setup` - For S0-XXX foundation stories
- `mvp` - Stories in the MVP release

### Switching Between Sources

**Use user-stories.md for:**
- Detailed user story specifications
- Acceptance criteria and edge cases
- Validation rules and error scenarios
- Traditional story-by-story import

**Use Sprint-plan.md for:**
- Sprint-based planning and organization
- Repository and team assignments
- Sprint goals and exit criteria
- Incremental delivery tracking

You can use both! Import detailed specs from user-stories.md first, then add sprint organization by re-importing from Sprint-plan.md with `--skip-existing`.

---

**Version:** 2.0  
**Last Updated:** 2026-06-04  
**Compatible with:** user-stories.md v2.0, Sprint-plan.md v2.0
