---
name: cli-bridge
description: Call the Claude Code and OpenAI Codex CLIs installed on this machine via the cli-bridge MCP tools (claude_prompt, codex_prompt, cli_probe). Use when the user asks you to delegate a coding task, review, or second opinion to Claude (Opus 5.5 or Fable) or Codex (Astra or its default model), or to check whether those CLIs are available. Never spend model quota without the user's explicit OK.
---

# CLI Bridge — using Claude Code and Codex from your agent

This plugin lets you hand work to two coding CLIs that live **on the same
machine your agent host runs on**: Claude Code (`claude`) and OpenAI Codex
(`codex`). Each CLI uses its own local login — you never see, ask for, or
handle the user's API keys or credentials.

## Tools

| Tool | What it does | Costs quota? |
|---|---|---|
| `cli_probe` | Runs only `claude --version` / `codex --version` | No |
| `claude_prompt` | `claude -p <prompt>` headless | **Yes** — user's Claude quota |
| `codex_prompt` | `codex exec <prompt>` headless | **Yes** — user's Codex quota |

## Model presets

- Claude: `model="opus-5.5"` → `claude-opus-5-5` (default) · `model="fable"` → Claude CLI alias `fable` · `model="default"` → configured default · or pass a raw model id.
- Codex: `model="astra"` → `gpt-6-astra` · `model="default"` → omit `--model` so Codex uses its own default (default choice) · or pass a raw model id.

## Required workflow

1. **Probe first, every new session.** Call `cli_probe` before the first
   `*_prompt` call. It is free (version check only). If a CLI is reported
   not found, tell the user exactly that: the CLI must be installed **and
   logged in on the machine where this plugin's MCP server runs** — a CLI
   installed on some other computer does not count. Give them the install /
   login hint from the error text. Do not retry a prompt call hoping it
   will appear.
2. **Never spend without the user's OK.** Every `claude_prompt` /
   `codex_prompt` call spends the user's paid Claude/Codex quota and can
   run for minutes. Before the first real call in a task, say which CLI,
   which model preset, what prompt you will send, and the working folder,
   and get explicit approval. A vague "go ahead" for other work is not
   approval to spend CLI quota. Cheap `--version` probing never needs approval.
3. **Permission ceilings — do not try to exceed them.** This plugin refuses
   Claude `bypassPermissions` and Codex `danger-full-access`. Defaults are
   the safe end: Claude `dontAsk`, Codex `read-only`. Only raise to
   `acceptEdits` / `workspace-write` when the user has asked for the CLI to
   actually edit files, and say so when you ask for approval. If a task
   seems to need more, stop and ask the user — do not look for a workaround.
4. **Working folder.** Pass `cwd` only inside the user's workspace. If you
   get an "allowed workspace root" error, report it and ask the user to set
   `CLI_BRIDGE_WORKSPACE_ROOT` (plugin Configure / variables) to their
   workspace folder, or extend it via the declared
   `CLI_BRIDGE_ALLOWED_ROOTS` variable. The allowlist cannot be disabled --
   do not suggest or look for a way to disable it.
5. **Prompts are work orders.** Send a self-contained prompt: goal, relevant
   file paths, constraints, and what to return. The CLI cannot see this
   conversation. Prefer read-only / review tasks unless the user approved edits.
6. **Report faithfully.** Relay the CLI's exit code and output, truncated
   output is marked as such. An auth/login error means: ask the user to run
   `claude` (or `codex login`) interactively on that machine once — never
   ask them to paste a key or token into chat.

## When NOT to use this

- The user has not approved spending CLI quota (probe-only is fine).
- The CLI is not installed/logged in per `cli_probe` — report, don't improvise
  a substitute model and claim it was Claude/Codex.
- The task needs interactive back-and-forth; these are one-shot headless calls.
