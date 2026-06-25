# rework

**rework measures how much of an AI agent's first complete implementation you change
before you're satisfied enough to merge** — a lead indicator of how well you prompt and how
agent-ready your repo is. It's a single CLI plus an optional agent playbook, and it works in
any coding harness or none.

## The idea

Teams measure AI velocity with a "rework" metric: of a merged PR's lines, how many get
touched again within ~2 weeks? rework adapts that to a **shorter, solo time scale.** Treat
the AI's first implementation as the "merged PR," and your own pre-merge blessing as the
"rework" version. The gap between them is the signal.

Two boundaries, both triggered by you during a session:

- **A — "start rework"** — the AI has finished its first complete pass (current `HEAD`).
- **B — "end rework"** — you've reviewed, made your changes, and you're ready to merge.

**Rework = the git churn between A and B.** Everything you changed after the AI's first
effort, as a line count and as a percentage of what the AI produced.

But the line count is only half of it. As you review and ask for changes, you also name
*what kind* of problem each fix was — architecture, a missed-spec extra, a correctness bug,
a style choice. Naming the category in the moment is the point: it keeps you reasoning about
the kind of issue you keep hitting, not just fixing it. Over time the log shows you whether
your rework clusters in file organization, in correctness, in under-specced features — and
whether that changes as you get better at prompting or make your repo more agent-ready.

The tool is deliberately **capture-only**. It produces clean, append-only data; it doesn't
chart it for you (yet). The discipline of capturing well is the product.

## How it works

You drive five verbs during a normal coding session:

```sh
rework start                      # the AI's first pass is done — stamp commit A
# ...you review and ask for changes...
rework note -c correctness "use NaN, not 0, for unvoiced frames"
rework note -c architecture "split models into separate files"
rework build 130                  # minutes: plan → AI's first implementation
rework review 318                 # minutes: review → merge
rework end                        # you're satisfied — stamp B, compute the diff, log it
```

`rework end` prints what it recorded:

```
logged 'ml-tone-pipeline' -> toneapp.jsonl
  ai_lines=1495  rework_lines=928  rework_pct=62.1%  files=30  hunks=112
```

That one line — *I reworked 62% of what the AI wrote, across 30 files* — plus your
categorized notes, is the data point. One append-only JSON line per work item, kept per
repo under `~/.rework/`.

If you work with a coding agent, it can drive all of this for you: you just say "start
rework" / "end rework" and describe your changes in plain language, and the agent runs the
commands and suggests the categories. See [Agent integration](#agent-integration).

## Install

One line:

```sh
curl -fsSL https://raw.githubusercontent.com/mdahewlett/rework/main/install.sh | bash
```

This clones to `~/.rework`, puts `rework` on your PATH, and — **only if it detects Claude
Code** — installs the optional skill and a SessionStart hook so the agent knows the tool is
available. It's idempotent; re-run anytime to update. Other harnesses are left untouched.

<details>
<summary>Prefer not to pipe curl into bash?</summary>

```sh
git clone https://github.com/mdahewlett/rework.git ~/.rework
ln -sf ~/.rework/rework.py ~/.local/bin/rework   # ensure ~/.local/bin is on PATH
```

That's the whole tool. For the optional agent layer, see
[Agent integration](#agent-integration).
</details>

The tool is a single Python file (stdlib only) that shells out to `git` — no dependencies.
Your **data** (`<repo>.jsonl`, `_tags.json`, `.wip-*.json`) is written under `~/.rework/`
but is gitignored, so it never reaches this public repo.

> Because data and code share `~/.rework/`, don't run `git clean -x` there — it would delete
> your logs. Plain `git clean` is safe (it respects `.gitignore`).

## Commands

```sh
rework start [slug] [description]   # stamp HEAD as A (slug defaults to the branch name)
rework note -c <category> "text"    # add a categorized rework note (vocabulary is open)
rework build <minutes>              # plan → first implementation (you supply the time)
rework review <minutes>             # review → merge (you supply the time)
rework end                          # stamp HEAD as B, compute the diff, finalize the entry
rework status                       # show the in-progress entry
rework base <commit>                # set the pre-AI baseline (rarely needed; see below)
```

- One work item = one branch. The slug defaults to the branch name (minus `feat/`, `fix/`).
- Notes and times can be added in any order, anytime between `start` and `end`.
- `--harness <name>` on `start` records which agent built it (default `claude-code`) so you
  can compare tools.
- **Parallel worktrees work out of the box.** Run an agent in each of several worktrees of
  the same repo and start a separate rework session in each — the in-progress state is keyed
  by `<repo>-<branch>`, so the sessions never collide. They all finalize into the same
  per-repo log.

**Back-filling a past session.** To reconstruct an entry from commits after the fact, point
`start`/`end` at specific SHAs instead of `HEAD`:

```sh
rework start --at <A-sha> --base <pre-AI-sha>   # explicit commit A and baseline
rework end --at <B-sha>                          # explicit commit B
```

The `--base` matters when commit A sits at the branch point: there's no AI-work span before
it, so `ai_lines` would be 0 and the percentage undefined. Passing the pre-AI commit as the
baseline fixes the denominator.

## What gets recorded

One append-only JSON line per work item in `~/.rework/<repo>.jsonl`:

| Field | Meaning |
|---|---|
| `commits.base / a / b` | the pre-AI baseline, commit A (start), commit B (end) |
| `metrics.ai_lines` | churn `base..A` — what the AI produced (the denominator) |
| `metrics.rework_lines` | churn `A..B` — what you changed after |
| `metrics.rework_pct` | `rework_lines / ai_lines * 100` (`null` if the AI produced nothing) |
| `metrics.files_touched / hunks` | breadth and fragmentation of the rework |
| `files[]` | raw per-file churn `A..B` — *where* the rework landed |
| `time.build_minutes / review_minutes` | your two time stages |
| `rework_notes[]` | `{category, note}` — *what kind* of rework, in your words |

This captures two independent axes of "where rework happens": the **mechanical** one (which
files, computed from the diff) and the **qualitative** one (what kind of problem, from your
notes). File-to-layer mapping is left to analysis time, not baked into the data, so the
rules can evolve without rewriting history.

### Categories

An open set — new tags auto-register in `_tags.json` as you use them. The seeds:

- **architecture** — how code is split across files/modules/layers; boundaries; wrong altitude.
- **wrong-abstraction** — duplication that should be shared; premature abstraction; wrong interface.
- **missed-spec** — the AI did what was asked, but the ask was incomplete; your extras.
- **style** — local code style: naming, idiom, type aliases, readability within a file.

Add whatever distinctions matter to you (`correctness`, `testing`, `typing`, `performance`,
`observability`, `harness-eng`, …). The vocabulary is yours to grow.

## Agent integration

The CLI is the whole tool — you can drive it by hand. But if you work *with* a coding agent,
`skill/SKILL.md` is a playbook that teaches the agent to drive it conversationally: recognize
"start rework" / "end rework," capture categorized notes as you give feedback, and finalize.
The agent runs the commands; it never touches the data files. The file is plain instructions
with Claude Code skill frontmatter on top, so it's harness-agnostic.

- **Claude Code** — the installer wires this up automatically (skill + a SessionStart hook
  that reminds the agent the tool is available). Manual installers run:
  ```sh
  mkdir -p ~/.claude/skills/rework-tracking
  ln -sf ~/.rework/skill/SKILL.md ~/.claude/skills/rework-tracking/SKILL.md
  ```
- **Codex / Cursor / Aider / others** — point the agent at the file, e.g. add to your
  `AGENTS.md` / `.cursorrules`: *"For rework tracking, follow `~/.rework/skill/SKILL.md` and
  use the `rework` CLI."*
- **No agent** — skip the skill; just run the commands yourself.

## Storage layout

```
~/.rework/
  rework.py                       # the CLI                      (this repo)
  skill/SKILL.md                  # the agent playbook           (this repo)
  install.sh                      # one-line installer           (this repo)
  hooks/session-start.sh          # Claude Code reminder hook     (this repo)
  <repo>.jsonl                    # append-only log, one line per work item   [data]
  _tags.json                      # category vocabulary                        [data]
  .wip-<repo>-<branch>.json       # transient in-progress entry, deleted on end [data]
```

Repo identity is the basename of `git rev-parse --show-toplevel`, so clones and worktrees of
the same repo log to the same file — while the work-in-progress entry is keyed by
`<repo>-<branch>`, which is what keeps parallel worktree sessions from clobbering each other.

## Roadmap

rework is capture-only by design. Not yet built — but the append-only data is shaped to
support all of it without rewriting history:

- **Reporting** — trends over time, slicing by category / harness / layer.
- **Layer aggregation** — mapping per-file churn to `api`/`services`/`models`/… at read time.
- **Cross-repo views** — globbing `~/.rework/*.jsonl` for a portfolio picture.
- **Time integration** — pulling build/review minutes from a tracker instead of by hand.

## License

MIT — see [LICENSE](LICENSE).
