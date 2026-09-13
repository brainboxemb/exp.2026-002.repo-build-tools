# Pants candidate

This candidate evaluates Pants as the repository-level affected/capability graph
for the shared experiment fixture.

## Versions

- Pants: `2.33.1` (current stable patch when this experiment was started)
- scie-pants launcher: `0.13.2`

The versions are pinned in `pants.toml` and the candidate workflow.

## Mapping strategy

The neutral fixture remains authoritative. For each scenario the harness creates a
temporary Git repository from `fixture/workspace/`, then copies:

```text
pants.toml      -> pants.toml
BUILD.fixture   -> BUILD
```

Pants `files()` targets own candidate-neutral input groups. Generic Pants
`target()` targets represent logical repository capabilities and are tagged with:

```text
capability
cap:<neutral-capability-id>
```

A capability depends on its direct input groups. Real downstream capability
relationships are represented as target dependencies. Shared inputs are depended
on by multiple capabilities instead of inventing dependencies between those
capabilities.

The harness runs two queries per scenario:

```text
--changed-dependents=direct
--changed-dependents=transitive
```

using `peek`, then extracts only targets tagged as capabilities and compares them
to `expected_direct` and `expected_affected` from the neutral scenario file.

## Important platform finding

Native Windows support is a material fit concern. The pinned scie-pants release
publishes Linux and macOS launchers but no Windows launcher, and Pants release
artifacts likewise do not provide a native Windows platform build. WSL may be a
workaround, but that is not equivalent to the current goal of one local/CI query
contract on native Windows and Linux.

The Linux experiment still proceeds so graph/affected quality can be evaluated
independently from platform fit.

## Scope boundary

This candidate intentionally does **not** ask Pants to compile Java, render SCAD,
run domain verification or assemble documents. The experiment only evaluates its
graph, Git-change and introspection behavior.
