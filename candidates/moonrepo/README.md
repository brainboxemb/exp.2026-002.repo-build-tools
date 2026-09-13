# moonrepo candidate

This candidate evaluates moonrepo as the repository-level affected/capability
graph for the shared experiment fixture.

## Version

- moon: `2.5.4`

The qualification uses official release binaries on both Linux x86_64 and native
Windows x86_64.

## Mapping strategy

The neutral fixture remains authoritative. Each scenario is executed in an
isolated temporary Git repository created from `fixture/workspace/`.

The candidate copies one root moon workspace/project into that temporary repo.
The six logical capabilities are represented as tasks. Each task declares its
direct file inputs; only genuine producer/consumer relationships are represented
as task `deps`.

The commands are inert placeholders for this experiment. They are never run.
moon is used only through `query affected`.

Neutral experiment semantics map directly to moon query options:

```text
neutral direct impact
    -> moon query affected --downstream none

neutral complete affected closure
    -> moon query affected --downstream deep
```

Both queries use the same explicit `--base HEAD~1 --head HEAD` Git comparison.

## Platform expectation

Unlike the Pants candidate, moon publishes an official native Windows x64 binary
as well as Linux binaries. This candidate therefore qualifies the same harness on
Ubuntu and Windows.

## Scope boundary

The experiment does not use `moon run`, moon output caching, toolchain management
or domain execution. Those remain important adoption-cost considerations because
they are part of moon's product model, but they are intentionally outside the
needed affected-query scope.
