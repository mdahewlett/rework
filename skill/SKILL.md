---
name: rework-tracking
description: Use when the user says "start rework" / "end rework", or otherwise wants to track how much of the AI's first implementation gets changed before merge. Drives the `rework` CLI to capture rework metrics and categorized notes during a coding session.
---

# Rework Tracking

> Agent playbook for the harness-agnostic `rework` CLI. It carries YAML frontmatter for
> Claude Code skill discovery, but the body is plain instructions — any coding agent
> (Codex, Cursor, Aider, …) can be pointed at this file as context to get the same behavior.

You help the user measure **rework**: how much of your (the AI's) first complete
implementation gets changed before the user is satisfied enough to merge. This is a
lead indicator of how well the user prompts and how agent-ready the repo is.

You drive the `rework` CLI. The CLI owns all storage and git math — you never read or
write its files (`~/.rework/`). You only run commands.

## The two boundaries

- **A — "start rework"**: the user signals your first complete implementation is done.
  Run `rework start`. This stamps the current `HEAD` as commit A.
- **B — "end rework"**: the user is satisfied and about to merge.
  Run `rework end`. This stamps `HEAD` as commit B and finalizes the entry.

Everything between A and B that the user changes is the rework being measured.

## What to do, and when

### When the user says "start rework" (or equivalent)
Run `rework start`. **"start rework" always means "stamp the current commit (HEAD) as A."**
Do NOT ask the user which commit to start from — current HEAD is the answer by definition.
The slug defaults to the branch name — that's almost always right, so don't pass a slug
unless the user gives one. Pass `--harness` only if you are NOT Claude Code (e.g.
`--harness codex`). Confirm it started. (Back-fill A to an earlier commit via `--at` only
when the user *explicitly* asks to anchor at a past commit — never the default.)

### As the user gives change-feedback during review
This is the core of the value. When the user asks you to change something AND frames it
as a *kind* of problem ("this is wrong, the flag client should be in core/" → that's an
architecture issue), capture it:

```
rework note -c <category> "<short description of the change>"
```

- **Suggest the category** from the vocabulary below (or run `rework tags` to see the
  current set), but the user's framing wins. If the user explicitly names a category
  ("this is a missed-spec thing"), use exactly that.
- If the right category isn't in the seed list, **just use a new one** — the vocabulary is
  open and the CLI auto-registers it. Prefer a short kebab-case tag.
- Keep the note text short and concrete — what changed, in the user's words.
- One note per distinct kind of change. Don't batch unrelated changes into one note.

Don't nag. Only log a note when the change is a *real* piece of rework with a nameable
category — not every tiny tweak. When in doubt, ask the user if it's worth noting.

### Recording time (user-supplied)
The user tracks time externally (e.g. Clockify). When they give you the numbers:

```
rework build <minutes>     # plan -> your first implementation
rework review <minutes>    # review -> merge
```

These can come anytime between start and end, in any order.

### When the user says "end rework"
**Never suggest ending or wrapping up the rework session yourself.** Only the user decides
when the cycle ends — don't propose `rework end`, don't ask "ready to wrap up?", don't hint
the work looks done. Wait for the user to explicitly say "end rework." A rework cycle can
stay open across many turns and a long review; that's expected, not something to close out.

When the user *does* say "end rework": before finalizing, make sure time is captured. If
`build`/`review` minutes haven't been given, **ask for them** ("How long did build and
review take?"). Then:

```
rework end
```

Report the resulting metrics line back to the user (ai_lines, rework_lines, rework_pct,
files, hunks). `end` also prints a short **id** for the finalized entry — relay it; it's
how a session note gets attached later.

### Session notes (free-text, not categorized)
A session note records a fact *about the cycle or its metrics* — e.g. "the headline % is
inflated by a one-time doc move; true rate is X." Distinct from `note` (which categorizes a
*piece of rework*). Add one to the live in-progress cycle, or to a past finalized entry:

```
rework session-note "<text>"             # the live wip cycle
rework session-note --id <id> "<text>"   # a finalized entry (get the id from `rework list`)
```

### Listing past cycles
`rework list [--limit N]` shows finalized entries newest-first (`id · date · slug`). Use it
to find the id of a past cycle you want to add a session note to.

### Change requests (about the tool itself)
If the user wants the rework *tool* to behave differently ("rework should exclude doc-only
moves from churn"), record it — don't try to implement it inline:

```
rework change-request "<the request>"             # record
rework change-request --list                      # show the queue (id, status, request)
rework change-request --set <id> <status>         # status: open | in-progress | done | wontfix
```

### Discovering commands
`rework help` (or `--help`) prints the command menu. `rework help --all` prints every
command **with its full arguments and descriptions** in one shot — use it when you need the
exact syntax of a command without drilling into each `rework <cmd> --help` separately.

### Checking state
`rework status` prints the in-progress entry. Use it to confirm what's captured so far if
you're unsure (e.g. after a long session, before `end`).

## Seed category vocabulary

Open set — add new ones freely. Starters:

- **architecture** — how code is split across files/modules/layers; boundaries; wrong altitude.
- **wrong-abstraction** — duplication that should be shared; premature/over-built abstraction; wrong interface.
- **missed-spec** — you did what was asked, but the ask was incomplete; user-added extras.
- **style** — local code style: naming, idiom, type aliases, readability within a file (not structural).

## Important

- The slug comes from the branch by default. One work item = one branch.
- Never invent the time numbers — they come from the user.
- Never try to read or edit files under `~/.rework/`. Use the CLI.
- If a command errors (e.g. "no rework in progress"), report it plainly and ask the user
  how to proceed — don't guess at fixing the state file.
