# Changelog

All notable changes are recorded here. Golden snapshot regenerations must be listed with their reason.

## Unreleased

- PT-M0 foundation: repository and tooling; vendored kernel from Tech Startup Tycoon @ `02fba2aa` (VENDORED.md, `tools/check_vendored.py`); calendar from the scenario (January 2005); Partner Track's chart of accounts with the client book apart; `GameState`, the 12-phase turn as no-ops, the founding capital entry; schema v1 (migration `0001_initial`); FastAPI app and CLI; front-end shell with Main menu, New game, Overview, Saves and Settings; guard tests (purity, turn order, stream call sites, ledger properties, crash rollback, 360-turn campaign). **Golden snapshots created** (seeds 1-3, 360 turns).
- Design pack: spec, ADRs PT-0001 to PT-0013, reuse map, roadmap, balance targets, v1 briefs.
