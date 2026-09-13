# moonrepo real Java consumer qualification

This follow-up qualifies the repository-orchestration direction against the real
`brainboxemb/template.java-project` reference consumer.

## Requirement-derived boundary

The current Java engineering contract is not split by Maven phase. The reusable
Java tool deliberately defines one canonical Linux chain:

```text
Maven Wrapper verify
    ↓
unit tests
    ↓
canonical JAR
    ↓
Surefire evidence + provenance
```

Publication consumes that prepared canonical output without running Maven again.
For the current system, this makes `java.canonical` the meaningful first high-level
task boundary. A separate `java.unit-test` task would duplicate the same lifecycle
without an independent consumer or publication need.

The existing Windows responsibilities remain separate high-level qualification
concerns:

```text
Windows compatibility verify
Windows execution of the exact canonical Linux JAR
```

GitHub Actions still owns runner selection. Moon is not being treated as a
cross-runner CI scheduler.

## Exact proof inputs

- consumer: `brainboxemb/template.java-project`
- consumer revision: `a40f246eccbda2876d02497866de8ed855e21757`
- `tool.java-project`: `3dd4b176956513948c601ec9cf95f09f6f21712a`
- Java: Eclipse Temurin `8.0.504+1`
- Maven Wrapper/Maven: `3.3.4` / `3.9.16`
- moon: `2.5.4`

## Task model

```text
java.canonical
  inputs:
    project.yml / project.java.yml
    pom.xml + Maven Wrapper
    src/main/**
    src/test/**
    exact tool stamp

  outputs:
    bld/java
    evidence/java-canonical
```

The experiment adapter invokes the consumer's existing Maven Wrapper and writes a
small generic evidence envelope around the resulting JAR, Surefire reports and
toolchain provenance. This adapter is experiment-only. If adopted, the local
canonical action belongs in `tool.java-project`, not in Moon configuration.

## Acceptance cases

The harness checks:

1. cold `mvn verify` executes and yields one passing unit test;
2. exact rerun skips Maven;
3. deleted declared outputs hydrate from Moon without restoring undeclared
   `target/` state;
4. a fresh workspace hydrates JAR + test evidence + human-readable execution log;
5. README-only revision leaves `java.canonical` cached;
6. a test-only source change reruns canonical verify and increases the passing test
   count from one to two;
7. a main-source change reruns canonical verify and changes the JAR;
8. cached execution evidence keeps the original producer revision.

The last case is deliberately important for publication provenance: when a later
README-only revision reuses a prior build, the original producer SHA must not be
rewritten. A later publication/materialization envelope should record both the
producer revision and the revision for which the cached result was materialized.
