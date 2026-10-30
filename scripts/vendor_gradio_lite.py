"""Vendor @gradio/lite into docs/gradio-lite/ with its Python dependencies pinned.

Gradio-Lite 5.45.0 (the last release) installs the gradio wheels with micropip, which
picks the newest version of every dependency and does not backtrack. Newer releases of
those dependencies (e.g. huggingface-hub 1.x, recent anyio) break the install or the
import. To keep the app working, we host Gradio-Lite ourselves and patch its web worker
so it first installs a pinned dependency set: the newest version of each package that
was released on or before the Gradio-Lite release date.

Run with `pdm run vendor-lite`.
"""

import io
import json
import re
import shutil
from graphlib import TopologicalSorter
import urllib.request
import zipfile
from functools import cache
from pathlib import Path

from packaging.markers import Marker
from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

VERSION = "5.45.0"
RELEASE_DATE = "2025-09-10"
PACKAGE = f"@gradio/lite@{VERSION}"
OUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "gradio-lite"
PYODIDE_ENV = {
    "sys_platform": "emscripten",
    "platform_system": "Emscripten",
    "platform_machine": "wasm32",
    "os_name": "posix",
    "python_version": "3.12",
    "python_full_version": "3.12.7",
    "implementation_name": "cpython",
    "platform_python_implementation": "CPython",
}
INSTALL_HOOK = 'await s.loadPackage(["ssl","setuptools"]),'


def fetch(url):
    with urllib.request.urlopen(url) as response:
        return response.read()


@cache
def pypi_project(name):
    return json.loads(fetch(f"https://pypi.org/pypi/{name}/json"))


@cache
def pypi_release(name, version):
    return json.loads(fetch(f"https://pypi.org/pypi/{name}/{version}/json"))


def marker_applies(requirement, extras):
    if requirement.marker is None:
        return True
    return any(
        Marker(str(requirement.marker)).evaluate({**PYODIDE_ENV, "extra": extra})
        for extra in extras or {""}
    )


def pick_version(name, specifier):
    """Newest pure-Python release matching `specifier` published by RELEASE_DATE."""
    candidates = []
    for version, files in pypi_project(name)["releases"].items():
        try:
            parsed = Version(version)
        except InvalidVersion:
            continue
        pure_wheels = [
            f for f in files
            if f["filename"].endswith("-none-any.whl") and not f["yanked"]
        ]
        if (
            pure_wheels
            and not parsed.is_prerelease
            and parsed in specifier
            and min(f["upload_time"] for f in pure_wheels)[:10] <= RELEASE_DATE
        ):
            candidates.append(parsed)
    if not candidates:
        raise RuntimeError(f"No pure-Python release of {name} matches '{specifier}'")
    return str(max(candidates))


def resolve_pins(root_requirements, pyodide_packages, skip):
    """Pin the transitive closure of `root_requirements`, leaving out packages
    that Pyodide ships itself (micropip loads those from its own lock file)."""
    specifiers = {}
    extras = {}
    pending = list(root_requirements)
    pins = {}
    while pending:
        requirement, requested_by_extras = pending.pop()
        if not marker_applies(requirement, requested_by_extras):
            continue
        name = canonicalize_name(requirement.name)
        if name in skip or name in pyodide_packages:
            continue
        specifiers[name] = specifiers.get(name, SpecifierSet()) & requirement.specifier
        extras[name] = extras.get(name, set()) | requirement.extras
        version = pick_version(name, specifiers[name])
        if pins.get(name) == (version, frozenset(extras[name])):
            continue
        pins[name] = (version, frozenset(extras[name]))
        for dependency in pypi_release(name, version)["info"]["requires_dist"] or []:
            pending.append((Requirement(dependency), extras[name]))
    return pins


def install_order(pins):
    """Order pins so every package comes after its own pinned dependencies."""
    graph = {}
    for name, (version, extras) in pins.items():
        graph[name] = {
            canonicalize_name(requirement.name)
            for dependency in pypi_release(name, version)["info"]["requires_dist"] or []
            if marker_applies(requirement := Requirement(dependency), extras)
            and canonicalize_name(requirement.name) in pins
        }
    return [f"{name}=={pins[name][0]}" for name in TopologicalSorter(graph).static_order()]


def wheel_requirements(wheel_bytes):
    with zipfile.ZipFile(io.BytesIO(wheel_bytes)) as wheel:
        metadata_name = next(n for n in wheel.namelist() if n.endswith(".dist-info/METADATA"))
        metadata = wheel.read(metadata_name).decode()
    return [
        (Requirement(line.removeprefix("Requires-Dist: ")), set())
        for line in metadata.splitlines()
        if line.startswith("Requires-Dist: ")
    ]


def main():
    listing = json.loads(fetch(f"https://data.jsdelivr.com/v1/package/npm/{PACKAGE}/flat"))
    paths = [
        f["name"]
        for f in listing["files"]
        if f["name"].startswith("/dist/") and not f["name"].endswith(".map")
    ]

    shutil.rmtree(OUT_DIR, ignore_errors=True)
    for path in paths:
        target = OUT_DIR / path.removeprefix("/dist/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(fetch(f"https://cdn.jsdelivr.net/npm/{PACKAGE}{path}"))

    worker_path = next(OUT_DIR.glob("assets/webworker-*.js"))
    worker = worker_path.read_text()
    pyodide_version = re.search(r"pyodide/(v[\d.]+)/full", worker).group(1)
    lock = json.loads(fetch(f"https://cdn.jsdelivr.net/pyodide/{pyodide_version}/full/pyodide-lock.json"))
    pyodide_packages = {canonicalize_name(name) for name in lock["packages"]}

    roots = []
    for wheel_path in OUT_DIR.glob("assets/*.whl"):
        roots += wheel_requirements(wheel_path.read_bytes())
    pins = resolve_pins(roots, pyodide_packages, skip={"gradio", "gradio-client", "ffmpy"})  # ffmpy is mocked by Gradio-Lite

    if worker.count(INSTALL_HOOK) != 1:
        raise RuntimeError(f"Could not find the install hook in {worker_path.name}")
    # Install one at a time, dependencies first, so micropip finds every requirement
    # already satisfied instead of resolving it to the newest release.
    # (`deps=False` would be simpler but hits a bug in Pyodide 0.27's micropip.)
    pinned = install_order(pins)
    worker_path.write_text(
        worker.replace(
            INSTALL_HOOK,
            f"{INSTALL_HOOK}await(async()=>{{for(const r of {json.dumps(pinned)})await i.install(r)}})(),",
        )
    )

    print(f"Vendored {len(paths)} files from {PACKAGE} into {OUT_DIR}")
    print(f"Pinned {len(pinned)} packages released by {RELEASE_DATE}:")
    for requirement in pinned:
        print(f"  {requirement}")


if __name__ == "__main__":
    main()
