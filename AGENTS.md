# Autonomous DS/DSi full-original-game development contract

## Goal and authority
Build a faithful playable Nintendo DS/DSi port of the **entire original Nintendo 3DS Pokémon Dream Radar game**, not a prototype or a reference-only recreation. The canonical compatibility contract is issue #157. Scope: Cloud search, sphere capture, research lab, upgrades, rewards, saves, camera adaptation and transfer.

## Every development run
1. Read the latest `main`, open PRs, current CI and emulator evidence, feature-parity inventory, and up to five active implementation milestone issues. Reuse existing issues; do not create duplicate milestones.
2. Select the highest-priority **unimplemented or unverified original feature** that can be advanced with a meaningful, testable source change. Prefer end-to-end gameplay, original assets and rendering, save integration and DS/DSi behavior over cosmetic cleanup or documentation-only changes.
3. Write a regression that fails on original code for the expected behavior, then implement the smallest real production change to pass it. Reject no-op edits, repeated assertions, tautologies, mock-only tests, and patches without a user-visible or safety-relevant effect.
4. Run applicable host tests, BlocksDS ROM compilation, and actual melonDS screenshots/smoke tests when toolchains are available. Record commands, commits, failures and evidence. Never report unavailable tests as passing.
5. Publish code on a branch/PR, require independent CI, and merge only after all applicable checks and guarded approval conditions succeed. A failing or missing check blocks merge. When permissions block PR creation, retain the branch and report the precise setting or error; do not claim merge success.
6. After a verified milestone is merged, close it, activate exactly one replacement while keeping at most five active milestone issues, and continue the next feature in the next available run. Keep progress and blockers visible in GitHub.

## Fidelity and hardware constraints
- Original gameplay rules, UI flow, save behavior, graphics, animations, audio, progression, and available original-version/update features are the completion target. Preserve authentic authorized source assets where technically possible; optimize them for DS hardware.
- DSi-only features must be gated on DS. DS and 3DS GPU, radio and camera capabilities differ: test real interoperability and never claim unsupported native 3DS communication or pixel-perfect equivalence.
- Private Nintendo archives, keys, decrypted assets and proprietary converted outputs must never enter public source, diffs, CI logs or downloadable artifacts.
- Status categories: not implemented; implemented/unverified; emulator verified; hardware verified; blocked by documented platform/source limitation. Never label the full game complete while requirements remain unverified.

## Bounded local agent
The scheduled free Ollama agent currently has a **small explicit source/test allowlist**, not permission to rewrite the whole game. Use its tasks to produce genuinely useful verified slices; use the existing hourly developer for broader milestone implementations. The local model must read this contract and issue #157 as direction, but text instructions do not override code allowlists, workflow permissions or CI gates.
