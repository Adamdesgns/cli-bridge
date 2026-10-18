#!/usr/bin/env python3
"""Smoke test WITHOUT model calls.

Reads the packaged mcp.json, expands ${CURSOR_PLUGIN_ROOT} to this folder
(simulating what the plugin host does), launches the server with cwd = this
folder exactly as configured, then checks:
  initialize, tools/list (cli_probe, claude_prompt, codex_prompt),
  cli_probe (version-only), and the missing-binary error path for both
  prompt tools (on a machine without claude/codex installed).
If a CLI *is* installed on this machine, the prompt-call phase is SKIPPED
for that tool — calling it would spend real quota.
"""
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
cfg = json.loads((ROOT / "mcp.json").read_text())["mcpServers"]["cli-bridge"]
CMD = [cfg["command"]] + [a.replace("${CURSOR_PLUGIN_ROOT}", str(ROOT)) for a in cfg["args"]]
ENV_NOTE = {k: v for k, v in cfg.get("env", {}).items()}
print(f"launch (cwd={ROOT}): {CMD}")
print(f"mcp.json env keys (values are host-substituted variables, not set here): {sorted(ENV_NOTE)}")

def send(proc, obj):
    proc.stdin.write(json.dumps(obj) + "\n"); proc.stdin.flush()

def read_msg(proc):
    line = proc.stdout.readline()
    if not line: raise RuntimeError("server closed stdout")
    return json.loads(line)

proc = subprocess.Popen(CMD, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, cwd=str(ROOT))
try:
    send(proc, {"jsonrpc":"2.0","id":1,"method":"initialize","params":{
        "protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"smoke","version":"0"}}})
    init = read_msg(proc)
    assert "result" in init, f"initialize failed: {init}"
    print("initialize: PASS", (init["result"] or {}).get("serverInfo"))
    send(proc, {"jsonrpc":"2.0","method":"notifications/initialized"})
    send(proc, {"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}})
    lst = read_msg(proc)
    tools = [t["name"] for t in lst["result"]["tools"]]
    print("tools/list:", tools)
    for expected in ("cli_probe", "claude_prompt", "codex_prompt"):
        assert expected in tools, f"missing tool {expected}"
    print("tools/list: PASS")

    send(proc, {"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"cli_probe","arguments":{"cli":"all"}}})
    res = read_msg(proc)
    probe_text = "".join(c.get("text","") for c in res["result"]["content"])
    print("cli_probe:"); print("  " + probe_text.replace("\n", "\n  ")[:1200])
    claude_missing = "claude CLI not found" in probe_text
    codex_missing = "codex CLI not found" in probe_text

    next_id = 4
    for name, missing in (("claude_prompt", claude_missing), ("codex_prompt", codex_missing)):
        if not missing:
            print(f"{name}: SKIPPED prompt-call phase (CLI is installed here; calling it would spend quota)")
            continue
        send(proc, {"jsonrpc":"2.0","id":next_id,"method":"tools/call","params":{
            "name": name, "arguments": {"prompt": "SMOKE TEST — binary should be missing, do not run"}}})
        next_id += 1
        res = read_msg(proc)
        text = "".join(c.get("text","") for c in res["result"]["content"])
        ok = "not found on the machine running this MCP server" in text and "No model call was made" in text
        print(f"{name} missing-binary path: {'PASS' if ok else 'FAIL'} :: {text[:200]}")
        assert ok, text

    # cwd allowlist must reject escaping the launch (workspace) root
    send(proc, {"jsonrpc":"2.0","id":99,"method":"tools/call","params":{
        "name":"claude_prompt","arguments":{"prompt":"x","cwd":"/etc"}}})
    res = read_msg(proc)
    text = "".join(c.get("text","") for c in res["result"]["content"])
    ok = "allowed workspace root" in text
    print(f"cwd allowlist (/etc rejected): {'PASS' if ok else 'FAIL'} :: {text[:200]}")
    assert ok, text

    # permission ceilings
    send(proc, {"jsonrpc":"2.0","id":100,"method":"tools/call","params":{
        "name":"claude_prompt","arguments":{"prompt":"x","permission_mode":"bypassPermissions"}}})
    res = read_msg(proc)
    text = "".join(c.get("text","") for c in res["result"]["content"])
    ok = "refused" in text
    print(f"claude bypassPermissions ceiling: {'PASS' if ok else 'FAIL'} :: {text[:160]}")
    assert ok, text

    print("SMOKE TEST PASS (no model calls made)")
finally:
    proc.terminate()
