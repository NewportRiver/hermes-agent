# HERMES-BILLION-030 — Gmail Skill Discovery & Security Inspection

Inspection date: 2026-11-06
Candidate repository: `https://github.com/NewportRiver/googleskills`
Audited revision: `993b979cf055de97dd15d4d5751d2672de561679`

## Decision

The candidate repository is not an approved executable dependency and was not
installed. No setup script, package manager command, MCP server, or external
skill was executed.

The repository contains Google Cloud and identity skills, but no Gmail-specific
skill, no `setup.py`, and no `google_api.py`. Its MCP material is for Google
Developer Knowledge and Google Cloud product guidance, not Gmail mailbox access.

Useful material can be adapted as documentation guidance only:

- Google Cloud authentication/IAM least-privilege guidance.
- Sign-In-with-Google identity architecture and security references.
- Google Cloud developer-knowledge MCP references, only if separately approved
  later for documentation research. It is not a Gmail connector.

## Candidate repository audit

- License: Apache License 2.0 (`LICENSE`).
- Repository shape: Markdown skills, references, scripts, and plugin metadata.
- Dependencies: no repository-level Python package manifest or Gmail client
  dependency was found.
- External calls: several skills document `gcloud`, HTTP APIs, and remote MCP
  endpoints. These are instructions/configuration, not proof of safe execution.
- MCP: discovered Google Developer Knowledge remote MCP metadata at
  `developerknowledge.googleapis.com`; not used.
- Android Termux: the collection assumes heterogeneous cloud tooling and does
  not establish a supported Termux/Gmail execution path. Installing the entire
  collection would add unnecessary surface area and dependencies.

## Existing Hermes Google Workspace implementation

Existing Hermes skill:
`skills/productivity/google-workspace/`

Existing `setup.py` and `google_api.py` were inspected but not executed.
Important findings:

- Existing default scopes include `gmail.readonly`, `gmail.send`,
  `gmail.modify`, Calendar, Drive, Contacts, Sheets, and Docs.
- Existing wrapper supports Gmail send/reply/label modification and many
  non-Gmail write operations.
- Existing setup can install `google-api-python-client`,
  `google-auth-oauthlib`, and `google-auth-httplib2`.
- Existing wrapper can execute an optional external `gws` subprocess.
- Existing token location is `~/.hermes/google_token.json`, which is not the
  requested preserved credential location.
- This is unsuitable as the first Gmail integration under the current
  least-privilege requirement without narrowing and separately auditing it.

## Preserved credentials

`~/.config/hermes/gmail/credentials.json` was not opened for content exposure or
modified. Verified metadata only:

- JSON is valid.
- It contains an `installed` client configuration object.
- File mode is `0600`.
- It is a client configuration, not an authorized-user access token: no token,
  refresh token, or token URI fields were present.

No OAuth flow was started and no consent screen was requested.

## Implemented native connector

Added `tools/gmail_readonly.py` and the `gmail_readonly` toolset.

The connector is intentionally small and stdlib-only:

- Uses the official Gmail API endpoint at
  `https://gmail.googleapis.com/gmail/v1/users/me`.
- Supports only bounded read-only search and message retrieval.
- Uses only Gmail `readonly` semantics at the API operation level.
- Never sends, modifies, labels, deletes, archives, or drafts mail.
- Keeps the existing `credentials.json` as client configuration.
- Expects a separate owner-authorized token at
  `~/.config/hermes/gmail/token.json` (overrideable by
  `HERMES_GMAIL_TOKEN_FILE`).
- OAuth initialization is implemented separately in
  `tools/gmail_oauth_init.py`: installed-app PKCE, random state validation,
  temporary `127.0.0.1` callback, exact-scope validation, and account
  verification for the owner-approved Gmail identity.
- Refreshes expired access tokens through the approved Google OAuth endpoint and persists refreshed metadata with mode `0600`.
- Rejects missing, malformed, revoked, or unexpected-scope tokens without attempting Gmail access.
- Uses HTTPS, a 15-second timeout, and a 512 KiB response limit.
- Rejects non-Gmail API paths.
- Bounds search queries and result counts.
- Writes refreshed token files with mode `0600`.
- Does not print tokens or credential values.

Native registrations:

- `gmail_search_readonly`
- `gmail_get_readonly`

The registry check remains false until both the preserved client file and an
owner-authorized token file exist. Therefore no Gmail network call is currently
available through the tool.

## Official Google guidance used

The implementation follows the official Gmail API model:

- Gmail API guide: `https://developers.google.com/gmail/api/guides`
- Gmail web-server OAuth guide:
  `https://developers.google.com/gmail/api/auth/web-server`
- Google OAuth 2.0 web-server guide:
  `https://developers.google.com/identity/protocols/oauth2/web-server`

Owner authorization remains an explicit external step. The agent must not
invent, request, or broaden scopes. The intended consent should be limited to
Gmail read-only access.

## Termux assessment

Suitable for Android Termux because the connector uses Python standard-library
`urllib`, JSON, filesystem permissions, and Hermes' native registry. It does
not require Node, `gws`, compiled Google client packages, or an MCP runtime.

The remaining platform-specific work is the owner-mediated OAuth authorization
flow. That flow must be performed outside autonomous execution and must write
the authorized token separately from the preserved client configuration.

## Verification

- `python -m pytest tests/tools/test_gmail_readonly.py -q -o addopts=''`
  passed: 2 tests.
- `python -m compileall -q tools/gmail_readonly.py tests/tools/test_gmail_readonly.py`
  passed.
- `git diff --check` passed.
- No live Gmail request was made.
- No OAuth credential value was exposed.

## Stop boundary

Implementation is ready for owner OAuth consent, but no authenticated Gmail
research session can run until the owner completes consent and provides the
separate authorized token. After that, perform a bounded read-only search and
message retrieval acceptance run only. Do not enable the existing broad
Workspace skill or install the candidate collection.
