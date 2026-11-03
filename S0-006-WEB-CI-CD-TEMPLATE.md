# Web CI/CD Pipeline - Template & Implementation Guide

**Status:** ⏳ READY (awaiting S0-003: Admin Web Setup)  
**Story:** S0-006: CI/CD Pipeline  
**Date:** 2026-11-03

---

## Overview

This document provides the Web CI/CD pipeline template for the ValueX admin web application. The workflow will be activated once the `valuex-web` repository is created as part of S0-003: Admin Web Setup.

---

## Web CI/CD Pipeline Specification

### Location
**File:** `valuex-web/.github/workflows/web-ci.yml`

### Trigger Configuration
```yaml
on:
  push:
    branches: [main, develop]
    paths:
      - 'valuex-web/**'
      - '.github/workflows/web-ci.yml'
  pull_request:
    branches: [main, develop]
    paths:
      - 'valuex-web/**'
```

**Triggers On:**
- Push to main or develop branches (web-related changes only)
- Pull requests to main or develop branches
- Manual workflow dispatch (optional)

### Technology Stack
| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 18+ |
| Build Tool | Vite | 5+ |
| Package Manager | npm | 10+ |
| Node Runtime | Node.js | 20 LTS |
| Testing | Vitest/Jest | Latest |
| Linting | ESLint | 8+ |
| Formatting | Prettier | 3+ |

---

## Workflow Jobs

### Job 1: Test & Build

**Runs On:** `ubuntu-latest`

**Steps:**

1. **Checkout Code**
   - Uses: `actions/checkout@v4`
   - Fetches repository code

2. **Set up Node.js**
   - Uses: `actions/setup-node@v4`
   - Version: `20` (LTS)
   - Caching: `npm`
   - Cache path: `valuex-web/package-lock.json`
   - **Benefit:** ~50% faster builds (cached node_modules)

3. **Install Dependencies**
   - Command: `npm ci`
   - **Why `npm ci`?** Clean install, reproducible builds (not `npm install`)
   - Installs from `package-lock.json`

4. **Run Linter**
   - Command: `npm run lint`
   - Tool: ESLint
   - `continue-on-error: true` - Warnings don't block CI
   - Checks code quality

5. **Run Tests**
   - Command: `npm run test`
   - Tool: Vitest or Jest
   - Executes unit and integration tests
   - **Fails if tests fail**

6. **Build Application**
   - Command: `npm run build`
   - Tool: Vite
   - Environment: `VITE_API_BASE_URL` from GitHub secrets
   - Output: `valuex-web/dist/` folder
   - **Fails if build fails**

7. **Upload Build Artifact**
   - Name: `valuex-web-dist`
   - Path: `valuex-web/dist/`
   - Retention: 5 days
   - Used by deploy job and manual staging

8. **Upload Coverage Report** (if coverage collected)
   - Name: `web-coverage-report`
   - Path: `valuex-web/coverage/`
   - Retention: 5 days
   - Useful for code quality tracking

**Estimated Duration:** 5-8 minutes

---

### Job 2: Build Docker Image

**Runs On:** `ubuntu-latest`

**Conditions:**
- `needs: test` - Only after test job succeeds
- `github.ref == 'refs/heads/main'` - Only on main branch
- `success()` - Only if test job succeeded

**Steps:**

1. **Checkout Code**
   - Fetches repository code

2. **Set up Docker Buildx**
   - Uses: `docker/setup-buildx-action@v3`
   - Enables advanced Docker build features
   - Better caching and multi-platform builds

3. **Build Docker Image**
   - Command: `docker build -t valuex-web:${SHA} .`
   - Tags:
     - `valuex-web:<git-sha>` - Unique per commit
     - `valuex-web:latest` - Always points to latest build
   - Dockerfile should:
     - Use Node 20 base image
     - Build with `npm run build`
     - Copy `dist/` to web server root (nginx)
     - Expose port 3000 or 80

4. **Verify Docker Image**
   - Command: `docker images | grep valuex-web`
   - Confirms image built successfully

**Estimated Duration:** 2-3 minutes

**Note:** Docker images are built locally. Push to registry (Docker Hub, Harbor, ECR) is deferred to container registry story.

---

### Job 3: Deploy (Placeholder)

**Runs On:** `ubuntu-latest`

**Conditions:**
- `needs: test` - Only after test job succeeds
- `github.ref == 'refs/heads/main'` - Only on main branch
- `success()` - Only if test job succeeded

**Current Status:** ⏳ Placeholder implementation

**Future Implementation:**
- Download build artifact from test job
- Deploy to staging environment
- Run smoke tests
- Deploy to production (with manual approval)

---

## Environment Variables & Secrets

### Required GitHub Secrets

**For Web CI/CD:**
- `API_BASE_URL` - Backend API URL (e.g., https://api.valuex.com)
  - Used in Vite build: `VITE_API_BASE_URL`
  - Keep different for dev/staging/prod

**For Future Deployment:**
- `STAGING_DEPLOY_KEY` - SSH key or deployment token
- `PROD_DEPLOY_KEY` - SSH key for production deployment
- `SLACK_WEBHOOK` - Slack notifications (optional)

### Configuration Steps

1. Go to GitHub repository settings
2. Navigate to **Settings → Secrets and variables → Actions**
3. Add new secret:
   - Name: `API_BASE_URL`
   - Value: `https://api.valuex.com` (for main branch)

---

## Dockerfile for Web

**Recommended Dockerfile** (place in `valuex-web/Dockerfile`):

```dockerfile
# Build stage
FROM node:20-alpine as builder

WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# Build environment - use production API
ARG VITE_API_BASE_URL=https://api.valuex.com
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

RUN npm run build

# Production stage
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx config (optional)
COPY nginx.conf /etc/nginx/conf.d/

# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

---

## Integration with S0-006

### Phase 4: Web CI/CD Implementation

**Prerequisite:** S0-003 must complete first (Admin Web Setup creates valuex-web repo)

**When S0-003 Completes:**

1. Create `.github/workflows/` directory in valuex-web
2. Copy `web-ci.yml` template from S0-006 deliverables
3. Update any project-specific configurations (Node version, package manager, etc.)
4. Add GitHub secrets (`API_BASE_URL`)
5. Test workflow with first PR
6. Enable branch protection on main

**Timeline:** Estimated 30 minutes for integration

---

## Pipeline Execution Flow

```
GitHub Event (push/PR)
        ↓
   Path Filter
   (valuex-web/*)
        ↓
   test Job (ubuntu-latest)
   ├─ Setup Node 20
   ├─ npm ci (install)
   ├─ npm run lint
   ├─ npm run test
   ├─ npm run build (Vite)
   ├─ Upload dist/ artifact
   └─ Upload coverage/
        ↓
   If: main branch && test succeeded
   │
   ├─→ build-docker Job
   │   ├─ Setup Docker Buildx
   │   ├─ docker build -t valuex-web:SHA
   │   ├─ docker tag valuex-web:latest
   │   └─ Verify image
   │
   └─→ deploy Job (placeholder)
       ├─ Download dist/ artifact
       └─ Deploy to staging
```

---

## Performance Expectations

| Phase | Duration | Notes |
|-------|----------|-------|
| Setup | 1-2 min | Node cache hit |
| Install | 1-2 min | npm ci with cache |
| Lint | 1 min | ESLint |
| Test | 1-3 min | Unit tests |
| Build | 2-3 min | Vite build |
| Docker | 1-2 min | Buildx |
| **Total** | **5-8 min** | Main branch only |

---

## Best Practices Implemented

✅ **Dependency Caching** - npm cache from package-lock.json  
✅ **Concurrency Control** - Cancel outdated runs  
✅ **Path Filtering** - Only run on web changes  
✅ **Artifact Retention** - 5 days (manage storage)  
✅ **Error Handling** - continue-on-error for linting  
✅ **Environment Isolation** - Separate test/prod configs  
✅ **Minimal Permissions** - Read-only access  
✅ **Pinned Actions** - All versions pinned for stability  
✅ **Multi-stage Build** - Docker layers optimized  
✅ **Health Checks** - Docker image includes health check  

---

## What's NOT Included (Deferred)

- ⏳ **Docker Registry Push** - Deferred to container registry story
- ⏳ **Deployment Automation** - Full CD pipeline deferred
- ⏳ **SonarQube Integration** - Code quality dashboard deferred
- ⏳ **E2E Testing** - Cypress/Playwright tests deferred
- ⏳ **Security Scanning** - SAST/dependency checks deferred

---

## Deployment Stages (Future Enhancements)

### Stage 1: Staging (Immediate after S0-006)
```
PR to develop → CI passes → Auto-deploy to staging
```

### Stage 2: Production (Requires approval)
```
Merge to main → CI passes → Manual approval → Deploy to prod
```

### Stage 3: Rollback
```
Previous version maintained in registry
Quick rollback available on demand
```

---

## Team Onboarding

### For Web Developers

**Local Equivalent Commands:**
```bash
cd valuex-web

npm ci                    # Install dependencies (equivalent to CI)
npm run lint              # Run linter
npm run test              # Run tests
npm run build             # Build for production
npm run dev               # Local development server
```

**Before Pushing:**
```bash
npm run lint              # Fix: npm run lint -- --fix
npm run test              # Ensure all tests pass
npm run build             # Verify build succeeds
```

### For DevOps Engineers

**Monitor Workflow:**
1. Repository → Actions tab
2. Select "Web CI/CD" workflow
3. View runs and logs
4. Download artifacts

**Docker Image Tagging:**
```
valuex-web:<commit-sha>     # Unique per commit
valuex-web:latest           # Always latest from main
```

---

## Integration Checklist

- [ ] S0-003: Admin Web Setup completes
- [ ] valuex-web repository created
- [ ] `.github/workflows/` directory created
- [ ] `web-ci.yml` file added to repository
- [ ] GitHub secrets configured (API_BASE_URL)
- [ ] package.json includes npm scripts:
  - `npm run lint`
  - `npm run test`
  - `npm run build`
- [ ] Dockerfile created
- [ ] First PR submitted
- [ ] CI workflow runs successfully
- [ ] Build artifacts downloaded and verified
- [ ] Branch protection enabled

---

## Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| npm ci fails | Cache miss or lock file mismatch | Run `npm ci` locally to verify |
| Build fails | Missing env variable | Check GitHub secrets: `API_BASE_URL` |
| Tests fail | Code issues | Fix tests locally before pushing |
| Lint errors | Code style | Run `npm run lint -- --fix` |
| Docker build fails | Missing Dockerfile | Create Dockerfile with Node base image |
| Artifact upload fails | Path incorrect | Verify `dist/` folder path in build |

---

## References

- [Vite Documentation](https://vitejs.dev/)
- [Node.js with GitHub Actions](https://docs.github.com/en/actions/using-nodejs-with-github-actions)
- [Docker Build Action](https://github.com/docker/build-push-action)
- [S0-006: CI/CD Pipeline](../S0-006-FINAL-REPORT.md)
- [LLD Sprint 0 §7.4](../LLD/Sprint-0-Foundation-Architecture-LLD.md)

---

## Next Steps

1. **Complete S0-003** - Admin Web Setup
2. **Copy Template** - Use web-ci-template.yml from S0-006 deliverables
3. **Customize** - Update for specific project needs
4. **Configure Secrets** - Add API_BASE_URL and other required secrets
5. **Test** - Submit first PR and verify workflow execution
6. **Enable Protection** - Set up branch protection on main

---

## Summary

✅ Web CI/CD workflow template created  
✅ Ready to be deployed when S0-003 completes  
✅ Follows same patterns as Backend and AI pipelines  
✅ Includes Docker support and staging deployment placeholder  
✅ Documentation comprehensive and ready for team

**Status:** ⏳ Ready for S0-003 integration

---

**Document Version:** 1.0  
**Created:** 2026-11-03  
**Status:** Template Ready  
**Blocking Issue:** S0-003 (Admin Web Setup) must complete first
