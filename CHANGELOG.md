# Changelog

## 0.1.0 — initial marketplace candidate
- MCP stdio server (`server/server.py`) with `cli_probe`, `claude_prompt`, `codex_prompt`.
- Claude presets: `opus-5.5` (`claude-opus-5-5`), `fable` (CLI alias), `default`.
- Codex presets: `astra` (`gpt-6-astra`), `default` (omit `--model`).
- Safety: argv-only subprocess, cwd allowlist, timeout/output caps,
  permission ceilings (no Claude bypassPermissions, no Codex danger-full-access).
- Bundled `cli-bridge` skill. Placeholder author/license fields — see PUBLISHING.md.
