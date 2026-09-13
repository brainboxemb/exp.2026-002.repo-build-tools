# moonrepo real SCAD consumer qualification

This follow-up qualifies the broadened repository-orchestration direction against a
real `brainboxemb/template.scad-project` consumer rather than a synthetic task
fixture.

## Purpose

The proof answers four questions:

1. Can moon own the high-level `scad.build` / `scad.verify` task graph without
   absorbing OpenSCAD/SCons internals?
2. Can an exact moon cache hit hydrate the complete logical task result, including
   human-readable execution logs and SCAD decision telemetry, without rerunning the
   domain command?
3. When the high-level SCAD task really must execute, does SCons remain the
   fine-grained authority for `BUILT`, `CACHE_RESTORED`, `CURRENT` and `ERROR`?
4. Can a verification-only source change execute only verification while leaving
   the normal build task cached?

## Exact inputs

- consumer: `brainboxemb/template.scad-project`
- consumer revision: `be344c59d310747a480a1606d81ec7534a5b99c3`
- SCAD tool revision: `0469bc14afe1600484d20441269b06608b8f6179`
- toolchain: `ghcr.io/brainboxemb/scad-toolchain:v0.4.1`
- moon: `2.5.4`

The template is cloned into a temporary workspace. The experiment overlays the
newer SCAD tool revision and aligns the template's tool pin/workflow refs only in
that temporary workspace. No production consumer repository is modified.

## Task model

```text
scad.build
  inputs: project config + dsg/** + exact tool stamp
  outputs: bld + evidence/scad-build

scad.verify
  deps: scad.build
  inputs: verification sources/scripts + exact tool stamp
  outputs: vrf/out + evidence/scad-verify
```

`scad.build` calls existing `tool.scad-project` commands. `scad.verify` uses the
existing verification-only `functional-verify` interface after the build producer
has supplied normal build output. This deliberately exposes an adapter question:
the current reusable Verify workflow also invokes the normal `verify` command,
which rebuilds configured outputs. A future moon-backed adapter should avoid that
duplicate high-level ownership rather than reproduce it.

## Required evidence

Each executed high-level task produces:

```text
evidence/<task>/execution.json
evidence/<task>/execution.log
evidence/<task>/domain/*.json
```

The domain directory contains the original SCAD/SCons decision reports. Moon caches
and hydrates the complete declared output, so a cache hit must restore logs and
telemetry together with generated files.

## Important cache boundary

This proof does **not** claim that moon replaces SCons cross-revision caching.

Moon supplies exact high-level task hashing and output hydration. If a SCAD source
change invalidates the high-level task, that task executes again and SCons remains
responsible for target-level reuse. Persisting SCons state/cache across fresh CI
workers remains a separate domain-cache concern and must be qualified separately.
