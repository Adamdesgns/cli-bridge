#!/usr/bin/env python3
"""Static package validation: no model calls, no network.
Checks manifest/mcp/skill structure per Cursor plugin reference and scans
for secrets / absolute or user-specific paths that must not ship."""
import json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
errors, warnings = [], []

def err(m): errors.append(m)
def warn(m): warnings.append(m)

# plugin.json
pj_path = ROOT / ".cursor-plugin" / "plugin.json"
try:
    pj = json.loads(pj_path.read_text())
except Exception as e:
    err(f"plugin.json unreadable: {e}"); pj = {}
name = pj.get("name", "")
if not re.fullmatch(r"[a-z0-9][a-z0-9.\-]*[a-z0-9]|[a-z0-9]", name or ""):
    err(f"plugin name not lowercase kebab-case: {name!r}")
if pj.get("version") != "0.1.0":
    warn(f"version is {pj.get('version')!r} (expected 0.1.0 for first submission)")
for field in ("description",):
    if not pj.get(field): err(f"plugin.json missing {field}")
author = (pj.get("author") or {}).get("name", "")
if "TODO" in str(pj.get("author")) or "TODO" in str(pj.get("repository")):
    warn("plugin.json still has TODO author/repository placeholders (must fix before submission)")
if pj.get("mcpServers") != "./mcp.json":
    warn("plugin.json mcpServers should point at ./mcp.json")
if pj.get("skills") != "./skills/":
    warn("plugin.json skills should point at ./skills/")
logo = pj.get("logo")
if logo and not (ROOT / logo).exists():
    err(f"logo path does not exist: {logo}")

# mcp.json
try:
    mcp_cfg = json.loads((ROOT / "mcp.json").read_text())
    srv = mcp_cfg["mcpServers"]["cli-bridge"]
    assert srv["command"] == "uv", "command must be uv"
    joined = " ".join(srv.get("args", []))
    assert "${CURSOR_PLUGIN_ROOT}/server/server.py" in joined, "args must use ${CURSOR_PLUGIN_ROOT}/server/server.py"
    assert not re.search(r"/workspace|/home/|/Users/|[A-Za-z]:\\", joined), "absolute/user path in mcp args"
except Exception as e:
    err(f"mcp.json problem: {e}")

# referenced paths stay inside root, relative, no ..
for key in ("skills", "mcpServers"):
    v = pj.get(key)
    if isinstance(v, str) and (".." in v or v.startswith("/")):
        err(f"plugin.json {key} must be relative without '..': {v}")

# SKILL.md frontmatter
skill = ROOT / "skills" / "cli-bridge" / "SKILL.md"
if not skill.exists():
    err("skills/cli-bridge/SKILL.md missing")
else:
    t = skill.read_text()
    m = re.match(r"^---\n(.*?)\n---\n", t, re.S)
    if not m: err("SKILL.md missing YAML frontmatter")
    else:
        if "name: cli-bridge" not in m.group(1): err("SKILL.md frontmatter name must be cli-bridge")
        if "description:" not in m.group(1): err("SKILL.md frontmatter missing description")

# required files
try:
    dot = json.loads((ROOT / ".mcp.json").read_text())
    if dot.get("mcpServers") != mcp_cfg.get("mcpServers"):
        err(".mcp.json must mirror mcp.json mcpServers (cursor.directory auto-detects the dotted file)")
except Exception as e:
    err(f".mcp.json problem: {e}")
for rel in ("README.md", "LICENSE", "PUBLISHING.md", "server/server.py", "assets/logo.svg", ".mcp.json"):
    if not (ROOT / rel).exists():
        err(f"missing required file: {rel}")

# scan shipped text files for secrets / user-specific paths (allow docs that *warn* about them generically)
SECRET_RE = re.compile(r"(sk-[A-Za-z0-9]{16,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|-----BEGIN [A-Z ]*PRIVATE KEY-----|api[_-]?key\s*[:=]\s*['\"][^'\"]{8,})", re.I)
USER_RE = re.compile(r"(AlienAdam|/workspace/|C:\\\\Users\\\\|machineId)", re.I)
skip_scan = {"PUBLISHING.md"}  # publishing notes may discuss the old scaffold by path in parent workspace? still scanned below separately
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix in (".py", ".md", ".json", ".svg") and "__pycache__" not in str(p) and p.name != "validate_package.py":
        text = p.read_text(errors="ignore")
        if SECRET_RE.search(text):
            err(f"possible secret in {p.relative_to(ROOT)}")
        # USER_RE scan: README/server/skill must be generic; PUBLISHING.md may mention verification context but should also stay generic
        if USER_RE.search(text):
            err(f"user-specific path/name in {p.relative_to(ROOT)}: {USER_RE.search(text).group(0)}")

print(f"validate_package: root={ROOT}")
for w in warnings: print(f"  WARN: {w}")
for e in errors: print(f"  ERROR: {e}")
print("RESULT:", "FAIL" if errors else "PASS (warnings allowed pre-submission)")
sys.exit(1 if errors else 0)
