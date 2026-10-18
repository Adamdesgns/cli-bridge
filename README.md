# CLI Bridge (Claude Code + Codex)

Let your agent call the **Claude Code** and **OpenAI Codex** CLIs that are
already installed and logged in **on your own machine**. Your agent gets
three MCP tools:

| Tool | Description |
|---|---|
| `cli_probe` | Free check: runs only `claude --version` / `codex --version`. Never a model call. |
| `claude_prompt` | One-shot headless Claude Code run. **Spends your Claude quota.** |
| `codex_prompt` | One-shot headless `codex exec` run. **Spends your Codex quota.** |

Model presets:

- **Claude** — `opus-5.5` → `claude-opus-5-5` (default) · `fable` → the Claude CLI's `fable` model alias · `default` → your configured default model · or any raw model id your CLI accepts.
- **Codex** — `astra` → `gpt-6-astra` · `default` → no `--model` flag, so Codex uses its own configured default · or any raw model id your CLI accepts.

> Preset model ids are only useful if your Claude/Codex account and CLI
> version actually have access to them. If a model is unavailable, the CLI
> itself will say so — this plugin passes the id through, it cannot grant access.

## Prerequisites (all on the machine where your agent host runs)

This plugin is a *bridge*, not a model subscription. It ships **no API keys,
no accounts, and no CLI binaries**. Before installing, on the **same machine
that will launch this plugin's MCP server** (for a local agent host, that is
your computer; it is *not* some other computer you can reach remotely):

1. **A plugin host** that can run local stdio MCP servers from a plugin
   (Cursor / Grok Bot plugin support), with:
   - Python 3.11+ available, and
   - [`uv`](https://docs.astral.sh/uv/) on `PATH` (`uv --version` works). The bundled
     server is launched as `uv run --with "mcp<2" python3 <plugin>/server/server.py`.
2. **Claude Code CLI** *(only if you want `claude_prompt`)* — install per
   https://code.claude.com/docs (for example `npm install -g @anthropic-ai/claude-code`),
   then run `claude` once interactively and log in.
3. **OpenAI Codex CLI** *(only if you want `codex_prompt`)* — install per
   https://developers.openai.com/codex (for example `npm install -g @openai/codex`),
   then run `codex login`.

You can install just one of the two CLIs; the other tool will simply report
"not found" until you do. Verify any time with the `cli_probe` tool, or in a
terminal: `claude --version` and `codex --version`.

## Install

- **From the marketplace** (once published): install "CLI Bridge" from your
  host's plugin marketplace / Customize panel like any other plugin.
- **Local / pre-publishing test (Cursor format):** copy this folder to
  `~/.cursor/plugins/local/cli-bridge`, restart the host (or Developer:
  Reload Window), and confirm the `cli-bridge` MCP server and skill load.
  Symlinks into `~/.cursor/plugins/local` may be skipped by the host if they
  point outside that folder — copy the files instead.
- The MCP config is [`mcp.json`](mcp.json) (mirrored to [`.mcp.json`](.mcp.json) so cursor.directory's auto-detector, which looks for the dotted filename, finds the same server). It launches the bundled server by
  plugin-relative path — the host expands `${CURSOR_PLUGIN_ROOT}` to this
  plugin's install folder in `command`/`args`/`env`/`cwd`. **Host caveat:**
  if your host does *not* expand `${CURSOR_PLUGIN_ROOT}`, replace that arg
  with the absolute path to `server/server.py` in your local copy, e.g.
  `uv run --with "mcp<2" python3 /path/to/cli-bridge/server/server.py`.
  Do not commit that machine-specific edit back to a shared repo.

## Configuration (optional)

Set these in the plugin's Configure/variables UI when your host offers it,
or as environment variables for the MCP server. All are optional; defaults
are shown. Unset values fall back to the defaults — no secrets are involved,
and API keys must **never** be put here (the CLIs use their own logins).

| Variable | Default | Meaning |
|---|---|---|
| `CLI_BRIDGE_CLAUDE_BIN` | `claude` | Claude CLI binary name or absolute path |
| `CLI_BRIDGE_CODEX_BIN` | `codex` | Codex CLI binary name or absolute path |
| `CLI_BRIDGE_CLAUDE_DEFAULT_MODEL` | `claude-opus-5-5` | Model used for Claude `model="default"` |
| `CLI_BRIDGE_CODEX_DEFAULT_MODEL` | *(empty)* | Model for Codex `model="default"`; empty = Codex's own default |
| `CLI_BRIDGE_WORKSPACE_ROOT` | *(launch folder)* | The one folder (tree) the CLIs are allowed to run in |
| `CLI_BRIDGE_TIMEOUT_SECONDS` | `300` | Per-call timeout default (clamped 5–900) |
| `CLI_BRIDGE_OUTPUT_CAP_CHARS` | `20000` | Max stdout/stderr chars returned per call |

Per-call options: `claude_prompt(prompt, model, cwd, timeout, permission_mode)`
and `codex_prompt(prompt, model, cwd, timeout, permission_mode)`.
`cwd` may be absolute-inside-the-workspace-root or relative to it.

## Privacy & security — read before enabling prompt tools

- **Where things run:** entirely on the machine that launches the MCP
  server. Prompts you approve are sent to that machine's Claude/Codex CLI,
  which sends them to Anthropic/OpenAI under **your** logged-in account,
  subject to those vendors' terms. This plugin's author receives nothing:
  no telemetry, no prompt collection, no server of ours is involved.
- **Credentials:** the server inherits the process environment so the CLIs
  can find their own logins, but it never prints, logs, stores, or returns
  environment values, and it never reads or asks for API keys/tokens.
- **Spending:** `claude_prompt` / `codex_prompt` consume your paid
  Claude/Codex quota and can run for minutes. The bundled skill instructs
  agents to probe free with `cli_probe` first and to get your explicit OK
  before any prompt call — but you are responsible for your agent's
  behaviour and your bills.
- **Filesystem / permissions:** calls run with the CLI's permissions inside
  the allowed workspace root only. Hard ceilings in code: Claude
  `bypassPermissions` is refused; Codex `danger-full-access` is refused
  (maximum `workspace-write`). Defaults are safer: Claude `dontAsk`,
  Codex `read-only`. Only raise them when you want that CLI to edit files.
- **No shell:** the server executes CLIs via argument arrays (`shell=False`),
  validates model ids, caps output, and enforces timeouts. Prompt text is
  passed as a single argument, never interpreted by a shell.
- **Escape hatch (unsafe):** `CLI_BRIDGE_ALLOW_ANY_CWD=1` disables the cwd
  allowlist. Leave it unset unless you fully understand the risk.

## Troubleshooting

- *"…CLI not found on the machine running this MCP server"* — install that
  CLI on this machine and make sure its binary name is on `PATH` (or set
  `CLI_BRIDGE_CLAUDE_BIN` / `CLI_BRIDGE_CODEX_BIN`), then re-run `cli_probe`.
- *Auth / login errors* — run `claude` once (or `codex login`) interactively
  on this machine. `--version` succeeding does not prove you are logged in.
- *cwd / allowed-root errors* — set `CLI_BRIDGE_WORKSPACE_ROOT` to your
  workspace folder (absolute path) in the plugin's configuration.
- *Server won't start* — check `uv --version` and `python3 --version`
  (3.11+) in a terminal; the first launch downloads the pinned `mcp<2`
  package via `uv`, which needs network access once.

## Development / local validation (no model calls)

```sh
python3 scripts/validate_package.py   # manifest, mcp.json, skill frontmatter, no-secrets / no-absolute-path scan
python3 -m py_compile server/server.py
python3 smoke_test.py                  # MCP initialize + tools/list + cli_probe + missing-binary paths
```

`smoke_test.py` reads `mcp.json`, expands `${CURSOR_PLUGIN_ROOT}` to this
folder (simulating the host), and launches the server exactly as configured.
It makes **no model calls**: on a machine without the CLIs, every prompt tool
must return the clean "not found" error.

## License

MIT — see [`LICENSE`](LICENSE). (Publisher: confirm the copyright holder
line before publishing; see `PUBLISHING.md`.)
