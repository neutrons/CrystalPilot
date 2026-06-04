"""Architectural import-boundary contracts.

Enforces the dependency rules that let TOPAZ (single-crystal) and USANS (SANS)
be developed in parallel without stepping on each other. Same spirit as a
``import-linter`` contracts file, implemented as a dependency-free AST scan in
the repo's existing ratchet style (cf. ``test_technique_coupling`` /
``test_beamline_coupling``) so it runs in the current pytest CI with no extra
tooling.

The contracts (a violation of any fails the build):

1. **Technique independence** — ``techniques/single_crystal`` and
   ``techniques/sans`` must not import each other. This is *the* guarantee that
   makes parallel development safe: churn in one technique cannot reach the
   other.
2. **Core is the bottom layer** — ``core/`` must not statically import ``app``,
   ``agent``, ``techniques`` or ``beamlines``. (Technique discovery happens via
   a lazy ``importlib`` string in ``core.beamline.technique``; that dynamic
   plug-in seam is intentional and invisible to this static check.)
3. **Techniques don't reach into the app shell** — a ``techniques/`` module must
   not import ``exphub.app``. Techniques depend only on ``core`` + the manifest
   contract.
4. **Beamline independence** — one ``beamlines/<id>/`` plug-in must not import
   another. (The ``beamlines/__init__`` aggregator that imports each to register
   it is exempt.)

App-shell modules (``mvvm_factory``, the dispatcher, type-checking hints) may
reference the default technique — the app is the composition root, so no
``app -> techniques`` rule is imposed.
"""

from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
_AGGREGATOR = "exphub.beamlines"  # the registration __init__; exempt from rule 4


def _module_name(path: Path) -> tuple[str, bool]:
    """Return (dotted module name, is_package) for a source file under ``src/``."""
    parts = list(path.relative_to(SRC).with_suffix("").parts)
    is_pkg = parts[-1] == "__init__"
    if is_pkg:
        parts = parts[:-1]
    return ".".join(parts), is_pkg


def _targets(importer: str, is_pkg: bool, node: ast.AST) -> set[str]:
    """Resolve an import node to the set of absolute ``exphub.*`` modules it pulls in."""
    out: set[str] = set()
    if isinstance(node, ast.Import):
        out.update(alias.name for alias in node.names)
    elif isinstance(node, ast.ImportFrom):
        if node.level == 0:
            base = node.module or ""
        else:
            pkg_parts = importer.split(".") if is_pkg else importer.split(".")[:-1]
            up = node.level - 1
            anchor = pkg_parts[: len(pkg_parts) - up] if up else pkg_parts
            base = ".".join(anchor)
            if node.module:
                base = f"{base}.{node.module}" if base else node.module
        if base:
            out.add(base)
            out.update(f"{base}.{alias.name}" for alias in node.names)
    return {t for t in out if t.startswith("exphub.")}


def _edges() -> list[tuple[str, str]]:
    """Every (importer_module, imported_exphub_module) static edge in src/exphub."""
    edges: list[tuple[str, str]] = []
    for py in SRC.rglob("*.py"):
        if "__pycache__" in py.parts:
            continue
        importer, is_pkg = _module_name(py)
        try:
            tree = ast.parse(py.read_text(encoding="utf-8", errors="ignore"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for target in _targets(importer, is_pkg, node):
                    edges.append((importer, target))
    return edges


def _beamline_id(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) >= 3 and parts[0] == "exphub" and parts[1] == "beamlines":
        return parts[2]
    return None


def _violations() -> list[str]:
    bad: list[str] = []
    for importer, target in _edges():
        # 1. technique independence
        if importer.startswith("exphub.techniques.single_crystal") and target.startswith("exphub.techniques.sans"):
            bad.append(f"single_crystal -> sans: {importer} imports {target}")
        if importer.startswith("exphub.techniques.sans") and target.startswith("exphub.techniques.single_crystal"):
            bad.append(f"sans -> single_crystal: {importer} imports {target}")
        # 2. core is the bottom layer
        if importer.startswith("exphub.core") and target.startswith(
            ("exphub.app", "exphub.agent", "exphub.techniques", "exphub.beamlines")
        ):
            bad.append(f"core -> upper layer: {importer} imports {target}")
        # 3. techniques must not import the app shell
        if importer.startswith("exphub.techniques") and target.startswith("exphub.app"):
            bad.append(f"technique -> app: {importer} imports {target}")
        # 4. beamline independence (aggregator __init__ exempt)
        if importer != _AGGREGATOR:
            a, b = _beamline_id(importer), _beamline_id(target)
            if a is not None and b is not None and a != b:
                bad.append(f"beamline {a} -> beamline {b}: {importer} imports {target}")
    return sorted(set(bad))


def test_no_import_boundary_violations() -> None:
    violations = _violations()
    assert not violations, (
        "Architectural import-boundary contract violated:\n"
        + "\n".join(f"  {v}" for v in violations)
        + "\n\nKeep techniques independent of each other, core at the bottom, "
        "techniques out of app/, and beamline plug-ins independent. See this "
        "module's docstring for the rationale."
    )
