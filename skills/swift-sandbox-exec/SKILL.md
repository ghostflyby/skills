---
name: swift-sandbox-exec
description: On macOS, pass --disable-sandbox to swift build/test/package when running inside Codex sandbox.
metadata:
  short-description: Disable SwiftPM nested sandbox-exec for Codex macOS sandbox
---

# Swift sandbox-exec fix (macOS + Codex)

This skill is a companion to `codex-writable-roots`. Together they cover the
two sides of making Swift work inside Codex's sandbox on macOS: filesystem
access (writable roots) and process sandboxing (this skill).

## Problem

Codex uses macOS App Sandbox (Seatbelt) to isolate command execution. The
macOS kernel does not allow a process already inside a sandbox to call
`sandbox-exec` to nest another sandbox.

SwiftPM calls `sandbox-exec` internally during `swift build` and `swift test`.
When run inside Codex's sandbox (`sandbox_mode = "workspace-write"` or
`"read-only"`), these nested calls fail with:

```
Sandbox: sandbox_exec(..., deny) - the process is already sandboxed
```

## Instruction for agents

When running Swift commands on macOS inside a Codex session with sandbox_mode
`workspace-write` or `read-only`, add `--disable-sandbox`:

```bash
swift build --disable-sandbox
swift test --disable-sandbox
swift package --disable-sandbox <subcommand>
```

### Rationale

- `--disable-sandbox` tells SwiftPM to skip its own sandbox-exec call.
- Codex's sandbox already provides isolation; the SwiftPM layer is redundant.
- The flag has no effect on non-macOS platforms (Linux, Windows), so it is
  safe to include unconditionally on macOS.
- To still allow SwiftPM filesystem writes, also apply the recommended
  writable roots from the `codex-writable-roots` skill.

### Detection

- If the user asks to build/test a Swift project and you are running on
  macOS, add `--disable-sandbox`.
- If a previous command failed with `sandbox_exec(..., deny)`, this is the
  cause.
- When in doubt, use `--disable-sandbox` on macOS -- it is harmless to
  non-sandboxed sessions and fixes the problem when sandboxed.
