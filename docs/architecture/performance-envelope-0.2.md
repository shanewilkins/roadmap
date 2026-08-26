# Performance envelope for 0.2

Roadmap 0.2 targets individual developers and small teams, not server-scale
workloads. Its supported regression dataset contains 500 issues attached to one
milestone: 400 active, 50 closed, and 50 archived. Every issue has an estimate,
an assignee, and a dependency on the preceding issue. This deliberately exercises
the most expensive ordinary graph and filesystem paths.

The automated envelope is measured from a warm Python process on each supported
Python and operating-system CI combination. Dataset construction is excluded.

| Journey | Maximum |
|---|---:|
| Rebuild SQLite projection from canonical documents | 8 s |
| Filtered projection lookup | 3 s |
| Daily summary and milestone board calculation | 8 s |
| Critical-path dependency analysis | 8 s |
| Full read-only health scan | 12 s |
| Deterministic JSON serialization of query rows | 1 s |

These are regression ceilings, not marketing claims or typical latency. They are
intentionally tolerant of shared CI runners while still detecting material
algorithmic or I/O regressions. Faster local measurements do not justify lowering
the ceilings without CI history. Workloads beyond this dataset may work, but are
not part of the 0.2 support claim.

The executable contract is
`tests/integration/performance/test_supported_envelope.py`. A ceiling change must
include measured evidence and a requirements review for TR-036.
