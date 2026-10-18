# Changelog

## 0.1.0 — initial marketplace candidate
- MCP stdio server (`server/server.py`) with `cli_probe`, `claude_prompt`, `codex_prompt`.
- Claude presets: `opus-5.5` (`claude-opus-5-5`), `fable` (CLI alias), `default`.
- Codex presets: `astra` (`gpt-6-astra`), `default` (omit `--model`).
- Safety: argv-only subprocess, cwd allowlist, timeout/output caps,
  permission ceilings (no Claude bypassPermissions, no Codex danger-full-access).
- Bundled `cli-bridge` skill. Publisher/repo/MIT license decided 2026-10-17; contact email still open before marketplace submission — see PUBLISHING.md.
- Fixes: exactly pinned `mcp==1.30.0`, removed `CLI_BRIDGE_ALLOW_ANY_CWD` bypass (allowlist can only be extended via declared `CLI_BRIDGE_ALLOWED_ROOTS`), added GitHub Actions CI (validate + py_compile + smoke, no model calls).
