#!/usr/bin/env bash
# rework installer — idempotent, safe to re-run.
#   curl -fsSL https://raw.githubusercontent.com/mdahewlett/rework/main/install.sh | bash
#
# Installs the harness-agnostic CLI for everyone; wires the optional Claude Code
# skill + SessionStart hook only if Claude Code is detected.
set -euo pipefail

REPO_URL="https://github.com/mdahewlett/rework.git"
REWORK_DIR="${REWORK_DIR:-$HOME/.rework}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
CLAUDE_DIR="${CLAUDE_DIR:-$HOME/.claude}"

say() { printf '  %s\n' "$1"; }

install_claude_integration() {
  # Skill: symlink the repo's SKILL.md where Claude discovers skills.
  mkdir -p "$CLAUDE_DIR/skills/rework-tracking"
  ln -sf "$REWORK_DIR/skill/SKILL.md" "$CLAUDE_DIR/skills/rework-tracking/SKILL.md"
  say "linked skill -> $CLAUDE_DIR/skills/rework-tracking/"

  # SessionStart hook: register the repo's hook script in settings.json (merged, idempotent).
  local settings="$CLAUDE_DIR/settings.json"
  local hook_cmd="$REWORK_DIR/hooks/session-start.sh"
  chmod +x "$hook_cmd" 2>/dev/null || true

  if ! command -v python3 >/dev/null 2>&1; then
    say "python3 not found — skipping hook registration (skill still works on description match)"
    return
  fi

  REWORK_HOOK_CMD="$hook_cmd" REWORK_SETTINGS="$settings" python3 - <<'PY'
import json, os
from pathlib import Path

settings_path = Path(os.environ["REWORK_SETTINGS"])
hook_cmd = os.environ["REWORK_HOOK_CMD"]

data = {}
if settings_path.exists():
    try:
        data = json.loads(settings_path.read_text())
    except json.JSONDecodeError:
        print("  WARNING: settings.json is not valid JSON — skipping hook, edit it by hand.")
        raise SystemExit(0)

hooks = data.setdefault("hooks", {})
session_start = hooks.setdefault("SessionStart", [])

already = any(
    h.get("command") == hook_cmd
    for group in session_start
    for h in group.get("hooks", [])
)
if already:
    print("  hook already registered")
else:
    session_start.append({"hooks": [{"type": "command", "command": hook_cmd}]})
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    print("  registered SessionStart hook")
PY
}

echo "rework installer"

# 1. Clone or update the repo.
if [ -d "$REWORK_DIR/.git" ]; then
  say "updating existing checkout at $REWORK_DIR"
  git -C "$REWORK_DIR" pull --ff-only --quiet || say "(local changes present; skipped pull)"
elif [ -e "$REWORK_DIR" ]; then
  echo "error: $REWORK_DIR exists but is not a git checkout. Move it aside and re-run." >&2
  exit 1
else
  say "cloning into $REWORK_DIR"
  git clone --quiet "$REPO_URL" "$REWORK_DIR"
fi

# 2. Symlink the CLI onto PATH.
mkdir -p "$BIN_DIR"
ln -sf "$REWORK_DIR/rework.py" "$BIN_DIR/rework"
say "linked rework -> $BIN_DIR/rework"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) say "NOTE: $BIN_DIR is not on your PATH. Add this to your shell rc:"
     say "      export PATH=\"$BIN_DIR:\$PATH\"" ;;
esac

# 3. Optional Claude Code integration — only if Claude Code is present.
if [ -d "$CLAUDE_DIR" ]; then
  say "Claude Code detected — installing skill + SessionStart hook"
  install_claude_integration
else
  say "Claude Code not detected — skipping skill/hook (the CLI works in any harness)"
  say "For other agents, point them at $REWORK_DIR/skill/SKILL.md (see README)."
fi

echo "done. Try: rework --help"
