# Local validation — 2026-10-27

Environment: Linux, Python 3.12.14, git version 2.51.1.

- 51 unittest executions passed: 22 analysis cases on both plain and Git-initialized trees, plus 7 Git-specific cases.
- Wheel built with setuptools and installed into a fresh virtual environment without network or dependencies.
- The installed CLI reproduced the synthetic demo: 1 changed path, 5 reached files, 2 candidate tests.
- Example JSON verified against those expected counts; no analysis warnings.
- HTML parsed successfully with 5 evidence cards and no external src/href assets.
- Report JavaScript passed Node syntax checking. Browser visual layout and interactive filtering were not end-to-end tested.
- Package source passed Python byte compilation.

The configured Windows/Python CI matrix has not run on GitHub. No public release, package-registry upload, third-party adoption, or star growth has been verified. No performance benchmark is claimed.
