# moonrepo orchestration follow-up

This candidate is the R1b follow-up triggered by broader repository-build requirements.

R1 evaluated moon only as an affected-task query engine and deliberately disabled task
execution and caching. The requirements discovered in R2 now include:

- symbolic high-level task execution;
- producer/consumer outputs;
- output restore/reuse on fresh CI workspaces;
- durable execution evidence and human-readable logs.

Those requirements cross the R1 reopen boundary for the native-thin recommendation.
This follow-up therefore evaluates moon as a **high-level orchestrator and output-cache
layer**, while still treating domain build engines such as SCons and Maven as nested
owners of fine-grained execution.

## Fixture

Two tasks are modeled:

```text
product.build -> publication
```

`product.build` produces:

```text
out/product/artifact.txt
out/product/evidence/execution.json
out/product/evidence/execution.log
```

`publication` requires the product artifact and produces its own package plus evidence.
Both tasks are cached by moon and both declare their generated directories as outputs.

The task commands are deliberately tiny Python domain adapters. A real SCAD task could
replace `python tools/product_build.py` with the stable `tool.scad-project` build entrypoint;
SCons would then remain responsible for target-level rebuild/cache decisions inside the
task.

## Acceptance checks

`run_orchestration.py` proves:

1. a cold publication run executes producer and consumer once;
2. an exact rerun executes neither command;
3. deleting generated outputs and rerunning hydrates outputs from moon cache without
   executing commands;
4. a fresh workspace receiving only `.moon/cache/hashes` and `.moon/cache/outputs`
   hydrates producer and consumer outputs without executing commands;
5. the hydrated output includes the original human-readable execution logs and JSON
   evidence;
6. changing product input executes product build and downstream publication;
7. changing release-only input executes publication without rerunning product build;
8. the same checks pass on Linux and native Windows.

This is not a remote-cache-service qualification. The test follows moon's documented
manual-persistence model for its portable `hashes` and `outputs` cache directories.
