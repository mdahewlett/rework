#!/usr/bin/env bash
# rework SessionStart hook for Claude Code.
# Injects a one-line reminder so Claude knows rework tracking is available this session.
# Light by design — points to the rework-tracking skill rather than dumping its body.
cat <<'JSON'
{
  "hookSpecificOutput": {
    "hookEventName": "SessionStart",
    "additionalContext": "rework tracking is available. When the user says \"start rework\" / \"end rework\", use the rework-tracking skill to drive the `rework` CLI (rework start | note -c <cat> \"...\" | build <min> | review <min> | end)."
  }
}
JSON
