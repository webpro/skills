---
name: configure-knip
description: Set up and optimize Knip configuration to find unused files, dependencies, and exports. Use when configuring knip.json or cleaning up a JavaScript or TypeScript codebase.
---

# Configure Knip

Set up and iteratively optimize [Knip][1] configuration to find unused files, dependencies, exports, and types.

## Setup

Ensure the `@knip/mcp` MCP server is registered in your AI coding agent:

```sh
npx -y @knip/mcp
```

This provides three MCP capabilities:

- `knip-configure` prompt — guided workflow for setup and optimization
- `knip-run` tool — runs analysis, returns configuration hints and issues
- `knip-docs` tool — fetches Knip documentation by topic

## Task Instructions

1. If the MCP server is not available, register it with your agent
2. Use the `knip-configure` MCP prompt — it contains the full workflow:
   - Reads essential docs via `knip-docs`
   - Runs analysis via `knip-run`
   - Iterates on knip.json until hints are resolved and false positives minimized

## Core Principles

- Configure Knip properly before jumping to conclusions about false positives
- Run Knip to get configuration hints and issues
- Address the hints by adjusting Knip configuration (`knip.json`)
- Repeat until hints are gone and false positives are minimized

## Configuration Review Hints

- Never use "ignore" patterns (hides real issues!), always prefer specific solutions; other `ignore*` options are allowed
- Many unused exported types → try `ignoreExportsUsedInFile: { interface: true, type: true }`
- Remove ignore patterns that don't match any files
- Remove redundant ignore patterns — Knip respects .gitignore (node_modules, dist, build, .git)
- Remove entry patterns covered by config defaults and auto-detected plugins
- Config files (e.g. vite.config.ts) showing as unused → try enable or disable the plugin explicitly (`vite: true`)
- Dependencies matching Node.js builtins: add to ignoreDependencies (e.g. buffer, process)
- Unresolved imports from path aliases: add paths to Knip config (tsconfig.json semantics)

[1]: https://knip.dev
