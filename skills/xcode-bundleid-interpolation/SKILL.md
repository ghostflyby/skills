---
name: xcode-bundleid-interpolation
description: configuring or changing Xcode bundle identifiers or ID of an app, extension target, XPC or app group. initializing a Xcode project with such ID.
metadata:
  short-description: Xcode identity tree — bundle ID interpolation, plist authority, TEAMID injection
---

# Xcode Identity Tree: Bundle ID Interpolation & Plist Authority

Pattern for multi-target projects (app + extension/XPC targets): one identity
root, everything else derived, runtime code reads Info.plist.

## One Root, Everything Derived

Define one project-level build setting as the only literal; derive the rest
with `$()` interpolation (nesting works):

```
BASE_BUNDLE_ID = com.example.myapp              ← the only literal
App bundle id       = $(BASE_BUNDLE_ID)
Extension bundle id = $(EXT_BUNDLE_ID_MAIN) = $(BASE_BUNDLE_ID).main
App Group ID        = APP_GROUP_ID = $(TeamIdentifierPrefix)group.$(BASE_BUNDLE_ID)
Connection names    = $(PRODUCT_BUNDLE_IDENTIFIER)_Connection   // if IME
```

Entitlements use the same variables; Xcode expands them at signing.

## Plist Is the Runtime Authority

Wherever code must equal another target's identity, make one build setting
dual-consumption: it is that target's `PRODUCT_BUNDLE_IDENTIFIER` **and** a
passthrough value in the app's Info.plist (e.g. an `ExtensionBundleIDs` dict).
Code reads the plist key — never a literal — and fails loudly if missing.

TEAMID: `$(TeamIdentifierPrefix)` is empty without a team, so open-source
contributors build with zero configuration; signed team builds get the prefix
automatically. App Store distribution = register the identifiers in the portal
and backfill the final string into the build setting. Never commit team data.

Never put the prefix into the bundle id itself: `CFBundleIdentifier` stays
plain reverse-DNS (the profile composites `TEAMID.bundleid` on its own).
Only entitlement *values* whose final string contains the team — App Groups
(`$(TeamIdentifierPrefix)group.…`) and keychain groups
(`$(AppIdentifierPrefix)…`) — take a prefix variable, at their use site.

## Gotchas

- Manual `codesign` does **not** expand `$(VARS)` in entitlements — sign via
  `xcodebuild`, or expand variables first.
- Info.plist expansion applies to **values only**; dictionary keys stay literal.
- Verification builds (`CODE_SIGNING_ALLOWED=NO`) embed no entitlements: no
  sandbox, no groups — fine for logic tests only.
