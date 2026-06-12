# Dependency Upgrade Plan — ConnectedVCS Tools

> **Generated**: June 12, 2026
> **Repository**: COG-GTM/leidos-connectedvcs-tools
> **Java Target**: 1.8 (all modules except Spring Boot services)

---

## Executive Summary

The ConnectedVCS Tools monorepo contains **12 Maven modules** with a shared parent POM. The dependency landscape has three distinct tiers:

| Tier | Modules | Key Concern |
|------|---------|-------------|
| **Legacy Core** (parent-inherited) | lib-asn1c, asn1decoder, mapencoder, timencoder, rgaencoder, message-builder, ISDcreator, TIMcreator, message-validator | Jersey 1.x / Jackson 1.x / JBoss Netty 3.x — all **end-of-life** with known CVEs |
| **Spring Boot Services** | map-georeferencing, map-services-proxy | Spring Boot **2.7.18 is EOL** — no more security patches |
| **Abandoned Module** | private-resources | CAS client 3.1.10 under dead `org.jasig.cas` groupId |

**Bottom line:** 7 dependencies have known CVEs or are EOL with unpatched vulnerabilities. The highest-priority work is replacing the EOL libraries (Jackson 1.x, JBoss Netty 3.x, Jersey 1.x) and upgrading Spring Boot from 2.7 → 3.x.

---

## Project Structure

```
leidos-connectedvcs-tools/
├── fedgov-cv-parent/              ← Parent POM (dependency management)
├── fedgov-cv-lib-asn1c/           ← Core ASN.1 library (jar)
├── fedgov-cv-asn1decoder/         ← ASN.1 decoder (jar)
├── fedgov-cv-mapencoder/          ← MAP encoder (jar)
├── fedgov-cv-timencoder/          ← TIM encoder (jar)
├── fedgov-cv-rgaencoder/          ← RGA encoder (jar)
├── fedgov-cv-message-builder/     ← Message builder (jar, web-fragment)
├── fedgov-cv-ISDcreator-webapp/   ← ISD Creator (war)
├── fedgov-cv-TIMcreator-webapp/   ← TIM Creator (war)
├── fedgov-cv-message-validator-webapp/ ← Validator (war)
├── fedgov-cv-map-georeferencing/  ← Georef REST API (war, Spring Boot 2.7.18)
├── fedgov-cv-map-services-proxy/  ← Map proxy (war, Spring Boot 2.7.18)
└── private-resources/             ← Private resources (war, stale)
```

### Module Dependency Graph

```
lib-asn1c ──┬── asn1decoder ──┬── timencoder ──┐
            │                 │                │
            ├── mapencoder ───┤── rgaencoder ──┤── message-builder ──┬── ISDcreator-webapp
            │                 │                │                     ├── TIMcreator-webapp
            │                 │                │                     └── message-validator-webapp
            │                 │                │
map-georeferencing (standalone, Spring Boot)   │
map-services-proxy (standalone, Spring Boot)   │
private-resources  (standalone, stale)         │
```

---

## Full Dependency Inventory

### A. Parent POM Managed Dependencies (`fedgov-cv-parent`)

| # | Dependency | Current Version | Latest Stable | Upgrade Type | CVEs / Risk | Notes |
|---|-----------|----------------|---------------|-------------|-------------|-------|
| 1 | `org.slf4j:slf4j-api` | 2.0.16 | **2.0.17** | Patch | None known | Safe upgrade |
| 2 | `org.slf4j:slf4j-log4j12` | 2.0.16 | **2.0.17** | Patch | None known | Bridge to Log4j 1.x; consider migrating to `slf4j-reload4j` or `log4j-slf4j2-impl` |
| 3 | `commons-io:commons-io` | 2.18.0 | **2.22.0** | Minor | None known | Safe upgrade |
| 4 | `commons-codec:commons-codec` | 1.17.1 | **1.22.0** | Minor | None known | Safe upgrade |
| 5 | `io.netty:netty-all` | 4.1.118.Final | **4.1.121.Final** | Patch | None known at current | Safe upgrade; 4.2.x is also available but may break APIs |
| 6 | `junit:junit` | 4.13.2 | 4.13.2 | — | None | **Latest JUnit 4**; consider migrating to JUnit 5 long-term |
| 7 | `org.mockito:mockito-core` | 3.12.4 | **5.18.0** | **Major** | None known | 5.x requires Java 11+; stay on **4.11.0** if constrained to Java 8 |
| 8 | `org.jasig.cas.client:cas-client-core` | 3.6.4 | 3.6.4 | — | None known | Latest in this line |
| 9 | `commons-collections:commons-collections` | 3.2.2 | 3.2.2 | — | CVE-2015-6420 fixed in 3.2.2 | Enforcer plugin bans < 3.2.2. Consider migrating to `commons-collections4` (4.5.0) |

### B. Parent POM Managed Plugins

| # | Plugin | Current Version | Latest Stable | Upgrade Type | Notes |
|---|--------|----------------|---------------|-------------|-------|
| 10 | `maven-compiler-plugin` | 3.13.0 | **3.14.0** | Minor | Safe; 4.x is beta |
| 11 | `maven-war-plugin` | 3.4.0 | **3.4.0** | — | Already latest stable |
| 12 | `maven-resources-plugin` | 3.3.1 | **3.3.1** | — | Already latest stable |
| 13 | `maven-surefire-plugin` | 3.5.2 | **3.5.2** | — | Already latest stable |
| 14 | `jacoco-maven-plugin` | 0.8.12 | **0.8.13** | Patch | Safe upgrade |

### C. Core Library Dependencies (lib-asn1c, asn1decoder, mapencoder, timencoder, rgaencoder)

| # | Dependency | Current | Latest Stable | Upgrade | CVEs / Risk | Used In |
|---|-----------|---------|---------------|---------|-------------|---------|
| 15 | `log4j-api` | 2.23.1 | **2.26.0** | Minor | None at 2.23.1 | All core modules |
| 16 | `log4j-core` | 2.23.1 | **2.26.0** | Minor | None at 2.23.1 (Log4Shell was 2.0–2.17.0) | All core modules |
| 17 | **`org.jboss.netty:netty`** | **3.2.10.Final** | 3.2.10.Final | — | **CVE-2019-16869** (HTTP smuggling, CVSS 7.5), **CVE-2019-20444** (CVSS 9.1), **CVE-2019-20445** (CVSS 9.1), **CVE-2021-21290** (CVSS 5.5), **CVE-2021-21295** (CVSS 5.9) | asn1decoder, mapencoder, timencoder, rgaencoder |
| 18 | `javax.xml.bind:jaxb-api` | 2.3.1 | 2.3.1 | — | None known | asn1decoder |

### D. Message Builder Dependencies

| # | Dependency | Current | Latest Stable | Upgrade | CVEs / Risk | Notes |
|---|-----------|---------|---------------|---------|-------------|-------|
| 19 | **`commons-lang:commons-lang`** | **2.5** | 2.6 | Patch | None known | **Superseded** by `org.apache.commons:commons-lang3` (3.17.0). commons-lang 2.x is unmaintained. |
| 20 | **`org.codehaus.jackson:jackson-mapper-asl`** | **1.9.13** | 1.9.13 | — | **CVE-2017-7525** (RCE via deserialization, CVSS 9.8), **CVE-2017-15095** (CVSS 9.8), **CVE-2017-17485** (CVSS 9.8), **CVE-2018-5968** (CVSS 8.1), **CVE-2018-7489** (CVSS 9.8), **CVE-2019-10172** (CVSS 7.5) | **EOL since 2013**. Must migrate to `com.fasterxml.jackson` (2.18.x). |
| 21 | **`com.sun.jersey:jersey-*`** | **1.19.3** | 1.19.4 | Patch | None critical known | **EOL**. Jersey 1.x superseded by `org.glassfish.jersey` 2.x/3.x. |
| 22 | `jersey-test-framework-*` | 1.18.1 | 1.19.4 | Minor | None | EOL with Jersey 1.x |
| 23 | **`javax.servlet:servlet-api`** | **2.5** | 2.5 | — | None known | **Ancient**. Superseded by `javax.servlet-api` 4.0.1 / `jakarta.servlet-api` 6.x |
| 24 | `org.eclipse.jetty:jetty-*` | 9.4.54.v20240208 | 9.4.57.v20241219 (9.4 line), **12.0.21** (latest) | Patch / **Major** | CVE-2024-6763 (CVSS 3.7, header validation) in 9.4.x; multiple in older 9.4.x | 9.4.x is EOL (community support ended 2024). Jetty 10.x requires Java 11+, 11.x/12.x requires Java 17+. |

### E. Webapp-Specific Dependencies

| # | Dependency | Current | Latest Stable | Upgrade | CVEs / Risk | Used In |
|---|-----------|---------|---------------|---------|-------------|---------|
| 25 | `commons-fileupload:commons-fileupload` | 1.5 | **1.6.0** | Minor | None at 1.5 (CVE-2023-24998 fixed in 1.5) | message-validator |
| 26 | `javax.servlet:javax.servlet-api` | 3.0.1 | **4.0.1** | **Major** | None known | message-validator |

### F. Private Resources (Stale Module)

| # | Dependency | Current | Latest Stable | Upgrade | CVEs / Risk | Notes |
|---|-----------|---------|---------------|---------|-------------|-------|
| 27 | **`org.jasig.cas:cas-client-core`** | **3.1.10** | 3.1.10 | — | Multiple CVEs in older CAS libraries | **Wrong groupId**. Modern artifact is `org.jasig.cas.client:cas-client-core` 3.6.4 (already used by parent POM). |
| 28 | `maven-compiler-plugin` | 3.3 | **3.14.0** | **Major** | None | Very outdated |
| 29 | `maven-war-plugin` | 2.6 | **3.4.0** | **Major** | None | Very outdated |

### G. Spring Boot Services (map-georeferencing, map-services-proxy)

| # | Dependency | Current | Latest Stable | Upgrade | CVEs / Risk | Notes |
|---|-----------|---------|---------------|---------|-------------|-------|
| 30 | **`spring-boot-starter-parent`** | **2.7.18** | **3.5.3** | **Major** | Spring Boot 2.7.x is **EOL** (OSS support ended Nov 2023). Multiple Spring Framework / Spring Security CVEs patched only in 3.x. | Requires Java 17+, Jakarta EE migration (`javax.*` → `jakarta.*`). |
| 31 | `springdoc-openapi-ui` | 1.7.0 | **1.8.0** | Minor | None known | For Spring Boot 3.x, must migrate to `springdoc-openapi-starter-webmvc-ui` 2.x |
| 32 | `com.google.guava:guava` | 32.1.3-jre | **33.4.8-jre** | **Major** | CVE-2023-2976 (CVSS 7.1, temp file permission) fixed in 32.0.1 — current version is safe. | 33.x requires Java 8+ (compatible). Safe upgrade. |
| 33 | `software.amazon.awssdk:s3` | 2.32.31 | **2.46.7** | Minor | None known | Safe upgrade, backward-compatible within 2.x |
| 34 | `software.amazon.awssdk:apache-client` | 2.32.31 | **2.46.7** | Minor | None known | Keep in sync with S3 SDK |
| 35 | `software.amazon.awssdk:utils` | 2.32.31 | **2.46.7** | Minor | None known | Keep in sync with S3 SDK |
| 36 | `com.github.ben-manes.caffeine:caffeine` | 2.9.3 | **3.2.0** | **Major** | None known | 3.x requires Java 11+. Stay on 2.9.3 if Java 8 required; upgrade after Spring Boot 3.x migration. |
| 37 | `org.projectlombok:lombok` | 1.18.32 | **1.18.38** | Patch | None known | Safe upgrade |
| 38 | `org.junit.jupiter:junit-jupiter` | 5.9.3 | **5.12.2** | Minor | None known | Safe upgrade |
| 39 | `org.mockito:mockito-junit-jupiter` | 4.11.0 | **5.18.0** | **Major** | None known | 5.x requires Java 11+; upgrade alongside Mockito core |
| 40 | `com.squareup.okhttp3:okhttp` | (managed ~4.12.0) | **4.12.0** | — | None known | Latest stable 4.x; 5.x is alpha |
| 41 | `jetty-maven-plugin` | 9.4.54.v20240208 | See #24 | — | Same as Jetty above | |
| 42 | `maven-surefire-plugin` (proxy) | 3.0.0-M7 | **3.5.2** | Minor | None | Should align with parent POM version |

---

## Prioritized Upgrade List

### Priority 1 — Critical Security (CVEs present, immediate action)

| # | Action | Risk | Effort | Modules Affected |
|---|--------|------|--------|-----------------|
| **P1-1** | **Replace `org.codehaus.jackson:jackson-mapper-asl` 1.9.13 → `com.fasterxml.jackson:jackson-databind` 2.18.x** | 6 RCE CVEs (CVSS 9.8). Library EOL since 2013. | **High** — API changes between Jackson 1.x and 2.x. Need to update import paths (`org.codehaus.jackson` → `com.fasterxml.jackson`), annotation names, and ObjectMapper usage. | message-builder |
| **P1-2** | **Remove `org.jboss.netty:netty` 3.2.10.Final** | 5 CVEs (CVSS up to 9.1). Library EOL. | **Medium** — Already depends on `io.netty:netty-all` 4.1.x via parent. Verify no code references old `org.jboss.netty` classes; if so, migrate imports to `io.netty` equivalents. | asn1decoder, mapencoder, timencoder, rgaencoder |
| **P1-3** | **Fix `org.jasig.cas:cas-client-core` 3.1.10 → `org.jasig.cas.client:cas-client-core` 3.6.4** | Stale groupId, old version with potential auth bypass issues. | **Low** — Change groupId + version in private-resources POM. | private-resources |

### Priority 2 — EOL Frameworks (no more security patches)

| # | Action | Risk | Effort | Modules Affected |
|---|--------|------|--------|-----------------|
| **P2-1** | **Upgrade Spring Boot 2.7.18 → 3.x** | EOL; future Spring CVEs won't be backported. | **Very High** — Requires Java 17+, Jakarta EE namespace migration, Spring Security config changes, Jetty upgrade (10+). | map-georeferencing, map-services-proxy |
| **P2-2** | **Replace Jersey 1.x → Jersey 2.x (or JAX-RS alternative)** | Jersey 1.x EOL. No security patches. | **Very High** — Completely different API. `com.sun.jersey` → `org.glassfish.jersey`. Need to rewrite resource classes, filters, and injection. | message-builder, message-validator |
| **P2-3** | **Replace `commons-lang:commons-lang` 2.5 → `org.apache.commons:commons-lang3` 3.17.0** | Unmaintained. | **Medium** — Package rename `org.apache.commons.lang` → `org.apache.commons.lang3`. Many utility method signatures are compatible. | message-builder, message-validator |
| **P2-4** | **Upgrade `javax.servlet:servlet-api` 2.5 → `javax.servlet-api` 4.0.1** (or `jakarta.servlet-api` if moving to Jakarta) | Ancient API. | **Low** — Mostly compile-scope; API is backward-compatible. | message-builder |

### Priority 3 — Safe Upgrades (backward-compatible, no breaking changes)

| # | Action | Risk | Effort | Modules Affected |
|---|--------|------|--------|-----------------|
| **P3-1** | Upgrade `log4j-api` + `log4j-core` 2.23.1 → 2.26.0 | None | **Low** — Centralize version in parent POM property. | All core modules |
| **P3-2** | Upgrade `commons-io` 2.18.0 → 2.22.0 | None | **Low** — Update parent property. | Parent-managed |
| **P3-3** | Upgrade `commons-codec` 1.17.1 → 1.22.0 | None | **Low** — Update parent property. | Parent-managed |
| **P3-4** | Upgrade `slf4j-api` + `slf4j-log4j12` 2.0.16 → 2.0.17 | None | **Low** — Update parent property. | Parent-managed |
| **P3-5** | Upgrade `netty-all` 4.1.118.Final → 4.1.121.Final | None | **Low** — Update parent property. | Parent-managed |
| **P3-6** | Upgrade `jacoco-maven-plugin` 0.8.12 → 0.8.13 | None | **Low** — Update parent + proxy POM. | Parent, map-services-proxy |
| **P3-7** | Upgrade `commons-fileupload` 1.5 → 1.6.0 | None | **Low** | message-validator |
| **P3-8** | Upgrade `lombok` 1.18.32 → 1.18.38 | None | **Low** | map-services-proxy |
| **P3-9** | Upgrade AWS SDK 2.32.31 → 2.46.7 | None | **Low** — Keep all 3 artifacts in sync. | map-services-proxy |
| **P3-10** | Upgrade `guava` 32.1.3-jre → 33.4.8-jre | None | **Low** — Java 8 compatible. | map-georeferencing |
| **P3-11** | Upgrade `springdoc-openapi-ui` 1.7.0 → 1.8.0 | None | **Low** | map-georeferencing |
| **P3-12** | Upgrade `junit-jupiter` 5.9.3 → 5.12.2 | None | **Low** | map-services-proxy |
| **P3-13** | Align `maven-surefire-plugin` in proxy (3.0.0-M7 → 3.5.2) | None | **Low** | map-services-proxy |
| **P3-14** | Upgrade `javax.servlet-api` 3.0.1 → 4.0.1 | None | **Low** — backward-compatible. | message-validator |
| **P3-15** | Upgrade private-resources plugins (compiler 3.3→3.14.0, war 2.6→3.4.0) | None | **Low** | private-resources |

---

## Risk Assessment

### High Risk Upgrades

#### Jackson 1.x → 2.x Migration (P1-1)
- **Breaking changes**: All imports change from `org.codehaus.jackson` to `com.fasterxml.jackson`
- `ObjectMapper` API differences (method renames, new defaults)
- Annotation migration: `@JsonProperty`, `@JsonIgnore` etc. have new package paths
- **Testing**: Extensive — all serialization/deserialization paths must be regression-tested
- **Mitigation**: Jackson 2.x provides `jackson-mapper-asl` compatibility shim for transition

#### Spring Boot 2.7 → 3.x Migration (P2-1)
- **Java 17 required** — entire project currently targets Java 8
- **Jakarta EE namespace**: All `javax.*` imports → `jakarta.*` (servlet, validation, persistence)
- Spring Security: `WebSecurityConfigurerAdapter` removed; must use component-based config
- Jetty: Must upgrade from 9.x to 11.x+ (Jetty 9 is not compatible with Spring Boot 3.x)
- Caffeine: Must upgrade to 3.x (Java 11+)
- Springdoc: Must migrate from `springdoc-openapi-ui` 1.x to `springdoc-openapi-starter-webmvc-ui` 2.x
- **Testing**: Full integration test suite must pass
- **Mitigation**: Spring Boot provides a [migration guide](https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide) and OpenRewrite recipes

#### Jersey 1.x → 2.x Migration (P2-2)
- Complete API rewrite: `com.sun.jersey` → `org.glassfish.jersey`
- JAX-RS version change: JAX-RS 1.1 → JAX-RS 2.x
- Dependency injection changes: HK2 replaces custom Jersey DI
- `WebResource` → `WebTarget`, `ClientResponse` → `Response`
- Test framework completely different
- **Testing**: All REST endpoints and tests must be rewritten

### Medium Risk Upgrades

| Upgrade | Risk Factor |
|---------|------------|
| Remove JBoss Netty 3.x (P1-2) | Need to verify no code uses `org.jboss.netty` imports |
| commons-lang → commons-lang3 (P2-3) | Package rename; search-and-replace plus compile check |
| Mockito 3.x → 5.x | Requires Java 11+; defer until Java version is bumped |

### Low Risk Upgrades
All P3 items are backward-compatible within their major version lines.

---

## Recommended Upgrade Order

### Phase 1: Safe Patch/Minor Upgrades (1 PR)
*Can all be bundled into a single PR. No code changes required — just version bumps.*

1. Parent POM properties: `slf4j` 2.0.17, `commons-io` 2.22.0, `commons-codec` 1.22.0, `netty` 4.1.121.Final, `jacoco` 0.8.13
2. Centralize `log4j` version in parent POM property → 2.26.0 (currently hardcoded in each module)
3. Upgrade `commons-fileupload` 1.5 → 1.6.0
4. Upgrade `lombok` 1.18.32 → 1.18.38
5. Upgrade AWS SDK 2.32.31 → 2.46.7
6. Upgrade `guava` 32.1.3 → 33.4.8
7. Upgrade `springdoc-openapi-ui` 1.7.0 → 1.8.0
8. Upgrade `junit-jupiter` 5.9.3 → 5.12.2
9. Align `maven-surefire-plugin` in proxy: 3.0.0-M7 → 3.5.2
10. Upgrade `javax.servlet-api` 3.0.1 → 4.0.1 in message-validator
11. Upgrade private-resources plugins (compiler 3.3→3.14.0, war 2.6→3.4.0)

### Phase 2: Remove JBoss Netty 3.x (1 PR)
1. Search codebase for `org.jboss.netty` imports
2. If found: migrate to `io.netty` equivalents (already a dependency)
3. Remove `org.jboss.netty:netty` from asn1decoder, mapencoder, timencoder, rgaencoder POMs
4. Run full test suite

### Phase 3: Fix Private Resources CAS Client (1 PR)
1. Change `org.jasig.cas:cas-client-core:3.1.10` → `org.jasig.cas.client:cas-client-core` (inherits 3.6.4 from parent)
2. Verify web.xml filter class references are compatible

### Phase 4: Jackson 1.x → 2.x Migration (1 PR)
1. Replace `org.codehaus.jackson:jackson-mapper-asl` with `com.fasterxml.jackson.core:jackson-databind` 2.18.x
2. Update all imports: `org.codehaus.jackson` → `com.fasterxml.jackson`
3. Update `ObjectMapper` usage and annotations
4. Add `jackson-databind` to parent POM `dependencyManagement`
5. Full regression test

### Phase 5: commons-lang → commons-lang3 (1 PR)
1. Replace `commons-lang:commons-lang:2.5` with `org.apache.commons:commons-lang3:3.17.0`
2. Update imports: `org.apache.commons.lang.*` → `org.apache.commons.lang3.*`
3. Check for API differences (most methods are compatible)

### Phase 6: Jersey 1.x → 2.x Migration (1–2 PRs)
1. Replace `com.sun.jersey:jersey-*` 1.19.x with `org.glassfish.jersey:jersey-*` 2.x
2. Rewrite JAX-RS resource classes, providers, filters
3. Update test framework
4. Update `web.xml` servlet configurations
5. Extensive testing

### Phase 7: Spring Boot 3.x Migration (separate PRs per service)
*Prerequisite: Upgrade Java target from 8 → 17 for these two modules.*

**PR 7a: map-georeferencing**
1. Update `spring-boot-starter-parent` to 3.5.x
2. Jakarta EE namespace migration (`javax.*` → `jakarta.*`)
3. Upgrade `springdoc-openapi-ui` → `springdoc-openapi-starter-webmvc-ui` 2.x
4. Upgrade Caffeine 2.9.3 → 3.2.0 (if used)
5. Test all endpoints

**PR 7b: map-services-proxy**
1. Update `spring-boot-dependencies` BOM to 3.5.x
2. Jakarta EE namespace migration
3. Upgrade Jetty plugin to 11.x+
4. Upgrade Spring Security config (remove deprecated `WebSecurityConfigurerAdapter`)
5. Upgrade Caffeine 2.9.3 → 3.2.0
6. Upgrade Mockito to 5.x
7. Test all endpoints

### Phase 8: Long-Term Modernization (optional)
1. Migrate JUnit 4 → JUnit 5 across legacy modules
2. Migrate Mockito 3.x → 5.x (requires Java 11+ across all modules)
3. Consider replacing `commons-collections` 3.2.2 with `commons-collections4` 4.5.0
4. Evaluate replacing Jetty 9.4.x with modern embedded server
5. Consolidate `servlet-api` versions across modules

---

## Suggested PR Grouping Summary

| PR | Contents | Risk | Est. Effort |
|----|----------|------|-------------|
| **PR 1** | Phase 1 — All safe version bumps | Low | 1–2 hours |
| **PR 2** | Phase 2 — Remove JBoss Netty 3.x | Low–Medium | 2–4 hours |
| **PR 3** | Phase 3 — Fix private-resources CAS client | Low | 30 min |
| **PR 4** | Phase 4 — Jackson 1.x → 2.x | High | 1–2 days |
| **PR 5** | Phase 5 — commons-lang → commons-lang3 | Medium | 2–4 hours |
| **PR 6** | Phase 6 — Jersey 1.x → 2.x | Very High | 2–3 days |
| **PR 7a** | Phase 7a — Spring Boot 3.x (georeferencing) | High | 1–2 days |
| **PR 7b** | Phase 7b — Spring Boot 3.x (services-proxy) | High | 1–2 days |
| **PR 8** | Phase 8 — JUnit 5 + Mockito 5 + cleanup | Medium | 1 day |

---

## Cross-Module Compatibility Notes

1. **Log4j version inconsistency**: Currently each module hardcodes `2.23.1`. Should be centralized in parent POM via a `<log4j.version>` property.
2. **Jetty version duplication**: `9.4.54.v20240208` is repeated in `message-builder`, `ISDcreator-webapp`, and `TIMcreator-webapp` dependencyManagement. Should be centralized in parent POM.
3. **Java version**: All legacy modules target Java 1.8. Spring Boot 3.x migration (Phase 7) requires Java 17 for those two modules only — they can be upgraded independently since they don't share the parent POM's Java target.
4. **Jackson conflict**: `message-builder` uses Jackson 1.x; `map-services-proxy` and `map-georeferencing` use Jackson 2.x (via Spring Boot). No conflict today because they're separate WARs, but consolidating on Jackson 2.x is necessary for any shared-library refactoring.
5. **AWS SDK BOM**: Consider importing the AWS SDK BOM (`software.amazon.awssdk:bom`) instead of pinning individual artifact versions.

---

## Appendix: Deprecated / Unmaintained Dependencies

| Dependency | Status | Replacement |
|-----------|--------|-------------|
| `org.codehaus.jackson:jackson-mapper-asl` | **EOL since 2013** | `com.fasterxml.jackson.core:jackson-databind` |
| `commons-lang:commons-lang` | **Unmaintained** | `org.apache.commons:commons-lang3` |
| `com.sun.jersey:jersey-*` | **EOL** | `org.glassfish.jersey:jersey-*` 2.x+ |
| `org.jboss.netty:netty` | **EOL** | `io.netty:netty-*` 4.x (already present) |
| `javax.servlet:servlet-api` 2.5 | **Superseded** | `javax.servlet:javax.servlet-api` 4.0.1 / `jakarta.servlet:jakarta.servlet-api` 6.x |
| `org.jasig.cas:cas-client-core` | **Wrong groupId** | `org.jasig.cas.client:cas-client-core` 3.6.4 |
| `org.springframework.boot` 2.7.x | **EOL Nov 2023** | `org.springframework.boot` 3.5.x |
| `org.eclipse.jetty` 9.4.x | **EOL 2024** | `org.eclipse.jetty` 11.x / 12.x |
