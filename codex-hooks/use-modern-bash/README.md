# use-modern-bash

A Codex `PreToolUse` hook that explicitly re-execs shell tool calls with the
first Bash 4+ on `PATH`. Codex normally uses the configured user shell; this
hook enforces modern Bash instead of relying on that configuration. The path is
discovered at runtime and is not hardcoded.

The hook preserves the complete tool input, rewrites only its command, enables
`globstar`, and fails open when modern Bash or `jq` is unavailable.

## Install

Copy the executable:

```sh
mkdir -p ~/.codex/hooks
cp use-modern-bash.sh ~/.codex/hooks/
chmod +x ~/.codex/hooks/use-modern-bash.sh
```

Then add this matcher group to `hooks.PreToolUse` in `~/.codex/hooks.json`:

```json
{
  "matcher": "^Bash$",
  "hooks": [
    {
      "type": "command",
      "command": "~/.codex/hooks/use-modern-bash.sh",
      "timeout": 5,
      "statusMessage": "Selecting modern Bash"
    }
  ]
}
```

Restart Codex, review and trust the hook with `/hooks`, then verify with
`printf '%s\n' "$BASH_VERSION"` in a Bash tool call.
