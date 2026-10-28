# Impact Trail

**Changed one file. What else should you inspect?**

Impact Trail explains the possible reach of a Python change, with a shortest import trail to every reached file. Run it locally before a pull request, attach a Markdown report, or share a self-contained HTML report.

**No API key. No runtime dependencies. No project imports. No network calls.**

[中文说明](README.zh-CN.md) · [Example report](docs/example-report.html) · [How it works](docs/design.md) · [Contributing](CONTRIBUTING.md)

> Alpha software. Import reachability is evidence for review, not proof of runtime impact, test coverage, or safety. Keep your required CI suite.

## Try it in 30 seconds

Python 3.10+; Git is needed only for Git comparisons. Clone the repository first:

```bash
git clone https://github.com/killerailian/impact-trail.git
cd impact-trail
python -m pip install .
impact-trail --root examples/shop --changed shop/pricing.py
impact-trail --root examples/shop --changed shop/pricing.py --format html --output report.html
```

Open `report.html` in your browser. It works offline and includes file search and a tests-only filter. Reports contain paths and import locations, not source bodies. Review paths before sharing.

The included demo finds two candidate tests:

```text
shop/pricing.py → shop/cart.py → tests/test_cart.py
shop/pricing.py → shop/cart.py → shop/api.py → tests/test_api.py
```

Each hop carries an importer, line number, reason, and snapshot. The unrelated email module is not reached by this import graph; that alone does not prove it is unaffected.

You can also run from source without installing:

```bash
PYTHONPATH=src python -m impact_trail --root examples/shop --changed shop/pricing.py
```

The package is not yet published on PyPI. Do not assume a registry package with a matching name is this project.

## Review a real change

From the root of the repository being reviewed:

```bash
# HEAD versus your working tree, including staged changes and untracked files
impact-trail

# A particular commit versus the working tree
impact-trail --base main --format markdown --output impact.md

# Changes since the branch point (POSIX shell)
impact-trail --base "$(git merge-base main HEAD)" --format html --output impact.html

# Custom source layouts: repeat the option to include each import root
impact-trail --source-root backend --source-root .

# Machine-readable evidence, useful for review tools and assistants
impact-trail --format json --output impact.json
```

`--base main` compares the exact commit to the current working tree; it does not automatically compute a merge base. In Git mode, `--root` must be the Git repository root. Source roots are relative to it. By default, both `src` and `.` are considered when `src/` exists; otherwise only `.` is used.

Use `--changed file.py other.py` to analyze an explicit set without Git. Pair `--changed` with `--base` if you also need baseline evidence for deleted files or removed imports. Explicit mode walks Python files and skips common build/virtualenv directories; it does not apply `.gitignore`. Git mode respects ignored untracked files.

## What you get

| Output | Useful for |
| --- | --- |
| Text | A fast local review |
| JSON | Editor integrations and assistant context |
| Markdown | Pull request descriptions |
| HTML | Searchable offline reports; no CDN or external assets |

Supports absolute and relative imports, `from package import module`, package initializers, namespace-style layouts, cycles, conditional imports, and scoped pytest `conftest.py` dependencies. Git mode unions changed files' baseline and current imports so deletions and removed imports retain evidence.

One deterministic shortest trail per reached file is returned. It is not a listing of every possible path. Import line numbers refer to the specified `working` or `base` snapshot; `inferred` fixture edges use line 0.

## Honest limits

- This is a **file-level static import graph**, not a call graph or coverage database.
- Runtime plugins, aliased dynamic loaders, fixture-name injection, non-Python assets, environment changes, and custom `sys.path` behavior can evade analysis.
- Type-only and conditional imports count conservatively. Ambiguous module names retain all candidates and produce a warning.
- Known dynamic calls, parse failures, skipped files, and changes outside the graph produce warnings. No warning does **not** mean complete analysis.
- `candidate_tests` is an inspection shortlist, not a safe subset for replacing your suite. This tool never runs or deselects tests.
- Symlinks outside the root are skipped. Python files above 2 MB are skipped with a warning. Git subprocesses have a 30-second timeout each.
- AST syntax support follows the interpreter running Impact Trail. Use an interpreter compatible with the target source.

`--strict` exits 2 on warnings. Normal success exits 0; input, Git, and write errors exit 1. These exit codes do not certify that a change is safe.

## Where it fits

Use [pytest-testmon](https://github.com/tarpas/pytest-testmon) when you want coverage-driven test selection. Investigate [pytest-impacted](https://github.com/promptromp/pytest-impacted) for a pytest-centered impact workflow. Impact Trail focuses on standalone, inspectable review reports without executing the inspected project. These are different workflows, not benchmark claims.

## Development

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
python -m pip wheel --no-deps . -w dist
```

Tests include temporary Git repositories, deleted files, renames, old import edges, unusual filenames, HTML escaping, cycles and fixture scope. No service credentials are needed.

## License

MIT. See [LICENSE](LICENSE).
