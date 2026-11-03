# Opt-in, GitHub-hosted milestone coding agent

This repository has an unattended **coding** job (separate from its existing five-minute host validation). The hosted Ubuntu runner is temporary, not a permanent Linux machine. GitHub Actions schedules have a five-minute minimum and may start late. Once a job starts, a bounded Codex CLI session may work for up to 20 minutes before tests and a draft pull request are prepared. This is not continuous 24/7 one-minute model execution.

## Enabling it without a Linux computer

1. Under repository **Settings > Secrets and variables > Actions > Secrets**, create a repository secret named **CODEX_API_KEY** containing an API key allowed to call Codex models. This is a separate metered OpenAI API service, not free Codex Cloud access. Choose spending limits in the API billing dashboard.
2. Under **Settings > Secrets and variables > Actions > Variables**, create **ENABLE_HOSTED_CODING_AGENT** with value **true**. Until this variable is explicitly enabled, scheduled AI jobs are skipped. The workflow can also be started from **Actions > Opt-in hosted milestone coding agent > Run workflow**, selecting **run_agent**. The secret is still mandatory.
3. In repository **Settings > Actions > General > Workflow permissions**, ensure GitHub Actions is permitted to create pull requests if you want the worker to open draft PRs. If organizational policy prevents this, the branch push may succeed and the draft-PR creation step may fail; the workflow logs identify that blocker.
4. The workflow makes a branch named agent/<run id>-<attempt>, executes one bounded Codex session in a workspace-write sandbox, runs the repository's public-source smoke tests, validates the Git diff against a restrictive allowlist, and (only on success) pushes an **unmerged draft PR** for CI review. It will not silently merge potentially untested game code.
5. It skips the AI invocation if an earlier agent-generated PR is still open. This avoids duplicate work and overlapping branches. The pre-existing hourly ChatGPT development automation can review or merge passing PRs. Otherwise PRs can be reviewed in the GitHub Pull requests tab. After merge/closure, the next scheduled worker can select a new milestone.

## Monitoring

Ask ChatGPT: **"Check all four Nintendo DS project repositories on GitHub: latest main commit, open agent PRs, test results, merged milestones, blockers and what comes next. Do not claim the game complete unless original-asset end-to-end validation passes."**

For new projects, copy tools/hosted_milestone_agent.py, tests/test_hosted_milestone_agent.py, .github/workflows/hosted-milestone-agent.yml and the task instructions, then adapt the public-source smoke-test command. New repositories require their own CODEX_API_KEY secret and ENABLE_HOSTED_CODING_AGENT variable. Never copy private game assets into public source or CI artifacts.

## Stop control

Set ENABLE_HOSTED_CODING_AGENT to **false** to prevent subsequent scheduled AI runs; existing jobs may need to be cancelled from Actions. Running GitHub-hosted agents consumes Actions minutes where applicable and metered model API usage. No credentials or paid API runs are created automatically by adding this workflow.
