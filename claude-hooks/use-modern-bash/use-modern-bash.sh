#!/bin/bash
# Claude Code PreToolUse hook on the Bash tool.
#
# Rewrites tool_input.command so each Bash invocation re-execs into a modern
# bash discovered on PATH. Reason: Claude Code's Bash tool hardcodes
# /bin/bash, which on macOS is Apple's frozen 3.2.57 (no mapfile, no
# associative arrays, no [[ -v ]], no globstar).
#
# Discovery walks $PATH for the first `bash` reporting BASH_VERSINFO >= 4.
# /bin/bash on macOS is 3.x and is filtered out by that test, so no path
# needs to be hardcoded.
#
# The modern bash is invoked with `-O globstar` so recursive `**` globs work
# without a per-command `shopt -s globstar` (globstar is off by default in
# every bash version). Add more `-O <opt>` flags below to enable others.
#
# Fail-safe: any failure path exits 0 with empty stdout → Claude runs the
# command under /bin/bash unchanged; nothing breaks.
INPUT=$(cat)
fail_open() { exit 0; }

MODERN=""
saved_IFS=$IFS
IFS=:
for dir in $PATH; do
  cand="$dir/bash"
  [ -x "$cand" ] || continue
  ver=$("$cand" -c 'echo ${BASH_VERSINFO[0]}' 2>/dev/null)
  if [ "${ver:-0}" -ge 4 ]; then
    MODERN="$cand"
    break
  fi
done
IFS=$saved_IFS

[ -n "$MODERN" ] || fail_open
command -v jq >/dev/null 2>&1 || fail_open

# updatedInput replaces the entire tool_input, so we clone tool_input and
# overwrite only .command. permissionDecision=allow lets the rewrite proceed
# without prompting; the user's deny/ask rules are still evaluated.
OUT=$(printf '%s' "$INPUT" | jq --arg m "$MODERN" '
  (.tool_input.command // "") as $cmd
  | if ($cmd | type) == "string" and ($cmd | length) > 0
    then {
      hookSpecificOutput: {
        hookEventName: "PreToolUse",
        permissionDecision: "allow",
        updatedInput: (.tool_input | .command = "exec \($m|@sh) -O globstar -c \($cmd|@sh)")
      }
    }
    else empty end
' 2>/dev/null) || fail_open
[ -n "$OUT" ] || fail_open
printf '%s' "$OUT"
