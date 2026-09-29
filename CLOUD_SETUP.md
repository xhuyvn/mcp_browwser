# Claude Code Cloud Setup — llm-browser

How to develop this project with Claude Code cloud sessions (claude.ai/code) on a private
GitHub repository.

## Summary

| Decision | Choice |
|---|---|
| Where code is written | Claude Code cloud sessions, one session and one PR per phase |
| Repo | Private GitHub repo; everything Claude needs is committed |
| Cloud environment | Dedicated `llm-browser` environment: Custom network, setup script installs Xvfb/noVNC + Playwright browsers |
| Project setup | `.claude/settings.json` SessionStart hook runs `scripts/cloud_setup.sh` (`uv sync`), no-op locally |
| LLM for Phase 8 in cloud | OpenRouter `:free` models, key held by the environment (API credential on Pro/Max) |
| Phase 6 handoff | Built and auto-tested in cloud; one manual noVNC check locally |
| Phase 8 evals | `smoke` set + cassette replay in cloud; `full` set with local models on the dev machine |
| Never in the cloud | Real sites, real profiles/cookies, bank data, secrets in env vars you share |

Phases 0, 2, 3, 4, 5, 7, 9 run fully in the cloud. Phases 1, 6, 8 run in the cloud with a
short local follow-up.

---

## Step 0 — Prerequisites

- [ ] Claude plan with Claude Code cloud sessions (Pro, Max, Team, or Enterprise with a
      premium / Chat + Claude Code seat). Cloud sessions are a research preview.
- [ ] GitHub account; `git` locally.
- [ ] OpenRouter account (only needed from Phase 8).
- [ ] Optional: Claude Code CLI locally (`claude`) for `/web-setup`, `claude --cloud`, `--teleport`.

## Step 1 — Create the private repo and commit the starter files

1. On GitHub, create a **private** repository, e.g. `llm-browser`, with no template files.
2. Put the starter files in place locally:

```
llm-browser/
  CLAUDE.md
  .claude/settings.json
  config/models.yaml
  docs/ARCHITECTURE.md
  docs/PLAN.md
  docs/CLOUD_SETUP.md
  scripts/cloud_setup.sh
  scripts/cloud_env_setup.sh      # reference copy; the real one lives in the environment UI
```

3. Add a `.gitignore` before the first commit:

```
.venv/
__pycache__/
profiles/
*.har
.env
storage_state*.json
artifacts/
cassettes/private/
```

4. Commit and push:

```bash
git init -b main
git add .
git commit -m "Project instructions, architecture, plan, cloud setup"
git remote add origin git@github.com:<you>/llm-browser.git
git push -u origin main
```

Cloud sessions start from a fresh clone, so only committed files exist there. Your
personal `~/.claude/` settings, skills and MCP servers do **not** carry over.

## Step 2 — Connect GitHub to Claude Code

Use one of these:

- **Web:** open https://claude.ai/code and follow onboarding to connect GitHub. If asked to
  install the Claude GitHub app, grant it **only the `llm-browser` repository**.
- **CLI:** run `claude`, sign in with `/login`, then `/web-setup`. This syncs your `gh` token
  and creates a **Default** environment if you have none.

Check: in claude.ai/code, the repository picker shows `llm-browser`.

## Step 3 — Create the OpenRouter key (can wait until Phase 8)

1. In OpenRouter, create a new key named `llm-browser-cloud`.
2. Set a **credit limit** on the key (e.g. $0–$2) so a leak costs nothing.
3. Optional: a one-time $10 credit purchase raises the free-model daily cap from 50 to
   1,000 requests (20 requests/minute stays the same).
4. Keep the key in your password manager. Do not paste it into any chat.

## Step 4 — Create the `llm-browser` cloud environment

At https://claude.ai/code, click the cloud icon with the environment name (row above the
message box) → **Add cloud environment**.

**4.1 Name:** `llm-browser`

**4.2 Network access:** **Custom**
- Tick **Also include default list of common package managers**.
- Allowed domains:

```
cdn.playwright.dev
playwright.download.prss.microsoft.com
playwright.azureedge.net
```

If a later install fails, the proxy error (`x-deny-reason: host_not_allowed`) names the
blocked host. Add it here. Changing the list rebuilds the environment cache.

On Team/Enterprise also add `openrouter.ai` (see 4.5).

**4.3 Environment variables** (non-secret only):

```
BASH_DEFAULT_TIMEOUT_MS=600000
BASH_MAX_TIMEOUT_MS=1200000
LLM_PROFILE=cloud
LLM_BASE_URL=https://openrouter.ai/api/v1
```

**4.4 Setup script:** paste the contents of `scripts/cloud_env_setup.sh`. Replace
`1.XX.0` with the exact Playwright version pinned in `pyproject.toml` (Phase 0 sets it;
until then, use the current release and update both places together).

Rules for this script: must exit 0, and should finish in under ~5 minutes, otherwise the
environment is not cached and every session reinstalls.

Click **Create environment**.

**4.5 Add the OpenRouter key** (from Phase 8)

- **Pro / Max:** open the environment again (gear icon) → **API credentials** → **Add
  credential**:
  - Name: `OpenRouter`
  - Allowed websites: `openrouter.ai`
  - Credential type: **Bearer**; header `Authorization`, prefix `Bearer`, value = the key
  - **Connect**
  The key never enters the VM; the proxy adds it to requests for `openrouter.ai`.
- **Team / Enterprise:** API credentials aren't available. Add
  `OPENROUTER_API_KEY=<key>` to environment variables and `openrouter.ai` to the allowed
  domains. Keep this environment **personal** (never share it with the org), because
  anyone who uses the environment can read its variables.

**4.6 Select it:** in the environment selector, check `llm-browser`. From the CLI, run
`/remote-env` and pick it.

## Step 5 — First session: verify the environment

Start a session on `llm-browser` / branch `main` with this prompt:

> Do not change any code yet. Verify the cloud environment and report:
> 1. `echo $CLAUDE_CODE_ENVIRONMENT_NAME` (must be `llm-browser`)
> 2. `python3 -m playwright --version` and `ls ~/.cache/ms-playwright`
> 3. `which Xvfb x11vnc websockify`
> 4. `uv --version`, `docker --version`
> 5. `curl -sS -o /dev/null -w "%{http_code}" https://cdn.playwright.dev` and the same for pypi.org
> Summarize as a pass/fail table.

If item 1 is wrong, the environment wasn't applied: start a new session and re-check the
selector. If items 2–3 fail, open the environment, fix the setup script or allowlist, and
start a new session (running sessions never re-run the setup script).

## Step 6 — Run the phases

For each phase in `docs/PLAN.md`:

1. Start a **new** session on `llm-browser`, branch `main` (after merging the previous phase).
2. Prompt:

   > Read CLAUDE.md, docs/ARCHITECTURE.md and docs/PLAN.md. Implement Phase N.
   > Use plan mode: show the plan and wait for my approval before writing code.
   > When acceptance criteria pass, tick them in PLAN.md, push the branch and open a PR
   > titled "Phase N: <name>".

3. Review and approve the plan. Answer questions when it stops for ambiguity.
4. Review the PR on GitHub. Ask for fixes in the same session.
5. Merge, then locally:

```bash
git pull
uv sync
uv run playwright install chromium firefox
uv run pytest -q -m engine_matrix
```

This catches Windows-only differences the Linux VM can't see.

### Phase-specific notes

| Phase | Cloud | Local follow-up |
|---|---|---|
| 0 | Set the Playwright pin; afterwards update the setup script to the same version | — |
| 1 | Spikes against the fixture site; drivers. If CloakBrowser/Camoufox binary download gets 403 or is blocked, stop and decide: temporary **Full** network, or mirror the pinned binaries | Real-site checks in `scripts/manual/` |
| 6 | Docker image, noVNC, handoff flow; test acts as the human | `docker compose up`, do one handoff yourself in the browser |
| 8 | Add the OpenRouter key (Step 4.5). First prompt: verify OpenRouter access with curl, then the OpenAI SDK with a placeholder key; record the working pattern in DECISIONS.md. Pick tool-calling `:free` models into `config/models.yaml`. Run `smoke` in `live` once, then `replay` | `full` eval set with local models; commit the baseline report |

## Step 7 — Moving between cloud and local

- Start a cloud session from your terminal: `claude --cloud "<task>"` (push your branch first;
  the VM clones from GitHub, not from your disk).
- Pull a cloud session into your terminal to finish locally: `--teleport` from the Claude Code
  CLI.
- Sessions stop after idle time; reopen from claude.ai/code. Uncommitted work in an expired
  VM is lost, so ask Claude to commit and push at the end of each work block.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `CLAUDE_CODE_ENVIRONMENT_NAME` empty or `Default` | Session started on the wrong environment | Re-select `llm-browser`, start a new session |
| `403 host_not_allowed` | Host not in the Custom allowlist | Add the host in 4.2, start a new session |
| 403 downloading a GitHub release asset | GitHub proxy only serves repos attached to the session | Full network temporarily, or mirror the binary |
| Every session is slow to start | Setup script > ~5 min, cache not built | Trim the script; move slow optional steps to the SessionStart hook |
| Command stops after 2 min | Default Bash timeout | Env vars in 4.3 |
| 429 from OpenRouter | 20 RPM or daily cap reached | Rate limiter, cassette replay, `smoke` set only |
| 402 from OpenRouter | Key credit limit or negative balance | Adjust key limit |
| Hook changes ignored | Session with several repositories | Use one repo per session |

## Security checklist

- [ ] Repo is private; GitHub app has access to this repo only.
- [ ] No real profiles, cookies, HAR files, internal URLs or bank data committed (`.gitignore` above).
- [ ] OpenRouter key has a credit limit; stored as API credential (Pro/Max) or in a personal environment only.
- [ ] No secrets in `CLAUDE.md`, `.claude/settings.json`, or setup script.
- [ ] Cloud tests hit only the local fixture site; real-site scripts are marked `real_site` / `manual`.
- [ ] Review every PR before merge; never merge with failing CI.
