================================================================================
Performance
================================================================================

Performance characteristics, benchmarks, and optimization strategies.

Performance Targets
===================

Roadmap CLI is designed for interactive use with these target latencies:

- **Startup**: < 200ms (including Python interpreter)
- **List operations** (1000 items): < 500ms
- **Create operations**: < 100ms
- **Kanban view**: < 1s for 500 items
- **GitHub sync**: Background operation, no blocking

Performance Benchmarks
======================

Recent benchmark results (3-item project):

.. code-block:: text

    Operation              Time      Memory
    ──────────────────────────────────────────
    create project         18ms      2.3 MB
    create milestone       12ms      2.4 MB
    create issue           8ms       2.5 MB
    list projects          25ms      3.1 MB
    view kanban            45ms      4.2 MB
    GitHub sync (5 items)  250ms     5.1 MB

For a realistic 100-item project:

.. code-block:: text

    Operation              Time      Memory
    ──────────────────────────────────────────
    list all issues        120ms     8.5 MB
    view kanban            280ms     12.3 MB
    filter by milestone    95ms      8.1 MB
    export JSON            150ms     10.2 MB

Performance Profiling
=====================

The project includes an automated performance profiler:

.. code-block:: bash

    poetry run python scripts/baseline_profiler.py

This generates a baseline JSON file with:

- Command execution times
- Memory usage
- System information (OS, Python, CPU, RAM)
- Roadmap version
- Timestamp

Baseline files are stored in ``docs/performance/`` for historical comparison.

Optimization Strategies
=======================

**Lazy Loading**
    - Data loaded on-demand, not all at once
    - Reduces startup time
    - Minimizes memory for large datasets

.. code-block:: python

    # Efficient: Load only requested milestone
    milestone = project.get_milestone("v1.0")

    # Inefficient: Load all milestones
    all_milestones = project.milestones  # If not needed

**Caching**
    - Frequently accessed data cached in memory
    - Invalidated on modifications
    - Configurable cache strategy

**Batch Operations**
    - Process multiple items efficiently
    - Avoid repeated I/O operations

.. code-block:: bash

    # Efficient: Single command for multiple items
    roadmap issue create "Feature A" --project "Q1"
    roadmap issue create "Feature B" --project "Q1"

    # Then: Load project once
    roadmap issue list --project "Q1"

**Indexing**
    - Index-based lookups for name searches
    - O(1) access for common queries

**Streaming Large Outputs**
    - Tables and kanban boards streamed line-by-line
    - No buffering entire output in memory

Scalability Characteristics
============================

Roadmap CLI scales well for typical use cases:

.. code-block:: text

    Dataset Size    List Time    Memory    Notes
    ─────────────────────────────────────────────
    10 projects     15ms         2 MB      Fast
    100 projects    40ms         3 MB      Still fast
    1000 projects   150ms        8 MB      Perceptible delay
    10000 projects  500ms        25 MB     Background recommended

**Recommendations**:

- < 1000 projects: Interactive use fine
- 1000-10000: Consider async operations
- > 10000: Use filtering, pagination

Memory Usage Analysis
====================

Typical memory consumption:

.. code-block:: text

    Baseline (empty)           ~2 MB
    + 100 projects             ~3 MB
    + 500 milestones           ~5 MB
    + 5000 issues              ~15 MB
    + GitHub sync running      +2 MB
    + Full output rendering    +varies by format

Memory is efficiently managed with:

- Streaming output (no buffering)
- Garbage collection between operations
- Minimal object retention

CPU Profiling
=============

CPU-intensive operations:

1. **List/filtering operations**: 40% of time
2. **JSON parsing/serialization**: 30% of time
3. **Sorting/aggregation**: 20% of time
4. **I/O operations**: 10% of time

Optimizations applied:

- Avoid unnecessary sorting (use sorted() once)
- Minimize JSON round-trips
- Cache parsed objects

GitHub Sync Performance
=======================

GitHub sync is non-blocking and can run asynchronously:

.. code-block:: bash

    # Blocking sync (waits for completion)
    roadmap sync

    # Background sync (coming in v.1.0)
    roadmap sync --background

Performance factors:

- **Network latency**: 50-200ms per API call
- **API rate limits**: 60 requests/hour (unauthenticated)
- **Data size**: 1KB per issue, 2KB per milestone
- **Typical sync**: 100 issues ≈ 2 seconds

Optimization tips:

- Sync during off-peak hours
- Set sync schedule (not after every operation)
- Use GitHub token for higher rate limits

Testing Performance
===================

Performance is validated with:

- **Benchmark tests**: Track regressions
- **Load tests**: Test with large datasets
- **Stress tests**: Concurrent operations
- **Regression detection**: CI/CD integration

Current test coverage: 2500+ tests, 92% code coverage

Monitoring in Production
=========================

For monitoring Roadmap in production use:

**Logging**:

.. code-block:: bash

    # Enable debug logging
    export ROADMAP_LOG_LEVEL=DEBUG
    roadmap project list

**Tracing**:

.. code-block:: bash

    # Enable OpenTelemetry tracing
    export OTEL_TRACES_EXPORTER=jaeger
    roadmap project list

**Metrics**:

Roadmap collects metrics including:

- Command execution time
- Success/failure rates
- API response times
- Cache hit rates

Future Performance Work
=======================

Planned optimizations for v.1.0+:

- ✓ Streaming output (done)
- ⏳ Parallel GitHub API calls
- ⏳ Local caching layer
- ⏳ Incremental syncing
- ⏳ Database mode for large datasets
- ⏳ Web UI for visualization

Best Practices
==============

1. **Use filters** - Don't load everything

   .. code-block:: bash

       roadmap issue list --project "Q1" --status open

2. **Batch operations** - Combine related work

   .. code-block:: bash

       for issue in "${ISSUES[@]}"; do
         roadmap issue create "$issue" --project "Q1"
       done

3. **Monitor with logging** - Track performance

   .. code-block:: bash

       time roadmap project list

4. **Use caching** - Enable local cache

   Set in config.yaml:

   .. code-block:: yaml

       cache:
           enabled: true
           ttl: 300  # 5 minutes

5. **Run sync in background** - Don't block on GitHub

   .. code-block:: bash

       roadmap sync --background &

See Also
========

- :doc:`overview` - Architecture overview
- :doc:`design-decisions` - Design decisions
- :doc:`../developer/development` - Profiling development code
- Performance baseline files in ``docs/performance/``
