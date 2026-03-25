---
allowed-tools: Bash(python3:*), Bash(pip3:*), Read(*), Edit(*), Write(*)
description: Instrument AI agent code with Juvera SDK for ROI tracking
disable-model-invocation: false
---

# /juvera-instrument

Invoke the `juvera:juvera-instrument` skill to instrument the current file or project with Juvera SDK.

Use the Skill tool to load the skill:
```
Skill("juvera:juvera-instrument")
```

Then follow the skill's progressive enhancement flow (Tier 1 → 2 → 3).

If the user passes a subcommand argument, handle it:

- `validate` — Read the current file and use the `juvera_validate` MCP tool to check instrumentation
- `roi` — Use the `juvera_roi` MCP tool to estimate ROI for workflow types found in the code
- (no args) — Run the full instrumentation flow from the skill
