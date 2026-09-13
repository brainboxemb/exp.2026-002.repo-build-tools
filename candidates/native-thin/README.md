# native-thin candidate

This candidate evaluates the smallest repository-owned implementation that can
satisfy the neutral affected/capability requirements without adopting a general
build graph framework.

## Scope

The implementation is deliberately narrow:

- Python standard library only;
- Git supplies the base/head changed-path set;
- the existing neutral `fixture/capability-model.json` supplies capability inputs
  and dependency edges;
- direct impact is path-selector matching;
- complete affected impact is reverse transitive dependency closure.

There is no cache engine, scheduler, plugin model, task runner or domain build
execution in this candidate.

The core query implementation is one `affected.py` file of about 4.2 KiB. The
larger `run_scenarios.py` file is experiment harness code, not production graph
logic.

## Query contract

The candidate CLI uses the same explicit concepts as the neutral experiment:

```text
python affected.py \
  --model capability-model.json \
  --base HEAD~1 \
  --head HEAD \
  --downstream none
```

returns direct capability impact, while `--downstream deep` adds the complete
downstream closure.

The CLI normalizes Windows path separators and implements only the glob semantics
needed by the declared repository model. In particular, `**/` may match zero or
more path segments so `docs/**/*.md` also matches `docs/guide.md`.

## Global inputs

`global_inputs` in the neutral fixture are treated as an explicit conservative
rule: when a changed path matches one of them, every declared capability is
selected directly. This is why the global project/tooling scenarios remain data,
not hard-coded path exceptions in the implementation.

## Qualification result

Workflow run `34755447995` qualified the same nine neutral scenarios on both
platforms:

| Platform | Scenarios | Result | Median query time |
| --- | ---: | --- | ---: |
| Linux x86_64 | 9 | 9/9 pass | ~0.032 s |
| Windows x86_64 | 9 | 9/9 pass | ~0.088 s |

The timings measure individual direct/deep CLI invocations in isolated temporary
Git repositories. They are comparison evidence rather than production
benchmarks.

Evidence artifact digests:

- Linux: `sha256:9c178eda54f850ba09dac21aeb2dd3044d0819197015a4c1da95eda158be763c`
- Windows: `sha256:1cf06bd33f3db86467ab1b7025777dabb25f0c05c72426a7c05e0c4a27f7df64`

## Evaluation question

The value of this candidate is not simply that all scenarios pass. The comparison
must ask whether owning this small amount of graph/query code is preferable to
adopting and maintaining an external framework configuration.

For the currently tested requirement set, native-thin has no external runtime or
framework dependency beyond Python and Git, keeps the neutral capability model as
the only graph declaration, and works with the same contract on Linux and native
Windows.

Conversely, if future requirements expand into scheduling, remote caching,
execution graph semantics, richer target discovery, or plugin ecosystems, this
thin implementation should not silently grow into a home-built build system. At
that point the make/buy decision must be reopened.
