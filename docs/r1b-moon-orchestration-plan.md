# R1b — moonrepo orchestration and output-cache follow-up

Status: **active bounded follow-up to R1**

## Why R1b exists

R1 intentionally evaluated only the narrow question:

```text
Git change -> affected repository capabilities
```

Under that narrow requirement, native-thin was selected and moonrepo was retained as the
preferred buy fallback if the problem expanded into generic task execution or output caching.

The R2 requirements work in `meta.scad-projects` has now made additional requirements explicit:

```text
affected selection
+ stable owner/action execution
+ producer/consumer output availability
+ reuse/hydration of unchanged outputs in fresh CI workspaces
+ retained build/execution logs and evidence
```

That crosses the R1 reopen condition. R1b therefore re-evaluates moonrepo for the expanded
scope before a custom `project.build.yml` execution/cache layer is designed.

## Question

Can moon provide the high-level orchestration and output reuse we now require while domain
engines remain nested and authoritative?

The intended architecture would be:

```text
moon high-level task
  inputs / deps / outputs / cache
        ↓
stable domain command
        ↓
SCons / Maven / eng-docs / validator
        ↓
fine-grained domain behavior
```

For SCAD this means moon may cache/hydrate the complete logical `scad.build` task output,
while SCons still decides individual target rebuilds whenever the task really executes.

## Acceptance criteria

The follow-up must prove on Linux and native Windows:

1. **cold execution** — producer and consumer commands both execute;
2. **exact cache hit** — unchanged rerun executes neither command;
3. **local hydration** — deleting declared outputs causes moon to restore them from cache without
   command execution;
4. **fresh-workspace hydration** — copying only moon's documented portable `hashes` and `outputs`
   cache directories into a fresh but identical workspace restores both tasks without command
   execution;
5. **evidence hydration** — the restored outputs include the exact human-readable execution log
   and structured evidence produced by the original execution;
6. **producer invalidation** — changing producer input executes producer and downstream consumer;
7. **consumer-only invalidation** — changing only consumer input reruns the consumer without the
   producer;
8. **domain boundary** — moon does not need knowledge of internal SCons/Maven target semantics.

## Non-goals

R1b does not yet:

- install moon into production repositories;
- qualify a remote-cache service;
- replace SCons or Maven caches;
- redesign SCAD/Java/docs domain actions;
- decide final task naming or inheritance structure;
- claim build logs in generated branches are solved solely by moon's console capture.

The test does, however, require task outputs themselves to contain a durable evidence/log envelope
so cached/hydrated artifacts remain self-describing.

## Decision rule

If moon satisfies the acceptance criteria cleanly, the architecture recommendation must be
revisited. At that point a custom native orchestration/cache implementation would duplicate
capabilities moon already provides and would violate the reason native-thin was originally chosen.

If moon cannot satisfy the requirements without taking over domain internals or introducing an
unacceptable operational burden, retain native-thin and explicitly design the missing output/evidence
contract without pretending it is still only an affected-query layer.
