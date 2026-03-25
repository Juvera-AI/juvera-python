# Juvera Claude Code Plugin

Auto-instrument your AI agents with [Juvera SDK](https://pypi.org/project/juvera-sdk/) for ROI tracking and business impact measurement.

## Install

### Marketplace (recommended)

```bash
/plugin marketplace add Juvera-AI/juvera-python
/plugin install juvera@juvera-plugins
```

### Git URL

```bash
claude plugin add https://github.com/Juvera-AI/juvera-python/tree/main/claude-plugin
```

### Local

```bash
pip install juvera-sdk
claude plugin add /path/to/claude-plugin
```

## What It Does

When you write AI agent code, the plugin detects your framework and offers to add Juvera instrumentation:

- **Auto-detection** — recognizes OpenAI, Anthropic, LangChain, CrewAI, LlamaIndex, FastAPI/Flask
- **Progressive instrumentation** — starts minimal, offers more as you go
- **ROI estimation** — shows cost savings vs human baseline
- **Validation** — checks your instrumentation is correct

## Usage

The plugin activates automatically when it detects agent code, or use the slash command:

```
/juvera              Instrument current file
/juvera validate     Check instrumentation correctness
/juvera roi          Show ROI estimate
/juvera traces       Show recent local traces
```

## MCP Server

The plugin includes an MCP server for trace inspection and validation tools. It starts automatically when the plugin is loaded.
