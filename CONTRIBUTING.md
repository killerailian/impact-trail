# Contributing

Start with a small reproduction: Python layout, changed path, import statements, expected evidence, actual output, and Python/Git versions. Remove private source and credentials before sharing it.

Use standard-library unittest tests. Add fixtures for new import semantics, preserve deterministic JSON, and keep the runtime dependency-free. Avoid tests that import the inspected fixture code. Every edge must retain its evidence source. Document false negatives rather than adding unsupported safety claims.

Run `PYTHONPATH=src python -m unittest discover -s tests -v` before a pull request. A focused change with a regression test is preferred. Improvements to Chinese and English documentation are welcome.

Good first contributions after launch: regression fixtures for real-world layouts, accessibility improvements for HTML reports, and clearer error messages. Discuss new language support before implementation: each language needs its own parser and evidence contract.
