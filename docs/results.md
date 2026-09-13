# Experiment results

Status: R1 candidate qualification complete; architecture recommendation ready for
`meta.scad-projects`.

## Shared baseline

All candidates were evaluated against the same candidate-neutral inputs:

- `fixture/capability-model.json`;
- `fixture/scenarios.json`;
- the source tree below `fixture/workspace/`;
- the method and scoring criteria in `experiment-plan.md`.

The first qualification round contained nine mutation scenarios. Before closing
R1, the fixture was extended with `S10-delete-product-source` because the
experiment plan explicitly required deletion or rename coverage. None of the
original nine expectations were changed.

The final shared suite therefore contains **10 scenarios**, including a real file
deletion. All three candidates passed their supported platform matrix on that
suite.

The experiment qualified committed **base/head** change selection and one deletion
case. It did **not** separately qualify merge-base selection, uncommitted working
tree changes or rename-specific behavior. Those must not be implied by the result.

## Final 10-scenario evidence

### Pants

- Pants `2.33.1`, scie-pants `0.13.2`;
- final model uses a small custom `repo_capability` target plugin;
- neutral direct impact maps to `--changed-dependents=none`;
- complete affected closure maps to `--changed-dependents=transitive`;
- **10/10 passed on Linux x86_64**, including source deletion;
- final cross-candidate run: `34755768833`;
- final evidence artifact:
  `sha256:9da2eba7ba6fa689f28277395906e44905a958617d858a7158df0fe8c792fb6d`.

The earlier built-in `files()` plus generic `target()` model introduced an extra
file-target graph level and did not map naturally to the neutral direct-capability
concept. Correct semantics therefore required the custom target type and a
Pants-specific translation of capability sources/dependencies.

The successful earlier timing run observed about `1.5 s` median query time after
the first bootstrap, with a roughly `16 s` first query while Pants installed its
managed environment. Speed is secondary here, but the runtime foundation is
materially heavier than the other two candidates for this narrow query problem.

Native Windows remains the decisive platform mismatch: the qualified Pants/scie-
pants versions do not provide the required native Windows runtime. WSL would be a
separate operating model rather than local/CI platform parity.

### moonrepo

- moon `2.5.4`;
- one root project with six capability tasks;
- task `inputs` model direct input ownership;
- task `deps` model genuine downstream relationships;
- no custom plugin or extension;
- changed paths come from `query changed-files --base/--head`;
- direct/full impact use `query tasks --affected` with explicit
  `--upstream none` and `--downstream none|deep`;
- **10/10 passed on Linux x86_64 and native Windows x86_64**, including deletion;
- final cross-candidate run: `34755768811`;
- final evidence artifacts:
  - Linux: `sha256:93d8896ea7c01a922e7243a3343ada5024b2dc185cabbf96971c580d26e0135f`;
  - Windows: `sha256:b14a01ad7d4bb2a440659e72862e671c2d598b1b1031374c73dc6287a290b212`.

The earlier timing qualification observed roughly `0.11 s` median affected-task
query time on Linux and `0.33 s` on Windows after first invocation.

moon is the strongest **buy** candidate in this experiment. It provides maintained
Git/graph/query behavior, native Windows support and a direct mapping from inputs
and dependencies to affected tasks without a custom plugin.

Its cost is architectural rather than correctness-related: adopting moon for only
this query layer creates a second moon-specific workspace/task representation of
the same capability input and dependency graph. The experiment deliberately did
not adopt moon task execution, output caching or toolchain ownership.

### native-thin

- Python standard library plus Git only;
- the neutral capability model remains the only graph declaration;
- core query implementation is one `affected.py` file of about `4.2 KiB`;
- direct impact is selector matching;
- full impact is reverse transitive dependency closure;
- no scheduler, task runner, cache engine or plugin system;
- **10/10 passed on Linux x86_64 and native Windows x86_64**, including deletion;
- final cross-candidate run: `34755768834`;
- final evidence artifacts:
  - Linux: `sha256:05e691d1c9ae75f85945cb12b58f8a3c38bf151f1f88d399cabf7c20c484be31`;
  - Windows: `sha256:beff3056bf1590d7958578345e4e6e04e7d5f5e25807be6c0f4828d63d66aacb`.

The earlier timing qualification observed roughly `0.032 s` median isolated query
time on Linux and `0.088 s` on Windows. Again, speed is not the primary decision
criterion; the more important result is that the required semantics fit in a very
small implementation without duplicating the graph declaration.

The cost is ownership: selector semantics, Git invocation behavior and graph
closure become repository-owned code. This remains acceptable only while the
implementation stays deliberately thin.

## Cross-candidate comparison

| Criterion | Pants | moonrepo | native-thin |
| --- | --- | --- | --- |
| Exact final scenario correctness | 10/10 Linux | 10/10 Linux + Windows | 10/10 Linux + Windows |
| Native Windows parity | **No** | **Yes** | **Yes** |
| Candidate-specific graph model | BUILD model + custom target plugin | moon project/task model | none beyond neutral graph |
| Duplicate graph burden | high for this scope | moderate | lowest |
| Structured output | JSON via Pants introspection | JSON query output | JSON CLI output |
| Qualified Git semantics | committed base/head + deletion | committed base/head + deletion | committed base/head + deletion |
| Query/runtime weight | highest | moderate/low | lowest |
| Execution/cache coupling in experiment | none required | none required | none exists |
| Domain execution remains external | yes | yes | yes |
| Maintained external graph behavior | strongest | strong | no; repository-owned |
| Extension path | mature Pants plugin ecosystem, but more adoption | richer moon task/query features | explicit code changes; must remain narrow |
| Principal risk | platform mismatch + over-sized foundation | second authoritative task graph / scope pull | custom-code scope creep |

## R1 recommendation

For the **current requirement**, choose **native-thin** as the repository affected-
capability query layer.

The reason is not raw speed. All technically supported candidates produced correct
results. native-thin best satisfies the current architecture constraints together:

1. one authoritative capability graph rather than a framework-specific copy;
2. the same contract on native Windows and Linux;
3. domain tools keep ownership of actual build, verification and documentation
   execution;
4. the custom implementation is small enough to audit and test directly;
5. adopting a general build/task framework would currently buy substantially more
   machinery than the repository-level query problem requires.

This recommendation has a **hard scope boundary**. native-thin must not gradually
become a home-built build system. It owns only:

```text
Git base/head changed paths
        +
capability input matching
        +
downstream graph closure
        +
structured query result
```

It must **not** take ownership of domain task execution, output caching, remote
cache protocols, generic scheduling, toolchain management or domain build
incrementality.

### Buy fallback / reopen rule

If requirements expand enough that the thin layer starts needing general task-
graph functionality, reopen the make/buy decision instead of adding that machinery
incrementally.

Based on this experiment, **moonrepo is the preferred buy fallback**. Re-evaluate
moon first when one or more of these become real requirements:

- generic task scheduling/orchestration;
- repository-level output or remote caching;
- richer target/task discovery than simple declared selectors;
- increasingly complex graph query semantics;
- a plugin/toolchain ecosystem becoming valuable;
- maintenance of native-thin becoming larger than the narrow contract above.

Pants remains technically capable and should not be described as a failed graph
engine. It is simply not the preferred fit for this scope and platform mix because
its configuration/runtime foundation is heavier and native Windows parity is
missing.

## What R1 does not decide

This result selects an **affected-query foundation**, not a universal build engine.
It does not change the existing ownership of SCAD builds, Java builds,
documentation producers, verification tools or their caches.

It also does not make changed-file pruning authoritative for every build mode.
`clean`, `qualification` and especially `release` may deliberately request more
than the affected set. The affected query produces planning evidence; execution
policy remains a separate layer.

The architecture decision and roadmap consequence are recorded in
`meta.scad-projects`; this experiment repository remains the reproducible evidence
source.
