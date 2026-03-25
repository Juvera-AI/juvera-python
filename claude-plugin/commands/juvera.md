---
allowed-tools: Bash(python3:*), Bash(pip3:*), Read(*), Edit(*), Write(*)
description: Instrument AI agent code with Juvera SDK for ROI tracking
disable-model-invocation: false
---

# /juvera Command

Instrument the current file or project with Juvera SDK.

## Subcommands

Parse the user's argument to determine which subcommand to run:

### `/juvera` (no args) or `/juvera instrument`

1. Identify the file the user is currently working on (ask if unclear)
2. Use the `juvera_suggest` MCP tool to analyze the file
3. Follow the juvera-instrument skill's progressive enhancement flow (Tier 1 → 2 → 3)

### `/juvera validate`

1. Identify the file to validate (ask if unclear)
2. Use the `juvera_validate` MCP tool
3. Report issues with severity levels:
   - **Errors** (red): must fix — missing init, no spans
   - **Warnings** (yellow): should fix — missing flush/shutdown
   - **Info** (blue): nice to have — missing model/token tracking, no workflow_type
4. Offer to fix any issues found

### `/juvera roi`

1. Check current file for `workflow_type` in agent_span calls
2. Use the `juvera_roi` MCP tool for each workflow type found
3. Display a summary table:
   ```
   Workflow Type        | Human Cost | Agent Cost | Savings | Time Saved
   ticket_deflection    | $22.00     | ~$0.002    | $21.998 | 14.9 min
   ```
4. If no workflow_type found, show all available baselines

### `/juvera traces`

1. Look for common log file locations: `juvera-debug.log`, `*.log` in current directory
2. If not found, instruct: "Pipe your agent output to a file: `python my_agent.py 2>&1 | tee juvera-debug.log`"
3. Use the `juvera_traces` MCP tool to parse the log
4. Display summary: span count, tokens, models, errors, handoffs

## Notes

- If MCP tools are not available, fall back to the juvera-instrument skill's built-in patterns
- Always use the Read tool to check file contents before suggesting changes
- Never modify files without user consent
