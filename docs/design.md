# Design and evidence contract

1. Discover Python files through Git, or a bounded directory walk in explicit mode.
2. Build a module index from configured import roots. Namespace package directories need no `__init__.py`.
3. Parse with the standard library AST. Never import target modules or evaluate their expressions.
4. Resolve local absolute/relative imports and package initializer prefixes. Unresolved third-party imports do not become graph nodes.
5. Add inferred edges from test files to ancestor `conftest.py` files.
6. In Git mode, add baseline versions of changed or deleted files; union their imports with current imports.
7. Traverse reverse edges using breadth-first search from all changed paths.
8. Return one deterministic shortest evidence trail per reached Python file.

A hop `dependency → importer` means a change can travel toward the importing file. It does not mean the dependency imports the importer. Baseline edges are explicitly labeled and may no longer exist in current source. Existing tests only appear in `candidate_tests`; a deleted test can still appear in the impact list.

## JSON v1

- `schema_version`: integer 1.
- `baseline`: resolved commit hash or null in explicit mode.
- `changed`: sorted repository-relative starting paths.
- `impacts`: sorted entries with `path`, `kind`, `changed`, `origin`, and `trail`.
- Each trail edge: `importer`, `dependency`, `line`, `reason`, `snapshot`.
- `candidate_tests`: existing `test_*.py` and `*_test.py` files reached by the graph.
- `warnings`: analysis gaps that were detected, not an exhaustive list of limitations.
- `full_suite_recommended`: true when warnings exist; false is not a recommendation to skip normal CI.
- `limitations`: explicit caveats carried into every report.

The graph is conservative only with respect to recognized imports; it is not sound for arbitrary Python behavior. There is no confidence percentage or unsupported safety score.

## Privacy and attack surface

No HTTP client, telemetry, model calls, or package execution. Git uses argument arrays and disables external diff execution. Reports HTML-escape all paths, avoid injecting JSON into scripts, and apply a restrictive content security policy. Terminal output renders control characters visibly. Git filters are not requested. Repository hooks are not invoked by the read-only Git operations used here.

Untrusted repositories can still exhaust parsing resources: use ordinary process isolation and resource limits for hostile inputs. Per-file source size is capped at 2 MB; this is not a complete sandbox. Reports disclose repository-relative file names and import structure. Source line numbers can refer to old code.

## Complexity

Graph indexing and breadth-first traversal are proportional to source size, resolved edges, and nodes. Storing a full shortest trail per reached file can require quadratic output on a long linear dependency chain. Baseline reads use one Git invocation per changed Python file. No large-monorepo speed claim is made.
