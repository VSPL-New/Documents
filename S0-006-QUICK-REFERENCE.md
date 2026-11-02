# S0-006: CI/CD Pipeline - Quick Reference Guide

**Status:** ✅ Implemented  
**Last Updated:** 2026-11-03

---

## What Was Implemented

### 1. Backend CI/CD Pipeline
**File:** `valuex-backend/.github/workflows/backend-ci.yml`

**What it does:**
- Runs on every push to `main` or `develop` branches
- Runs on every pull request to `main` or `develop` branches
- Automatically:
  - Starts PostgreSQL 16 database
  - Starts Redis 7 cache
  - Runs Maven tests
  - Builds JAR package
  - Generates test coverage reports
  - Checks code quality (Checkstyle)
  - Builds Docker image (main branch only)

**Status:** ✅ Active

---

### 2. AI CI/CD Pipeline
**File:** `valuex-ai/.github/workflows/ai-ci.yml`

**What it does:**
- Runs on every push to `main` or `develop` branches
- Runs on every pull request to `main` or `develop` branches
- Automatically:
  - Sets up Python 3.11 environment
  - Installs dependencies (FastAPI, pytest, etc.)
  - Lints code with Ruff
  - Checks code formatting with Ruff
  - Runs pytest tests with coverage (90% gate)
  - Builds Docker image (main branch only)

**Status:** ✅ Active

---

### 3. Mobile CI Pipeline
**File:** `valuex-mobile/.github/workflows/mobile-ci.yml`

**Status:** ✅ Already implemented, validated, no changes needed

---

## How to Use

### Before Pushing Code

**Backend:**
```bash
cd valuex-backend
mvn clean test              # Run all tests locally
mvn clean package           # Build JAR
```

**AI:**
```bash
cd valuex-ai
pip install -r requirements.txt -r requirements-dev.txt
ruff check .                # Lint check
pytest --cov=app            # Run tests with coverage
```

### After Pushing

1. Go to **GitHub** → Your Repository
2. Click **Actions** tab
3. See the workflow running in real-time
4. Click on the workflow run to see details
5. Workflow status appears as:
   - 🟡 **Pending** - Running
   - ✅ **Passed** - All checks passed
   - ❌ **Failed** - Something went wrong

### View Build Artifacts

After workflow completes successfully:
1. Click on the workflow run
2. Scroll to **"Artifacts"** section
3. Download:
   - **Backend:** `valuex-backend-jar` (compiled JAR), `backend-coverage-report` (test coverage)
   - **AI:** `ai-coverage-report` (test coverage)

---

## Workflow Requirements

### Environment Variables (Auto-configured)

**Backend (in workflow):**
- `DATABASE_URL=jdbc:postgresql://localhost:5432/valuex_test`
- `DATABASE_USERNAME=test_user`
- `DATABASE_PASSWORD=test_password`
- `REDIS_HOST=localhost`
- `REDIS_PORT=6379`
- `SPRING_PROFILES_ACTIVE=test`

**AI (in workflow):**
- `PYTHONPATH=./`

### GitHub Secrets (None Required Yet)

Current pipelines use no secrets. Future enhancements (container registry push) will require:
- `DOCKER_USERNAME`
- `DOCKER_PASSWORD`
- `REGISTRY_URL`

---

## Troubleshooting

### Workflow Failed?

**Check these in order:**

1. **View the failed step:**
   - Click workflow run → Failed step
   - Read error message

2. **Common issues:**

   | Error | Fix |
   |-------|-----|
   | Tests fail | Check code locally: `mvn test` or `pytest` |
   | Build fails | Verify dependencies: `mvn clean install` or `pip install -r requirements*.txt` |
   | Docker build fails | Ensure Dockerfile exists in repo root |
   | Coverage below threshold | Add tests (Backend: JaCoCo, AI: 90% required) |
   | Checkstyle fails | Run `mvn checkstyle:check` locally to see violations |
   | Ruff fails | Run `ruff check .` locally |

3. **Need help?**
   - Check the action logs in GitHub
   - Review the LLD: `Documents/LLD/Sprint-0-Foundation-Architecture-LLD.md`
   - Check implementation plan: `Documents/US-Implementation-Plans/S0-006-Implementation-Plan.md`

---

## Workflow Execution Times

| Pipeline | Typical Duration | Max Duration |
|----------|-----------------|--------------|
| Backend CI | 8-10 min | 15 min |
| AI CI | 3-4 min | 8 min |
| Mobile CI | 15-20 min | 30 min |

---

## GitHub Actions Configuration

### For Repo Admins

**Enable branch protection (recommended):**
1. Settings → Branches
2. Add rule for `main` branch
3. ✓ Require status checks to pass before merging
4. Select `test` job as required check
5. ✓ Dismiss stale pull request approvals when new commits are pushed

**Result:** PRs can only be merged after CI passes ✅

---

## Files Modified

| File | Status | Commit |
|------|--------|--------|
| `valuex-backend/.github/workflows/backend-ci.yml` | ✅ Added | fac525f |
| `valuex-ai/.github/workflows/ai-ci.yml` | ✅ Added | fa773b6 |

---

## What's NOT Included (Deferred)

❌ **Docker registry push** - Deferred to container registry story  
❌ **Deployment pipelines** - Deferred to deployment story  
❌ **SonarQube integration** - Deferred to code quality story  
❌ **Web CI/CD** - Blocked by S0-003 (Admin Web Setup)  

---

## Key Features

✅ **Automated Testing** - Runs on every push/PR  
✅ **Multiple Services** - PostgreSQL, Redis for backend tests  
✅ **Quality Gates** - Checkstyle, Ruff, 90% coverage enforcement  
✅ **Artifact Storage** - Coverage reports, JAR files archived  
✅ **Docker Support** - Image builds on main branch  
✅ **Fast** - Dependency caching for quick runs  
✅ **Smart Cancellation** - Outdated runs automatically cancelled  
✅ **Minimal Permissions** - Read-only access (no write/admin)

---

## Next Steps

### For Developers
1. Push code to a branch
2. Create a PR
3. Watch the CI pipeline run
4. Fix any failures
5. Merge after CI passes

### For Team Leads
1. Enable branch protection on main branches (optional)
2. Configure Slack/email alerts (optional, future)
3. Monitor workflow execution times
4. Report any consistent failures

### For DevOps/Infra
1. Set up Docker registry (future story)
2. Configure deployment pipelines (future story)
3. Integrate SonarQube dashboard (future story)

---

## Questions?

📖 **Read:** `Documents/US-Implementation-Plans/S0-006-IMPLEMENTATION-COMPLETE.md`  
📋 **Plan:** `Documents/US-Implementation-Plans/S0-006-Implementation-Plan.md`  
📘 **Design:** `Documents/LLD/Sprint-0-Foundation-Architecture-LLD.md`

---

**Last Updated:** 2026-11-03  
**Status:** ✅ Complete and Validated
