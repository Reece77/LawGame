# ADR PT-0001: Share code by a selective transplant now, and extract `sim-core` from two working games later

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Related: TST ADR-0001, 0002, 0020; `docs/reuse-map.md`

## Context

Reece's question: fork Tech Startup Tycoon (TST), or first extract a shared core library ("sim-core": engine, RNG, ledger, people, org and automation, events and LLM, regulators, UI shell) that both games depend on. His current preference is to extract the core after TST's v5 closes.

Facts from reading TST at `main` (2026-11-17):

1. **Size and pace.** About 169,000 backend lines and 45,000 front-end lines. v5 is mid-flight: M36–M41 merged in the last four days; M40, M42, M43a, M44, M45 and M43 remain, with up to seven lanes running at once. `GameState`, `turn.py`, `balance.yaml` and the migrations change in nearly every milestone.
2. **Coupling.** The kernel is clean, but the rich general systems import industry code: `org` imports `products` (9 sites) and `markets_public` (6); `automation` imports `products`, `mining`, `fabs`, `exploration`; `GameState` has about 150 fields, ~110 of them industry-specific; `turn.py` calls every industry's phase directly. An extraction is therefore not a move of folders but a redesign: a state made of registered parts, a phase registry, an area registry for automation, KPI providers, and per-domain effect types for events.
3. **TST's guard rails are strict.** Golden snapshots, M30's state-hash cache, and history fingerprints must stay unchanged unless deliberately re-recorded. An extraction refactor in TST would touch every one of them while other lanes are merging.
4. **What a law firm needs from the core is narrower than it looks.** People, hiring, org, seats, authority, automation, events, founder and family are needed; but each needs its *product* dependency replaced by *matters*. Nobody can yet say which interfaces a second game really needs, because the second game does not exist.

## Options

| | A. Fork the repository | B. Extract `sim-core` first (Reece's preference: after TST v5) | C. Selective transplant now, extract later (**recommended**) |
| --- | --- | --- | --- |
| What happens | Copy all of TST into a new repo, delete what a law firm doesn't need | Refactor TST into a core library plus a TST game package; Partner Track starts on the library | Start a new repo with a **copied kernel** (as-is modules) and **ported modules** (changed modules re-written from TST's code); record provenance; extract a shared library only once both games run |
| Speed to a playable Partner Track | Fast to start, slow to clean: ~110 industry fields, 30 industry packages, ~1,000 tests and 40 screens to remove, each removal breaking imports | Slowest: waits for v5 (several more milestones), then a multi-week refactor, then Partner Track starts | Fast: v1's kernel exists on day one; ported modules arrive milestone by milestone |
| Risk to TST | None | **High**: the largest refactor in TST's history, touching every guard, while v5/v6 lanes run | None now; at extraction time, lower, because the interfaces are proven by two consumers |
| Maintenance | Two diverging copies of everything, including dead code | One core, two games: best long-run | Two copies of the kernel for a while (small, stable: rng, money, ledger, people, llm, shell); a scheduled merge into one library |
| Design quality of the core | Inherits TST's coupling | Interfaces designed for one game and guessed for the second | Interfaces designed from two real games ("rule of two") |

## Decision (proposed)

**Option C.** I disagree with waiting for v5 to close before starting, and agree that extraction should happen, but later and differently: extracted **from both games**, not carved out of TST alone.

1. **Now (Partner Track M0):** create `partner-track` with package `ptk`. Copy the modules marked AS IS in `docs/reuse-map.md` into `ptk/kernel/` (rng, money, ledger, dmath, scale, log, decisions, calendar), `ptk/llm/`, `ptk/db/` (session, migrate, backup, saves, history framework), and the front-end shell and table components. Copy the guard tests (purity, turn order, stream uniqueness, ledger and clamp properties, hidden-value API, golden and state-cache frameworks).
2. **Provenance.** `VENDORED.md` lists every copied or ported file with its TST path and the TST commit SHA it came from. Ported files carry a one-line header: `# Ported from tst/sim/org/formulas.py @ <sha>; changed: units are practice groups`. A CI script (`tools/check_vendored.py`) diffs AS IS files against the recorded upstream SHA and fails if a copied kernel file drifted without a note.
3. **Keep the kernel boundary clean from day one.** `ptk/kernel/` never imports anything outside itself; domain packages never reach into each other except through named interfaces (`ptk/sim/interfaces.py`: `WorkSource` for whatever consumes people's time, `KpiProvider`, `AreaRule`, `EffectType`). These are the seams a future `sim-core` will need; Partner Track designs them consciously, TST already has them implicitly.
4. **One-way bug flow until extraction.** A bug found in a copied kernel module is fixed in TST first (by a TST session, through TST's own process) and then re-copied, so the copies never fork in behaviour. A Partner Track session never edits TST (Reece's rule: read-only).
5. **Extraction checkpoint** (a later decision, not now): when **TST v5 has closed and Partner Track v1 has closed**, write `sim-core` from the intersection of the two codebases: kernel, people, hiring, org/seats/authority, automation framework, events framework, founder and family, persistence, LLM, UI shell. Both games then depend on it by version. Expected size: 25,000–35,000 lines. Its own ADRs and tests come from both games' guard suites.

## Consequences

- Partner Track can start immediately and does not slow TST.
- For a period (likely three to six months), two copies of about 10,000 lines exist. They are the most stable lines in TST (the kernel has barely changed since M1), so drift is small and the vendoring check catches it.
- Partner Track pays a porting cost for changed modules (org, automation, events, founder, family) of roughly one milestone each, which is the same work an extraction would require, done once, with a real second consumer.
- If Reece later prefers a fork for speed, the reuse map still applies: the same AS IS and CHANGED lists decide what survives the pruning.

## Alternatives considered

- **A Git submodule or subtree of TST now:** brings TST's coupling along, and any TST change would move Partner Track's golden snapshots.
- **Publishing TST's kernel as a package now from TST:** a change to TST's repository, which Reece has asked not to make; and premature for the same reasons as option B.
