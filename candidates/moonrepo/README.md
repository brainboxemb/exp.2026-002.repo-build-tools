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
moon is used only for Git change discovery and affected task queries.

The harness deliberately keeps revision selection separate from graph traversal:

```text
moon query changed-files --base HEAD~1 --head HEAD --json
    -> exact changed-path set

changed-path set
    -> moon query tasks --affected --upstream none --downstream none
       = neutral direct impact

changed-path set
    -> moon query tasks --affected --upstream none --downstream deep
       = neutral complete affected closure
```

`--upstream none` is explicit so moon does not silently broaden the neutral
semantics by including dependencies of an affected task.

No plugin or custom moon extension is required for this mapping.

## Qualification result

Workflow run `34755047449` qualified the same nine neutral scenarios on both
platforms.

| Platform | Scenarios | Result | Median affected-query time | First affected-query |
| --- | ---: | --- | ---: | ---: |
| Linux x86_64 | 9 | 9/9 pass | ~0.11 s | ~1.22 s |
| Windows x86_64 | 9 | 9/9 pass | ~0.33 s | ~1.56 s |

The timings above measure the `query tasks` calls in this deliberately isolated
per-scenario harness. They are comparison evidence, not a production benchmark.
The harness performs 18 affected-task queries per platform.

Evidence artifacts from the successful run:

- Linux: `sha256:21f5fb6c34c04a2b57b03c7cd3698208ca51b786259c72faef71fe1292a8e6dd`
- Windows: `sha256:675d215960d7ad595946d891b9bd9f0b965830a4788a043f234904118ca988fa`

## Platform finding

moon publishes an official native Windows x64 binary as well as Linux binaries.
The experiment confirmed that the same harness and logical query contract work on
Ubuntu and native Windows. This is a material fit advantage over the Pants
candidate for repositories that are expected to support native Windows locally.

## Configuration cost

For this fixture, moon's native project/task model can represent the required
concepts directly:

- task `inputs` represent direct capability inputs;
- task `deps` represent genuine downstream producer/consumer relationships;
- `query changed-files` supplies explicit Git base/head change discovery;
- `query tasks --affected` performs graph impact selection.

The price is that the repository would adopt moon workspace/project configuration
and task terminology even if moon is used only as a graph/query engine. That
adoption cost must be weighed against the native-thin candidate rather than being
hidden by the successful query result.

## Scope boundary

The experiment does not use `moon run`, moon output caching, toolchain management
or domain execution. Those remain important adoption-cost considerations because
they are part of moon's product model, but they are intentionally outside the
needed affected-query scope.
