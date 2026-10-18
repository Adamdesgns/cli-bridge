#!/usr/bin/env python3
"""
cli-bridge: local MCP stdio server bridging an agent to coding CLIs
installed on the SAME machine that launches this server.

Tools:
  cli_probe    -- cheap, no model call: `<cli> --version` only
  claude_prompt -- `claude -p <prompt> --model <model> --output-format text --permission-mode <mode>`
  codex_prompt  -- `codex exec [--model <model>] --sandbox <sandbox> --skip-git-repo-check <prompt>`

Model presets:
  Claude: "opus-5.5" -> claude-opus-5-5 | "fable" -> fable (Claude CLI alias)
          "default"  -> $CLI_BRIDGE_CLAUDE_DEFAULT_MODEL or claude-opus-5-5
          any other value is passed through after strict validation.
  Codex:  "astra"    -> gpt-6-astra
          "default" / "" -> omit --model (Codex CLI's own default), unless
          $CLI_BRIDGE_CODEX_DEFAULT_MODEL is set, in which case that is used.
          any other value is passed through after strict validation.

Safety (marketplace build):
  - subprocess argument arrays only, shell=False, stdin=DEVNULL
  - permission ceilings: Claude never bypassPermissions;
    Codex never danger-full-access (read-only / workspace-write only)
  - cwd allowlist: cwd must resolve inside an allowed root. Roots come from
    $CLI_BRIDGE_WORKSPACE_ROOT plus optional $CLI_BRIDGE_ALLOWED_ROOTS
    (os.pathsep separated, declared in plugin.json variables / mcp.json env);
    if neither is set, the folder this server was launched from (its
    startup cwd) is the single allowed root. Relative cwd is resolved
    against that root. The allowlist cannot be disabled; it can only be
    extended via those declared variables.
  - timeout clamped 5-900s (default $CLI_BRIDGE_TIMEOUT_SECONDS or 300)
  - stdout/stderr each capped ($CLI_BRIDGE_OUTPUT_CAP_CHARS or 20000 chars)
  - environment is inherited so CLIs can use their own login, but env
    values are NEVER printed, logged, or returned. Unresolved host
    placeholders such as "${SOME_VAR}" are ignored, never treated as paths.
  - no API keys are read, stored, or sent by this server; Claude/Codex
    handle their own auth on the machine where they run.

Run (as wired in ../mcp.json, host expands ${CURSOR_PLUGIN_ROOT}):
  uv run --with "mcp==1.30.0" python3 ${CURSOR_PLUGIN_ROOT}/server/server.py
Exactly pinned to mcp==1.30.0 (the 1.x line whose FastMCP API this server
uses; mcp 2.x renamed that API). First launch fetches that exact version
from PyPI via uv.
"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("cli-bridge")

STARTUP_CWD = Path.cwd().resolve()
_MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
MAX_TIMEOUT = 900


def _env(name: str, default: str = "") -> str:
    """Env value, ignoring unresolved host placeholders like ${VAR}."""
    v = os.environ.get(name, "").strip()
    if not v or "${" in v:
        return default
    return v


def _int_env(name: str, default: int) -> int:
    try:
        return int(_env(name, str(default)))
    except Exception:
        return default


OUTPUT_CAP = max(1000, _int_env("CLI_BRIDGE_OUTPUT_CAP_CHARS", 20_000))
DEFAULT_TIMEOUT = max(5, min(_int_env("CLI_BRIDGE_TIMEOUT_SECONDS", 300), MAX_TIMEOUT))

CLAUDE_PRESETS = {
    "opus-5.5": "claude-opus-5-5",
    "opus5.5": "claude-opus-5-5",
    "opus-5-5": "claude-opus-5-5",
    "claude-opus-5-5": "claude-opus-5-5",
    "fable": "fable",
}
CODEX_PRESETS = {
    "astra": "gpt-6-astra",
    "gpt-6-astra": "gpt-6-astra",
}
CLAUDE_PERMISSIONS = ("default", "plan", "acceptEdits", "auto", "dontAsk")
CODEX_SANDBOX_MAP = {
    "read-only": "read-only",
    "default": "read-only",
    "plan": "read-only",
    "dontAsk": "read-only",
    "acceptEdits": "workspace-write",
    "auto": "workspace-write",
    "workspace-write": "workspace-write",
}


def _allowed_roots() -> list[Path]:
    roots: list[Path] = []
    ws = _env("CLI_BRIDGE_WORKSPACE_ROOT")
    if ws:
        roots.append(Path(ws).expanduser())
    extra = _env("CLI_BRIDGE_ALLOWED_ROOTS")
    if extra:
        roots += [Path(p).expanduser() for p in extra.split(os.pathsep) if p.strip()]
    if not roots:
        roots = [STARTUP_CWD]
    out = []
    for r in roots:
        try:
            out.append(r.resolve())
        except Exception:
            out.append(r)
    return out


def _resolve_cwd(cwd: Optional[str]) -> Path:
    roots = _allowed_roots()
    if cwd:
        p = Path(cwd).expanduser()
        if not p.is_absolute():
            p = roots[0] / p
        p = p.resolve()
    else:
        p = roots[0]
    if not any(p == r or r in p.parents for r in roots):
        raise ValueError(
            f"cwd must be inside an allowed workspace root { [str(r) for r in roots] }, got: {p}. "
            "Set CLI_BRIDGE_WORKSPACE_ROOT to your workspace folder if the host launched "
            "this server from elsewhere."
        )
    if not p.is_dir():
        raise ValueError(f"cwd does not exist or is not a directory: {p}")
    return p


def _clamp_timeout(timeout) -> int:
    try:
        return max(5, min(int(timeout), MAX_TIMEOUT))
    except Exception:
        return DEFAULT_TIMEOUT


def _truncate(text: str, label: str) -> str:
    if len(text) <= OUTPUT_CAP:
        return text
    return text[:OUTPUT_CAP] + f"\n...[truncated {label} at {OUTPUT_CAP} chars]"


def _find(env_var: str, default_name: str) -> Optional[str]:
    override = _env(env_var)
    name = override or default_name
    # Absolute/relative path override: must exist. Bare name: search PATH.
    if Path(name).parent != Path("."):
        return name if Path(name).expanduser().exists() else None
    return shutil.which(name)


def _not_installed(tool: str, binary_name: str, install_hint: str) -> str:
    return (
        f"ERROR: {tool} CLI not found on the machine running this MCP server "
        f"(looked for '{binary_name}' on PATH). {install_hint} "
        "The CLI must be installed and logged in on the same machine where "
        "your agent host launches this plugin's MCP server — a CLI installed "
        "on a different computer is not visible here. Run cli_probe to re-check. "
        "No model call was made."
    )


def _auth_hint(text: str, tool: str) -> str:
    low = text.lower()
    if any(k in low for k in ("not logged in", "login", "unauthenticated", "unauthorized", "auth")):
        cmd = "claude" if tool == "claude" else "codex login"
        return (f" Hint: this looks like an auth/login problem. On the machine running "
                f"this server, run `{cmd}` interactively once to log in, then retry. "
                "This plugin never handles your credentials itself.")
    return ""


def _run(tool: str, argv: list[str], cwd: Path, timeout) -> str:
    display = [Path(argv[0]).name] + argv[1:]
    # Never echo the full prompt (last arg for both CLIs) in the header.
    safe_args = display[1:-1] if len(display) > 2 else display[1:]
    header = f"tool={tool} cwd={cwd} timeout={_clamp_timeout(timeout)}s cmd={display[0]} args={safe_args}"
    try:
        proc = subprocess.run(
            argv, cwd=str(cwd), timeout=_clamp_timeout(timeout),
            capture_output=True, text=True, shell=False, stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        return f"{header}\nERROR: timed out after {_clamp_timeout(timeout)}s.\n{_truncate(out, 'stdout')}"
    except Exception as e:  # launch failure, permission, etc.
        return f"{header}\nERROR: failed to launch: {type(e).__name__}: {e}"
    parts = [header, f"exit_code={proc.returncode}"]
    if proc.stdout:
        parts.append("--- stdout ---\n" + _truncate(proc.stdout, "stdout"))
    if proc.stderr:
        parts.append("--- stderr ---\n" + _truncate(proc.stderr, "stderr"))
    if not proc.stdout and not proc.stderr:
        parts.append("(no output)")
    if proc.returncode != 0:
        parts.append(_auth_hint((proc.stderr or "") + (proc.stdout or ""), tool))
    return "\n".join(p for p in parts if p)


def _resolve_claude_model(model: Optional[str]) -> str:
    m = (model or "").strip()
    if not m or m.lower() == "default":
        return _env("CLI_BRIDGE_CLAUDE_DEFAULT_MODEL", "claude-opus-5-5")
    preset = CLAUDE_PRESETS.get(m.lower())
    if preset:
        return preset
    if not _MODEL_RE.match(m):
        raise ValueError(f"invalid model id '{m}' (allowed: opus-5.5, fable, default, or a plain model id)")
    return m


def _resolve_codex_model(model: Optional[str]) -> Optional[str]:
    """Returns model to pass, or None to omit --model (Codex default)."""
    m = (model or "").strip()
    if not m or m.lower() == "default":
        env_default = _env("CLI_BRIDGE_CODEX_DEFAULT_MODEL")
        return env_default or None
    preset = CODEX_PRESETS.get(m.lower())
    if preset:
        return preset
    if not _MODEL_RE.match(m):
        raise ValueError(f"invalid model id '{m}' (allowed: astra, default, or a plain model id)")
    return m


def _prepare(prompt: str, cwd: Optional[str]) -> Path:
    if not prompt or not prompt.strip():
        raise ValueError("prompt must be non-empty")
    if len(prompt) > 100_000:
        raise ValueError("prompt too long (max 100000 chars)")
    return _resolve_cwd(cwd)


# ---------------- Probe (no model call) ----------------
@mcp.tool()
def cli_probe(cli: str = "all") -> str:
    """Cheap availability check — runs ONLY `<cli> --version`, never a model call.
    cli: all | claude | codex. Use this before any *_prompt call."""
    which = (cli or "all").strip().lower()
    if which not in ("all", "claude", "codex"):
        return "ERROR: cli must be one of: all, claude, codex"
    lines = [f"cli_probe cwd={STARTUP_CWD} allowed_roots={[str(r) for r in _allowed_roots()]}"]
    targets = []
    if which in ("all", "claude"):
        targets.append(("claude", "CLI_BRIDGE_CLAUDE_BIN", "claude",
                        "Install Claude Code: https://code.claude.com/docs (e.g. npm install -g @anthropic-ai/claude-code), then run `claude` once to log in."))
    if which in ("all", "codex"):
        targets.append(("codex", "CLI_BRIDGE_CODEX_BIN", "codex",
                        "Install Codex: https://developers.openai.com/codex (e.g. npm install -g @openai/codex), then run `codex login`."))
    for tool, env_var, default_name, hint in targets:
        binary = _find(env_var, default_name)
        if not binary:
            lines.append(_not_installed(tool, _env(env_var, default_name), hint))
            continue
        try:
            proc = subprocess.run([binary, "--version"], timeout=15, capture_output=True,
                                  text=True, shell=False, stdin=subprocess.DEVNULL, cwd=str(STARTUP_CWD))
            version = (proc.stdout or proc.stderr or "").strip().splitlines()
            lines.append(f"{tool}: FOUND at {binary} version={(version[0] if version else '(no version output)')!r} exit_code={proc.returncode}")
        except Exception as e:
            lines.append(f"{tool}: found at {binary} but --version failed: {type(e).__name__}: {e}")
    lines.append("Note: --version proves the binary exists; it does NOT prove you are logged in. "
                 "A *_prompt call that fails with an auth error means: log in on this machine first.")
    return "\n".join(lines)


# ---------------- Claude ----------------
@mcp.tool()
def claude_prompt(prompt: str, model: str = "opus-5.5", cwd: Optional[str] = None,
                  timeout: int = DEFAULT_TIMEOUT, permission_mode: str = "dontAsk") -> str:
    """Run Claude Code headless on this machine. THIS SPENDS the local Claude account's quota — get the user's OK first.
    model presets: opus-5.5 (=claude-opus-5-5, default), fable (=Claude CLI alias `fable`), default (=configured default), or a raw model id.
    permission_mode: default|plan|acceptEdits|auto|dontAsk (bypassPermissions is refused by this plugin).
    cwd: folder inside the allowed workspace root; omit to use the workspace root."""
    try:
        workdir = _prepare(prompt, cwd)
        resolved_model = _resolve_claude_model(model)
    except ValueError as e:
        return f"ERROR: {e}"
    if permission_mode not in CLAUDE_PERMISSIONS:
        return (f"ERROR: invalid permission_mode '{permission_mode}'. Allowed: {', '.join(CLAUDE_PERMISSIONS)}. "
                "bypassPermissions is intentionally refused by this plugin.")
    binary = _find("CLI_BRIDGE_CLAUDE_BIN", "claude")
    if not binary:
        return _not_installed("claude", _env("CLI_BRIDGE_CLAUDE_BIN", "claude"),
            "Install Claude Code: https://code.claude.com/docs (e.g. npm install -g @anthropic-ai/claude-code), then run `claude` once to log in.")
    argv = [binary, "-p", prompt, "--model", resolved_model,
            "--output-format", "text", "--permission-mode", permission_mode]
    return _run("claude", argv, workdir, timeout)


# ---------------- Codex ----------------
@mcp.tool()
def codex_prompt(prompt: str, model: str = "default", cwd: Optional[str] = None,
                 timeout: int = DEFAULT_TIMEOUT, permission_mode: str = "read-only") -> str:
    """Run OpenAI Codex headless (`codex exec`) on this machine. THIS SPENDS the local Codex account's quota — get the user's OK first.
    model presets: astra (=gpt-6-astra), default (=omit --model, Codex CLI's own default; default choice), or a raw model id.
    permission_mode / sandbox: read-only (default) | workspace-write. danger-full-access is refused by this plugin.
    cwd: folder inside the allowed workspace root; omit to use the workspace root."""
    try:
        workdir = _prepare(prompt, cwd)
        resolved_model = _resolve_codex_model(model)
    except ValueError as e:
        return f"ERROR: {e}"
    sandbox = CODEX_SANDBOX_MAP.get(permission_mode)
    if not sandbox:
        return (f"ERROR: invalid permission_mode '{permission_mode}'. Allowed: read-only, workspace-write "
                "(aliases: default, plan, dontAsk, acceptEdits, auto). danger-full-access is intentionally refused by this plugin.")
    binary = _find("CLI_BRIDGE_CODEX_BIN", "codex")
    if not binary:
        return _not_installed("codex", _env("CLI_BRIDGE_CODEX_BIN", "codex"),
            "Install Codex: https://developers.openai.com/codex (e.g. npm install -g @openai/codex), then run `codex login`.")
    argv = [binary, "exec"]
    if resolved_model:
        argv += ["--model", resolved_model]
    argv += ["--sandbox", sandbox, "--skip-git-repo-check", prompt]
    return _run("codex", argv, workdir, timeout)


if __name__ == "__main__":
    mcp.run(transport="stdio")
