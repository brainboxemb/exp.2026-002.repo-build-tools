# Pants candidate

This candidate evaluates Pants as the repository-level affected/capability graph
for the shared experiment fixture.

## Versions

- Pants: `2.33.1`
- scie-pants launcher: `0.13.2`
- qualification platform: GitHub-hosted Ubuntu 24.04, x86_64

The versions are pinned in `pants.toml` and the candidate workflow.

## Mapping strategy

The neutral fixture remains authoritative. For each scenario the harness creates a
temporary Git repository from `fixture/workspace/`, copies the Pants candidate
configuration into it, creates a baseline commit, applies one shared scenario and
queries Pants against `HEAD~1`.

### Attempt 1 — built-in `files()` plus generic `target()`

The first model used `files()` targets for input groups and generic `target()`
targets for logical capabilities.

This produced correct **transitive affected** results, but the generated per-file
target introduced an extra graph level. A changed source selected a generated
`file` target first, so Pants' direct changed/dependent view did not map naturally
to the experiment's `expected_direct` capability concept.

That attempt was useful evidence rather than a failed fixture: the neutral
expectation was kept unchanged.

### Final model — small custom capability target

The accepted Pants experiment model uses an in-repo plugin with one target type:

```text
repo_capability
    sources
    dependencies
    tags
```

Each capability directly owns the source selectors that should impact it. Shared
inputs may be owned by multiple capabilities. Only genuine producer/consumer
relationships are declared as target dependencies.

This cleanly preserves the fixture distinction:

```text
src/product/**
    -> product.build        direct input impact
    -> verification         direct input impact


docs.diagrams
    -> docs.assemble        real downstream relationship
    -> publication          transitive relationship
```

The custom plugin has no execution rules. Pants is used only for target/source
ownership, Git change selection and graph traversal.

## Pants vocabulary mapping

The neutral experiment field `expected_direct` means "capabilities whose own
input selectors matched the changed files".

Pants' `--changed-dependents=direct` means "changed targets plus one downstream
hop", which is a different concept. The correct mapping is therefore:

```text
neutral direct impact
    -> --changed-dependents=none

neutral complete affected closure
    -> --changed-dependents=transitive
```

Both queries use `peek`; the harness extracts logical capability IDs from target
tags.

## Result

Final Linux qualification on branch head `3b496dca2084f646a82174e2ba2e67c42908b360`:

```text
9 / 9 scenarios passed
```

GitHub Actions run: `Pants candidate #4` / run `34754675551`.

Evidence artifact:

```text
pants-candidate-evidence
sha256:66ff6614eac2db3f864c3d9d3efa06bf3b5badbbf481229c1f94fdf9d8e070a5
```

The scenarios cover irrelevant changes, product source, test-only input, authored
docs, diagram producer input, verification-only config, publication-only input,
global project config and generic tooling.

### Query timing observed in this harness

The experiment intentionally launches many isolated temporary Git repositories,
so this is not a production performance benchmark.

Observed on the successful CI run:

- first direct query: about `15.96 s`, including first Pants 2.33.1 bootstrap;
- subsequent direct-query median: about `1.50 s`;
- transitive-query median: about `1.49 s`;
- 18 total queries across 9 isolated scenarios: about `41.48 s` of measured query
  time.

The first bootstrap installed Pants into the scie-pants managed environment; later
queries reused that installation.

## Configuration cost observed

Correct semantics required more than only `pants.toml`:

- `pants.toml`;
- one Pants BUILD model containing the six logical capabilities;
- one small in-repo plugin target type plus registration;
- a Pants-specific translation of the neutral input selectors and capability
  dependencies.

This is manageable, but it is a real second graph/config representation that must
be weighed against Pants' maintained Git/graph/plugin behavior.

## Important platform finding

Native Windows support is a material fit concern. The pinned `scie-pants` release
publishes Linux and macOS launchers but no Windows launcher, and the Pants 2.33.1
release likewise does not publish a native Windows build.

WSL may be a practical workaround, but it is not equivalent to the current goal
of one local/CI query contract that works natively on both Windows and Linux.
This remains a major comparison criterion against moonrepo and native-thin.

## Scope boundary

This candidate intentionally does **not** ask Pants to compile Java, render SCAD,
run domain verification or assemble documents. The experiment only qualifies its
graph, Git-change and introspection behavior.

## Current assessment

Pants is technically capable of representing the required affected-capability
semantics accurately on Linux. Its strongest advantages are its mature graph,
Git-aware changed selection and extensible target model. Its largest observed
costs are the Pants-specific graph/plugin representation, substantial runtime
foundation for a relatively small query problem, and lack of native Windows
support.

No make/buy decision is made from this candidate alone. moonrepo and native-thin
must be tested against the same fixture first.
