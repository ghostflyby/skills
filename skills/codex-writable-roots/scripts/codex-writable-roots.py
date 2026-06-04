#!/usr/bin/env python3
"""Inspect and maintain Codex writable roots for toolchain caches."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


HOME = Path.home()
CODEX_HOME = Path(os.environ.get("CODEX_HOME", HOME / ".codex")).expanduser()
DEFAULT_CONFIG = CODEX_HOME / "config.toml"
SHORT_TIMEOUT = 4


@dataclass(frozen=True)
class Root:
    tool: str
    classification: str
    path: str
    source: str
    exists: bool
    notes: str


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect or update Codex writable roots for rebuildable tool caches."
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("inspect", "emit-toml", "apply"),
        default="inspect",
        help="inspect prints a table, emit-toml prints a config snippet, apply updates config.toml",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG),
        help="Codex config.toml path for apply and existing-root reads",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="include optional roots in emitted or applied writable_roots",
    )
    parser.add_argument(
        "--no-probe",
        action="store_true",
        help="skip tool subprocess probes and rely on environment/config/defaults",
    )
    args = parser.parse_args()

    roots = collect_roots(probe=not args.no_probe)
    roots = dedupe_roots(roots)

    if args.command == "inspect":
        print_markdown_table(roots)
        return 0
    if args.command == "emit-toml":
        selected = selected_roots(roots, include_optional=args.include_optional)
        print(emit_toml_snippet(selected))
        return 0
    if args.command == "apply":
        selected = selected_roots(roots, include_optional=args.include_optional)
        result = apply_config(Path(args.config).expanduser(), selected)
        print(result)
        return 0

    parser.error(f"unknown command: {args.command}")


def collect_roots(*, probe: bool) -> list[Root]:
    roots: list[Root] = []
    roots.extend(gradle_roots())
    roots.extend(maven_roots())
    roots.extend(swift_roots())
    roots.extend(go_roots(probe=probe))
    roots.extend(cargo_roots())
    roots.extend(rustup_roots())
    roots.extend(nuget_roots(probe=probe))
    roots.extend(python_roots(probe=probe))
    roots.extend(node_roots(probe=probe))
    roots.extend(deno_roots(probe=probe))
    roots.extend(kotlin_daemon_roots())
    roots.extend(konan_roots())
    roots.extend(vcpkg_roots())
    roots.extend(codex_runtime_roots())
    roots.extend(avoid_roots())
    return roots


def gradle_roots() -> list[Root]:
    path = first_path_env("GRADLE_USER_HOME") or HOME / ".gradle"
    source = "GRADLE_USER_HOME" if "GRADLE_USER_HOME" in os.environ else "default"
    return [
        make_root(
            "Gradle",
            "recommended",
            path,
            source,
            "Gradle user home; rebuildable caches, wrapper dists, and daemon state",
        )
    ]


def maven_roots() -> list[Root]:
    settings = [HOME / ".m2" / "settings.xml", HOME / ".m2" / "settings-security.xml"]
    repo = parse_maven_local_repo(settings)
    source = "~/.m2/settings.xml" if repo else "default"

    return [
        make_root(
            "Maven",
            "optional",
            repo or HOME / ".m2" / "repository",
            source,
            "Local artifact repository; optional because ~/.m2 may also contain credentials/settings",
        )
    ]


def swift_roots() -> list[Root]:
    env_path = first_path_env("SWIFTPM_HOME")
    if env_path:
        cache_path = env_path
        cache_source = "SWIFTPM_HOME"
    else:
        cache_path = cache_home() / "org.swift.swiftpm"
        cache_source = "default macOS cache"

    roots = [
        make_root(
            "SwiftPM",
            "recommended",
            cache_path,
            cache_source,
            "Swift Package Manager cache: cloned repos, manifests, prebuilts, artifacts",
        ),
    ]

    # Data directory: package fingerprints, collection config, SDKs.
    # macOS puts it at ~/Library/org.swift.swiftpm (not under Caches).
    # This is machine-generated metadata that can be recreated.
    # SWIFTPM_HOME only controls the cache dir, not the data dir.
    data_path = swiftpm_data_dir()
    if data_path:
        roots.append(
            make_root(
                "SwiftPM",
                "recommended",
                data_path,
                "platform convention",
                "SwiftPM data dir: fingerprints, collection config, SDKs; written during dependency resolution and build",
            )
        )

    return roots


def swiftpm_data_dir() -> Path | None:
    """Return the SwiftPM data directory by platform convention."""
    if sys.platform == "darwin":
        return HOME / "Library" / "org.swift.swiftpm"
    if os.name == "nt":
        local_app_data = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local"))
        return local_app_data / "swift-pm"
    xdg_data = first_path_env("XDG_DATA_HOME") or HOME / ".local" / "share"
    return xdg_data / "swift-pm"


def go_roots(*, probe: bool) -> list[Root]:
    values = go_env(["GOCACHE", "GOMODCACHE", "GOPATH"], probe=probe)
    gopath = values.get("GOPATH") or str(HOME / "go")
    return [
        make_root(
            "Go",
            "recommended",
            values.get("GOCACHE") or cache_home() / "go-build",
            "go env GOCACHE" if "GOCACHE" in values else "default",
            "Build cache",
        ),
        make_root(
            "Go",
            "recommended",
            values.get("GOMODCACHE") or Path(gopath) / "pkg" / "mod",
            "go env GOMODCACHE" if "GOMODCACHE" in values else "default GOPATH/pkg/mod",
            "Module download cache",
        ),
    ]


def cargo_roots() -> list[Root]:
    path = first_path_env("CARGO_HOME") or HOME / ".cargo"
    source = "CARGO_HOME" if "CARGO_HOME" in os.environ else "default"
    return [
        make_root(
            "Cargo",
            "recommended",
            path,
            source,
            "Cargo registry/git cache plus installed binaries",
        )
    ]


def rustup_roots() -> list[Root]:
    path = first_path_env("RUSTUP_HOME") or HOME / ".rustup"
    source = "RUSTUP_HOME" if "RUSTUP_HOME" in os.environ else "default"
    return [
        make_root(
            "rustup",
            "optional",
            path,
            source,
            "Toolchain downloads; large but rebuildable",
        )
    ]


def nuget_roots(*, probe: bool) -> list[Root]:
    parsed: dict[str, Path] = {}
    if probe:
        out = run_cmd(["dotnet", "nuget", "locals", "all", "--list"])
        if out.ok:
            parsed = parse_nuget_locals(out.stdout)

    roots = []
    defaults = {
        "global-packages": HOME / ".nuget" / "packages",
        "http-cache": platform_nuget_cache_base() / "http-cache",
        "plugins-cache": platform_nuget_cache_base() / "plugin-cache",
    }
    for name, default in defaults.items():
        notes = "NuGet package/cache directory"
        if name == "global-packages":
            notes = "Global package cache; use the packages subdir, not all ~/.nuget"
        roots.append(
            make_root(
                "NuGet",
                "recommended",
                parsed.get(name) or default,
                f"dotnet nuget locals {name}" if name in parsed else "default",
                notes,
            )
        )
    if "temp" in parsed:
        roots.append(
            make_root(
                "NuGet",
                "optional",
                parsed["temp"],
                "dotnet nuget locals temp",
                "NuGet scratch temp directory",
            )
        )
    return roots


def python_roots(*, probe: bool) -> list[Root]:
    roots = []
    uv_path = first_path_env("UV_CACHE_DIR")
    source = "UV_CACHE_DIR" if uv_path else "default"
    if uv_path is None and probe:
        out = run_cmd(["uv", "cache", "dir"])
        if out.ok and out.stdout.strip():
            uv_path = Path(out.stdout.strip().splitlines()[-1])
            source = "uv cache dir"
    roots.append(
        make_root(
            "uv",
            "recommended",
            uv_path or cache_home() / "uv",
            source,
            "uv package/build cache",
        )
    )

    pip_path = first_path_env("PIP_CACHE_DIR")
    source = "PIP_CACHE_DIR" if pip_path else "default"
    if pip_path is None and probe:
        out = run_cmd([sys.executable, "-m", "pip", "cache", "dir"])
        if not out.ok:
            out = run_cmd(["python3", "-m", "pip", "cache", "dir"])
        if out.ok and out.stdout.strip():
            pip_path = Path(out.stdout.strip().splitlines()[-1])
            source = "pip cache dir"
    roots.append(
        make_root(
            "pip",
            "recommended",
            pip_path or cache_home() / "pip",
            source,
            "pip wheel/http cache",
        )
    )
    return roots


def node_roots(*, probe: bool) -> list[Root]:
    roots = []
    npm_path = first_path_env("npm_config_cache")
    npm_source = "npm_config_cache" if npm_path else "default"
    if npm_path is None and probe:
        out = run_cmd(["npm", "config", "get", "cache"])
        if out.ok and out.stdout.strip() and out.stdout.strip() != "undefined":
            npm_path = Path(out.stdout.strip().splitlines()[-1])
            npm_source = "npm config get cache"
    roots.append(
        make_root(
            "npm",
            "recommended",
            npm_path or cache_home() / "npm",
            npm_source,
            "npm cache",
        )
    )

    pnpm_path = first_path_env("PNPM_STORE_DIR") or first_path_env("npm_config_store_dir")
    pnpm_source = "PNPM_STORE_DIR/npm_config_store_dir" if pnpm_path else "default"
    if pnpm_path is None:
        pnpm_path, pnpm_source = read_pnpm_store_dir_config()
    if pnpm_path is None:
        pnpm_path, pnpm_source = pnpm_default_store_dir()
    pnpm_path = trim_pnpm_version_dir(pnpm_path)
    roots.append(
        make_root(
            "pnpm",
            "recommended",
            pnpm_path,
            pnpm_source,
            "pnpm content-addressable store",
        )
    )
    return roots


def deno_roots(*, probe: bool) -> list[Root]:
    deno_dir = first_path_env("DENO_DIR")
    source = "DENO_DIR" if deno_dir else "default"
    if deno_dir is None and probe:
        out = run_cmd(["deno", "info"])
        if out.ok:
            parsed = parse_deno_dir(out.stdout)
            if parsed:
                deno_dir = parsed
                source = "deno info"
    return [
        make_root(
            "Deno",
            "recommended",
            deno_dir or cache_home() / "deno",
            source,
            "Deno dependency and transpile cache",
        )
    ]


def kotlin_daemon_roots() -> list[Root]:
    roots = [
        make_root(
            "Kotlin compile daemon",
            "recommended",
            kotlin_daemon_run_files_path(),
            "Kotlin runtime-state default",
            "Kotlin/JVM daemon run files; narrow rebuildable state directory",
        )
    ]

    fallback = HOME / ".kotlin" / "daemon"
    if normalize_path(fallback) != roots[0].path:
        roots.append(
            make_root(
                "Kotlin compile daemon",
                "optional",
                fallback,
                "Kotlin fallback",
                "Fallback when the platform runtime-state base is unavailable",
            )
        )
    return roots


def kotlin_daemon_run_files_path() -> Path:
    """Mirror Kotlin's FileSystem.getRuntimeStateFilesPath("kotlin", "daemon")."""
    base = runtime_state_files_base_path()
    if base.exists() and base.is_dir():
        return base / "kotlin" / "daemon"
    return HOME / ".kotlin" / "daemon"


def runtime_state_files_base_path() -> Path:
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", tempfile_dir()))
    if sys.platform == "darwin":
        return HOME / "Library" / "Application Support"
    return first_path_env("XDG_DATA_HOME") or HOME / ".local" / "share"


def tempfile_dir() -> str:
    return os.environ.get("TMPDIR") or os.environ.get("TEMP") or os.environ.get("TMP") or "/tmp"


def konan_roots() -> list[Root]:
    path = first_path_env("KONAN_DATA_DIR") or HOME / ".konan"
    source = "KONAN_DATA_DIR" if "KONAN_DATA_DIR" in os.environ else "default"
    return [
        make_root(
            "Kotlin Native",
            "recommended",
            path,
            source,
            "Kotlin/Native compiler dependency cache",
        )
    ]


def vcpkg_roots() -> list[Root]:
    root = first_path_env("VCPKG_ROOT")
    if not root:
        root = HOME / "vcpkg" if (HOME / "vcpkg").exists() else HOME / ".local" / "vcpkg"
    roots = []
    for subdir in ("downloads", "buildtrees", "packages"):
        roots.append(
            make_root(
                "vcpkg",
                "optional",
                root / subdir,
                "VCPKG_ROOT" if "VCPKG_ROOT" in os.environ else "default candidate",
                "vcpkg rebuildable cache/work directory",
            )
        )
    return roots


def codex_runtime_roots() -> list[Root]:
    return [
        make_root(
            "Codex plugins",
            "optional",
            CODEX_HOME / "plugins" / "cache",
            "Codex convention",
            "Plugin cache; narrower than all ~/.codex",
        ),
        make_root(
            "Codex runtimes",
            "optional",
            cache_home() / "codex-runtimes",
            "Codex convention",
            "Runtime plugin cache",
        ),
    ]


def avoid_roots() -> list[Root]:
    paths: list[tuple[str, Path, str]] = [
        ("Homebrew", Path("/opt/homebrew"), "Package-manager installation prefix, not just cache"),
        ("Codex", CODEX_HOME, "Too broad; contains config, secrets, sessions, and skills"),
        ("XDG config", HOME / ".config", "Too broad; usually persistent app configuration"),
        ("User caches", cache_home(), "Too broad; prefer specific tool cache subdirectories"),
        ("NuGet", HOME / ".nuget", "Too broad; prefer ~/.nuget/packages"),
    ]
    return [make_root(tool, "avoid", path, "guardrail", notes) for tool, path, notes in paths]


def make_root(
    tool: str, classification: str, path: str | Path, source: str, notes: str
) -> Root:
    normalized = normalize_path(path)
    return Root(
        tool=tool,
        classification=classification,
        path=normalized,
        source=source,
        exists=Path(normalized).exists(),
        notes=notes,
    )


def selected_roots(roots: Iterable[Root], *, include_optional: bool) -> list[str]:
    allowed = {"recommended"}
    if include_optional:
        allowed.add("optional")
    paths = [root.path for root in roots if root.classification in allowed]
    return sorted(dict.fromkeys(paths))


def dedupe_roots(roots: Iterable[Root]) -> list[Root]:
    by_key: dict[tuple[str, str], Root] = {}
    priority = {"recommended": 0, "optional": 1, "avoid": 2}
    for root in roots:
        key = (root.classification, root.path)
        if key not in by_key:
            by_key[key] = root
            continue
        old = by_key[key]
        if priority[root.classification] < priority[old.classification]:
            by_key[key] = root
    return sorted(by_key.values(), key=lambda r: (priority[r.classification], r.tool.lower(), r.path))


def print_markdown_table(roots: list[Root]) -> None:
    headers = ["Tool", "Class", "Path", "Source", "Exists", "Notes"]
    rows = [
        [
            root.tool,
            root.classification,
            root.path,
            root.source,
            "yes" if root.exists else "no",
            root.notes,
        ]
        for root in roots
    ]
    print("| " + " | ".join(headers) + " |")
    print("| " + " | ".join("---" for _ in headers) + " |")
    for row in rows:
        print("| " + " | ".join(escape_cell(cell) for cell in row) + " |")


def emit_toml_snippet(paths: list[str]) -> str:
    lines = ["[sandbox_workspace_write]", "writable_roots = ["]
    for path in paths:
        lines.append(f'  "{toml_escape(path)}",')
    lines.append("]")
    return "\n".join(lines)


def apply_config(config_path: Path, paths: list[str]) -> str:
    config_path = config_path.expanduser()
    had_config = config_path.exists()
    existing = config_path.read_text(encoding="utf-8") if had_config else ""
    existing_roots = parse_existing_writable_roots(existing)
    merged = sorted(dict.fromkeys([*existing_roots, *paths]))
    updated = replace_sandbox_section(existing, merged)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = config_path.with_name(f"{config_path.name}.bak-{timestamp}")
    if had_config:
        shutil.copy2(config_path, backup)
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(updated, encoding="utf-8")

    backup_text = f" backup: {backup}" if had_config else " no previous config to back up"
    return f"updated {config_path} with {len(merged)} writable_roots;{backup_text}"


def replace_sandbox_section(text: str, roots: list[str]) -> str:
    lines = text.splitlines()
    start, end = find_section(lines, "sandbox_workspace_write")
    root_block = ["writable_roots = [", *[f'  "{toml_escape(path)}",' for path in roots], "]"]

    if start is None:
        prefix = text.rstrip()
        addition = "\n\n[sandbox_workspace_write]\n" + "\n".join(root_block) + "\n"
        return prefix + addition if prefix else addition.lstrip()

    section_lines = lines[start:end]
    new_section: list[str] = []
    idx = 0
    inserted = False
    while idx < len(section_lines):
        line = section_lines[idx]
        key = line.split("=", 1)[0].strip()
        if key == "writable_roots":
            new_section.extend(root_block)
            inserted = True
            idx += 1
            if "[" in line and "]" not in line:
                while idx < len(section_lines) and "]" not in section_lines[idx]:
                    idx += 1
                if idx < len(section_lines):
                    idx += 1
            continue
        new_section.append(line)
        idx += 1

    if not inserted:
        insert_at = 1 if new_section and new_section[0].strip() == "[sandbox_workspace_write]" else len(new_section)
        new_section[insert_at:insert_at] = root_block

    replaced = [*lines[:start], *new_section, *lines[end:]]
    return "\n".join(replaced) + ("\n" if text.endswith("\n") or text else "")


def find_section(lines: list[str], section: str) -> tuple[int | None, int]:
    target = f"[{section}]"
    start = -1
    for idx, line in enumerate(lines):
        if line.strip() == target:
            start = idx
            break
    if start == -1:
        return None, len(lines)
    end = len(lines)
    for idx in range(start + 1, len(lines)):
        stripped = lines[idx].strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            end = idx
            break
    return start, end


def parse_existing_writable_roots(text: str) -> list[str]:
    lines = text.splitlines()
    start, end = find_section(lines, "sandbox_workspace_write")
    if start is None:
        return []
    section = lines[start:end]
    roots: list[str] = []
    collecting = False
    for line in section:
        stripped = line.strip()
        if stripped.startswith("writable_roots"):
            collecting = True
        if collecting:
            roots.extend(re.findall(r'"((?:[^"\\]|\\.)*)"', stripped))
            if "]" in stripped:
                collecting = False
    return [normalize_path(unescape_basic_toml(value)) for value in roots]


def parse_maven_local_repo(settings_paths: Iterable[Path]) -> Path | None:
    for settings in settings_paths:
        if not settings.exists():
            continue
        try:
            text = settings.read_text(encoding="utf-8")
        except OSError:
            continue
        match = re.search(r"<localRepository>\s*(.*?)\s*</localRepository>", text, re.DOTALL)
        if match:
            return Path(os.path.expandvars(match.group(1).strip())).expanduser()
    return None


def go_env(keys: list[str], *, probe: bool) -> dict[str, str]:
    values = {key: os.environ[key] for key in keys if os.environ.get(key)}
    if not probe:
        return values
    out = run_cmd(["go", "env", *keys])
    if not out.ok:
        return values
    for line in out.stdout.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in keys and value.strip():
            values[key] = value.strip().strip("'\"")
    if not values:
        plain_values = [line.strip() for line in out.stdout.splitlines() if line.strip()]
        for key, value in zip(keys, plain_values):
            values[key] = value.strip("'\"")
    return values


def parse_nuget_locals(text: str) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        name, path = line.split(":", 1)
        path = path.strip()
        if name.strip() and path:
            result[name.strip()] = Path(path)
    return result


def parse_deno_dir(text: str) -> Path | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("DENO_DIR"):
            _, _, value = stripped.partition(":")
            value = value.strip()
            if value:
                return Path(value)
    return None


def trim_pnpm_version_dir(path: Path) -> Path:
    if re.fullmatch(r"v\d+", path.name):
        return path.parent
    return path


def read_pnpm_store_dir_config() -> tuple[Path | None, str]:
    candidates = [
        HOME / ".npmrc",
        HOME / ".config" / "pnpm" / "rc",
        Path(os.environ.get("XDG_CONFIG_HOME", HOME / ".config")) / "pnpm" / "rc",
    ]
    for config in dict.fromkeys(candidates):
        if not config.exists():
            continue
        try:
            text = config.read_text(encoding="utf-8")
        except OSError:
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", ";")) or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            if key.strip() == "store-dir" and value.strip():
                return Path(os.path.expandvars(value.strip())).expanduser(), str(config)
    return None, "default"


def pnpm_default_store_dir() -> tuple[Path, str]:
    pnpm_home = first_path_env("PNPM_HOME")
    if pnpm_home:
        return pnpm_home / "store", "default PNPM_HOME"
    xdg_data_home = first_path_env("XDG_DATA_HOME")
    if xdg_data_home:
        return xdg_data_home / "pnpm" / "store", "default XDG_DATA_HOME"
    if sys.platform == "darwin":
        return HOME / "Library" / "pnpm" / "store", "default macOS"
    if os.name == "nt":
        local_app_data = Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local"))
        return local_app_data / "pnpm" / "store", "default Windows"
    return HOME / ".local" / "share" / "pnpm" / "store", "default Linux"


def cache_home() -> Path:
    if os.environ.get("XDG_CACHE_HOME"):
        return Path(os.environ["XDG_CACHE_HOME"]).expanduser()
    if sys.platform == "darwin":
        return HOME / "Library" / "Caches"
    return HOME / ".cache"


def platform_nuget_cache_base() -> Path:
    if sys.platform == "darwin":
        return HOME / ".local" / "share" / "NuGet"
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", HOME / "AppData" / "Local")) / "NuGet"
    return HOME / ".local" / "share" / "NuGet"


def first_path_env(name: str) -> Path | None:
    value = os.environ.get(name)
    if not value:
        return None
    return Path(os.path.expandvars(value)).expanduser()


def normalize_path(path: str | Path) -> str:
    raw = str(path)
    expanded = os.path.expandvars(os.path.expanduser(raw))
    return os.path.abspath(expanded).rstrip("/") or "/"


def toml_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def unescape_basic_toml(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def escape_cell(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


@dataclass(frozen=True)
class CmdResult:
    ok: bool
    stdout: str
    stderr: str


def run_cmd(cmd: list[str]) -> CmdResult:
    if shutil.which(str(cmd[0])) is None:  # noqa: Windows false positive; cmd[0] is always str on POSIX
        return CmdResult(False, "", f"{cmd[0]} not found")
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=SHORT_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return CmdResult(False, "", str(exc))
    return CmdResult(proc.returncode == 0, proc.stdout, proc.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
