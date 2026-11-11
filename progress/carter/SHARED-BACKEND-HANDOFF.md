# Current Vercel deployment — 2026-11-10

The user selected the Vercel plugin instead of Railway and authorized the team
connection. This is the current deployment route; the earlier preparation notes
below are historical. Normative sources: design/02 §2, §4.5, §5.9 and §6.

Current session's exact handoff:

- `api/workbench.mjs`
- `index.html`
- `vercel.json`
- `recoup/ui/start_server.py`
- `tests/ui/test_start_server.py`
- `tests/ui/test_vercel_launcher.mjs`
- `progress/carter/SHARED-BACKEND-HANDOFF.md`
- `progress/carter/PROGRESS.md`

## Resources and entry point

Open https://recoup-sonny1106-4950.vercel.app/ . Use the same shared access secret
at the launcher and in Recoup. The launcher starts/resumes the backend before
redirecting to it. Bookmark the launcher, rather than relying on the backend URL
to wake a stopped session. No Vercel or Claude account is required for a visitor.

- Team: `team_Y790EQALOyI5JtZH4BDYsf9F` (`sonny1106-4950`).
- Project: `prj_2Y7NW3Bvl1PPN6DRi0uaxcDcEaN1` (`recoup`).
- Named Sandbox: `recoup-workbench`, region `iad1`, one vCPU / 2 GiB RAM.
- Drive: `recoup-data` (`drive_6ynZRsFkER9D103ehTgxB9ahUDvv`), 1 GiB at `/data`.
- SQLite: `/data/recoup.db`; recordings: `/data/app/runs/recordings`.
- Backend source: `/data/app`; Python 3.11 runtime: `/data/python`; existing
  package dependencies installed into `/data/venv`.

Vercel Sandbox/Drive are beta features. The session timeout is 45 minutes, so an
open browser session can disconnect when that limit is reached. Return to the
launcher and enter the access secret to resume; sign in to Recoup again. The
Drive retains the database and recordings. The Sandbox retains only its latest
environment snapshot with no expiration (`snapshotExpiration=0`). Processes
restart on resume. Do not change the session into a stateless Vercel container:
that would discard SQLite/recordings and the shared process lock.

## Server configuration and security

Vercel production has sensitive `OPENAI_API_KEY` and `RECOUP_ACCESS_SECRET`
variables. The existing Anthropic key was transferred in memory from the macOS
launch environment. It was not printed or written into source files. A distinct
random shared access secret was generated, saved as a Vercel sensitive variable,
and delivered locally at `~/.config/recoup/vercel-access-secret` with mode 0600.
Only the shared access secret should be given to the partner, privately.

The launcher authenticates before any Sandbox API call. It uses Vercel's trusted
request-context OIDC token, not a browser-supplied token, to resume the existing
Sandbox. Startup is serialized with a filesystem lock and runs one Streamlit
process. Its environment is passed server-to-server:

```text
RECOUP_LLM=live
RECOUP_MODEL=claude-haiku-5-5
OPENAI_BASE_URL=https://api.anthropic.com/v1/
RECOUP_DB=/data/recoup.db
RECOUP_VISION=0
PYTHONPATH=/data/app
```

The provider/access secrets are injected from Vercel's production environment,
never from frontend inputs. Only a validated public Sandbox URL is returned to
the browser. Provider/control API bodies are neither rendered nor logged. The
launcher emits only fixed diagnostic stages/status codes; backend process output
is discarded, and the existing SDK diagnostic suppression remains in effect.
The private source setting is retained. The new project's Vercel SSO gate was
replaced with the application's shared-secret gates so the partner can sign in
without a Vercel membership. Authenticated sessions share one workspace.

The static deployment contains only `index.html`, `api/workbench.mjs` and
`vercel.json`. No Python backend, recordings, local databases or secret files are
uploaded as public static files. The source scan found no actual Claude key in
tracked files or new implementation files.

## Reproducible backend provisioning

Through the Vercel plugin, create/reuse the named Drive and Sandbox in this
project. Mount `recoup-data` read-write at `/data` with port 8501 exposed. Upload
only `pyproject.toml`, `README.md`, package `.py` files,
`recoup/engine/prompts/system_v1.md`, and bundled case/policy `.json` files to
`/data/app`. The prompt is runtime data and must be included explicitly; the
existing wheel does not package it. `PYTHONPATH=/data/app` ensures the existing
engine reads this unmodified source prompt. Do not modify protected packaging
metadata to work around it.

Provision the existing runtime/dependencies using the Sandbox's bundled `uv`:

```sh
UV_PYTHON_INSTALL_DIR=/data/python uv venv --python 3.11 /data/venv
uv pip install --python /data/venv/bin/python /data/app
```

Deploy the three launcher files to the existing project. The launcher invokes
`/data/venv/bin/python -m recoup.ui.start_server` with the secret environment.
Do not print environment-variable values or pass credentials in command args.
Existing Docker/Railway files are unused by this Vercel deployment.

## Verification

`make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint/format PASS;
**1145 passed, 2 optional OCR skips** in 206.73s (final check). Separate built-in Node tests:
`node --test tests/ui/test_vercel_launcher.mjs`: **5 passed**. No automated test
calls a provider or the network. New checks cover unauthorized startup, origin
validation, trusted runtime token selection, secret-safe responses, bounded
startup and process reuse. Existing app-built tests retain contract/gate checks.

Production deployment `dpl_3JJcHMemRNsS1Pe72qcLk3KY15Sb` is READY. Manual
verification: HTTPS login page returns 200, wrong-secret POST returns 401,
authenticated launch returns 303, and Chrome follows the launcher to Streamlit,
signs in, and runs the SYNTHETIC H/C/N demo using real Claude. The browser run
finished with decisions for all three cases and four proposals (H=2, C=1, N=1),
zero receipts, zero pending events, and **101 saved live responses**, all labeled
`claude-haiku-5-5`. No approval or MOCK submit was performed during the live run.

Important acceptance limit: H/N ended `needs_human` because the existing recorder
rejected conflicting responses for an already-recorded request; C ended
`needs_human` on the existing loop guard. Drafts/decisions were saved, but a clean
model-case acceptance or complete live replay is not claimed. Those engine and
recording behaviors were deliberately preserved, not bypassed or modified.
Loading the full demo processes each existing evidence event and took several
minutes; use the selected-case Run agent control for a scoped re-investigation.

After the run completed, the backend was stopped and resumed **through the
deployed launcher**, creating a new session. The SHA-256 of serialized case views
matched before/after (`cf44d904eafebd1ca7c1484254ce3e6e7b9c98bffa9b7c572456eb1d6a007513`),
as did the aggregate recording hash
(`90b3486503199daeb720a51f4062c21f37cb5906e5e4255e317e3c61bd1f0d3c`).
All 101 recordings and H/C/N case states survived with zero pending events.
Chrome signed in again after that restart and displayed the persisted case queue
with LLM live provenance. The verified workspace tab is left open for the user.
The actual Claude key was absent from serialized case responses, the database
bytes and every recording. Non-secret verification evidence is stored privately
on the Drive at `/data/deployment-verification.json`. Inspection used app-built
in-memory snapshots without running FakeLLM or mutating production case state.

The production browser check caught and corrected same-origin form handling:
Referrer-Policy is `same-origin` (so the launcher can validate Origin), and the
form-action CSP permits only self and Vercel Sandbox HTTPS redirects. Production
file watching is disabled to prevent recordings from generating rerun prompts.

Implementation references inspected without adding dependencies:
`@vercel/sandbox` 3.9.1 REST client and `@vercel/oidc` 4.0.8 trusted-context token
resolution; https://vercel.com/docs/sandbox/concepts/persistent-sandboxes ,
https://vercel.com/docs/sandbox/concepts/drives and
https://vercel.com/docs/rest-api/sandboxes/get-a-named-sandbox .

# Historical shared-backend step — 2026-11-10

Current task handoff (user-authorized one-step UI/backend wiring):

- `recoup/ui/__init__.py`
- `recoup/ui/workbench.py`
- `tests/ui/test_workbench.py`
- `progress/carter/SHARED-BACKEND-HANDOFF.md`
- `progress/carter/PROGRESS.md`

Inspection: this checkout had no frontend, HTTP entry point, hosting manifest,
or deployment integration. `recoup.app.build()` already composes the live
adapter through `recoup.engine.factory.get_llm()`. The SDK reads
`OPENAI_API_KEY` on the server. Existing uncommitted engine changes are preserved.
Normative sources: design/02 §2, §4.5, §5.9 and §6.

This step supplies a Streamlit frontend and backend in one Python process.
Authentication precedes app construction, reads, mutations and provider calls.
The shared access secret is separate from the Claude key; sessions expire after
eight hours or access-secret rotation. Failed login attempts have a process-wide
two-second cooldown. Login state is held in server memory; reconnection requires
sign-in. No provider-key input, browser key storage, config export or provider exception
display is supplied. SDK/HTTP diagnostic logging is suppressed by the entry point.
All sessions share the same SQLite database, with operations serialized by a
process lock. Connections open and close on the current Streamlit thread.

## Railway deployment step — 2026-11-10

Current deployment task handoff, authorized by the user's request to complete
hosting, configuration, secrets and live verification:

- `Dockerfile`
- `.dockerignore`
- `progress/carter/SHARED-BACKEND-HANDOFF.md`
- `progress/carter/PROGRESS.md`

Railway is selected because its CLI is already installed locally. The stored
OAuth login is expired (`invalid_grant`); no connected Railway integration is
available. The Railway integration was offered for connection. An Anthropic key
was subsequently found in macOS's launch environment and used entirely in memory
for a successful manual connectivity request through `app.build()` and the
existing live adapter, with model `claude-haiku-5-5` and the requested base URL.
One live response was recorded outside the repository; the key was absent from
that recording. No credential values or provider response bodies were printed.
This verifies local adapter connectivity, not remote deployment or a full case run.
Docker Desktop was started to attempt
a local build, but stopped during dependency installation; BuildKit reported
`error reading from server: EOF`. A subsequent status check confirmed Docker
Desktop was no longer running. No runnable container image was verified.
No hosting project, service, volume, domain or secret has been created yet.

The root Dockerfile uses Python 3.11 and installs only existing package
dependencies. It starts one Streamlit process on the assigned `PORT` and keeps
the database at `/data/recoup.db` and recordings at `/data/runs/recordings`.
Synthetic fixture paths resolve through `/data/cases` to the image's `/app/cases`.
The build context allowlist includes only package Python files, synthetic JSON,
the existing package metadata/README, and Dockerfile. No credential build args,
source credentials, databases, recordings or Git history are included.

Once Railway is connected:

1. Create one `recoup` persistent service using this Dockerfile and one replica.
2. Attach a private persistent volume at `/data`; use the image's default start
   command, healthcheck path `/_stcore/health`, and a Railway HTTPS domain.
3. Set service variables `RECOUP_LLM=live`,
   `RECOUP_MODEL=claude-haiku-5-5`,
   `OPENAI_BASE_URL=https://api.anthropic.com/v1/`, and
   `RECOUP_DB=/data/recoup.db`.
4. Generate a random shared access secret and set `RECOUP_ACCESS_SECRET` through
   the platform secret mechanism without printing it. Transfer the existing
   Claude key directly from the macOS launch environment to Railway's server-side
   `OPENAI_API_KEY` variable, using memory/stdin rather than command arguments or
   tracked files. Seal both secret variables in Railway. If a replacement key is
   needed, the owner should enter it directly in the Variables panel. Never paste
   the key into chat.
5. Upload an allowlisted source snapshot (Dockerfile, `.dockerignore`,
   `pyproject.toml`, `README.md`, package Python files and synthetic case JSON),
   rather than the entire working checkout. Deploy and inspect bounded build
   diagnostics. Do not export or log the service's environment variables.
6. Verify the remote authentication, live request, browser/log secret absence,
   recording/database restart persistence and approval-bound MOCK behavior using
   the acceptance steps below. Deploying alone is not live-provider verification.

Railway documentation checked 2026-11-10:
https://docs.railway.com/builds/dockerfiles ,
https://docs.railway.com/volumes , https://docs.railway.com/variables .
Use direct service settings; legacy config-as-code files are deprecated:
https://docs.railway.com/config-as-code/reference .

Deployment preparation checks: Docker CMD passes shell syntax validation and
contains no credential build arguments. A 69-file allowlisted source snapshot
was staged outside Git for deployment. The build copied package/fixture source
and built the package wheel before its connection was lost during dependency
installation. `make check PYTHON=/tmp/recoup-007-check/bin/python` passed again:
Ruff lint/format PASS, 1142 passed and 2 optional OCR skips in 203.93s. Image
startup, remote deployment, server secrets, remote authentication and a remote
Claude case run remain unverified. The single manual live connectivity request
was separate from the offline automated tests.

## General hosting requirements

Choose a host supporting Python 3.11, a long-running Streamlit process,
WebSockets, HTTPS, server-side environment secrets and a persistent private disk.
Use exactly one process/replica for this single shared workspace. No deployment
was performed, and no remote authentication or provider success was verified.
The Railway deployment preparation above uses its service Variables mechanism;
general host-independent instructions follow.

Install the existing package dependencies with `python -m pip install .`.
Run from the repository root (so the bundled demo paths resolve):

```sh
python -m streamlit run recoup/ui/workbench.py --server.address=0.0.0.0 --server.port="$PORT" --server.headless=true --server.enableXsrfProtection=true --server.enableCORS=true --client.showErrorDetails=none --browser.gatherUsageStats=false
```

Set `PORT` using the host's assigned port (8501 for a local run). Keep the
Streamlit origin/XSRF protections enabled; configure the public address to match
the host if its proxy needs that. Terminate TLS at the hosting ingress.

Configure these non-secret environment settings:

```text
RECOUP_LLM=live
RECOUP_MODEL=claude-haiku-5-5
OPENAI_BASE_URL=https://api.anthropic.com/v1/
RECOUP_DB=/persistent/recoup/recoup.db
```

Use the chosen hosting platform's **server-side secret manager** to supply
`OPENAI_API_KEY` (a workspace-scoped Claude API key) and `RECOUP_ACCESS_SECRET`
(a distinct cryptographically random secret of at least 32 characters).
Do not put either value in Git, command-line arguments, frontend configuration,
local tracked secret files or build arguments. Share only the access secret with
the partner through a private channel. Rotating it invalidates existing sessions.
The app does not require the partner to have a Claude key or Claude subscription.

Mount a persistent private disk at the database path's parent; also persist
`runs/recordings` relative to the working directory. Keep recordings private.
The existing adapter's recording/replay path is unchanged. Fake remains the
default when `RECOUP_LLM` is unset; replay uses the existing model and recordings.

Compatibility documentation checked on 2026-11-10:
https://platform.claude.com/docs/en/cli-sdks-libraries/libraries/openai-sdk
and https://platform.claude.com/docs/en/models/overview . No provider requests
were made. Provider availability and key permissions require remote verification.

Before partner use, verify over HTTPS that signed-out/incorrect-secret sessions
cannot load cases or call the provider, then sign in and run a SYNTHETIC case.
Confirm LLM live provenance, a successful Claude request, recording persistence,
and a matching approval before any MOCK receipt. Check browser traffic and host
logs for absence of the API key without printing its value. Verify restart
persistence and access-secret rotation. No multi-user isolation is implemented.

## Offline verification

`make check PYTHON=/tmp/recoup-007-check/bin/python`: Ruff lint and format pass;
**1142 passed, 2 skipped** (existing optional OCR skips). Eight Streamlit AppTest
checks cover fail-closed configuration, unauthenticated access, throttling,
rotation/expiry/logout, fake agent execution, explicit approval and MOCK receipt,
mocked Claude HTTP routing, recording/replay and sensitive startup failures.
All UI tests block socket connections and build an actual in-memory SQLite app.
The final transport-logger suppression adjustment is also checked by rerunning
the UI suite. No credentials were read from the hosting platform or committed.
