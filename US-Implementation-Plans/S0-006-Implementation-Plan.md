# S0-006: CI/CD Pipeline — Implementation Plan

**Sprint:** 0 · **Points:** 8 · **Dependency:** None · **Type:** infra
**Reference:** [Sprint-0 LLD §7](../LLD/Sprint-0-Foundation-Architecture-LLD.md)

## Scope

GitHub Actions CI for the four repositories. Each repository is its own git repo, so every workflow runs from the
repository root (no `valuex-*/` path prefixes, no `working-directory`).

| Repo | Workflow | PR | State |
|---|---|---|---|
| valuex-mobile | `mobile-ci.yml` | pre-existing | Reviewed, unchanged |
| valuex-backend | `backend-ci.yml` | [#47](https://github.com/VSPL-New/valuex-backend/pull/47) | Added; Sonar step waits on config |
| valuex-ai | `ai-ci.yml` | [#9](https://github.com/VSPL-New/valuex-ai/pull/9) | On `main`; PR fixes paths |
| valuex-web | `web-ci.yml` | [#2](https://github.com/VSPL-New/valuex-web/pull/2) | On `main`; PR fixes paths, skips until scaffolded |

## What each pipeline does

### Backend (`valuex-backend`)
- Triggers: push and pull request on `main`/`develop`.
- Job `build` (JDK 21, Maven cache, full git history): `mvn -B clean verify`. This runs, in order, Checkstyle
  (bound to `validate`, fails the build), the test suite (Testcontainers starts PostgreSQL; no CI service containers
  are needed), the JaCoCo report and the 65% line-coverage gate (bound to `verify`), and packaging.
- SonarQube: `mvn sonar:sonar -Dsonar.qualitygate.wait=true`. Runs only when the secret `SONAR_TOKEN` and the
  repository variable `SONAR_HOST_URL` are set; otherwise it emits a warning and is skipped. The pom's
  `sonar.host.url` is `http://localhost:9000`, which GitHub-hosted runners cannot reach, so the URL is passed in.
  Project key and exclusions come from the pom.
- Uploads the JAR and the JaCoCo report (5-day retention).
- Job `docker` (only on `main`): downloads the JAR from `build` and runs `docker build` (the Dockerfile copies
  `target/*.jar`). The image is not pushed anywhere yet.

### AI (`valuex-ai`)
- Triggers: push and pull request on `main`/`develop`.
- Python 3.11 with pip cache keyed on `requirements*.txt`; installs `requirements.txt` and `requirements-dev.txt`.
- `ruff check` and `ruff format --check` (both non-blocking for now), then `pytest`. Coverage options and the 90%
  gate (`fail_under = 90`) come from `pyproject.toml`.
- Uploads the HTML coverage report; on `main` builds the Docker image (not pushed).
- No Sonar step (not requested for this repo).

### Web (`valuex-web`)
- Triggers: push and pull request on `main`/`develop`.
- The repository currently holds only a README (the web app is S0-003). A `Detect web project` step checks for
  `package.json`; until it exists every build step is skipped with a warning, so the workflow stays green.
- Once scaffolded: Node 20, `npm ci`, `npm run lint`, `npm test`, `npm run build` (with `VITE_API_BASE_URL` taken
  from the repository variable `API_BASE_URL`), then uploads `dist/`.
- Not included: Docker build and deploy (there is no Dockerfile or deploy target yet). Add them with the web app.

### Mobile (`valuex-mobile`) — reviewed, no change
Runs on pull requests, pushes to `main` and manual dispatch (Flutter 3.47.5):
semantic PR-title check; generated-code freshness; `dart format --set-exit-if-changed`;
`flutter analyze --fatal-infos`; `flutter test --coverage`; 85% coverage gate; static store-compliance check;
debug Android APK build; debug iOS build (no codesign). It exceeds the LLD §7.3 baseline.

## Repository configuration required

| Repo | Item | Type | Purpose |
|---|---|---|---|
| valuex-backend | `SONAR_TOKEN` | Secret | Sonar analysis token |
| valuex-backend | `SONAR_HOST_URL` | Variable | Reachable SonarQube/SonarCloud URL |
| valuex-web | `API_BASE_URL` | Variable | Build-time API URL (once the app exists) |

Also recommended: branch protection on `main` requiring the CI checks.

## Deviations from LLD §7

| LLD | Implemented | Reason |
|---|---|---|
| Backend: Postgres/Redis service containers, `mvn test` | `mvn clean verify`, Testcontainers | Tests already provision PostgreSQL; `verify` is what enforces Checkstyle and the JaCoCo gate |
| Backend: no Sonar | Sonar scan with quality gate | Sonar is part of the team's pre-push standard |
| Web: build, Docker, deploy stub | Build only, skipped until scaffolded | No `package.json`, Dockerfile or deploy target exists yet |
| Monorepo-style paths | Repo-root paths | Four separate repositories |

## Known gaps / follow-ups

- Sonar server decision: SonarCloud, hosted SonarQube, or a self-hosted runner. Until `SONAR_TOKEN` and
  `SONAR_HOST_URL` are set, CI has no Sonar gate.
- AI and Web workflows reached `main` by a direct push before their PRs; PRs #9 and #2 correct them.
- GitHub reports Node 20 and `actions/setup-java@v4` deprecation warnings; Dependabot is configured for Actions.
- Container registry push, deployment (CD), and security scanning are out of scope for this story.
- Dependabot PRs on `valuex-ai` (#5–#8) bump action versions and may touch the same workflow.

## Acceptance criteria

- [x] Backend CI runs build, tests, Checkstyle, JaCoCo gate on every PR (verified green on PR #47).
- [ ] Backend Sonar scan active — blocked on server and token (see above).
- [x] AI CI green on PR #9 (pytest and the 90% coverage gate passed; Ruff is non-blocking).
- [x] Web CI present; real checks begin when the app is scaffolded.
- [x] Mobile CI reviewed; includes `flutter analyze --fatal-infos`.
