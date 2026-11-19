# Vendored files

Files copied or ported from Tech Startup Tycoon (`Reece77/Tech_Executive_Tycoon`, read-only) under ADR PT-0001. Upstream commit for every row below: **`02fba2aae1be2e43b179d3b6c1794d48e5dcdf56`** (2026-11-17).

- **AS IS**: identical to upstream after the package rename (`tst` → `ptk`, `TST_` → `PTK_`, `.tst.sqlite` → `.ptk.sqlite`, the game's name). `tools/check_vendored.py` checks each against the recorded hash; CI fails on drift. To change one, fix it in TST first (a TST session, TST's process), re-copy, and re-record with `python tools/check_vendored.py --record <tst clone>`; or mark it `ported` with a header saying what changed.
- **ported**: copied, then changed; the file's header names its upstream path, commit and what changed.

| Local | Upstream | Mark | SHA-256 after rename |
| --- | --- | --- | --- |
| `backend/ptk/sim/money.py` | `backend/tst/sim/money.py` | AS IS | 8f8874d2bbe3e504b3b7a438196d3674256067b6c0bb1a8ac918d1e30c70a88e |
| `backend/ptk/sim/dmath.py` | `backend/tst/sim/dmath.py` | AS IS | 393d6385fbfd59e1e2a36f4d1ae7c4e7bec5ba2e9d5542b9f772bff4dad49fa9 |
| `backend/ptk/sim/scale.py` | `backend/tst/sim/scale.py` | AS IS | 523d04548df6c24877bd61032924a22f7fbcb47c22c4cbb0fa57f40ae6342f2c |
| `backend/ptk/sim/decisions.py` | `backend/tst/sim/decisions.py` | AS IS | eae6d01d583ebd6c5f5dd3219bb2d1978ab1b1c9e8322ae1b09ce4bda88d57a3 |
| `backend/ptk/db/session.py` | `backend/tst/db/session.py` | AS IS | 6dfda42e7fb17ceeced01bbf7572dd79ec83a12b7139c5dc20d5cc68ea253139 |
| `backend/ptk/db/backup.py` | `backend/tst/db/backup.py` | AS IS | b7c52b11c994f857c729599e2e88d14272057e8b1671aba65f193c488c2dd7f6 |
| `backend/ptk/db/migrate.py` | `backend/tst/db/migrate.py` | AS IS | 76e1757e66b73c0d94660a1224630e8d16f642985972c6e0dad4f6dc5513cf8b |
| `backend/ptk/llm/base.py` | `backend/tst/llm/base.py` | AS IS | 16fe420641f1238d2502ef40e53325a3fc1cf04d1dd87a58bb5e589766ec93e0 |
| `backend/ptk/llm/anthropic_adapter.py` | `backend/tst/llm/anthropic_adapter.py` | AS IS | f3eaaf654bacbc01bac6942c6dc212f79c5d5f292cd50ea9d450215642a21882 |
| `backend/ptk/llm/offline.py` | `backend/tst/llm/offline.py` | AS IS | aef6f1df81a0fb310637b5b4e9052240f49942264e8c3e094e7810202e126793 |
| `backend/ptk/llm/settings.py` | `backend/tst/llm/settings.py` | AS IS | b47d436e94c9dea7fa0a3cfd3a526fdeaa4df8cb46e8f1c8a43437b69d3cf5ad |
| `backend/ptk/config.py` | `backend/tst/config.py` | AS IS | 9e06cae529e5b7bad224049a81cd59bf91465a086ee6c96a8b9333a8b82b86e4 |
| `backend/migrations/env.py` | `backend/migrations/env.py` | AS IS | a6f666ebb069ace1194d48e791ff46417bb161ff90ab9bc85ff8368dc446a6f7 |
| `backend/migrations/script.py.mako` | `backend/migrations/script.py.mako` | AS IS | 525cbde01738dc04ba12b7430f2344185eea0709537631a6292d91c368a48182 |
| `backend/scripts/export_openapi.py` | `backend/scripts/export_openapi.py` | AS IS | 71b2ff6f5ffb55d55a68536ee9469ecc014ad2eca6532d8933794883daf3ad10 |
| `frontend/scripts/gen-api.mjs` | `frontend/scripts/gen-api.mjs` | AS IS | 201b3f6312a44e0c978035bff4942ef4b1596b99d7d13d81abab2465380d86ae |
| `frontend/eslint.config.js` | `frontend/eslint.config.js` | AS IS | 11d17b914a43bd7c3ac0aa0482a6b1367ff62355942968943fd2fd23f4c45e0f |
| `frontend/tsconfig.json` | `frontend/tsconfig.json` | AS IS | e8d6f7b50828db3953e21c7e92584f9206b3cd2551b4012507372afbb7fe9ce3 |
| `frontend/tsconfig.app.json` | `frontend/tsconfig.app.json` | AS IS | 82a5db4f3335b292a2080cc9b9981e7ddf06cab32089a7096282e3949fe75d28 |
| `frontend/tsconfig.node.json` | `frontend/tsconfig.node.json` | AS IS | bdc4ff59093bf9a08d6117c6bae4823201bbb1e6bbd4ef1fe70acc6b28035db6 |
| `frontend/.prettierrc.json` | `frontend/.prettierrc.json` | AS IS | 85378d4d734cb7d35641c44ffdf322fe0bc76a3b12841927f20aa5f0eba12695 |
| `backend/data/personality.yaml` | `backend/data/personality.yaml` | AS IS | 9086d8dd35efdb93894aa85dbb880d42f120d080a6bcc43980ad00d4e5972ad8 |
| `backend/data/interests.yaml` | `backend/data/interests.yaml` | AS IS | b3be7dd7e48fe844b67f57e27ab8f6556d194c529658d9417ae96b862bd111ff |
| `backend/ptk/sim/rng.py` | `backend/tst/sim/rng.py` | ported | — |
| `backend/ptk/sim/calendar.py` | `backend/tst/sim/calendar.py` | ported | — |
| `backend/ptk/sim/errors.py` | `backend/tst/sim/errors.py` | ported | — |
| `backend/ptk/sim/ledger.py` | `backend/tst/sim/ledger.py` | ported | — |
| `backend/ptk/sim/log.py` | `backend/tst/sim/log.py` | ported | — |
| `backend/ptk/sim/snapshot.py` | `backend/tst/sim/snapshot.py` | ported | — |
| `backend/tests/unit/test_sim_purity.py` | `backend/tests/unit/test_sim_purity.py` | ported | — |
| `backend/tests/unit/test_rng_call_sites.py` | `backend/tests/unit/test_rng_call_sites.py` | ported | — |
| `frontend/src/main.tsx` | `frontend/src/main.tsx` | ported | — |
| `backend/ptk/sim/people/models.py` | `backend/tst/sim/people/models.py` | ported | — |
| `backend/ptk/sim/people/formulas.py` | `backend/tst/sim/people/formulas.py` | ported | — |
| `backend/ptk/sim/people/generator.py` | `backend/tst/sim/people/generator.py` | ported | — |
| `backend/ptk/sim/people/reveal.py` | `backend/tst/sim/people/reveal.py` | ported | — |
| `backend/ptk/sim/people/founder.py` | `backend/tst/sim/people/founder.py` | ported | — |
| `backend/ptk/sim/people/growth.py` | `backend/tst/sim/people/growth.py` | ported | — |
| `frontend/src/lib/attr.ts` | `frontend/src/lib/attr.ts` | ported | — |
| `frontend/src/components/AttributeRange.tsx` | `frontend/src/components/AttributeRange.tsx` | ported | — |
| `backend/data/tags.yaml` | `backend/data/tags.yaml` | ported | — |
| `backend/data/names.yaml` | `backend/data/names.yaml` | ported | — |
| `backend/data/backgrounds.yaml` | `backend/data/backgrounds.yaml` | ported | — |
| `backend/ptk/sim/hiring/models.py` | `backend/tst/sim/hiring/models.py` | ported | — |
| `backend/ptk/sim/hiring/formulas.py` | `backend/tst/sim/hiring/formulas.py` | ported | — |
| `backend/ptk/sim/hiring/rules.py` | `backend/tst/sim/hiring/rules.py` | ported | — |
| `backend/ptk/sim/hiring/phases.py` | `backend/tst/sim/hiring/phases.py` | ported | — |
| `backend/ptk/sim/hiring/actions.py` | `backend/tst/sim/actions/hiring.py` | ported | — |
| `backend/ptk/sim/actions/__init__.py` | `backend/tst/sim/actions/__init__.py` | ported | — |
| `backend/ptk/db/inbox.py` | `backend/tst/db/inbox.py` | ported | — |
| `backend/data/inbox_templates.yaml` | `backend/data/inbox_templates.yaml` | ported | — |

Changes in ported files:

- `backend/ptk/sim/rng.py`: Partner Track's STREAM_IDS table.
- `backend/ptk/sim/calendar.py`: turn 0 from the scenario, not a constant.
- `backend/ptk/sim/errors.py`: generic errors only.
- `backend/ptk/sim/ledger.py`: PT chart; practice and office dimensions; client book apart.
- `backend/ptk/sim/log.py`: link kinds; firm_id.
- `backend/ptk/sim/snapshot.py`: PT KPIs.
- `backend/tests/unit/test_sim_purity.py`: package rename.
- `backend/tests/unit/test_rng_call_sites.py`: known names a parameter.
- `frontend/src/main.tsx`: no glossary or busy retry yet.
- `backend/ptk/sim/people/models.py` (PT-M1a): class-year levels; familiarity, school tier, bar, strain, book and portability on a person; every person has a role; employment with a firm.
- `backend/ptk/sim/people/formulas.py` (PT-M1a): growth times `learn(h)`; familiarity and strain formulas; no salary expectation yet.
- `backend/ptk/sim/people/generator.py` (PT-M1a): school tier first; familiarity and portability draws last; one US pool; no cities or salary.
- `backend/ptk/sim/people/reveal.py` (PT-M1a): firm observers; familiarity records (narrow); TST's first six actions.
- `backend/ptk/sim/people/founder.py` (PT-M1a): the founding partner build: home practice role at equity partner, familiarity, book, bar admissions, age 34-52; stream keyed by founder index.
- `backend/ptk/sim/people/growth.py` (PT-M1a): growth times `learn(h)` from a month of work; familiarity growth and decay; growth in the person's own role.
- `frontend/src/lib/attr.ts` (PT-M1a): ranges as `{lo, hi}`; a strain band; no morale band yet.
- `frontend/src/components/AttributeRange.tsx` (PT-M1a): ranges as `{lo, hi}`.
- `backend/data/tags.yaml` (PT-M1a): PT's seven new tags appended; the `negative` flag (ADR PT-0013).
- `backend/data/names.yaml` (PT-M1a): one `us` pool (TST's north_america list); rival names dropped.
- `backend/data/backgrounds.yaml` (PT-M1a): PT's five founding-partner backgrounds; TST's presets as is.
- `backend/ptk/sim/hiring/models.py` (PT-M1b): firms; campus, recruiter, job post and referral channels; tier filters and a target level on a search; the ask on the candidate; campus offers signed a year ahead; per-person energy and morale; the firm's pay policy; no equity, NextIds, rival, exec or city searches.
- `backend/ptk/sim/hiring/formulas.py` (PT-M1b): no equity or stage terms, a prestige term instead; fit counts interests the practice favours; recruiter fee 20% or 25%; no runway term; PT's hours, interesting-work, prospects and bonus-fairness morale terms; resignation with lifer, burnout, bonus timing and lateral heat; no retirement.
- `backend/ptk/sim/hiring/rules.py` (PT-M1b): no option pool or mission; the campus calendar; the hint from revealed ranges with prestige.
- `backend/ptk/sim/hiring/phases.py` (PT-M1b): campus pools, summer months and a September start; payroll to PT's accounts with December bonuses; the scale raises associates in phase 9; PT's morale terms and bonus timing; no rivals, options, offices, divisions, free agents, relocation or retirement.
- `backend/ptk/sim/hiring/actions.py` (PT-M1b): PT's channels and campus months; scouting and the pay policy as actions; no firing, equity, poach, exec, interest or city searches.
- `backend/ptk/sim/actions/__init__.py` (PT-M1b): hiring actions only; decision_log payloads.
- `backend/ptk/db/inbox.py` (PT-M1b): firms; no archive, bookmarks, digest or event links.
- `backend/data/inbox_templates.yaml` (PT-M1b): PT's hiring templates only.
- `backend/ptk/sim/people/generator.py` (PT-M1b): a fixed school tier for tier-filtered searches and campus visits (drawn first all the same); `weighted_pick` public.
- `backend/ptk/sim/people/models.py` (PT-M1b): an employment's salary.
