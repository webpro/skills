#!/usr/bin/env bash

set -u

if [ "$#" -ne 4 ]; then
  echo "usage: run-claude-review.sh <seconds> <model> <effort> <prompt-file>" >&2
  exit 64
fi

seconds=$1
model=$2
effort=$3
prompt_file=$4

case $seconds in
  '' | *[!0-9]*)
    echo "error: seconds must be a positive integer" >&2
    exit 64
    ;;
esac

if [ "$seconds" -eq 0 ]; then
  echo "error: seconds must be a positive integer" >&2
  exit 64
fi

if [ ! -f "$prompt_file" ]; then
  echo "error: prompt file not found: $prompt_file" >&2
  exit 66
fi

for command_name in claude jq python3 tee; do
  if ! command -v "$command_name" >/dev/null 2>&1; then
    echo "error: required command not found: $command_name" >&2
    exit 69
  fi
done

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd -P)
filter_file=$script_dir/claude-stream.jq
deadline_script=$script_dir/run-with-deadline.py
if ! jq -n -f "$filter_file" >/dev/null; then
  echo "error: invalid stream filter: $filter_file" >&2
  exit 65
fi
stream_file=$(mktemp "${TMPDIR:-/tmp}/cross-review-claude.XXXXXX") || exit 74

set -o pipefail
NO_COLOR=1 python3 "$deadline_script" "$seconds" \
  claude -p --safe-mode --permission-mode plan --no-session-persistence \
  --model "$model" --effort "$effort" --output-format stream-json \
  --include-partial-messages --verbose "$(< "$prompt_file")" < /dev/null \
  | tee "$stream_file" \
  | jq --unbuffered -r -f "$filter_file"
pipeline_status=("${PIPESTATUS[@]}")

printf 'STREAM_FILE=%s\nCLAUDE_EXIT=%s TEE_EXIT=%s JQ_EXIT=%s\n' \
  "$stream_file" "${pipeline_status[0]}" "${pipeline_status[1]}" "${pipeline_status[2]}"

if [ "${pipeline_status[0]}" -ne 0 ]; then
  exit "${pipeline_status[0]}"
fi
if [ "${pipeline_status[1]}" -ne 0 ] || [ "${pipeline_status[2]}" -ne 0 ]; then
  exit 74
fi
if ! jq -s -e 'any(.[]; .type == "result" and .subtype == "success")' "$stream_file" >/dev/null; then
  echo "error: reviewer stream has no terminal success result" >&2
  exit 70
fi
