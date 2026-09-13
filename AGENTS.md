# AGENTS.md

## Purpose

This repository is a controlled experiment for cross-project repository build and
impact tooling. It provides evidence; it is not the normative production owner of
the final architecture.

Cross-project intent and decision ownership remain in
`brainboxemb/meta.scad-projects`, especially issue/PR #12 and the repository
execution roadmap.

## Core rule

Compare candidates against the same candidate-neutral fixture and expected
outcomes.

Do **not** change the fixture expectation merely because one candidate cannot
express it conveniently. If evidence proves the expectation itself is wrong,
update the experiment plan and explain why before changing the fixture.

## Candidate isolation

Candidate-specific files belong below:

```text
candidates/pants/
candidates/moonrepo/
candidates/native/
```

Do not put Pants, moonrepo or native implementation details into the neutral
fixture format.

## Scope boundary

The experiment evaluates the repository-level layer:

- Git changed-file/base-head semantics;
- logical capability impact;
- direct/transitive dependent propagation;
- structured affected output;
- build-mode planning where applicable;
- local/CI parity;
- configuration/runtime/maintenance cost.

It must not quietly redesign or replace Maven, SCons/OpenSCAD, diagram rendering,
verification assertions or other domain-level target execution.

## Evidence discipline

For each candidate record:

- exact tool/runtime version;
- installation/bootstrap mechanism;
- all configuration required to model the fixture;
- exact commands used for queries;
- machine-readable result where available;
- CI behavior;
- mismatches/limitations;
- whether execution/cache features had to be enabled even though only impact was
  required;
- approximate duplicated concepts compared with the neutral model.

Prefer committed scripts/tests over prose-only claims.

## Git workflow

`main` holds the neutral baseline and reproducible accepted experiment evidence.
Short-lived candidate branches/PRs may be used when useful. Branch protection is
not required.

Do not introduce a production dependency from another repository to this
experiment repository.

## Outcome

The final recommendation is written back to `meta.scad-projects`. If a generic
contract is accepted, normative implementation belongs in `tool.git-project` or
an explicitly selected external tool, not here.
