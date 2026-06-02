# use-modern-bash

A Claude Code `PreToolUse` hook that re-execs every Bash-tool call under a modern bash on `PATH`, side-stepping macOS `/bin/bash` = 3.2.57.
See the script header for how it works.

## Install

```sh
mkdir -p ~/.claude/hooks
cp use-modern-bash.sh ~/.claude/hooks/ && chmod +x ~/.claude/hooks/use-modern-bash.sh
jq '.hooks.PreToolUse += [{ matcher: "Bash", hooks: [{ type: "command", command: "\(env.HOME)/.claude/hooks/use-modern-bash.sh" }] }]' \
  ~/.claude/settings.json > ~/.claude/settings.json.new && mv ~/.claude/settings.json.new ~/.claude/settings.json
```

Restart Claude Code, then verify: `echo "$BASH_VERSION"` reports 5.x. Requires `jq` on `PATH`.
