---
name: send-ntfy-notification
description: >
  Send plain-text ntfy notifications after a task is verified complete. Use when
  asked to notify user about finished work, or when standing instructions
  authorize a completion notification. Do not use for excessive progress updates
  or without authorization.
---

# Send ntfy Notification

After completing and verifying the task, run exactly once:

```sh
env -u NTFY_TOPIC ntfy publish --title '<title>' --message '<concise outcome>' "${NTFY_SERVER}/${NTFY_TOPIC}"
```

- Read `NTFY_SERVER` and `NTFY_TOPIC` from the current process environment. If either is unset, stop and report that notification configuration is unavailable. Never print their values.
- Unset `NTFY_TOPIC` only for the `ntfy` child process because the CLI otherwise treats it as its own topic override and ignores the positional server URL.
- Optionally, add `-U <URL>` before the topic URL if relevant. Keep all options before the topic; `ntfy` treats arguments after the topic as message text.
- Keep the message to one plain-text line. Never include secrets, source text, command output, absolute paths, or other private data. Do not add Markdown.
- Use no more than 4095 bytes for the message.
- If `ntfy` is unavailable or publishing fails, do not install, configure, or retry anything. Mention the notification failure in the final response without changing the task result.
