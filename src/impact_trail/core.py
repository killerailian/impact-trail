"""Static, conservative import evidence. Never import the inspected project."""
from __future__ import annotations

import ast
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
import os
import subprocess
import tokenize


class AnalysisError(Exception):
    """An actionable input or Git error."""


@dataclass(frozen=True, order=True)
class Edge:
    importer: str
    dependency: str
    line: int
    reason: str = "import"
    snapshot: str = "working"


def git(root: Path, *args: str) -> bytes:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args], capture_output=True, timeout=30,
            env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AnalysisError(f"Cannot run Git: {exc}") from exc
    if result.returncode:
        raise AnalysisError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def split_paths(raw: bytes) -> list[str]:
    return [os.fsdecode(p) for p in raw.split(b"\0") if p]


def normalize_path(value: str) -> str:
    p = PurePosixPath(value.replace("\\", "/"))
    if p.is_absolute() or ".." in p.parts or (p.parts and ":" in p.parts[0]):
        raise AnalysisError(f"Expected a repository-relative path: {value!r}")
    return p.as_posix()


def discover(root: Path) -> list[str]:
    excluded = {".git", ".venv", "venv", "node_modules", "__pycache__", "build", "dist", ".tox"}
    result = []
    for parent, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in excluded and not (Path(parent) / d).is_symlink())
        for name in sorted(files):
            p = Path(parent) / name
            if name.endswith(".py") and not p.is_symlink():
                result.append(p.relative_to(root).as_posix())
    return sorted(result)


def module_name(path: str, source: str) -> str | None:
    p = PurePosixPath(path)
    try:
        p = p.relative_to(source) if source != "." else p
    except ValueError:
        return None
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def is_test(path: str) -> bool:
    name = PurePosixPath(path).name
    return name.startswith("test_") and name.endswith(".py") or name.endswith("_test.py")


def build_edges(sources: dict[str, list[tuple[str, str]]], roots: list[str]):
    index: dict[str, set[str]] = defaultdict(set)
    names: dict[str, str] = {}
    warnings: set[str] = set()
    for path in sorted(sources):
        for root in roots:
            name = module_name(path, root)
            if name:
                index[name].add(path)
                names.setdefault(path, name)
    for name, paths in sorted(index.items()):
        if len(paths) > 1:
            warnings.add(f"Ambiguous module {name}: {', '.join(sorted(paths))}; all candidates retained.")
    edges: set[Edge] = set()
    for path, versions in sorted(sources.items()):
        for snapshot, content in versions:
            try:
                tree = ast.parse(content, filename=path)
            except (SyntaxError, ValueError, RecursionError) as exc:
                warnings.add(f"Cannot parse {path} ({snapshot}): {type(exc).__name__}; import evidence is incomplete.")
                continue
            current = names.get(path, "")
            package = current if path.endswith("/__init__.py") else current.rpartition(".")[0]
            def add(target: str, line: int):
                # Importing a.b executes local a/__init__.py as well.
                parts = target.split(".")
                for size in range(1, len(parts) + 1):
                    candidate = ".".join(parts[:size])
                    for dependency in index.get(candidate, ()):
                        if dependency != path:
                            edges.add(Edge(path, dependency, line, "import", snapshot))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        add(alias.name, node.lineno)
                elif isinstance(node, ast.ImportFrom):
                    if node.level:
                        parts = package.split(".") if package else []
                        if node.level > len(parts):
                            warnings.add(f"Unresolved relative import in {path}:{node.lineno} ({snapshot}).")
                            continue
                        prefix = parts[:len(parts) - node.level + 1]
                        base = ".".join(prefix + ([node.module] if node.module else []))
                    else:
                        base = node.module or ""
                    add(base, node.lineno)
                    for alias in node.names:
                        if alias.name != "*":
                            add(f"{base}.{alias.name}" if base else alias.name, node.lineno)
                elif isinstance(node, ast.Call):
                    fn = node.func
                    if ((isinstance(fn, ast.Name) and fn.id in {"__import__", "exec", "eval"})
                        or (isinstance(fn, ast.Attribute) and fn.attr == "import_module")):
                        warnings.add(f"Dynamic code/import in {path}:{node.lineno} ({snapshot}); review manually.")
    # pytest discovers conftest.py without an explicit import.
    for fixture in sorted(sources):
        if PurePosixPath(fixture).name != "conftest.py":
            continue
        parent = PurePosixPath(fixture).parent
        for test in sorted(sources):
            if is_test(test) and PurePosixPath(test).is_relative_to(parent):
                edges.add(Edge(test, fixture, 0, "pytest conftest scope", "inferred"))
    return sorted(edges), sorted(warnings)


def analyze(root: Path, changed: list[str] | None = None, base: str | None = None,
            source_roots: list[str] | None = None) -> dict:
    root = root.resolve()
    if not root.is_dir():
        raise AnalysisError(f"Not a directory: {root}")
    roots = [normalize_path(x) for x in (source_roots or (["src", "."] if (root / "src").is_dir() else ["."]))]
    if not roots:
        raise AnalysisError("At least one source root is required")
    warnings: list[str] = []
    baseline = None
    old_paths: set[str] = set()
    if base is not None or changed is None:
        top = Path(os.fsdecode(git(root, "rev-parse", "--show-toplevel")).strip()).resolve()
        if top != root:
            raise AnalysisError("For Git mode, --root must be the repository root")
        ref = base or "HEAD"
        baseline = git(root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode().strip()
        # --no-renames includes both sides of a rename; -z preserves unusual filenames.
        detected = split_paths(git(root, "diff", "--no-ext-diff", "--no-renames", "--name-only", "-z", baseline, "--"))
        detected += split_paths(git(root, "ls-files", "--others", "--exclude-standard", "-z"))
        if changed is None:
            changed = detected
        current_paths = set(split_paths(git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")))
        old_paths = set(split_paths(git(root, "ls-tree", "-r", "--name-only", "-z", baseline)))
        paths = sorted(p for p in current_paths | old_paths if p.endswith(".py"))
        old_needed = set(detected)
    else:
        paths = discover(root)
        old_needed = set()
    changed = sorted(set(normalize_path(p) for p in changed or []))
    sources: dict[str, list[tuple[str, str]]] = {}
    for path in paths:
        full = root / path
        # Never follow symlinks out of the requested tree.
        if not full.resolve().is_relative_to(root) or full.is_symlink():
            warnings.append(f"Skipped symlink or external path: {path}")
            continue
        versions = []
        if full.is_file():
            try:
                if full.stat().st_size > 2_000_000:
                    warnings.append(f"Skipped file over 2 MB: {path}")
                else:
                    with tokenize.open(full) as f:
                        versions.append(("working", f.read()))
            except (OSError, UnicodeError, SyntaxError) as exc:
                warnings.append(f"Cannot read {path}: {type(exc).__name__}")
        if baseline and path in old_paths and (path in old_needed or not versions):
            raw = git(root, "show", f"{baseline}:{path}")
            if len(raw) <= 2_000_000:
                import io
                try:
                    encoding, _ = tokenize.detect_encoding(io.BytesIO(raw).readline)
                    versions.append(("base", raw.decode(encoding)))
                except (UnicodeError, SyntaxError):
                    warnings.append(f"Cannot decode baseline file: {path}")
            else:
                warnings.append(f"Skipped baseline file over 2 MB: {path}")
        if versions:
            sources[path] = versions
    edges, parse_warnings = build_edges(sources, roots)
    warnings.extend(parse_warnings)
    reverse: dict[str, list[Edge]] = defaultdict(list)
    for edge in edges:
        reverse[edge.dependency].append(edge)
    trails: dict[str, list[dict]] = {p: [] for p in changed}
    origins = {p: p for p in changed}
    queue = deque(changed)
    while queue:
        dependency = queue.popleft()
        for edge in reverse[dependency]:
            if edge.importer not in trails:
                trails[edge.importer] = trails[dependency] + [asdict(edge)]
                origins[edge.importer] = origins[dependency]
                queue.append(edge.importer)
    impacts = [{"path": p, "kind": "test" if is_test(p) else "module",
                "changed": p in changed, "origin": origins[p], "trail": trails[p]}
               for p in sorted(trails) if p in sources]
    unknown = [p for p in changed if p not in sources]
    if unknown:
        warnings.append("Changes outside the analyzed Python graph: " + ", ".join(unknown))
    warnings = sorted(set(warnings))
    tests = sorted(p for p in trails if is_test(p) and p in sources and (root / p).is_file())
    return {
        "schema_version": 1, "tool": "impact-trail", "baseline": baseline,
        "source_roots": roots, "changed": changed, "files_analyzed": len(sources),
        "edges_analyzed": len(edges), "impacts": impacts, "candidate_tests": tests,
        "warnings": warnings, "full_suite_recommended": bool(warnings),
        "limitations": [
            "Static import reachability is not proof of runtime behavior or test coverage.",
            "Dynamic imports, plugins, data files, runtime path changes and monkeypatching may be missed.",
            "Conditional and type-only imports are included conservatively; false positives are expected.",
            "Always run your normal required CI suite; this tool does not deselect tests.",
        ],
    }
