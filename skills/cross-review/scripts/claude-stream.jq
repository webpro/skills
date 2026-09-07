if .type == "system" and .subtype == "init" then
  "INIT model=\(.model) session=\(.session_id)"
elif .type == "assistant" then
  .message.content[]? |
    if .type == "text" then
      "UPDATE \(.text)"
    elif .type == "tool_use" then
      "TOOL \(.name)"
    else
      empty
    end
elif .type == "user" then
  .message.content[]? | select(.type == "tool_result") | "TOOL_DONE"
elif .type == "rate_limit_event" then
  "RATE_LIMIT \(.rate_limit_info.status // "unknown")"
elif .type == "result" then
  "RESULT subtype=\(.subtype) cost=\(.total_cost_usd) turns=\(.num_turns) duration_ms=\(.duration_ms)\n\(.result // "")"
else
  empty
end
