# Repository build-tool experiment plan

## Goal

Compare Pants, moonrepo and a deliberately small native-thin implementation as
possible foundations for a generic repository capability/affected layer.

The experiment is intentionally narrower than a full build-system comparison.
The question is whether each candidate can correctly and maintainably answer:

```text
Given a repository state or base/head change:
- which logical capabilities are directly affected?
- which downstream capabilities become affected through declared relationships?
- what structured result can local tooling and CI consume?
- how much duplicate configuration/runtime/execution machinery is introduced?
```

## Candidates

### Pants

Evaluate Pants as both:

1. a directly adopted repository graph/affected engine;
2. a restricted query layer that delegates real execution to existing domain
   tools.

Record where BUILD targets, plugins or shell commands are needed merely to model
repository capabilities.

### moonrepo

Evaluate moonrepo as both:

1. a directly adopted task/affected engine;
2. a restricted query layer with candidate execution/cache behavior disabled or
   unused wherever possible.

Record whether the task graph can remain only an impact model or naturally pulls
execution/cache ownership into moon.

### native-thin

Implement only enough code to establish the lower bound on custom complexity:

- changed-file/base-head calculation;
- input selector matching;
- capability graph traversal;
- conservative global impact;
- JSON result.

Do not implement task execution, output caching or domain build semantics.

## Candidate-neutral model

`fixture/capability-model.json` is an experiment fixture, not a proposed final
`project.yml` schema. It models these concerns:

```text
repository validity
product build
verification/test
document producer
document assembly
publication
```

The model deliberately contains both:

- capabilities affected independently by the same source input; and
- a real producer -> consumer relationship whose impact must propagate.

This distinction is important. Shared source inputs must not be faked as build
dependencies merely to make an affected graph work.

## Scenario rules

`fixture/scenarios.json` defines mutations and expected affected sets. At minimum
the candidates must cover:

- irrelevant README-only change;
- product-source change;
- test-only change;
- documentation-source change;
- diagram/producer-source change with downstream propagation;
- verification-only configuration change;
- publication-only metadata change;
- broad/global project configuration change;
- generic tooling change;
- file deletion or rename once candidate baselines support it.

Expected outcomes are part of the experiment specification. Candidate-specific
workarounds must not silently weaken them.

## Build modes

Affected classification and build mode are evaluated separately.

The experiment should test at least these conceptual modes:

- `incremental`: use affected pruning and allow normal domain incremental/cache
  behavior;
- `clean`: execute the requested capability set from clean local/domain state;
- `qualification`: run the explicitly selected conformance set even if a source
  diff would prune part of it;
- `release`: produce the complete required release set for one exact revision;
  release completeness must not be inferred only from changed files.

A candidate does not need to own domain cache cleanup to pass. It must be possible
to express or return a plan that lets the owning domain tool apply the mode.

## Measurements

For each candidate record:

| Area | Evidence |
| --- | --- |
| Correctness | exact scenario pass/fail against expected affected sets |
| Config size | candidate-specific files/lines/concepts required |
| Duplicate graph | concepts repeated beside the neutral/project/domain model |
| Runtime | install/bootstrap dependencies and startup/query behavior |
| Structured output | JSON or equivalent stable machine-readable query result |
| Git semantics | base/head, merge-base, working tree, deletes/renames |
| Propagation | direct and transitive downstream dependents |
| Domain neutrality | ability to represent SCAD, Java and docs without fake language ownership |
| Execution coupling | whether task execution/cache must be adopted to use affected queries |
| Extensibility | cost of adding domain metadata or unsupported semantics |
| CI parity | same conceptual query locally and in GitHub Actions |
| Maintenance | external maintained behavior versus custom code surface |

Raw speed is secondary for the small repository sizes under discussion, but
installation/query timings may still be recorded when useful.

## Decision rule

Do not choose the candidate with the largest feature set.

Prefer the solution that:

1. produces the required affected result correctly;
2. avoids a second authoritative target/build graph where possible;
3. can be used identically locally and in CI;
4. preserves domain-tool ownership of concrete execution;
5. has the lowest long-term configuration and maintenance cost;
6. uses mature external behavior where that meaningfully reduces custom risk.

The final make/buy decision belongs in `meta.scad-projects`, not in this file.
