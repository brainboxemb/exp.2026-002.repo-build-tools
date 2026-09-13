# moonrepo real engineering-documentation consumer qualification

This follow-up qualifies the repository-orchestration direction against the real
`brainboxemb/2026-010-01.meta.event-timing-software` documentation build.

## Requirement-derived boundary

The current documentation workflow contains several sequential shell steps, but
the meaningful build boundaries are the independently owned generated trees:

```text
docs.diagrams ─┐
               ├──> docs.assemble
docs.planning ─┘
```

- `docs.diagrams` owns `bld/docs/architecture`;
- `docs.planning` owns `bld/docs/planning`;
- `docs.assemble` consumes both and owns the generated documents, copied assets,
  and root documentation index.

The three SIP/planning generator scripts remain one high-level task because they
collaboratively manage the same planning output tree. Source/reference validators
remain CI gates rather than artificial artifact dependencies. Publication to a
generated branch remains an explicit external side effect outside the cacheable
producer graph.

## Exact proof inputs

- consumer: `brainboxemb/2026-010-01.meta.event-timing-software`
- consumer revision: `33d2a5bcec547694c1541da52563e26b08c3ded0`
- `tool.eng-docs`: `184e030a188385451a3392a8c43b081ae18c0650`
- Python: `3.12`
- Moon: `2.5.4`

## Acceptance cases

The harness checks:

1. cold build executes all three producers exactly once;
2. exact rerun skips all three producers;
3. deleting all declared generated documentation/evidence hydrates it from Moon;
4. a fresh workspace with portable Moon cache state hydrates generated output and
   human-readable task logs without producer execution;
5. an authored Markdown-only change reruns only `docs.assemble`;
6. a declarative diagram-source change reruns `docs.diagrams` and downstream
   `docs.assemble`, but not planning;
7. a planning-data change reruns `docs.planning` and downstream `docs.assemble`,
   but not diagrams;
8. cached task evidence preserves each task's original producer revision.

The final provenance case matters for `prod/docs`: one materialized documentation
snapshot may legitimately combine task outputs produced by different revisions
when their individual task inputs remained equivalent. Publication therefore must
record per-task producer identity/hash plus the revision for which the combined
snapshot was materialized, rather than pretending every component was rebuilt on
one source SHA.
