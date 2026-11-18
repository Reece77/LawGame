# Questions for Reece

**Answered (Reece, 2026-11-17):** all defaults accepted, with one change to question 6: **real lawyers and real judges by name** (personal use). Recorded in ADR PT-0013 with the rules for real people.

## Sharing code and process

1. **Code sharing.** Selective transplant now, extract `sim-core` from both games after TST v5 and Partner Track v1 close (ADR PT-0001), rather than waiting for TST v5 to close before Partner Track starts. **Default: yes.**
2. **Repository.** A new private repository `Reece77/partner-track`, package `ptk`, milestone tags `pt-mX-done`, same CI and merge rules as TST. **Default: yes; you create it and grant access.**
3. **Bug flow.** A kernel bug found by a Partner Track session is reported to you for a TST session to fix, then re-copied; Partner Track never edits TST. **Default: yes.**

## Setting

4. **Start year.** January 2005, ending December 2034; a 2010 scenario pack in v3. **Default: 2005.**
5. **Home market for v1.** The US (New York as the default city; Chicago, Washington, Boston, Pittsburgh, the Bay Area as alternatives). London arrives in v2. **Default: US, New York.**
6. **Real names.** Real firms (yes, per your brief); real clients for the top 300 companies of 2005; generated people throughout (no real lawyers or GCs by name). **Default: real firms and clients, generated people.** **Answer: real firms and clients, plus real notable lawyers and real judges under ADR PT-0013's rules; GCs stay generated.**
7. **Scale.** Rivals at real scale in one economy (ADR PT-0008), avoiding TST's `economy_scale` problem. **Default: yes.**

## The player

8. **The founder bills hours** in the early game, with a working or full-time MP choice from stage 3 (spec §2.2). **Default: yes.**
9. **Losing an MP election is not game over** in standard play: stay on as a partner, or hand over and play a successor you choose (ADR PT-0007). Ironman makes it final. **Default: yes.**
10. **Succession** to an elected partner whom you then play (TST §45's "play the heir", adapted); children may join and must make partner on merit. **Default: yes.**

## Design

11. **Default comp system** for a new firm: modified lockstep, changeable by a two-thirds vote. **Default: modified lockstep.**
12. **Named-matter threshold:** $250,000 of expected fees (2005 dollars), key clients, critical risk, or flagged (ADR PT-0004). **Default: as stated.**
13. **Opposing counsel:** on named matters, the other side is a real rival's team where history or the market says so, and their quality affects outcomes. **Default: yes.**
14. **Trial weeks** (weekly sub-turns for jury trials of key matters) in v2, not v1. **Default: v2.**
15. **AI's strength.** By 2030, exposed tasks take 40–70% fewer hours for a fully adopted firm; clients claw back much of it on hourly bills (ADR PT-0011). **Default: as stated.**
16. **External capital** (ABS, outside equity, listing) in v3, only where the jurisdiction allows it. **Default: v3.**
17. **Recent US policy events affecting large firms (2025).** Model them as neutral, dated market events with business consequences only (clients, recruiting, a choice of response), or leave them out. **Default: leave them out of the history pin and keep the 2026+ seeded world free of real political actors.**
18. **Pro bono** as a lever (morale, learning, recruiting, reputation) from v1. **Default: yes.**
19. **Associate salary scale** follows history to 2025 as market events; the player can lead, match or lag. **Default: yes.**
20. **LLM budget.** TST's $10 a month, shared meter or separate. **Default: separate $10 a month for Partner Track.**

## Scope

21. **v1's scope** as in `docs/roadmap.md`: one country, ten practices, 2005–2015 history, no seats or automation (they arrive in v2's first two milestones). **Default: yes.** Alternative: bring automation into v1 at the cost of about two milestones.
22. **Family and dynasty.** Family in v2 (PT-M17) with succession; dynasty mode in v3. **Default: yes.**
