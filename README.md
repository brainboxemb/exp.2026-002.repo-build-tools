# exp.2026-002.repo-build-tools

Experiment repository for evaluating **Pants**, **moonrepo**, and a deliberately
small **native-thin** approach for repository capability graphs, affected-impact
analysis, and build modes.

This repository provides reproducible evidence for the cross-project architecture
coordinated from [`meta.scad-projects`](https://github.com/brainboxemb/meta.scad-projects),
issue/PR #12. It is deliberately an experiment repository: the final normative
repository contract should live in `tool.git-project` if and when the architecture
is accepted.

## What is being tested

The missing generic layer is narrower than a universal build system:

```text
Git base/head or working-tree change
        ↓
logical repository capability impact
        ↓
dependency/dependent propagation
        ↓
structured affected result
        ↓
existing domain owner executes concrete work
```

The experiment must not silently replace Maven, SCons, SCAD rendering,
document-generation semantics, or verification logic.

## Candidates

- **Pants** — polyglot target graph, Git-aware changed/dependent selection and a
  plugin API.
- **moonrepo** — task graph, VCS affected queries and arbitrary system tasks.
- **native-thin** — the minimum capability graph and Git-impact logic needed to
  measure how much custom functionality would really be required in
  `tool.git-project`.

## Fair-comparison rule

All candidates use the same candidate-neutral model and the same Git-change
scenarios under `fixture/`. A candidate may translate the model into its own
configuration, but it may not redefine the expected affected set.

The comparison measures more than whether a tool can produce the right answer:

- amount and duplication of configuration;
- installation/runtime burden;
- Git base/head and merge-base semantics;
- direct versus transitive impact;
- structured query output;
- ability to remain a query/orchestration layer instead of becoming the build
  engine;
- local/CI parity;
- extension cost for domains the tool does not understand natively.

## Layout

```text
.github/workflows/       reproducible experiment checks
candidates/
  pants/                  Pants-specific configuration and observations
  moonrepo/               moonrepo-specific configuration and observations
  native/                 deliberately small native reference implementation
docs/
  experiment-plan.md      fixed experiment method and scoring criteria
  results.md              evidence and comparison as experiments complete
fixture/
  capability-model.json   candidate-neutral graph and selectors
  scenarios.json          Git mutations and expected affected capabilities
  workspace/              small representative source tree
scripts/                  neutral validation/evaluation helpers
```

The fixture format is **not** a proposal for the eventual `project.yml` schema.
It exists only to make the experiment reproducible and fair.

## Working method

`main` is the neutral baseline and shared evidence. Candidate work may be done on
short-lived branches when that makes the evidence clearer; branch protection is
intentionally not required for this experiment repository.

When evidence changes an assumption, update the experiment plan before changing
the expected result. Do not tune expected outcomes to make a candidate pass.

## Decision ownership

Results feed back into `meta.scad-projects`. The experiment repository does not
become a production dependency. After a make/buy decision, the accepted generic
contract and GitHub adapters belong in `tool.git-project`; domain-specific build
execution remains with its domain tool.
