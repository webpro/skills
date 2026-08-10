#!/bin/bash

# Codex PreToolUse hook for the Bash tool. Keep this script compatible with
# macOS /bin/bash 3.2 because it selects the modern Bash used by tool calls.

INPUT=$(cat)

fail_open() {
  exit 0
}

MODERN_BASH=
saved_IFS=$IFS
IFS=:
for directory in $PATH; do
  [ -n "$directory" ] || directory=.
  candidate=$directory/bash
  [ -x "$candidate" ] || continue
  major=$(
    "$candidate" -c "printf '%s\\n' \"\${BASH_VERSINFO[0]}\"" 2>/dev/null
  )
  if [ "${major:-0}" -ge 4 ] 2>/dev/null; then
    MODERN_BASH=$candidate
    break
  fi
done
IFS=$saved_IFS

[ -n "$MODERN_BASH" ] || fail_open
command -v jq >/dev/null 2>&1 || fail_open

OUTPUT=$(printf '%s' "$INPUT" | jq --arg bash "$MODERN_BASH" '
  (.tool_input.command // "") as $command
  | if ($command | type) == "string" and ($command | length) > 0
    then {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "allow",
        updatedInput: (
          .tool_input
          | .command = "exec \($bash | @sh) -O globstar -c \($command | @sh)"
        )
      }
    }
    else empty
    end
' 2>/dev/null) || fail_open

[ -n "$OUTPUT" ] || fail_open
printf '%s' "$OUTPUT"
