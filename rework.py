#!/usr/bin/env python3
"""rework — solo AI-velocity rework tracker.

Measures how much of the AI's first complete effort (commit A, "start rework")
gets changed before the user is satisfied enough to merge (commit B, "end rework").

Storage lives in ~/.rework/:
  <repo>.jsonl                 append-only, one finalized work item per line
  _tags.json                   evolving category vocabulary
  .wip-<repo>-<branch>.json    transient in-progress entry, deleted on `end`

All mechanical concerns (storage, git, diff math) live here. The agent only
runs these commands; it never touches the files directly.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.home() / ".rework"
TAGS_PATH = ROOT / "_tags.json"

SEED_TAGS = {
    "architecture": "how code is split across files/modules/layers; boundaries; wrong altitude",
    "wrong-abstraction": "duplication that should be shared; premature/over-built abstraction; wrong interface",
    "missed-spec": "AI did what was asked, but the ask was incomplete; user-added extras",
    "naming-style": "names, conventions, matching surrounding idiom, comment/docstring fixes",
}


def main():
    parser = argparse.ArgumentParser(prog="rework", description="solo AI-velocity rework tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="stamp HEAD as commit A (AI's first effort)")
    p_start.add_argument("slug", nargs="?", help="work slug (default: branch name)")
    p_start.add_argument("description", nargs="?", help="one-line description")
    p_start.add_argument("--harness", default="claude-code", help="AI harness (default: claude-code)")
    p_start.set_defaults(func=cmd_start)

    p_note = sub.add_parser("note", help="add a categorized rework note")
    p_note.add_argument("-c", "--category", required=True, help="rework category tag")
    p_note.add_argument("text", help="what was changed, in your words")
    p_note.set_defaults(func=cmd_note)

    p_build = sub.add_parser("build", help="record build minutes (plan -> first impl)")
    p_build.add_argument("minutes", type=int)
    p_build.set_defaults(func=cmd_build)

    p_review = sub.add_parser("review", help="record review minutes (review -> merge)")
    p_review.add_argument("minutes", type=int)
    p_review.set_defaults(func=cmd_review)

    p_end = sub.add_parser("end", help="stamp HEAD as commit B, finalize the entry")
    p_end.set_defaults(func=cmd_end)

    p_status = sub.add_parser("status", help="show the current in-progress entry")
    p_status.set_defaults(func=cmd_status)

    args = parser.parse_args()
    ROOT.mkdir(exist_ok=True)
    args.func(args)


def cmd_start(args):
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    slug = args.slug or slug_from_branch(branch)
    wip_path = wip_path_for(repo_name(), branch)

    if wip_path.exists():
        die(f"already tracking '{json.loads(wip_path.read_text())['slug']}' on this branch — "
            f"run `rework end` first, or delete {wip_path}")

    if branch in ("main", "master"):
        warn(f"on default branch '{branch}' — you usually start rework on a feature branch. "
             "Slug inference and WIP keying are weakest here.")

    entry = {
        "slug": slug,
        "description": args.description,
        "harness": args.harness,
        "branch": branch,
        "commits": {"a": git("rev-parse", "HEAD")},
        "time": {},
        "rework_notes": [],
    }
    write_json(wip_path, entry)
    print(f"started '{slug}' [{args.harness}] — A={entry['commits']['a'][:7]} on {branch}")


def cmd_note(args):
    entry = load_wip()
    register_tag(args.category)
    entry["rework_notes"].append({"category": args.category, "note": args.text})
    write_json(wip_path_for(repo_name(), entry["branch"]), entry)
    print(f"noted [{args.category}] {args.text}")


def cmd_build(args):
    set_time("build_minutes", args.minutes)


def cmd_review(args):
    set_time("review_minutes", args.minutes)


def set_time(field, minutes):
    entry = load_wip()
    entry["time"][field] = minutes
    write_json(wip_path_for(repo_name(), entry["branch"]), entry)
    print(f"{field} = {minutes}")


def cmd_end(args):
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    entry = load_wip()
    commit_a = entry["commits"]["a"]
    commit_b = git("rev-parse", "HEAD")
    base = merge_base(commit_a)

    ai_files, ai_lines = churn(f"{base}..{commit_a}")
    rework_files, rework_lines = churn(f"{commit_a}..{commit_b}")
    rework_pct = round(rework_lines / ai_lines * 100, 1) if ai_lines else None

    entry["commits"].update({"base": base, "b": commit_b})
    entry["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    entry["metrics"] = {
        "ai_lines": ai_lines,
        "rework_lines": rework_lines,
        "rework_pct": rework_pct,
        "files_touched": len(rework_files),
        "hunks": hunk_count(f"{commit_a}..{commit_b}"),
    }
    entry["files"] = rework_files
    entry.pop("branch", None)

    log_path = ROOT / f"{repo_name()}.jsonl"
    with log_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")
    wip_path_for(repo_name(), branch).unlink(missing_ok=True)

    pct = f"{rework_pct}%" if rework_pct is not None else "n/a"
    print(f"logged '{entry['slug']}' -> {log_path.name}")
    print(f"  ai_lines={ai_lines}  rework_lines={rework_lines}  rework_pct={pct}  "
          f"files={entry['metrics']['files_touched']}  hunks={entry['metrics']['hunks']}")


def cmd_status(args):
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    wip_path = wip_path_for(repo_name(), branch)
    if not wip_path.exists():
        print(f"no rework in progress on branch '{branch}'")
        return
    print(json.dumps(json.loads(wip_path.read_text()), indent=2))


def load_wip():
    branch = git("rev-parse", "--abbrev-ref", "HEAD")
    wip_path = wip_path_for(repo_name(), branch)
    if not wip_path.exists():
        die(f"no rework in progress on branch '{branch}' — run `rework start` first")
    return json.loads(wip_path.read_text())


def register_tag(category):
    tags = json.loads(TAGS_PATH.read_text()) if TAGS_PATH.exists() else dict(SEED_TAGS)
    if category not in tags:
        tags[category] = ""
        write_json(TAGS_PATH, tags)


def churn(rev_range):
    out = git("diff", "--numstat", rev_range)
    files, total = [], 0
    for line in out.splitlines():
        added, deleted, path = line.split("\t", 2)
        if added == "-":
            continue
        file_churn = int(added) + int(deleted)
        files.append({"path": path, "churn": file_churn})
        total += file_churn
    return files, total


def hunk_count(rev_range):
    out = git("diff", "--unified=0", rev_range)
    return sum(1 for line in out.splitlines() if line.startswith("@@"))


def merge_base(commit_a):
    return git("merge-base", default_branch(), commit_a)


def default_branch():
    origin_head = run_git("rev-parse", "--abbrev-ref", "origin/HEAD")
    if origin_head.returncode == 0:
        return origin_head.stdout.strip().split("/", 1)[1]
    for candidate in ("main", "master"):
        if run_git("rev-parse", "--verify", candidate).returncode == 0:
            return candidate
    return "main"


def slug_from_branch(branch):
    for prefix in ("feat/", "feature/", "fix/", "refactor/", "chore/", "docs/"):
        if branch.startswith(prefix):
            return branch[len(prefix):]
    return branch


def repo_name():
    return Path(git("rev-parse", "--show-toplevel")).name


def wip_path_for(repo, branch):
    safe = f"{repo}-{branch}".replace("/", "-")
    return ROOT / f".wip-{safe}.json"


def git(*args):
    result = run_git(*args)
    if result.returncode != 0:
        die(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def run_git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


def warn(message):
    print(f"warning: {message}", file=sys.stderr)


def die(message):
    print(f"error: {message}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
