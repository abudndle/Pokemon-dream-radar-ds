# Unattended Linux coding agent

This project has two distinct automated processes:

- Five-minute Dream Radar host validation builds/tests existing code, but never writes new gameplay code.
- The new Unattended Linux coding agent attempts a narrowly scoped code-and-test change with a local Ollama model and opens a **draft PR** only after the host suite passes. It never merges generated work.

## Schedule

GitHub-hosted Actions supports no schedule faster than once every **five minutes**. This workflow uses `*/5 * * * *`, runs on an ephemeral Linux runner, and queues concurrent starts. Scheduled starts can be delayed or skipped by GitHub. While any `agent/local-` pull request is open, the next run skips model inference to avoid duplicate PRs.

A true per-minute loop (`* * * * *`) needs an always-on Linux machine, VPS, or self-hosted runner with an agent installed and authenticated. GitHub-hosted Linux is not a permanent server. A minute tick cannot guarantee a finished improvement every minute, because model generation and tests may take longer. ChatGPT's existing hourly development automation remains a separate schedule.

## Operation and limits

The generation job fetches a small Ollama model on a Linux VM and exposes no GitHub write credentials. It allows literal edits only to one of these implementation/test pairs:

- DS/DSi platform compatibility: source/platform_compat.c and tests/test_platform_compat.c.
- Photo album: source/photo_album.c and tests/test_photo_album.c.
- Cloud animation: source/cloud_animation.c and tests/test_cloud_animation.c.

The agent cannot edit workflows, build settings, other code, or proprietary assets. It requires changes to both source and a test, passes `make test-host test-syntax`, checks `git diff --check`, and emits a patch. A separate publication job checks allowed paths and opens a **draft PR**. It also requests existing BlocksDS and capture acceptance workflows, because PRs created by GitHub's token do not generally trigger other PR workflows automatically.

**Important:** Repository Settings → Actions → General → Workflow permissions must permit GitHub Actions to create pull requests. If that setting or organizational restrictions block it, automated PR publishing will fail. Do not bypass those restrictions. Draft PRs need review and full ROM/emulator CI before merging.

The small local model can be inaccurate, fail to produce any safe changes, or exceed runner time limits. It is an experimental constrained code agent, **not** the full 3DS port or an equivalent to a large Codex agent. No private original Nintendo assets should enter the repository or public CI.

## Controls

Actions → Unattended Linux coding agent (draft PR only) → Run workflow triggers a manual attempt. Disable the workflow in GitHub Actions to stop new attempts. The existing hourly ChatGPT automation is unaffected.
