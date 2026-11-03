# S0-006 — CI/CD Pipeline: Testing Guide

How to verify the GitHub Actions pipelines. See the [Implementation Plan](../US-Implementation-Plans/S0-006-Implementation-Plan.md)
for what each one does.

## Backend (`valuex-backend`)

1. Open a pull request against `main` and confirm the **Backend CI / build** check starts (no path filter applies).
2. Expected steps: Build, test and verify → SonarQube scan (or "Sonar scan skipped") → Upload JAR → Upload coverage.
3. Locally reproduce: `mvn -B clean verify` (needs Docker for Testcontainers). Checkstyle violations, a failing test or
   coverage below 65% each fail the job.
4. Negative test: introduce a Checkstyle violation on a throwaway branch; the job must fail in `validate`.
5. Sonar (after configuration): add secret `SONAR_TOKEN` and variable `SONAR_HOST_URL`; re-run. The scan step runs and
   fails the job if the quality gate fails. Without them the run shows the warning
   "SonarQube scan skipped" and passes.
6. On `main` only, the `docker` job downloads the JAR artifact and builds the image.

## AI (`valuex-ai`)

1. Open a PR; confirm **AI CI/CD / test** runs.
2. Locally: `pip install -r requirements.txt -r requirements-dev.txt && ruff check . && ruff format --check . && pytest`.
3. Coverage below 90% fails the job (from `pyproject.toml`). Ruff findings are reported but do not fail it yet.

## Web (`valuex-web`)

1. While the repo has no `package.json`: the job passes and shows the warning
   "No package.json found - web CI steps skipped".
2. After the app is scaffolded: confirm lint, test and build run and `valuex-web-dist` is uploaded. Set the repository
   variable `API_BASE_URL` if the build needs it.

## Mobile (`valuex-mobile`)

Open a PR and confirm: PR-title check, Analyze (`flutter analyze --fatal-infos`), Test with the 85% coverage gate,
store-compliance check, and the Android and iOS build jobs.
