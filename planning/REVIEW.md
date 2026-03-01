# Review: Changes Since Last Commit

## Findings

### 1. [HIGH] Stop hook can recursively trigger itself via `codex exec`
The new plugin registers a wildcard `Stop` hook that runs `codex exec ... planning/REVIEW.md`. If stop hooks are processed for nested `codex exec` sessions, this can self-trigger repeatedly and spawn review loops.

References:
- [independent-reviewer/hooks/hooks.json](/Users/garrettkucinski/dev/agentic-coding/finally/independent-reviewer/hooks/hooks.json:3)
- [independent-reviewer/hooks/hooks.json](/Users/garrettkucinski/dev/agentic-coding/finally/independent-reviewer/hooks/hooks.json:5)
- [independent-reviewer/hooks/hooks.json](/Users/garrettkucinski/dev/agentic-coding/finally/independent-reviewer/hooks/hooks.json:9)

### 2. [HIGH] Documented quick start is currently not runnable from repo contents
README instructs `cp .env.example .env` and `docker compose up`, but the repository currently has neither `.env.example` nor `docker-compose.yml`. New users following the documented path will fail immediately.

References:
- [README.md](/Users/garrettkucinski/dev/agentic-coding/finally/README.md:10)
- [README.md](/Users/garrettkucinski/dev/agentic-coding/finally/README.md:11)

### 3. [HIGH] `PLAN.md` presents planned infrastructure as if already present
The plan now describes concrete files (`frontend/Dockerfile`, `backend/Dockerfile`, `docker-compose.yml`, `backend/schema/`) and compose-driven workflows as existing project structure. In the current tree, these files are absent, which creates implementation drift and misleading onboarding guidance.

References:
- [planning/PLAN.md](/Users/garrettkucinski/dev/agentic-coding/finally/planning/PLAN.md:97)
- [planning/PLAN.md](/Users/garrettkucinski/dev/agentic-coding/finally/planning/PLAN.md:100)
- [planning/PLAN.md](/Users/garrettkucinski/dev/agentic-coding/finally/planning/PLAN.md:105)
- [planning/PLAN.md](/Users/garrettkucinski/dev/agentic-coding/finally/planning/PLAN.md:114)

### 4. [MEDIUM] Database schema section is internally inconsistent on `user_id`
The schema intro states all tables use `user_id` defaulting to `'default'`, but the table definitions specify UUID foreign keys to `users(id)`. These models are incompatible and can cause conflicting implementations.

References:
- [planning/PLAN.md](/Users/garrettkucinski/dev/agentic-coding/finally/planning/PLAN.md:223)
- [planning/PLAN.md](/Users/garrettkucinski/dev/agentic-coding/finally/planning/PLAN.md:232)

### 5. [MEDIUM] Repo-level config now hard-enables a local custom plugin
`.claude/settings.json` enables `independent-reviewer@gk-tools`, but that depends on local marketplace/plugin setup. In clean environments this can cause tooling drift or startup/config errors unless the plugin is installed everywhere.

References:
- [.claude/settings.json](/Users/garrettkucinski/dev/agentic-coding/finally/.claude/settings.json:2)
- [.claude/settings.json](/Users/garrettkucinski/dev/agentic-coding/finally/.claude/settings.json:3)
- [.claude-plugin/marketplace.json](/Users/garrettkucinski/dev/agentic-coding/finally/.claude-plugin/marketplace.json:10)

## Open Questions
- Should README/PLAN describe current state only, or explicitly separate "implemented now" vs "target architecture"?
- Should the review hook be opt-in (manual command) instead of global `Stop` automation?
- Should local/editor-specific files like `.claude/settings.local.json` and plugin marketplace metadata be gitignored?

## Residual Risk
This review is limited to changed/untracked files in the working tree and does not validate runtime behavior because the described Docker/runtime artifacts are not yet present.
