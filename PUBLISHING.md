# Publishing CLI Bridge to the marketplace — exact path, blockers, decisions

Status: **package built and locally validated, NOT submitted.** Nothing in
this document has been sent anywhere. The publisher (repo owner) must approve
the final package and make the decisions in §5 before anyone follows §4.

---

## 0. "Launched and live when I wake up" — what is actually possible

Short answer: **a public listing by morning is realistically possible only
on the community directory (cursor.directory), and only if the publisher
personally does the sign-in/submit clicks in §4A tonight. The official
Cursor Marketplace cannot be live by morning — it is gated by an external
manual reviewer, and no one on our side controls that clock.**

| Track | Who gates "live"? | Realistic time to live | Live by morning? |
|---|---|---|---|
| **A. cursor.directory** (community listing) | Automated security scan (`safe`/`suspicious`/`malicious` verdict by a Cursor SDK agent on a fresh clone), then indexing | Scan typically starts almost immediately; a third-party submission guide reports verdicts "within a few minutes". **No SLA is published** — treat minutes-to-hours as hope, not promise; a `suspicious` flag means a human/admin queue instead | **Possibly yes**, if the repo is public tonight, the scan returns `safe`, and the publisher does the submit clicks. Still not guaranteed or in our control |
| **B. Official Cursor Marketplace** (cursor.com/marketplace) | Anysphere humans: manual review of every plugin *and every update*, curated, sole discretion, no reasons owed | Forum staff (May 2026): "reviews typically take **1–2 weeks**". Forum staff (Apr 2026): "we don't have a specific SLA… timelines can vary." Public reports include 3+ weeks with no acknowledgement; the form sends **no confirmation email and no status page** | **No.** Anyone promising this by morning is promising someone else's queue |
| C. Local install only (`~/.cursor/plugins/local`) | Nobody — your own machine | Minutes | Yes, but that is *installed for you*, not "listed on a marketplace" for anyone else |

Two more facts that change the plan, both from Cursor's own forum staff
(Jul 2026, after the docs pages above were written): direct submissions
through the old marketplace publish form "generally aren't accepted
anymore" and publishing has been "centralized" on cursor.directory, which
is "now the main listing location, replacing the marketplace". The official
docs still describe the publish form (they may simply be stale). The sane
launch sequence is therefore: **directory first (tonight, fastest real
"live"), official-marketplace form as a second, slow track — expect the
directory, not the curated marketplace, to be what users find first.**

What "submitted tonight" can honestly mean by wake-up: repo public and
final, directory submission in/scan passed or pending, marketplace form (if
used) in Anysphere's queue with no confirmation to show. The remaining wait
is an external reviewer's, not engineering time.

**Where the PR Gate (PR-approval agent) fits — and where it does not:**
neither listing track has a submission PR. cursor.directory is explicit:
"All content is submitted through the website — no pull requests needed."
The official track is a web form. A PR approval only appears if *our own
repo* is run that way: e.g. plugin code lands on `main` via a pull request
under branch protection, and the PR Gate reviews/approves that merge before
submission (and again for every later change — directory re-indexing and
marketplace re-review both key off what's on the repo). The PR Gate can
gate our code; it cannot gate, speed up, or approve Cursor's listing review.

---


## 1. What "a marketplace plugin" verifiably is here

Two host ecosystems are in play, and they are not proven to be the same
marketplace:

### 1a. Cursor Marketplace — VERIFIED (official docs, fetched 2026-10-17)

A Cursor Plugin is a folder (distributed as a **public Git repository**) with:

- `.cursor-plugin/plugin.json` at the plugin root — only `name`
  (lowercase kebab-case) is strictly required; `description`, `version`,
  `author{name,email}`, `homepage`, `repository`, `license`, `keywords`,
  `logo`, `skills`, `mcpServers`, `variables`, etc. are documented optional
  fields and are what real marketplace listings use.
- `mcp.json` at the plugin root for MCP servers (auto-discovered; only
  override via the manifest's `mcpServers` field when using a custom path).
  This package instead points `mcpServers: "./mcp.json"` explicitly, as real
  listings do (see §1c).
- `skills/<skill-name>/SKILL.md` (YAML frontmatter `name` + `description`)
  auto-discovered from `skills/`; rules/agents/commands/hooks are optional
  extras this package does not need.
- Optional `assets/logo.svg` committed to the repo and referenced by
  relative path (relative paths resolve to `raw.githubusercontent.com` URLs).
- A `README.md` documenting usage/configuration (on the submission checklist).
- `${CURSOR_PLUGIN_ROOT}` is the documented variable the host expands to the
  plugin's install path in an MCP server's `command`, `args`, `env`, and
  `cwd`. The Agent Plugins standard's `${PLUGIN_ROOT}` is explicitly **not**
  expanded by Cursor — do not use it.
- Alternative format: an "Agent Plugin" has `plugin.json` at the root
  (`$schema: https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`)
  and can bundle only skills + MCP servers. This package uses the **Cursor
  Plugin** format because the marketplace docs, submission checklist, and
  every inspected real listing use it, and because it supports `variables`
  (dashboard-configured, non-secret settings) for the CLI binary paths /
  workspace root.

Sources (all fetched live for this package):

- Plugin reference / manifest / components / submission checklist:
  https://cursor.com/docs/reference/plugins
- Building & submitting (same reference, `/docs/plugins/building` route):
  https://cursor.com/docs/plugins/building
- Plugins overview, local testing, marketplace description:
  https://cursor.com/docs/plugins.md (= https://cursor.com/docs/plugins)
- Marketplace security / review policy:
  https://cursor.com/help/security-and-privacy/marketplace-security
- Publisher Terms (legal contract for submitters, last updated 2026-05-06):
  https://cursor.com/marketplace-publisher-terms
- Official template repo: https://github.com/cursor/plugin-template
  (single-plugin guidance: plugin contents at repo root, one
  `.cursor-plugin/plugin.json`, no `marketplace.json`; multi-plugin repos
  add a root `.cursor-plugin/marketplace.json` listing each plugin)
- Official example plugins repo: https://github.com/cursor/plugins
- Community directory submission (website form, `.mcp.json` auto-detection,
  automated security scan, admin moderation queue):
  https://github.com/cursor/community-plugins (README, "Contributing") and
  https://cursor.directory/plugins/new (sign-in required; form not readable
  anonymously when fetched for this package)
- Review-time reality checks (Cursor forum, staff replies): "typically
  1–2 weeks" (May 2026, forum.cursor.com/t/plugin-marketplace/160943);
  "no specific SLA" (Apr 2026, t/cursor-plugin-submit-as-company-not-individual/156274);
  ~3 weeks' silence + "centralized on cursor.directory… old publish form
  generally aren't accepted anymore" (Jul 2026, t/pending-review-xpoz-plugin-submission-submitted-june-24/165776);
  form sends no confirmation, "usually a couple of weeks, sometimes longer"
  (t/whatsetter-plugin-submitted-on-sept-13-no-acknowledgement-yet/172489).
  These are forum reports/staff posts, not contractual SLAs — cited to size
  expectations, and they outrank any optimistic guess.

### 1b. Grok Bot plugin loading — PARTIALLY VERIFIED, marketplace UNVERIFIED

What could be verified locally: this machine's installed plugins live under
the local plugin cache (`agent-data/plugins/cache/cursor-public/<name>/<commit>/` on the build machine) and use
exactly the Cursor format above (`.cursor-plugin/plugin.json`, root
`mcp.json`, `skills/*/SKILL.md`). So a package in Cursor Plugin format is the
format this environment actually loads — that is verified from real files,
not marketing copy.

What could **not** be verified: any Grok Bot–specific marketplace, publisher
portal, or submission process separate from Cursor's. No such portal was
found in the available tools or docs. **Do not assume submitting to Cursor
automatically lists the plugin in any Grok Bot catalogue, or vice versa.**
Whoever submits must first confirm (with the Grok Bot/Cursor team, or in the
publish form itself) which catalogue `cursor.com/marketplace/publish` feeds
and whether a separate Grok Bot listing step exists. This is Blocker B4 in §5.

### 1c. Real installed plugins inspected (structure only, no secrets read)

Inspected in the local plugin cache (`cursor-public/<name>/<commit>/` folders):

- `context-dev/.../.cursor-plugin/plugin.json` — fields this package mirrors:
  `name`, `displayName`, `version`, `description`, `author{name,email}`,
  `homepage`, `repository`, `license`, `logo`, `keywords`, `category`,
  `tags`, `skills: "./skills/"`, `mcpServers: "./mcp.json"`; root `mcp.json`
  with a `mcpServers` object.
- `github/...` and `google-calendar/...` — same manifest shape; `github`
  also shows the `variables` pattern (JSON-Schema object in `plugin.json`,
  `${VAR}` placeholders in `mcp.json`, values set by users in the dashboard,
  never committed). This package follows that pattern for its optional,
  non-secret settings.
- `shadcn/...` — shows the alternative inline form
  (`"mcpServers": {"shadcn": {"command": "npx", "args": [...]}}` inside
  `plugin.json`). This package uses a separate `mcp.json` file instead,
  which is the more common form in the inspected listings.
- `superpowers/.../skills/*/SKILL.md` — skill frontmatter is exactly
  `name` + `description` between `---` fences; this package's skill matches.

No tokens, keys, or credential files in those folders were opened or copied.

---

## 2. This package

Repo-root layout (this `marketplace/` folder **is** the plugin root and
should become the root of the submission repository — see §4 step 1):

```
.cursor-plugin/plugin.json   manifest: name cli-bridge, v0.1.0, TODO author/repo placeholders
mcp.json                     stdio MCP launch: uv run --with "mcp<2" python3 ${CURSOR_PLUGIN_ROOT}/server/server.py
server/server.py             cli_probe + claude_prompt + codex_prompt (generic, no machine-specific paths)
skills/cli-bridge/SKILL.md   when/how to use the tools, probe-first, spend-approval, permission ceilings
assets/logo.svg              placeholder logo (replace or keep, see §5)
README.md                    prerequisites, config, privacy/security, troubleshooting
LICENSE                      MIT text with <year> <copyright holders> placeholder
CHANGELOG.md                 0.1.0 entry
PUBLISHING.md                this file (may be kept in the repo; reviewers reading it is fine)
smoke_test.py                host-simulating MCP test, no model calls
scripts/validate_package.py  static manifest/skill/no-secrets validation
.gitignore
```

Deliberate design choices a reviewer (and the publisher) should know:

- **No binaries shipped, no keys handled.** The server is a single stdlib +
  `mcp<2` Python file launched via `uv`; Claude/Codex are the *user's own*
  installs using their own logins. First launch needs network once so `uv`
  can fetch the pinned `mcp<2` package.
- **Permission ceilings in code:** Claude `bypassPermissions` refused;
  Codex `danger-full-access` refused. Cwd allowlist, timeout/output caps,
  argv-only execution, validated model ids.
- **Generic presets only:** Claude `opus-5.5`/`fable`, Codex `astra`/`default`.
  These ids help only users whose CLI/account has access to those models;
  the README says so plainly instead of promising access.

---

## 3. Verified marketplace rules that affect this plugin

From the Publisher Terms + Marketplace security pages (read in full):

1. **Open source is mandatory.** "All marketplace plugins must be open
   source." The submission repo must be public.
2. **Free to users.** The Marketplace is free for publishers to use, and the
   publisher "will not charge Users any fees, whether directly or
   indirectly, for access to or use of a Plugin through the Marketplace."
   (Users still spend their *own* Claude/Codex quota — that is their CLI
   vendor relationship, not a fee for this plugin — but the plugin itself
   cannot be paywalled.)
3. **Permissive licenses only.** "You may only use open-source licenses that
   are classified as permissive (e.g., MIT, BSD, and Apache 2.0). Copyleft
   or restrictive licenses (e.g., GPL, AGPL, LGPL) may not be included."
   → MIT (current placeholder) or Apache-2.0 both comply; GPL anything does not.
4. **Manual review of everything.** Every plugin *and every update* is
   manually reviewed for security, data handling, and quality before
   listing; the marketplace is curated, approval is at Anysphere's sole
   discretion, and no reasons are given for rejection. Updates are **not**
   auto-pulled from the repo — after changing a listed plugin the publisher
   requests a re-index and works through any reviewer questions.
5. **Publisher obligations after listing:** maintain the plugin, keep it
   compatible, respond to/resolve reported security or stability issues
   (or risk delisting), provide end-user support yourself, keep all
   descriptions accurate, never collect/process plugin/user data beyond the
   disclosed functionality, never train models on user content, comply with
   Cursor Brand Guidelines (call the product "Cursor"), and accept the
   Terms' arbitration / liability-cap / indemnity clauses. Read the Terms
   before submitting — submitting *is* accepting them.
6. **Submission checklist (docs):** valid manifest; unique lowercase
   kebab-case `name`; clear `description`; valid frontmatter on all
   components; logo committed + relatively referenced if provided;
   `README.md` documenting usage/configuration; every `${VAR}` used in
   `mcp.json` declared in the manifest `variables` schema; all manifest
   paths relative and valid (no `..`, no absolute paths); plugin tested
   locally first.

**Is submission open to individuals? — plainly: the form is open, listing
is not guaranteed.** The docs tell any builder to submit at
`cursor.com/marketplace/publish`, and the Publisher Terms describe an
application any publisher may make (with identity/business-legitimacy
verification). At the same time the security page says Cursor works "with a
small group of trusted partners," keeps the marketplace "curated," and plans
to "open this up more broadly." So: an individual can apply; whether an
individual CLI-bridge plugin is accepted is unverified and entirely at
Cursor's discretion. Budget for rejection or silence.

---

## 4. Exact publishing path (verified steps; do NOT run until §5 is decided)

### Shared preparation (whoever prepares the repo; no account needed yet)

1. **Create the public repo.** New public Git repository (host/org = Decision
   D2). Put the *contents of this `marketplace/` folder at the repo root*
   (single-plugin layout per the official template guidance). Do not include
   the parent scaffold folders, any `__pycache__`, or local test edits.
   This repo is also the artifact both listing tracks scan/review — the
   `mcp.json` serves Cursor-format hosts and the identical [`.mcp.json`](.mcp.json)
   mirror exists because cursor.directory's auto-detector looks for the
   dotted filename at the repo root.
   - Multi-plugin alternative (only if bundling several plugins in one repo):
     keep this folder as `cli-bridge/` inside the repo and add a root
     `.cursor-plugin/marketplace.json`:
     `{"name": "<your-marketplace>", "owner": {"name": "...", "email": "..."}, "plugins": [{"name": "cli-bridge", "source": "cli-bridge", "description": "..."}]}`.
     Not recommended for a first single-plugin submission.
2. **Fill every placeholder.** `author.name/email`, `homepage`, `repository`
   in `.cursor-plugin/plugin.json`; copyright holder + year in `LICENSE`;
   confirm `license` matches; replace or approve `assets/logo.svg`; make
   sure the README support/contact route is real (publisher provides support).
3. **Re-validate in the repo copy:** `python3 scripts/validate_package.py`
   (must be PASS with no TODO warnings), `python3 -m py_compile server/server.py`,
   `python3 smoke_test.py` (PASS, no model calls).
4. **Test as a local plugin:** copy the repo folder to
   `~/.cursor/plugins/local/cli-bridge` on a test machine, restart the host /
   Developer: Reload Window, confirm the skill + `cli-bridge` MCP server
   load, run `cli_probe`, and — only with the test account owner's explicit
   OK and a cheap prompt — one real call per installed CLI. Also test on
   each OS you claim to support (see Blocker B5). Remove the local copy
   afterwards if a marketplace install would shadow it (marketplace
   installs take precedence over same-name local copies).
5. **(If the repo uses PRs) get the merge approved.** If `main` is protected
   and changes land by pull request, this is where the PR Gate fits: it
   reviews/approves the PR that puts the final package on `main`. Submit
   only what is on `main` — both tracks read the repo as submitted. The PR
   Gate has **no** role in either listing form itself.

### 4A. Fast track — cursor.directory community listing (the "by morning" hope)

6. The **publisher personally** opens https://cursor.directory/plugins/new,
   signs in with GitHub or Google (the account that should own the listing),
   pastes the public GitHub repo URL, and clicks **Submit**. No PR, no fee
   found in the docs.
7. An automated Cursor SDK agent (`composer-2`) security-scans a fresh clone
   plus inline component content and records `safe` / `suspicious` /
   `malicious`. The scan is asynchronous (queued, cron-drained every
   minute). The listing appears once the scan returns `safe`; `suspicious`
   goes to an admin moderation queue (slower, human-gated), `malicious`
   blocks. If flagged wrongly, the recovery path is the contact route on
   cursor.directory / issues on the `cursor/community-plugins` repo.
8. Verify the live listing page renders the README, detects
   `skills/cli-bridge/SKILL.md` and the MCP server from `.mcp.json`, and
   shows the right license. "Detected" on the directory does not by itself
   prove a given host expands `${CURSOR_PLUGIN_ROOT}` — the local test in
   step 4 remains the functional proof.

### 4B. Slow track — official Cursor Marketplace (curated, human-reviewed)

9. The **publisher personally** goes to
   **https://cursor.com/marketplace/publish** and submits the same public
   repository URL with accurate listing metadata. Treat the form as possibly
   deprecated in favour of §4A (Jul 2026 staff note, §0) — submitting there
   too does no harm that we know of, but do not duplicate-submit repeatedly
   ("Don't submit the form again. It'll just create a duplicate entry." —
   staff, WhatSetter thread). This step binds the submitter to the
   Publisher Terms and was **not** done for this package.
10. **Review:** expect manual code review of `server/server.py`, scrutiny of
    the subprocess/permission design and quota-spending behaviour, and
    identity/business-legitimacy verification. Typically 1–2 weeks, no SLA,
    sometimes longer, no confirmation email/status page (status, if needed:
    email `marketplace-publishing@cursor.com` with plugin name, repo URL,
    and submission date). Approval/rejection is at Anysphere's sole
    discretion with no reasons owed.
11. **After listing (either track):** releases = push changes (via PR + PR
    Gate if that's the repo's flow), then for the official marketplace
    request a re-index per the Publisher Terms and re-clear manual review;
    for the directory, expect a re-scan of the updated repo. Monitor user
    issues; the publisher, not Cursor, provides support.

### What only the publisher (Adam) can do — nobody else can substitute

- **Own the accounts:** create/own the public GitHub repo under his account
  or org (D2), and be the GitHub/Google identity that submits on
  cursor.directory and the identity that accepts the Publisher Terms on the
  official form. An agent can prepare every file; it cannot be the legal
  publisher, pass identity/business verification, or click Submit as him.
- **Make the §5 decisions** (publisher name/email, repo home, license +
  copyright holder) — placeholders ship unfilled until he does.
- **Approve any PR** that branch protection puts in front of `main` (or
  delegate it to the PR Gate acting on his rules) before submission.
- **Log in the real CLIs** on a real test machine (his Claude/Codex
  accounts) for the §4 step-4 live test, and explicitly approve the cheap
  test prompts — agents must not spend his quota on their own say-so.
- **Answer reviewers** and provide ongoing user support/security response
  after listing (a Publisher Terms obligation that attaches to him).

No other portal, submission PR to Cursor, or fee was found in the official
docs. If either form asks for anything not covered here (business details,
additional attestations), that is new information — record it in this file
before proceeding.

---

## 5. Blockers / decisions the publisher must make BEFORE submission

**Decisions (publisher chooses, then placeholders get filled):**

- **D1 — Publisher identity.** Legal name / display name, contact email, and
  homepage for `plugin.json` + `LICENSE`. The Terms have the publisher
  warrant their identity and accept indemnity/arbitration — a person, not
  this tooling, must own that.
- **D2 — Repo host + account.** Which GitHub (per the logo-URL resolution,
  GitHub is the assumed host in the docs) org/user owns the public repo, and
  the final repo URL for `plugin.json: repository`. Also confirm the plugin
  `name` `cli-bridge` is acceptable/unique there, or rename now (renaming
  after listing is painful).
- **D3 — License.** MIT (placeholder, simplest, complies) vs Apache-2.0
  (also complies, adds a patent grant). Must be permissive — no copyleft.
  Also fill the `<year> <copyright holders>` line; an unfilled template
  license is a sloppy-review risk.

**Blockers / open questions (need answers or acceptance of risk):**

- **B1 — Individual acceptance is unverified.** The publish form is open but
  the marketplace is curated around trusted partners (§3.6). Submission may
  be rejected or ignored without reasons. Accept that risk or seek a
  partner/introduction route first.
- **B2 — Which catalogue does this actually enter?** It is unverified
  whether Cursor's publish form also lists plugins for Grok Bot users, or
  whether Grok Bot has a separate process (§1b). Confirm before promising
  anyone a "Grok Bot marketplace" listing.
- **B3 — Host expansion + runtime assumptions.** This package relies on the
  host expanding `${CURSOR_PLUGIN_ROOT}` (documented for Cursor) and on
  `uv` + Python 3.11+ existing on the user's machine. Cursor-variable
  defaults for the `CLI_BRIDGE_*` settings are declared, but dashboard
  configuration behaviour should be confirmed in the local-plugin test
  (§4.4) on the real target host(s). If a target host doesn't expand the
  variable, users need the documented absolute-path fallback edit.
- **B4 — Model preset availability.** `claude-opus-5-5`, the Claude `fable`
  alias, and `gpt-6-astra` may not exist for every user's CLI version or
  account. Listing copy must not promise them; expect reviewer/user
  confusion and support questions. Consider whether presets stay prominent
  or become "examples" in a later version — copy is already written to the
  safer wording.
- **B5 — Cross-platform proof.** The server was validated only on Linux
  without either CLI installed (missing-binary paths). Claude/Codex present
  + logged-in behaviour, and Windows/macOS launches, are untested. At
  minimum one real-machine test per claimed OS is needed before submission
  claims are made (§4.4) — with the account owner's explicit OK for the
  cheap test prompts, since real calls spend quota.
- **B6 — Review scrutiny of design.** A plugin that shells out to other
  agents and spends user quota will (rightly) get hard security review:
  permission ceilings, cwd allowlist, and the spend-approval skill wording
  are the mitigations. A reviewer may still require changes (e.g. remote-MCP
  instead of local stdio, or no prompt tools at all). Also note the security
  page's "Plugins are lightweight… No binaries are shipped" framing — this
  package ships executable Python launched via `uv`; be ready to justify it.

---

## 6. What was validated locally for this package (2026-10-17, Linux box)

See the build report accompanying this package for the exact command output:
`validate_package.py`, `py_compile`, and `smoke_test.py` (MCP initialize +
tools/list against the packaged `mcp.json` launch command with
`${CURSOR_PLUGIN_ROOT}` expanded to the package folder and cwd = that
folder), covering `cli_probe` and both missing-binary error paths plus the
cwd-allowlist and permission-ceiling rejections. **Caveat:** neither
`claude` nor `codex` is installed on the validation machine, so no real
model call, login flow, or successful CLI execution has been exercised —
§4.4/B5 remain open. No submission, registration, or paid model call was
made while building this package.
