# SonarQube Scanning — Setup and Usage Guide

Static code analysis for ValueX backend. Checks for bugs, vulnerabilities, code smells, security hotspots, and coverage gaps.

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Docker Desktop | Any recent | Run SonarQube locally |
| Java 21 | Required | Maven build |
| Maven 3.9+ | Required | `mvn sonar:sonar` goal |
| SonarQube token | From console | Authentication |

---

## 1. Start SonarQube (Local)

```powershell
docker run -d --name sonarqube -p 9000:9000 sonarqube:community
```

Wait ~60 seconds, then open: **http://localhost:9000**

Default credentials: `admin` / `admin`
You will be forced to change the password on first login.

> **Persistent data across restarts** — use volumes:
> ```powershell
> docker run -d --name sonarqube -p 9000:9000 `
>   -v sonarqube_data:/opt/sonarqube/data `
>   -v sonarqube_logs:/opt/sonarqube/logs `
>   sonarqube:community
> ```

---

## 2. Create a Project in SonarQube Console

1. Login → **Create project → Manually**
2. **Project key:** `valuex-backend`
3. **Display name:** `ValueX Backend`
4. Click **Set up → Locally**
5. Click **Generate a token** → copy the token value

Keep the token — you will pass it as `-Dsonar.token=<value>` at scan time.

---

## 3. pom.xml Configuration (Already Applied)

The following plugin declaration and properties are already added to `valuex-backend/pom.xml`.

The plugin declaration is required — without it Maven cannot resolve the `sonar:sonar` shorthand goal:

```xml
<plugin>
    <groupId>org.sonarsource.scanner.maven</groupId>
    <artifactId>sonar-maven-plugin</artifactId>
    <version>${sonar-maven-plugin.version}</version>
</plugin>
```

The following properties are also set:

```xml
<sonar.projectKey>valuex-backend</sonar.projectKey>
<sonar.host.url>http://localhost:9000</sonar.host.url>
<sonar.coverage.jacoco.xmlReportPaths>
    ${project.build.directory}/site/jacoco/jacoco.xml
</sonar.coverage.jacoco.xmlReportPaths>
<sonar.exclusions>
    **/com/valuex/order/**,
    **/com/valuex/listing/**,
    **/com/valuex/shipping/**,
    **/com/valuex/search/**,
    **/com/valuex/plans/**,
    **/com/valuex/payment/**,
    **/com/valuex/returns/**,
    **/com/valuex/negotiation/**,
    **/com/valuex/dispute/**,
    **/com/valuex/escrow/**,
    **/com/valuex/cart/**,
    **/com/valuex/support/**,
    **/com/valuex/notification/**,
    **/ValuexApplication.java
</sonar.exclusions>
```

The exclusions match the JaCoCo exclusions — future-sprint domain stubs and the Spring Boot entry point are excluded from both coverage and Sonar analysis.

---

## 4. Running a Scan

### Local development

```powershell
cd C:\ValueX-Code\valuex-backend

mvn clean verify sonar:sonar "-Dsonar.token=YOUR_TOKEN_HERE"
```

`sonar.host.url` and `sonar.projectKey` are already in `pom.xml` — only the token needs to be passed on the command line. The double quotes around `-Dsonar.token` are required in PowerShell to prevent URL/colon parsing issues.

This single command:
1. Compiles the project
2. Runs all tests
3. Generates the JaCoCo XML coverage report
4. Uploads results to `http://localhost:9000`

Duration: ~2–3 minutes on first run.

Results appear at: **http://localhost:9000/dashboard?id=valuex-backend**

### Skip tests (re-scan only, tests already ran)

```powershell
mvn sonar:sonar -DskipTests "-Dsonar.token=YOUR_TOKEN_HERE"
```

Only do this when you have a fresh `target/` from a recent `mvn verify` — Sonar reads the existing JaCoCo XML.

### Override host for a remote SonarQube server

```powershell
mvn clean verify sonar:sonar "-Dsonar.token=YOUR_TOKEN" "-Dsonar.host.url=https://sonar.yourdomain.com"
```

> **PowerShell note:** Always wrap `-D` arguments that contain `://` URLs or special characters in double quotes. Without quotes, PowerShell splits the argument at the colon and Maven receives malformed tokens.

---

## 5. Understanding the Dashboard

| Category | What Sonar reports |
|---|---|
| **Bugs** | Definite logic errors — null dereferences, incorrect equals, resource leaks |
| **Vulnerabilities** | Security flaws — hardcoded secrets, insecure crypto, injection risks |
| **Security Hotspots** | Code requiring manual review — JWT handling, OTP validation, hashing |
| **Code Smells** | Maintainability issues — high complexity, duplicate blocks, dead code |
| **Coverage** | Line and branch % from JaCoCo (minimum 65% enforced in pom.xml) |
| **Duplications** | Copy-pasted blocks across source files |

### Quality Gate

The default Quality Gate passes when:
- No new bugs or vulnerabilities on new code
- Coverage on new code ≥ 80% (configurable)
- Duplication on new code ≤ 3%

A **failed Quality Gate** means the code should not proceed to production until the flagged issues are resolved.

### Severity levels

| Level | Action required |
|---|---|
| **Blocker** | Must fix before merging |
| **Critical** | Fix before merging |
| **Major** | Fix in the same sprint |
| **Minor / Info** | Fix opportunistically |

---

## 6. Security Hotspots (ValueX-specific)

These are not automatic bugs — they require a developer to review and mark as **Safe** or **To Review**:

| Hotspot area | Location | Expected verdict |
|---|---|---|
| JWT secret handling | `JwtTokenProvider.java` | Safe — loaded from env, not hardcoded |
| OTP storage | `UserRegistrationService.java` | Safe — stored in Redis with TTL, SHA-256 hashed |
| Aadhaar number hashing | `AadhaarVerificationService.java` | Safe — SHA-256 via `HashUtils`, never plain text |
| Google token validation | `HttpGoogleTokenAdapter.java` | Safe — validated server-side against Google API |
| Password encoder | `SecurityConfig.java` | Safe — BCrypt with default strength |

Mark hotspots as **Safe** with a comment explaining why. This clears them from the dashboard.

---

## 7. GitHub Actions — CI Integration

When a CI pipeline is added, add a Sonar scan step after tests:

```yaml
# .github/workflows/ci.yml

- name: Build and analyse
  env:
    SONAR_TOKEN: ${{ secrets.SONAR_TOKEN }}
    SONAR_HOST_URL: ${{ secrets.SONAR_HOST_URL }}
  run: |
    mvn clean verify sonar:sonar \
      -Dsonar.token=$SONAR_TOKEN \
      -Dsonar.host.url=$SONAR_HOST_URL
```

Add to GitHub repo secrets:
- `SONAR_TOKEN` — token generated from the SonarQube project
- `SONAR_HOST_URL` — URL of the production SonarQube server

The token and host URL must **never** be committed to `pom.xml` or `.env`.

---

## 8. Future Repos

Only `valuex-backend` has application code as of US-101. When other repos are implemented, add `sonar-project.properties` to each.

### valuex-web (React / TypeScript — when implemented)

```properties
# sonar-project.properties
sonar.projectKey=valuex-web
sonar.projectName=ValueX Web
sonar.sources=src
sonar.exclusions=**/node_modules/**,**/*.test.ts,**/*.spec.ts
sonar.javascript.lcov.reportPaths=coverage/lcov.info
sonar.host.url=http://localhost:9000
```

Run with:
```bash
npx sonar-scanner -Dsonar.token=YOUR_TOKEN
```

### valuex-mobile (Flutter — when implemented)

Install the Flutter Sonar plugin and add:
```properties
sonar.projectKey=valuex-mobile
sonar.projectName=ValueX Mobile
sonar.sources=lib
sonar.tests=test
sonar.exclusions=**/generated/**
sonar.dart.lcov.reportPaths=coverage/lcov.info
```

---

## 9. Stopping and Restarting SonarQube

```bash
# Stop
docker stop sonarqube

# Start again (data persists if using volumes)
docker start sonarqube

# Remove entirely and start fresh
docker rm -f sonarqube
```

---

## 10. Troubleshooting

**SonarQube not reachable at localhost:9000**
- Check Docker is running: `docker ps`
- Check logs: `docker logs sonarqube`
- SonarQube needs ~60s to start — wait and retry

**`Coverage report not found`**
- Run `mvn clean verify` first before `sonar:sonar` — the XML is generated during the `test` phase
- Confirm the file exists: `target/site/jacoco/jacoco.xml`

**`Authentication required` or `401 Unauthorized`**
- The token has expired or was not passed correctly
- Generate a new token from SonarQube → My Account → Security → Tokens
- Pass it with `-Dsonar.token=<value>`, not as an env var unless using the `SONAR_TOKEN` env var name specifically

**`Quality Gate failed — Coverage < 80%`**
- The default Quality Gate threshold for new code is 80%
- Our `pom.xml` enforces 65% at the bundle level, which is a lower bar
- Either raise test coverage or adjust the Quality Gate in SonarQube → Quality Gates

**Checkstyle fails before Sonar runs**
- Checkstyle runs at the `validate` phase, before tests
- Fix all checkstyle violations first: `mvn checkstyle:check`
- Sonar also reports style issues independently but does not block the build

---

## Quick Reference

| Task | Command |
|---|---|
| Start SonarQube | `docker start sonarqube` |
| Full scan (tests + upload) | `mvn clean verify sonar:sonar "-Dsonar.token=<token>"` |
| Scan only (skip tests) | `mvn sonar:sonar -DskipTests "-Dsonar.token=<token>"` |
| Open dashboard | http://localhost:9000/dashboard?id=valuex-backend |
| Check SonarQube logs | `docker logs sonarqube` |
| Stop SonarQube | `docker stop sonarqube` |
