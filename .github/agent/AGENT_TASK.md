# Autonomous DS/DSi milestone development (GitHub-hosted, opt-in)

Work on ONE high-impact, currently incomplete milestone for this Nintendo 3DS -> DS/DSi homebrew port.

1. Read README, feature backlog, relevant source/tests, and the compact OPEN PR and issue titles in the environment-provided context. Do not duplicate or overwrite existing work. Prefer substantive original-game functionality, rendering correctness, safe wireless/DSi-gated feature plumbing, save handling, and regressions over superficial chores.
2. Make concrete, bounded code changes in source/, tests/, tools/, docs/ or the established native build scripts. Add focused reproducible positive/negative tests. Keep original Nintendo media, commercial game binaries, extracted proprietary model/texture/audio data, encrypted materials, private hashes/manifests and privately staged ROMs OUT of all public commits and artifacts. Do not manufacture original assets.
3. Run tests when possible. Do not modify .github/, automation scripts, protected test files, credentials, CI permission settings or other infrastructure. Never delete a tracked file. Do not commit, create PRs, push to GitHub, fetch secrets, or call any external posting API yourself. The separate CI controller handles validation and draft PR creation.
4. If a task needs unavailable proprietary original data or device/emulator capability, do not fake acceptance; instead work on the highest-impact independent source improvement and add a failing-closed synthetic regression. End with a brief factual report about the code changes and tests. Do not claim original visual/gameplay parity unless actually proven.

An unattended job is bounded and can stop before the port is complete. Its next GitHub-hosted run or existing ChatGPT hourly milestone task will resume from GitHub. The workflow does NOT promise uninterrupted 60-second AI development or free inference.
