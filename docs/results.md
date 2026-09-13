# Experiment results

Status: baseline only; candidate experiments not yet completed.

## Shared baseline

All candidates are evaluated against:

- `fixture/capability-model.json`;
- `fixture/scenarios.json`;
- the source tree below `fixture/workspace/`;
- the method and scoring criteria in `experiment-plan.md`.

## Candidate evidence

### Pants

Pending.

Record exact Pants version, installation/bootstrap, BUILD/plugin configuration,
commands, structured query output, scenario results and any execution/cache
coupling required to obtain affected results.

### moonrepo

Pending.

Record exact moon version, installation/bootstrap, workspace/task configuration,
commands, JSON query output, scenario results and any execution/cache coupling.

### native-thin

Pending.

Record implementation size, tests, Git semantics, JSON contract and scenario
results. The native implementation is a lower-bound comparison, not automatically
the preferred solution.

## Cross-candidate comparison

Do not fill this table from expectations; populate it from committed experiment
evidence.

| Criterion | Pants | moonrepo | native-thin |
| --- | --- | --- | --- |
| Exact scenario correctness | pending | pending | pending |
| Candidate config burden | pending | pending | pending |
| Duplicate graph burden | pending | pending | pending |
| Structured output | pending | pending | pending |
| Git semantics | pending | pending | pending |
| Local/CI parity | pending | pending | pending |
| Execution/cache coupling | pending | pending | pending |
| Extension cost | pending | pending | pending |
| Maintenance tradeoff | pending | pending | pending |

The final recommendation is made in `meta.scad-projects` after the evidence is
complete.
