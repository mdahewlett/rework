# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project aims to follow [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `rework list [--limit N]` — list finalized entries (id, date, slug), newest first.
- `rework session-note <text> [--id <id>]` — free-text note about a cycle or its metrics, on the live in-progress cycle or a finalized entry.
- `rework change-request <text>` — record a request to change the tool itself; `--list` shows the queue and `--set <id> <status>` updates it (`open` / `in-progress` / `done` / `wontfix`).
- `rework tags` — list the current category vocabulary.
- `rework help` (word command) and `rework help --all` — the command menu, or every command with its full arguments.
- `--json` output on `status`, `list`, `tags`, and `end` for machine-readable results; also the default when stdout is not a TTY. Works before or after the subcommand.
- `--version` / `-V`.
- Worked examples in `--help`.
- Finalized entries now carry a short id (e.g. `rXXXXXX`), printed by `end` and shown by `list`, used to attach a session note later.

### Changed
- Skill: "start rework" always stamps the current commit (HEAD) as A — the agent never asks which commit to use.
- Skill: the agent never suggests ending or wrapping up a rework session; only the user decides when to end.

### Fixed
- Worktrees logged to the wrong file: repo identity used the worktree directory name, so a worktree wrote to `<branch>.jsonl` instead of the shared `<repo>.jsonl`. Now derived from the common git dir, so all worktrees and the main checkout share one per-repo log (as documented).

## [0.1.0] - 2026-06-24

### Added
- Core rework tracking: `start` (commit A) → `note` / `build` / `review` → `end` (commit B), computing `ai_lines`, `rework_lines`, `rework_pct`, files, and hunks.
- `base` command and `--base` / `--at` flags for setting the pre-AI baseline and back-filling commit A.
- `status` — show the in-progress entry.
- Open, auto-registering category vocabulary for notes.
- Harness-agnostic packaging: CLI-first, with an optional per-harness skill file and a one-line installer.
- Parallel-worktree support (one in-progress entry keyed per repo + branch).
