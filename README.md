# rework

A solo AI-velocity tracker. It measures how much of an AI agent's **first complete
implementation** you change before you're satisfied enough to merge.

Industry "rework" metrics ask: of a merged PR's lines, how many get touched again within
~2 weeks? This adapts that to a **shorter, solo time scale** — treat the AI's first
implementation as the "merged PR," and your own pre-merge blessing as the "rework"
version. The gap between them tells you how well you're prompting and how agent-ready your
repo is.

Two boundaries, both triggered by you during a session:

- **A** — `rework start` — the AI's first complete implementation (current `HEAD`).
- **B** — `rework end` — you're satisfied, about to merge (current `HEAD`).

**Rework = git churn between A and B.**

## Install

The tool is a single Python file (stdlib only) that shells out to `git`. It works in **any
harness or none** — Claude Code, Codex, Cursor, Aider, or just your terminal.

One line:

```sh
curl -fsSL https://raw.githubusercontent.com/mdahewlett/rework/main/install.sh | bash
```

This clones to `~/.rework`, puts `rework` on your PATH, and — **only if it detects Claude
Code** — installs the optional skill and a SessionStart hook so Claude knows the tool is
there. It's idempotent; re-run it anytime to update. Other harnesses are left untouched.

<details>
<summary>Prefer not to pipe curl into bash? Manual install:</summary>

```sh
git clone https://github.com/mdahewlett/rework.git ~/.rework
ln -sf ~/.rework/rework.py ~/.local/bin/rework   # ensure ~/.local/bin is on PATH
```

That's the whole tool. For the optional agent integration, see
[Optional: agent integration](#optional-agent-integration) below.
</details>

The repo's code lives in `~/.rework/`. Your **data** — `<repo>.jsonl`, `_tags.json`,
`.wip-*.json` — is written alongside it but is gitignored, so it never gets committed.

> **Caveat:** because data and code share `~/.rework/`, avoid `git clean -x` here — it
> would delete your gitignored logs. Plain `git clean` is safe (respects `.gitignore`).

## Usage

```sh
rework start [slug] [description] [--harness X]   # stamp HEAD as A (AI's first effort)
rework note -c <category> "what you changed"      # add a categorized rework note
rework build <minutes>                            # plan -> first impl (you supply)
rework review <minutes>                           # review -> merge   (you supply)
rework end                                         # stamp HEAD as B, finalize & log
rework status                                      # show the in-progress entry
```

- Slug defaults to the current branch name (minus `feat/`, `fix/`, etc.). Override by
  passing it. One work item = one branch.
- Harness defaults to `claude-code`; override with `--harness codex` etc. to compare tools.
- Notes and times can be added in any order, anytime between `start` and `end`.

### Typical session

```sh
# on branch feat/feature-flags, after the AI's first pass:
rework start
# ...you review, ask for changes...
rework note -c architecture "moved flag client to core/ — config-adjacent infra"
rework note -c missed-spec  "added per-role targeting, not in original ask"
rework build 95
rework review 40
rework end
# logged 'feature-flags' -> toneapp.jsonl
#   ai_lines=420  rework_lines=63  rework_pct=15.0%  files=4  hunks=9
```

## What gets measured

For each work item, one append-only JSON line in `~/.rework/<repo>.jsonl`:

| Field | Meaning |
|---|---|
| `commits.base` | merge-base of your branch vs the default branch — the denominator anchor |
| `commits.a` / `commits.b` | the two boundaries (start / end rework) |
| `metrics.ai_lines` | churn `base..A` (added + deleted) — what the AI produced |
| `metrics.rework_lines` | churn `A..B` (added + deleted) — what you changed after |
| `metrics.rework_pct` | `rework_lines / ai_lines * 100` (`null` if the AI produced nothing) |
| `metrics.files_touched` / `metrics.hunks` | breadth + fragmentation of the rework |
| `files[]` | raw per-file churn `A..B` — *where* the rework landed (layer derived later) |
| `time.build_minutes` / `time.review_minutes` | your two time stages (supplied by you) |
| `rework_notes[]` | `{category, note}` — *what kind* of rework, in your words |

## Two axes of "where rework happens"

1. **Mechanical** — which files the churn landed in. Captured automatically from the diff.
   Layer mapping (`api`/`services`/`models`/…) is applied later at analysis time, not
   stored, so the rules can evolve without rewriting history.
2. **Qualitative** — what *kind* of problem it was, via the `rework_notes` categories.
   Naming the category in the moment is itself the point: it keeps you reasoning about the
   kind of issue, not just fixing it.

### Category vocabulary

An open set (new tags auto-register in `_tags.json`). Seeds:

- **architecture** — how code is split across files/layers; boundaries; wrong altitude.
- **wrong-abstraction** — duplication that should be shared; premature abstraction; wrong interface.
- **missed-spec** — the AI did what was asked, but the ask was incomplete; your extras.
- **style** — local code style: naming, idiom, type aliases, readability within a file (not structural).

## Storage layout

```
~/.rework/
  rework.py                       # the CLI (this repo)
  README.md                       # (this repo)
  .gitignore                      # excludes all data below
  <repo>.jsonl                    # append-only log, one work item per line  [data]
  _tags.json                      # category vocabulary                       [data]
  .wip-<repo>-<branch>.json       # transient in-progress entry, deleted on end [data]
```

Repo identity = basename of `git rev-parse --show-toplevel`, so clones/worktrees of the
same repo log to the same file. The WIP is keyed by `<repo>-<branch>` so two concurrent
worktrees never clobber each other.

## Optional: agent integration

The CLI is the whole tool — you can drive it by hand. But if you work *with* a coding agent,
`skill/SKILL.md` is a playbook that teaches the agent to drive the CLI conversationally:
recognize "start rework" / "end rework," capture categorized notes as you give feedback, and
finalize. The agent runs the commands; it never touches the data files. It's harness-agnostic
— the file is plain instructions with Claude Code frontmatter on top.

**Claude Code** — the one-line installer wires this up automatically (skill + a SessionStart
hook that reminds Claude the tool is available). If you installed manually, do it yourself:

```sh
mkdir -p ~/.claude/skills/rework-tracking
ln -sf ~/.rework/skill/SKILL.md ~/.claude/skills/rework-tracking/SKILL.md
```

**Codex / Cursor / Aider / others** — point the agent at the file as context, e.g. add a
line to your `AGENTS.md` / `.cursorrules` / project instructions:

```
For rework tracking, follow ~/.rework/skill/SKILL.md and use the `rework` CLI.
```

**No agent** — skip the skill entirely; just run the commands yourself.

## Not yet built

Reporting/charting, layer-aggregation, cross-repo dashboards, Clockify integration,
merge-hook auto-finalize. The append-only JSONL + `_tags.json` are designed so all of these
can be added later without rewriting history. v1 is purely **capture**.
