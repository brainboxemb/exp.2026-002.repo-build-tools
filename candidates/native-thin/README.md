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

## Evaluation question

The value of this candidate is not simply whether nine scenarios pass. The
comparison must also ask whether owning this small amount of graph/query code is
preferable to adopting and maintaining an external framework configuration.

Conversely, if future requirements expand into scheduling, remote caching,
execution graph semantics, richer target discovery, or plugin ecosystems, this
thin implementation should not silently grow into a home-built build system. At
that point the make/buy decision must be reopened.
