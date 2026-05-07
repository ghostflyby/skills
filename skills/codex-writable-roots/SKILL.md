---
name: codex-writable-roots
description: Inspect language and package-manager directories that are safely rebuildable and generate or apply Codex sandbox_workspace_write.writable_roots entries. Use when configuring Codex writable roots for Gradle, Maven, SwiftPM, Go, Cargo, NuGet, Python, Node, Deno, Kotlin Native, vcpkg, or similar rebuildable toolchain paths.
metadata:
  short-description: Generate Codex writable roots for rebuildable tool paths
---

# Codex Writable Roots

Use this skill when a user wants to discover, generate, or maintain Codex
`sandbox_workspace_write.writable_roots` for toolchain directories that are clearly and easily
rebuildable without loss. The goal is to allow writes to the narrowest possible set of
directories -- whether they are caches, data directories, or local stores -- as long as
they can be recreated on demand.

## Caveats

- The extra writable roots from `[sandbox_workspace_write].writable_roots` only take effect
  when `sandbox_mode = "workspace-write"` is set in the config profile. If the mode is
  `"use_default"` or anything else, the extra roots are silently ignored.
- In the Codex desktop app, the user must manually select **Custom** in the permissions
  dialog for the extra writable roots to be applied. The default permission presets do
  not include the custom writable roots from the config.
- When inspecting or debugging writable-roots behavior, always verify
  `sandbox_mode == workspace-write` and the effective writable-roots list in the
  target environment.

## Workflow

1. Run the bundled script in read-only mode first:

```bash
python3 "$CODEX_HOME/skills/codex-writable-roots/scripts/codex-writable-roots.py" inspect
```

If `CODEX_HOME` is unset, use `~/.codex` as the skill root.

2. Review the table before proposing changes. Prefer `recommended` roots for
routine sandbox writes; mention `optional` roots for paths that are rebuildable but larger
or less universally hit by common workflows. Do not suggest `avoid` roots as writable roots.

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
  whole config homes, package-manager installations, or broad parent directories.
- Prefer any path that is clearly and easily rebuildable without loss, regardless of whether
  it is called a "cache" or a "data" directory. The deciding factor is whether the tool
  can recreate it on demand with no user-visible side effects.
- Treat results as environment-specific. Tool probes, config files, and
  environment variables should override defaults when available.
- Re-check default path rules against official docs or online search when
  available. Do not blindly trust cwd-sensitive probes such as active package
  store commands.
- Read-only commands are safe for exploration; `apply` is the only command that
  writes config.
