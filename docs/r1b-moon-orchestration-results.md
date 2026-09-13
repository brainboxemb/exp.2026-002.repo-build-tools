# R1b results — moonrepo orchestration and output hydration

Status: **qualified on Linux and native Windows**

## Why this follow-up changed the decision context

R1 selected native-thin for a deliberately narrow requirement: calculate affected
repository capabilities and leave all execution/cache behavior outside the generic layer.
The R1 result explicitly required reopening make/buy if generic task execution or
repository-level output caching became real requirements.

R2 requirements work in `meta.scad-projects` subsequently made these requirements explicit:

- high-level task execution;
- producer/consumer dependencies;
- reusable outputs on fresh CI workspaces;
- durable execution evidence and human-readable logs alongside generated outputs.

R1b therefore evaluated moon `2.5.4` for that expanded scope.

## Qualified head and CI

- experiment PR: #6 — `Evaluate moon orchestration and output hydration`;
- exact head: `8e267bba251533f4a1feb5eb7bfda353cfd87962`;
- workflow run: `34758272132`;
- Ubuntu 24.04: **success**;
- Windows Server 2025: **success**.

Evidence artifacts:

- Linux: `sha256:d8fda05b4c0863ecdeb4ab9080eee740f462160deee24b7573851e1a8679884b`;
- Windows: `sha256:8e34a857e748433420e9e864b465f51bfcd9715d5bffa3398b5bbf99b2a6dfef`.

## Test graph

The follow-up modeled a small real execution graph:

```text
product.build
    |
    v
publication
```

`product.build` declares source/tool inputs and `out/product` as output. The output contains:

```text
artifact.txt
evidence/execution.json
evidence/execution.log
```

`publication` consumes the product artifact, has its own release input and writes its own
package plus evidence/log output.

The commands are deliberately small Python domain adapters. The relevant architecture point is
that moon only sees the stable high-level command. A production SCAD task can invoke
`tool.scad-project`; SCons remains free to make all target-level dirty/current/cache decisions
inside that command.

## Qualified behavior

Both Linux and Windows passed all checks below.

| Check | Result |
| --- | --- |
| cold run executes producer | pass |
| cold run executes consumer | pass |
| exact rerun skips both commands | pass |
| deleted outputs hydrate from local moon cache without commands | pass |
| fresh workspace hydrates outputs without commands | pass |
| fresh workspace hydrates JSON evidence and human-readable execution logs | pass |
| product input change executes producer and downstream consumer | pass |
| release-only input change executes only consumer | pass |

Execution counters prove the cache behavior rather than relying only on moon console text.
After cold execution plus exact/local hydration, the first workspace still reported:

```text
product.build executions = 1
publication executions   = 1
```

A fresh workspace received only moon's documented portable cache directories:

```text
.moon/cache/hashes
.moon/cache/outputs
```

It then hydrated both tasks with **zero command executions**. After a product-input change and a
later release-only change, final fresh-workspace counters were:

```text
product.build executions = 1
publication executions   = 2
```

This proves producer and consumer invalidation remained selective after cache reuse.

## Representative Linux task output

Cold run:

```text
product.build executed count=1
publication executed count=1
Tasks: 2 completed
```

Exact rerun and both hydration cases reported two cached tasks. Product and publication command
counters remained unchanged.

After changing only release metadata, product.build remained cached while publication executed
again.

## Evidence/log conclusion

The declared output archive contained the domain-generated `execution.json` and
`execution.log`. Removing all generated output and hydrating from moon restored those exact files,
including in a separate fresh workspace.

This directly satisfies the R2 requirement that reusable generated output remain accompanied by
the evidence/log that explains the execution which originally produced it.

moon also maintains task stdout/stderr and task/hash state in its own cache model, but production
publication should still carry our explicit evidence envelope so generated branches remain
self-describing independently from moon's internal cache layout.

## Architecture conclusion

For the **expanded** requirements, the R1 recommendation changes.

Using native-thin beyond affected-query selection would now require us to build and maintain:

- a generic command/task runner;
- dependency scheduling;
- task hashing;
- output archiving;
- output hydration;
- portable cache persistence;
- execution-state/log plumbing.

Those were explicitly the responsibilities native-thin was selected **not** to own.

moon already provides the required high-level behavior and has now been qualified on both required
platforms. The preferred direction for the expanded scope is therefore:

```text
moonrepo
  high-level repository task graph
  inputs / deps / outputs
  affected selection
  task hashing + output cache/hydration
        |
        v
stable domain commands
  tool.scad-project / tool.java-project / tool.eng-docs / repository validators
        |
        v
SCons / Maven / domain-specific fine-grained execution
```

This does **not** replace SCons or Maven. It adds the missing high-level orchestration/cache layer
above them.

## Configuration consequence

If moon is adopted, there is little value in designing a parallel custom
`project.build.yml` capability/task graph. `moon.yml` (plus optional `.moon/tasks/*` inheritance)
can be the authoritative declarative task graph itself.

Domain complexity should be hidden behind stable commands. For example:

```yaml
tasks:
  scad.build:
    command: 'tools/tool.scad-project/... build'
    inputs:
      - 'dsg/**'
      - 'project.scad.yml'
    outputs:
      - 'bld/**'

  java.unit-test:
    command: 'tools/tool.java-project/... unit-test'
    inputs:
      - 'src/main/**'
      - 'src/test/**'
```

Exact production command interfaces remain domain-tool design work.

## Publication side effects

A task that only produces deterministic workspace output is a good cache candidate.
A task whose primary purpose is an external side effect — for example pushing `prod/build`,
creating a release/tag or updating another external system — should not be treated as an ordinary
cacheable build task. Such publication/finalization work should consume already built/hydrated
artifacts and normally execute explicitly with caching disabled.

This preserves the useful distinction:

```text
build output generation    -> cacheable
publication side effect    -> explicit / normally non-cacheable
```

## What is still not qualified

R1b did not yet prove:

- a production remote-cache service;
- GitHub Actions cache wiring across separate workflow runs;
- real `tool.scad-project` nested inside moon;
- real `tool.java-project` task splitting;
- release/qualification intent conventions;
- final evidence/publication branch layout;
- task inheritance/distribution strategy across repository templates.

Those belong to the next contract/consumer qualification steps. They no longer justify building a
native generic task/cache engine first.
