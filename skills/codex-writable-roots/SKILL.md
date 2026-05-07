---
name: codex-writable-roots
description: Inspect language and package-manager cache directories and generate or apply Codex sandbox_workspace_write.writable_roots entries. Use when configuring Codex writable roots for Gradle, Maven, SwiftPM, Go, Cargo, NuGet, Python, Node, Deno, Kotlin Native, vcpkg, or similar rebuildable toolchain caches.
metadata:
  short-description: Generate Codex writable roots for tool caches
---

# Codex Writable Roots

Use this skill when a user wants to discover, generate, or maintain Codex
`sandbox_workspace_write.writable_roots` for rebuildable toolchain caches and
package directories.

## Workflow

1. Run the bundled script in read-only mode first:

```bash
python3 "$CODEX_HOME/skills/codex-writable-roots/scripts/codex-writable-roots.py" inspect
```

If `CODEX_HOME` is unset, use `~/.codex` as the skill root.

2. Review the table before proposing changes. Prefer `recommended` roots for
routine sandbox writes; mention `optional` roots when they are useful but larger
or less universally needed. Do not suggest `avoid` roots as writable roots.

If a root comes from a default convention rather than an explicit environment
variable or config file, verify that convention with official docs or web search
when those tools are available. This is especially important for commands whose
output can depend on the current directory, sandbox write permissions, or project
state.

3. Generate a TOML snippet when the user asks what to add:

```bash
python3 "$CODEX_HOME/skills/codex-writable-roots/scripts/codex-writable-roots.py" emit-toml
```

4. Only mutate `~/.codex/config.toml` when the user explicitly asks to apply:

```bash
python3 "$CODEX_HOME/skills/codex-writable-roots/scripts/codex-writable-roots.py" apply
```

The apply command creates a timestamped backup and merges the recommended roots
into `[sandbox_workspace_write].writable_roots`.

## Guardrails

- Emit absolute paths. Codex config should not rely on `~`, environment
  variables, or interpolation for writable roots.
- Keep writable roots narrow: cache/store subdirectories are preferred over
  whole config homes, package-manager installations, or broad cache parents.
- Treat results as environment-specific. Tool probes, config files, and
  environment variables should override defaults when available.
- Re-check default path rules against official docs or online search when
  available. Do not blindly trust cwd-sensitive probes such as active package
  store commands.
- Read-only commands are safe for exploration; `apply` is the only command that
  writes config.
