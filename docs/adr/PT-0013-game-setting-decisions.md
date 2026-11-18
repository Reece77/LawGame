# ADR PT-0013: Game-setting decisions

- Status: **Accepted** (Reece, 2026-11-17)
- Supersedes for Partner Track: TST ADR-0011
- Records: Reece's answers to `docs/questions.md`

## Decision

1. **Defaults accepted.** Every proposed default in `docs/questions.md` (questions 1–22) is accepted as written, including ADR PT-0001's selective transplant now with `sim-core` extracted from both games later, a January 2005 start, the US (New York) for v1, rivals at real scale, the founder billing early, a lost MP election not ending a standard game, modified lockstep, the $250,000 named-matter threshold, trial weeks and AI eras in v2, external capital in v3, and the 2025 US policy events left out.
2. **Amended by Reece: real lawyers and real judges.** Question 6's "generated people throughout" changes: **real lawyers and real judges appear by name** (personal use only), under the rules below. Client-side people (GCs) stay generated.

### Real people: rules

| Rule | Detail |
| --- | --- |
| **Who** | **Notable lawyers:** about 300 at the 2005 start: each major rival's chair or managing partner and its best-known partners (directory band-1 names, celebrated trial lawyers, practice founders), 5–10 per rival. **Judges:** about 150 trial judges in the courts the game models (spec §7.6a). Everyone else is generated. |
| **Sources** | Each real person's entry in `notables.yaml` or `judges.yaml` carries a source (firm biography, directory listing, court website, published docket statistics) and a tag S (sourced), D (derived) or A (assumed), as TST's v5 dossiers do. |
| **Attributes** | Skills are derived from public standing (directory bands, honours, notable matters) into a range, with seeded noise inside it. Personality and hidden traits are drawn from the neutral distribution, never inferred about the real person. |
| **What is never attached to a real person** | negative tags (rule-bender, cowboy, toxic high performer, credit taker), misconduct, disciplinary cases, malpractice blamed on them, scandals, harassment or workplace-conduct events, burnout collapses, health events, affairs, divorces or deaths. Those systems only ever choose generated people. A real person's career ends by **retirement** (by their real date to 2025 where known, then by age). |
| **Judges' traits** | **Procedural only:** docket speed, appetite for trial, discovery strictness, settlement pressure, summary-judgment appetite, sanctions strictness, and AI standing orders where a judge published one. For real judges these come from published statistics and orders, never from political or ideological labels; no real judge is modelled as favouring a party, a side or an outcome. |
| **Appellate courts and supreme courts** | Modelled as institutions (reversal rates, timing), not as individual named judges. |
| **History** | Real people's firm moves, appointments and retirements follow history to December 2025 where the dossier has them; afterwards the engine moves them freely, and new judges are generated. |
| **LLM text** | Prompts about a real person carry the rule "business and procedural matters only; no misconduct, private life or real-world controversies"; the validator rejects drafts whose effects target a real person outside the allowed effect types. Their in-game statements are written as in-game fiction in their professional role. |
| **Setting** | `world.real_people` (default **on**); off swaps every real lawyer and judge for a generated name and biography, keeping the same attributes and draws, so play is identical apart from names. |

## Consequences

- PT-M3a builds courts and judges with generated judges; PT-M5 adds the real-people dossier (notable lawyers and judges) beside the rivals' dossier.
- A test asserts that no restricted event, tag or effect ever selects a person flagged `real`.
