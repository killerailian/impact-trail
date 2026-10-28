# Impact Trail 0.1.0 Alpha

Explain the possible reach of a Python change with inspectable import trails.

- Local static analysis; no API key or runtime dependencies.
- Git comparisons including deleted files and removed imports.
- Relative imports, src layouts and scoped conftest evidence.
- Text, JSON, Markdown and offline HTML reports.
- English and Chinese documentation.

Install the attached wheel with `python -m pip install impact_trail-0.1.0-py3-none-any.whl`, or clone the repository and run `python -m pip install .`.

Requires Python 3.10+. This is an alpha review aid, not a safe test selector. Dynamic imports and runtime dependencies can be missed. Keep your required full CI suite. See README for limitations.
