# Hermes Agent Changelog

## 2026-10-23 — require human approval for agent reboot commands

Metadata:
- repo branch: `update-traceability-20260814`
- implementation commit: `90dce2ef2`
- environment: Android 16 / Termux

Change:
- Reboot and shutdown commands now require an explicit interactive human approval.
- `--yolo`, `/yolo`, approval mode overrides, cached approvals, and cron approval mode cannot bypass this requirement.
- Noninteractive contexts fail closed; destructive hardline commands remain unconditionally blocked.

Verification:
- `python -m py_compile tools/approval.py`
- Direct command checks confirmed `reboot` blocks without a human, `echo reboot` remains allowed, and `rm -rf /` remains hardline-blocked.
- Targeted pytest collection was blocked because `python-dotenv` is not installed in this checkout.

## 2026-08-14 — local maintenance update

Metadata:
- repo branch: `main`
- local commit: `b146ea41f`
- upstream base: `86fb04638`
- Hermes version: `0.19.0`
- Hermes release date: `2026.7.20`
- recorded file mtimes (UTC):
  - `hermes_cli/main.py`: 2026-07-22T11:51:26.436519+00:00
  - `README.md`: 2026-07-22T10:49:31.329443+00:00

Update list:
1. `hermes_cli/main.py`
   - Added `from pathlib import Path`.
   - Replaced the static install-directory print target with `Path(__file__).resolve().parent.parent`.
   - Effect: `hermes --version` / fast version output now reports the resolved checkout path instead of a stale constant.
2. `README.md`
   - Added an append-only maintenance addendum at the bottom to preserve traceability.
   - The addendum is intended to record future update metadata, commit ids, and file-level provenance.

Verification:
- Compared against `86fb04638` with `git diff 86fb04638..b146ea41f -- hermes_cli/main.py README.md`.
- Confirmed the local repo commit contains only the install-directory fix before documentation updates.
