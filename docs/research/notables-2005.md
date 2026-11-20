# Notable lawyers dossier: the 43 rivals' notable lawyers at January 2005

**Status:** first pass, compiled 2026-11-19 for PT-M5 (`notables.yaml`; ADR PT-0013, spec §10.1). Research only: no code or data YAML was changed. Firms and `rival_key`s match `rivals-2005.md`.

**Rules (ADR PT-0013), applied to every row.** Public professional standing only: role in 2005, office, practice, directory standing and honours, notable matters, and professional moves 2005–2015. Nothing about private life, family, health, age, death, politics, misconduct, discipline, malpractice, scandals, workplace conduct or criticism; a departure for a non-professional reason reads only "left the firm (YYYY)". Candidates mainly known for a controversy were not picked. For firms that later dissolved (Heller Ehrman, Howrey, Dewey & LeBoeuf, Bingham), only professional moves are recorded and nothing about causes; Dewey Ballantine and LeBoeuf entries are practising partners, not the 2007–2012 leadership. `standing` (elite | leading | strong) is always [D], derived from the row's evidence, and is what the game maps to an attribute range; no personality or hidden traits are recorded.

**Tags:** **[S]** sourced this session, **[D]** derived, **[A]** assumed (basis stated).

**Known weaknesses.** 212 people across 43 firms. **No Chambers USA 2005 or 2006 band was found for anyone** (archived editions unreachable); later bands appear only with their year. Firms below the 5–7 target: White & Case 3, Cooley 2, Reed Smith 3, LeBoeuf 1, and 4 each at Jones Day, Sidley, Baker & McKenzie, Morgan Lewis, Ropes & Gray, Dewey Ballantine, Hogan & Hartson, Wilson Sonsini and Bingham. Part 2's last eight firms (Milbank to LeBoeuf) rely partly on [A] recall, with 19 rows [A]-only; part 3 has about 15 [A] items. All [A] rows need checking before `notables.yaml`. Each part ends with its gaps list, including leadership dates where sources disagree.


## Review notes (product manager, 2026-11-19)

The rules are applied well: no row carries private-life, health, misconduct or controversy content, and the scan for restricted terms found only role titles (for example "DOJ Fraud Section"). Three gaps must be closed in PT-M5's sub-task 1a before `notables.yaml` is built:

1. **An end year for everyone who stopped practising by 2025.** ADR PT-0013 retires real people "by their real date to 2025 where known, then by age". Rows reading "none recorded" for lawyers who are known to have stopped practising (for example Joseph Flom, and those the gaps list says were left out under the rule) would otherwise practise indefinitely. Record **"left practice (YYYY)"** with no reason, whatever the cause. That keeps the rule (no cause is stated) and gives the engine its date.
2. **A career-start year** (law school graduation or bar admission year, [S] where a firm biography gives it) for every row, so the engine can estimate age for retirement after 2025 without recording age or birth date.
3. **The 19 [A]-only rows and roughly 15 [A] items in part 3** need a source or removal. A real person enters the game only with at least one [S] fact for their 2005 role.

Low-value rows to keep but not weight: Christine Lagarde leaves Baker & McKenzie in June 2005 (month 6), so she matters only for the first half-year.

## Notable real lawyers, part 1: 14 rival firms (Partner Track, start January 2005)

Research session: 2026-11-19. Deliverable for the PT-M5 real-people dossier (`notables.yaml`), under ADR PT-0013.

### Rules applied (ADR PT-0013)

- **Public professional standing only:** name, 2005 role, office, practice, directory standing, honours, notable matters (with years), and professional moves 2005–2015 (laterals, government appointments, leadership roles, retirement from partnership). Law school and graduation year are included where a source gave them.
- **Excluded on purpose:** private life, family, health, age or birth date, death, politics, donations, misconduct, discipline, sanctions, lawsuits against the person, scandals, workplace-conduct matters and criticism. Where a source covered any of these, I left it out. Where someone left for a reason that was not purely professional, the entry says only "left the firm (YYYY)". I did not pick anyone mainly known for a controversy.
- **People at the firm in 2005:** every person was at the firm in 2005, as shown by a source [S], inferred from dated tenure [D], or assumed with the basis stated [A]. I left out candidates who were not at the firm in 2005, without comment.
- **Directory bands:** I found no Chambers USA 2005/2006 band for anyone, because the archived editions were not reachable. Where a source gave a later band, it is shown with that year (or as "current", meaning the live directory page in 2026) and tagged. Otherwise the entry reads "band: not found".
- **Standing** (`elite | leading | strong`) is my derived [D] judgement from honours, matters and leadership. The game maps it to an attribute range. It records no personality or hidden traits.

**Tag legend:** **[S]** sourced this session (URL in the footnotes) · **[D]** derived from sourced facts (for example a year inferred from a stated tenure) · **[A]** assumed (basis stated).

**Count:** 68 people across 14 firms. The brief asked for 5–7 per firm; four firms fall short (White & Case 3, Baker & McKenzie 4, Jones Day 4, Sidley 4, Morgan Lewis 4). See *Gaps*.

---

### Skadden Arps (`skadden`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Robert C. Sheehan | `skadden__robert_sheehan` | Executive Partner (firm CEO, since 1994; third 5-yr term from May 2004) | New York [A: firm HQ] | Firm management | leading [D] | band: not found; Legal Aid Society Servant of Justice Award 2005 [S] | Led firm through its 1994–2009 growth [S] | Stepped down as Executive Partner Apr 2009 (succeeded by Eric Friedman) [S] | 1,2,3 |
| Joseph H. Flom | `skadden__joseph_flom` | Senior / name partner (partner since 1954) | New York | M&A, takeover defence | elite [D] | band: not found; Am Law "Lawyers of the Century" 1999 [S] | Revlon (Perelman) 1985; ABC/Capital Cities 1985; InBev–Anheuser-Busch 2008 [S] | none recorded [S] | 4,5 |
| Peter Allan Atkins | `skadden__peter_atkins` | Partner (summer associate 1967; HLS 1968) | New York | M&A, corporate governance | elite [D] | Chambers ranked (band and year not found) [S]; Best Lawyers since 1983 [S]; NYLJ Lifetime Achievement 2023 [S] | Contested and negotiated takeovers, LBOs, spin-offs for acquirors, targets and banks [S] | Remained partner; of counsel from 31 Dec 2021 [S] | 6,7 |
| Eric J. Friedman | `skadden__eric_friedman` | M&A partner | New York | M&A | leading [D] | band: not found; NLJ "Most Influential" law-firm leader 2011 [S] | Skadden No. 1 global M&A by value 2009 (firm-level) [S] | Executive Partner from Apr 2009 [S] | 2,8,9 |
| Sheila L. Birnbaum | `skadden__sheila_birnbaum` | Partner; founder of product liability practice, co-head of mass torts and insurance litigation | New York [S] | Product liability, mass torts | elite [D] | band: not found; known as the "queen of torts" (press) [S] | 33 years at Skadden building its mass-torts group [S] | Special Master, September 11th Victim Compensation Fund 2011 [S]; to Quinn Emanuel Apr 2013 [S] | 10,11 |
| Jay B. Kasner | `skadden__jay_kasner` | Securities litigation partner [A: long-tenured Skadden practice leader] | New York | Securities litigation | leading [D] | Chambers NY Securities Litigation Band 1 + Star Individual (current, "22 years ranked", so ranked from c. 2005) [S/D] | Heads global securities litigation practice [S] | none recorded | 12,13 |

1. Law.com Legal Week, "Skadden Arps chief gets third term", 23 Jun 2004: https://www.law.com/legal-week/sites/legalweek/2004/06/23/skadden-arps-chief-gets-third-term/
2. Skadden press release, "Eric Friedman becomes Executive Partner; Bob Sheehan…", Apr 2009: https://skadden.com/about/news-and-rankings/news/2009/04/eric-friedman-becomes-executive-partner-bob-sheeha
3. Penn Law news (2005 Servant of Justice Award): https://www.law.upenn.edu/live/news/1801-skadden-arps-gift-to-support-penn-law-human-rights
4. Wikipedia, "Joseph Flom": https://www.wikipedia.org/wiki/Joe_Flom
5. Harvard Law Today, "Joseph H. Flom '48": https://hls.harvard.edu/today/joseph-h-flom-48-1923-2011
6. Skadden bio, Peter A. Atkins: https://www.skadden.com/en/Professionals/A/Atkins-Peter-A ; Chambers profile: https://chambers.com/lawyer/peter-allan-atkins-usa-5:33039
7. Skadden news, "Longest-Tenured Partner, Peter Atkins…", Jan 2022: https://www.skadden.com/about/news-and-rankings/news/2022/01/longest-tenured-partner-peter-atkins-shares-thoughts
8. LEADERS magazine, Eric Friedman, Oct 2011: https://leadersmag.com/issues/2011.4_Oct/New%20York%20City/LEADERS-Eric-Friedman-Skadden-Arps-Slate-Meagher-and-Flom.html
9. Biglaw.org, "Skadden is top global M&A adviser in 2009": https://biglaw.org/news/2741/
10. ABA Journal, "Skadden's longtime mass torts leader jumps to Quinn Emanuel", Apr 2013: https://www.abajournal.com/news/article/skaddens_long-time_mass_torts_leader_jumps_to_quinn_emanuel
11. Dechert bio, Sheila L. Birnbaum (9/11 VCF Special Master 2011): https://www.dechert.com/people/b/sheila-l--birnbaum.html
12. Chambers USA, NY Securities Litigation ranking table: https://chambers.com/legal-rankings/litigation-securities-new-york-5:413:12806:1
13. Skadden bio, Jay B. Kasner: https://www.skadden.com/professionals/k/kasner-jay-b

### Baker & McKenzie (`baker_mckenzie`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| John Conroy | `baker_mckenzie__john_conroy` | Chairman of the Executive Committee (elected Oct 2004) | Chicago [S] | Firm management | leading [D] | band: not found | Led firm 2004–2010 (two terms) [S] | Chair to 2010; succeeded by Eduardo Leite [S] | 1,2,3 |
| Christine Lagarde | `baker_mckenzie__christine_lagarde` | Chairman of the Global Policy Committee (Oct 2004 – Jun 2005); former global chair 1999–2004 | Paris [S] | Antitrust, labour, M&A [S] | elite [D] | band: not found; first woman to chair the firm (1999) [S] | Paris partner from 1987, Paris MP 1991; executive committee from 1995 [S] | Left the firm Jun 2005 to become French Minister for Foreign Trade (2 Jun 2005); Finance Minister Jun 2007; IMF Managing Director Jul 2011 [S] | 3,4,5 |
| Paul Rawlinson | `baker_mckenzie__paul_rawlinson` | Partner (since 1996); head of Global IP practice group (2004–2010) | London [S] | Intellectual property | leading [D] | band: not found | Clients incl. Cisco, L'Oréal, HP, Eli Lilly [S] | London Managing Partner 2013–2016; Global Chair Oct 2016 [S] | 6 |
| Eduardo C. Leite | `baker_mckenzie__eduardo_leite` | Partner [A: became global chair in 2010, so presumed a senior partner in 2005] | not found | not found | leading [D] | band: not found | — | Global Chair 2010–2016 [S] | 3,7 |

1. Law.com International, "Bakers names new chair as turnover surges", 10 Oct 2004: https://www.law.com/international-edition/2004/10/10/bakers-names-new-chair-as-turnover-surges/
2. Baker McKenzie bio, John Conroy (chair 2004–2010), from search snippet: https://www.bakermckenzie.com/JohnConroy/
3. Wikipedia, "Baker McKenzie" (chairs list): https://en.wikipedia.org/wiki/Baker_McKenzie
4. LawFuel, Baker & McKenzie press release, Chicago, 3 Jun 2005: https://www.lawfuel.com/blog/chicago-3-june-2005-lawfuel-the-law-news-network-baker
5. Wikipedia, "Christine Lagarde": https://en.wikipedia.org/wiki/Christine_Lagarde
6. Wikipedia, "Paul Rawlinson": https://en.wikipedia.org/wiki/Paul_Rawlinson
7. Law.com International, "Ex-Bakers chair Lagarde becomes first-ever female IMF head", 29 Jun 2011: https://law.com/international-edition/2011/06/29/ex-bakers-chair-lagarde-becomes-first-ever-female-imf-head

### Jones Day (`jones_day`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Stephen J. Brogan | `jones_day__stephen_brogan` | Managing Partner (from 2003; named late 2002; previously led Washington office) | Washington [S] | Firm management | leading [D] | band: not found | Seventh MP of the firm [S] | Remained MP through 2015 (and to 2020s) [S] | 1,2 |
| Patrick F. McCartan | `jones_day__patrick_mccartan` | Senior partner; former Managing Partner (1993 – c. 2002) [S] | Cleveland [A: firm HQ, Cleveland career] | Trial litigation | elite [D] | band: not found | Led Litigation Group from 1976 for 16 yrs; GM Corvair class action 1975; Marathon v Mobil antitrust; takeover defences (Gillette, Marathon Oil) [S] | At the firm 54 years from 1960, so active into the 2010s [D] | 3,4 |
| Robert A. Profusek | `jones_day__robert_profusek` | M&A partner [A: NYU JD 1975; long-time Jones Day M&A head] | New York [S] | M&A, private equity | leading [D] | Chambers USA/Global Band 1 (current) [S]; Am Law Dealmaker of the Year (year not given) [S] | Nextel–Sprint $46.5bn merger (2004–05) [S; year A]; Federated–May $17bn (2005) [S; year A]; GenCorp proxy contest 2006 [S] | Global Chair of M&A (date not found) [S] | 5 |
| Corinne Ball | `jones_day__corinne_ball` | Restructuring partner [A: Best Lawyers listing since 1995; 2005 tenure assumed] | New York [S] | Business restructuring | elite [D] | Chambers USA/Global tier one (current; now "Senior Statesperson") [S]; IWIRC Woman of the Year in Restructuring 2012 [S] | Chrysler sale to Fiat-led New Chrysler, Jun 2009 [S]; Dana, Metaldyne, City of Detroit [S] | none recorded | 6 |

1. Law.com Legal Week, "Jones Day names Washington chief as new managing partner", 16 Dec 2002 (headline): https://www.law.com/legal-week/sites/legalweek/2002/12/16/jones-day-names-washington-chief-as-new-managing-partner/
2. Bloomberg Law, "Jones Day's leader stays in top role…": https://news.bloomberglaw.com/daily-tax-report/jones-days-leader-stays-in-top-role-francisco-orr-promoted
3. Jones Day, "15 Fascinating Facts About Pat McCartan", Dec 2025: https://www.jonesday.com/en/insights/2025/12/15-fascinating-facts-about-pat-mccartan
4. Jones Day firm page, Dec 2020 (tenure facts only): https://www.jonesday.com/en/insights/2020/12/remembering-pat-mccartan
5. Jones Day bio, Robert A. Profusek: https://www.jonesday.com/en/lawyers/p/robert-profusek
6. Jones Day bio, Corinne Ball: https://www.jonesday.com/en/lawyers/b/corinne-ball

### Latham & Watkins (`latham`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Robert M. Dell | `latham__robert_dell` | Chair and Managing Partner (from 1 Jan 1995) | San Francisco [A: from bio context; not confirmed] | Firm management | leading [D] | band: not found; NACD "Directorship 100" 2014 [S] | Firm grew from c. 600 to 2,200+ lawyers in his tenure [S] | Retired from partnership Dec 2014; succeeded by William Voge [S] | 1,2,3 |
| Charles M. Nathan | `latham__charles_nathan` | Global Co-Chair, M&A (from Oct 2001; joined from Fried Frank Feb 2001) | New York [S] | M&A, corporate governance | leading [D] | band: not found | Former Cleary partner and M&A banker (Merrill, Salomon, Smith Barney) [S] | Retired from partnership Dec 2009 (firm bio); joined RLM Finsbury 2012 [S] | 4,5,6 |
| Kirk A. Davenport II | `latham__kirk_davenport` | Capital markets partner [A: Michigan JD 1984; 30+ yrs at firm per bio] | New York [S] | Capital markets, securities | leading [D] | Chambers USA Band 1, 2012–2014 [S]; band 2005: not found; Law360 Capital Markets MVP 2015 [S] | Co-chair of firm's national (securities) office [S] | Retired from partnership Dec 2016 [S] | 7,8 |
| Mark D. Gerstein | `latham__mark_gerstein` | M&A partner (Latham partner from 1996) [S] | Chicago [S] | M&A, activism defence | leading [D] | band: not found; Law360 Rainmaker 2016, NLJ M&A Trailblazer 2016 [S] | Special committee of CBOT directors in CME–CBOT merger (2007) [S; year D] | Global Co-Chair, M&A (dates not found); retired Dec 2022 [S] | 9,10 |
| Maureen E. Mahoney | `latham__maureen_mahoney` | Appellate partner (rejoined 1993) | Washington [S] | Supreme Court and appellate | elite [D] | band: not found; Fellow, American Academy of Arts and Sciences [S] | Argued *Grutter v. Bollinger* (2003) for University of Michigan; appellate work for Arthur Andersen 2003 [S] | none recorded this session | 11 |
| William Voge | `latham__william_voge` | Partner [A: project finance partner, later elected chair] | London [S] | Project finance | leading [D] | band: not found | — | Elected Chair and Managing Partner Jul 2014, took office 1 Jan 2015 [S]; left the firm (2018) | 3,12 |

1. Latham bio, Robert Dell: https://www.lw.com/people/robert-dell
2. Latham news, "Firm Chair and Managing Partner Named to 'Directorship 100'", Aug 2014: https://www.lw.com/en/news/2014/08/firm-chair-managing-partner-named-to-directorship-100
3. Daily Journal, "Latham names successor to Robert Dell", Jul 2014: https://www.dailyjournal.com/article/301831-latham-names-successor-to-robert-dell
4. Law.com International, "Latham's Nathan made M&A chief", 24 Oct 2001: https://www.law.com/international-edition/2001/10/24/lathams-nathan-made-ma-chief/
5. Latham bio, Charles M. Nathan: https://www.lw.com/en/people/charlesmnathan
6. Above the Law, "Musical chairs: a prominent deal lawyer's unusual move", Sep 2012: https://abovethelaw.com/2012/09/musical-chairs-a-prominent-deal-lawyers-unusual-move/
7. Latham bio, Kirk Davenport: https://www.lw.com/en/people/kirk-davenport
8. Martindale listing (education, admission 1985): https://www.martindale.com/attorney/kirk-addison-davenport-ii-459265/
9. Latham bio, Mark Gerstein: https://www.lw.com/en/people/mark-gerstein
10. Latham news, "NLJ M&A Trailblazer", Sep 2016: https://www.lw.com/en/news/2016/09/nlj-ma-trailblazer-mark-gerstein-2016
11. Wikipedia, "Maureen Mahoney": https://en.wikipedia.org/wiki/Maureen_Mahoney
12. Law.com International, "Latham elects London partner to succeed Bill Voge as firmwide chair", 29 Jun 2018: https://law.com/international-edition/2018/06/29/latham-elects-london-partner-to-succeed-bill-voge-as-firmwide-chair

### Sidley Austin Brown & Wood (`sidley`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Charles W. Douglas | `sidley__charles_douglas` | Chair of the Management Committee (1999–2014) | Chicago [A: firm HQ] | Firm management | leading [D] | band: not found | Chaired management committee through the 2001 Brown & Wood combination [S] | Chair to 2014 [S] | 1,2 |
| Thomas A. Cole | `sidley__thomas_cole` | Chair of the Executive Committee (c. 1998 – Apr 2013) | Chicago [S] | Public M&A, corporate governance | leading [D] | band: not found | About 60 announced public mergers, spin-offs and takeover defences [S] | Stepped down as chair Apr 2013; senior counsel 2017 [S] | 1,3 |
| Carter G. Phillips | `sidley__carter_phillips` | Managing Partner, Washington office (1994–2012) | Washington [S] | Supreme Court and appellate | elite [D] | band: not found; Am Law Lifetime Achievement 2022 [S]; Legal 500 Hall of Fame 2017 [S] | 82 Supreme Court arguments in private practice, the most of any private-practice lawyer (91 in total) [S] | Chair of Executive Committee 2012–2017 [S] | 4,5 |
| Virginia A. Seitz | `sidley__virginia_seitz` | Appellate partner (joined 1998) | Washington [S] | Appellate, constitutional and labour law | strong [D] | band: not found | — | Assistant Attorney General, DOJ Office of Legal Counsel, 30 Sep 2011 – 20 Dec 2013; returned to Sidley 2013 [S] | 6 |

1. LawFuel, Sidley partner announcement, 29 Jun 2005 (names Douglas and Cole in their 2005 roles): https://www.lawfuel.com/chicago-and-new-york-june-29-lawfuel-the-law-news-network/
2. Law360 article (tenure facts only): https://law360.com/amp/articles/1720068 ; Sidley bio: https://sidley.com/ja/people/d/douglas-charles-w
3. Sidley bio, Thomas A. Cole: https://www.sidley.com/en/people/c/cole-thomas-a
4. Sidley bio, Carter G. Phillips: https://www.sidley.com/ja/people/p/phillips-carter-g
5. Above the Law, "Carter Phillips to take the reins at Sidley Austin", Apr 2012: https://abovethelaw.com/2012/04/carter-phillips-to-take-the-reins-at-sidley-austin/
6. Wikipedia, "Virginia A. Seitz": https://en.wikipedia.org/wiki/Virginia_A._Seitz

### White & Case (`white_case`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Duane Wall | `white_case__duane_wall` | Managing Partner (from Apr 2000; re-elected Apr 2004) | New York [A: firm HQ] | Firm management | leading [D] | band: not found | First MP under the 2000 governance structure [S] | Term ended 2007–08 (Verrier elected 6 Aug 2007) [S] | 1,2,3 |
| Hugh Verrier | `white_case__hugh_verrier` | Member of the Management Board (from Apr 2004) | office: not found | practice: not found | leading [D] | band: not found | — | Chair of the Firm from 1 Oct 2007; re-elected 2011 and 2015 [S] | 1,2,4 |
| Carolyn B. Lamm | `white_case__carolyn_lamm` | Partner [A: long-standing W&C partner, from 1980s per Wikipedia] | Washington [S] | International arbitration, sovereign disputes | elite [D] | band: not found | Represents sovereign states in international disputes [S] | Partnership Committee from Oct 2007 [S]; ABA President 2009–2010 [S] | 1,5 |

1. White & Case history, "Senior Leadership Chronology": https://history.whitecase.com/senior-leadership-chronology
2. Law.com International, "Verrier to succeed Wall at White & Case helm", 6 Aug 2007: https://law.com/international-edition/2007/08/06/verrier-to-succeed-wall-at-white-case-helm
3. Wikipedia, "White & Case" (chairs): https://en.wikipedia.org/wiki/White_%26_Case
4. Law.com International, "White & Case confirms new four-year term for firmwide chair Verrier", 10 Jun 2011: https://law.com/international-edition/2011/06/10/white-case-confirms-new-four-year-term-for-firmwide-chair-verrier
5. Wikipedia, "Carolyn Lamm": https://en.wikipedia.org/wiki/Carolyn_Lamm

### Weil Gotshal & Manges (`weil`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Stephen J. Dannhauser | `weil__stephen_dannhauser` | Chairman (2002–2012; Executive Partner from 1989); Brooklyn JD 1975 | New York [S] | Firm management; M&A, capital markets | leading [D] | band: not found; NYSBA Root-Stimson Award 2007 [S] | Restructuring counselling and crisis management [S] | Chairman to end-2012; consulting role to 2015 [S] | 1 |
| Ira M. Millstein | `weil__ira_millstein` | Senior partner (at Weil since 1951); Columbia JD 1949 | New York | Antitrust, corporate governance | elite [D] | band: not found; Fellow, American Academy of Arts and Sciences 1995 [S] | Board counsel to GM, GE, Westinghouse, Disney; OECD governance principles [S] | Yale governance centre named for him 2006; chaired NY public-authorities commission (2009 Act) [S] | 2 |
| Marcia L. Goldstein | `weil__marcia_goldstein` | Restructuring partner [A: Cornell JD 1975; later chaired department] | New York [S] | Restructuring | elite [D] | band: not found; WWL Global Insolvency Lawyer of the Year ×7 [S]; Am Law Dealmaker 2019 [S] | Weil's restructuring practice: Enron 2001, WorldCom 2002, Lehman 2008, GM 2009 (firm-level; personal role not confirmed) [S/A] | Chair of Restructuring Dept and Management Committee (dates not found); retired 2020 [S] | 3,6 |
| Howard Chatzinoff | `weil__howard_chatzinoff` | M&A partner [A: UVA JD 1977; retired from partnership 2020] | New York [S] | M&A, corporate governance | leading [D] | Chambers USA and Global ranked (band and year not found) [S]; Legal 500 Hall of Fame [S] | Co-Head of Transactions Practice (dates not found) [S] | none recorded | 4 |
| Barry M. Wolf | `weil__barry_wolf` | Private funds partner [A: Michigan JD 1984, NYU LLM 1989] | New York [S] | Private equity funds | strong [D] | band: not found | — | Executive Partner (succeeded Dannhauser in that role, c. 2009–10) [S; date D] | 5,7 |

1. Weil bio, Stephen J. Dannhauser: https://www.weil.com/people/stephen-dannhauser
2. Wikipedia, "Ira Millstein": https://en.wikipedia.org/wiki/Ira_Millstein
3. Weil bio, Marcia L. Goldstein: https://www.weil.com/people/marcia-goldstein
4. Weil bio, Howard Chatzinoff: https://www.weil.com/people/howard-chatzinoff
5. Weil bio, Barry M. Wolf: https://www.weil.com/people/barry-wolf
6. Wikipedia, "Weil, Gotshal & Manges" (bankruptcy matters list): https://en.wikipedia.org/wiki/Weil,_Gotshal_%26_Manges
7. JD Journal, "New leadership at Weil Gotshal", 10 Dec 2009: https://jdjournal.com/2009/12/10/new-leadership-at-weil-gotshal

### Mayer Brown Rowe & Maw (`mayer_brown`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Tyrone C. Fahner | `mayer_brown__tyrone_fahner` | Chairman (sole chair from May 2001; co-chair 1998–2001) | Chicago [S] | Firm management | leading [D] | band: not found | Led the 2002 merger with Rowe & Maw; firm grew from c. 800 to c. 1,400 lawyers [S] | Stepped down as chairman spring 2007 under the partnership agreement [S] | 1,2,3 |
| James D. Holzhauer | `mayer_brown__james_holzhauer` | Appellate partner; firm General Counsel [S] | Chicago [S] | Appellate litigation | leading [D] | band: not found | — | Chairman (Office of the Chairman) from 1 Jun 2007 [S] | 3 |
| Kenneth S. Geller | `mayer_brown__kenneth_geller` | Partner-in-Charge, Washington office (1995–2007); partner since 1986 | Washington [S] | Supreme Court and appellate | elite [D] | band: not found | Deputy Solicitor General 1979–1986; 40+ Supreme Court arguments; c. 300 Supreme Court briefs [S] | Vice Chairman 2007; Managing Partner 2009 [S] | 3,4 |
| Paul Maher | `mayer_brown__paul_maher` | Senior Partner, London [S; role at Oct 2006, assumed for 2005] | London [S] | Corporate transactions | leading [D] | band: not found | — | Vice Chairman (global strategy) from 1 Jun 2007 [S] | 3 |
| Richard Ben-Veniste | `mayer_brown__richard_ben_veniste` | Partner (2002 – Jan 2023) | Washington [A] | White-collar litigation, investigations [A] | strong [D] | band: not found | Former Chief, Watergate Task Force (1973–75); 9/11 Commission member (2002) [S] | none recorded | 5 |

1. Mayer Brown bio, Tyrone C. Fahner (tenure dates, from search snippet): https://mayerbrown.com/people/Tyrone-C-Fahner
2. Law.com International, "Mayer Brown shakes up management", 22 May 2001: https://law.com/international-edition/2001/05/22/mayer-brown-shakes-up-management-2
3. LawFuel, Mayer Brown Rowe & Maw press release, Chicago, 3 Oct 2006: https://www.lawfuel.com/blog/october-3-2006-chicago-international-law-firm-mayer-brown-rowe
4. Wikipedia, "Kenneth Geller": https://en.wikipedia.org/wiki/Kenneth_Geller
5. Wikipedia, "Richard Ben-Veniste": https://en.wikipedia.org/wiki/Richard_Ben-Veniste

### Morgan Lewis & Bockius (`morgan_lewis`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Francis M. Milone | `morgan_lewis__francis_milone` | Chair (since 1999; re-elected for 2nd five-year term 2004) | Philadelphia [A: firm HQ] | Firm management | leading [D] | band: not found | Led the 1999 overhaul of the management structure [S] | Chair until 1 Oct 2014 (succeeded by Jami McKeon) [S] | 1,2 |
| Jami Wintz McKeon | `morgan_lewis__jami_mckeon` | Partner (joined 1981) [S] | Philadelphia [A] | Litigation [A] | leading [D] | band: not found | — | Elected chair Oct 2013; Chair from 1 Oct 2014 (first woman to chair the firm) [S] | 2,3,4 |
| Philip A. Miscimarra | `morgan_lewis__philip_miscimarra` | Labour and employment partner (joined May 2005 from Seyfarth Shaw) | Chicago / Washington [S] | Labour law (NLRB) | strong [D] | band: not found | — | Left 2013 for the NLRB (member from 7 Aug 2013) [S] | 5 |
| John F. Ring | `morgan_lewis__john_ring` | Labour and employment partner (since 1999) | Washington [A] | Labour law, collective bargaining | strong [D] | band: not found | Former co-chair of the labour and employment practice (dates not found) [S] | None recorded in 2005–2015; NLRB chair 2018 [S] | 6 |

1. Law.com International, "Morgan Lewis restates belief in chairman", 10 May 2004: https://www.law.com/international-edition/2004/05/10/morgan-lewis-restates-belief-in-chairman/
2. Morgan Lewis press release, McKeon election, 1 Oct 2013 (from search snippet): https://www.morganlewis.com/news/pr_mckeonelection_01oct13 ; McKeon begins term, 1 Oct 2014: https://www.morganlewis.com/news/pr_mckeonbeginstermaschair_1oct2014
3. Philadelphia Inquirer, "Morgan Lewis & Bockius names a woman as chair", 2 Oct 2013: https://www.inquirer.com/philly/business/20131002_Morgan_Lewis___Bockius_names_a_woman_as_chair.html
4. Wikipedia, "Morgan, Lewis & Bockius" (McKeon joined 1981): https://en.wikipedia.org/wiki/Morgan,_Lewis_%26_Bockius
5. Wikipedia, "Philip Miscimarra": https://en.wikipedia.org/wiki/Philip_Miscimarra
6. Wikipedia, "John F. Ring": https://en.wikipedia.org/wiki/John_F._Ring

### Kirkland & Ellis (`kirkland`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Thomas D. Yannucci | `kirkland__thomas_yannucci` | Chair, Firmwide Management Committee (from 2001) | Washington [S] | Litigation; media and First Amendment | leading [D] | Chambers USA: General Commercial Litigation, Media & Entertainment, First Amendment (years not found) [S] | Quoted as chair in Kirkland's Jul 2005 arbitration-hire release [S] | Succeeded as chair by Jeffrey Hammes, 2010 [S] | 1,2,3 |
| Jeffrey C. Hammes | `kirkland__jeffrey_hammes` | Private equity / M&A partner (at Kirkland since 1985; partner 1991) | Chicago [S] | Private equity M&A, LBOs | leading [D] | band: not found | Core client Bain Capital [S] | Chair of the Management Committee from 2010 (named Dec 2009) [S] | 2,4 |
| Kirk A. Radke | `kirkland__kirk_radke` | Private equity partner [A: 25+ yrs of practice and Kirkland tenure per bio] | New York [S] | Private equity | leading [D] | Chambers USA top private equity lawyer 2009–2011 (band not stated) [S] | — | Moved to Willkie Farr & Gallagher, 3 Feb 2014 [S] | 5,6 |
| Richard C. Godfrey | `kirkland__richard_godfrey` | Litigation partner (at Kirkland since 1979) | Chicago [S] | Trial litigation, class actions | elite [D] | band: not found; Lawdragon Hall of Fame 2017 [S] | Amoco Cadiz damages case (1980s); counsel to BP in Deepwater Horizon litigation (from 2010) [S; year D] | none in 2005–2015 (moved to Quinn Emanuel 2023) [S] | 7,8 |
| Stephen Fraidin | `kirkland__stephen_fraidin` | M&A partner (joined May 2003 from Fried Frank) | New York [S] | M&A | elite [D] | band: not found | Fried Frank rainmaker; long-time adviser to Pershing Square [S] | Left c. 2014 to become Vice Chairman of Pershing Square Capital Management [S; year A: Law360 article date not read] | 9,10 |

1. Kirkland press release, Jul 2005: https://www.kirkland.com/news/press-release/2005/07/leading-international-arbitration-lawyer-joins-kir
2. Law.com International, "Kirkland names private equity specialist as new chairman", 9 Dec 2009: https://law.com/international-edition/2009/12/09/kirkland-names-private-equity-specialist-as-new-chairman
3. Kirkland bio, Thomas D. Yannucci: https://www.kirkland.com/lawyers/y/yannucci-thomas-d-pc
4. Kirkland bio, Jeffrey C. Hammes: https://www.kirkland.com/lawyers/h/hammes-jeffrey-c-pc
5. Willkie press release, "Leading private equity lawyer Kirk A. Radke joins", Feb 2014: https://www.willkie.com/news/2014/02/leading-private-equity-lawyer-kirk-a-radke-joins__
6. LittleSis profile (Chambers accolades 2009–2011; secondary): https://littlesis.org/person/75218-Kirk_A_Radke
7. Law360, "Trial Pros: Kirkland & Ellis' Richard Godfrey", Feb 2016: https://www.kirkland.com/siteFiles/News/Law360%20(Trial%20Pros_Godfrey)%20Feb%202016.pdf
8. Law.com, "Longtime Kirkland executive committee leader heads to Quinn Emanuel", 13 Mar 2023: https://www.law.com/2023/03/13/longtime-kirkland-executive-committee-leader-heads-to-quinn-emanuel/
9. Law.com International, "Fried Frank loses Fraidin to Kirkland & Ellis", 12 May 2003: https://www.law.com/international-edition/2003/05/12/fried-frank-loses-fraidin-to-kirkland-ellis/
10. Law360, "Ackman Poaches Kirkland M&A Veteran For Activist Fund": https://www.law360.com/articles/612861

### Gibson Dunn & Crutcher (`gibson_dunn`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Kenneth M. Doran | `gibson_dunn__kenneth_doran` | Chairman and Managing Partner (from 2002); USC JD 1981 | Los Angeles [S] | Firm management; M&A, capital markets | leading [D] | band: not found | Co-chaired Corporate Practice and sat on the Executive Committee from 1996 [S] | Chair to 2021 (succeeded by Barbara Becker) [S] | 1,2 |
| Theodore B. Olson | `gibson_dunn__theodore_olson` | Partner; Co-Chair, Appellate and Constitutional Law Group (rejoined Jul 2004) | Washington [S] | Supreme Court and appellate | elite [D] | band: not found | Former U.S. Solicitor General (to Jul 2004) [S] | none recorded | 3,4 |
| Theodore J. Boutrous Jr. | `gibson_dunn__theodore_boutrous` | Partner; Co-Chair, Appellate and Constitutional Law Group (Jul 2004 announcement) [S] | Los Angeles [S] | Appellate, media and class-action litigation | elite [D] | band: not found; Am Law Litigator of the Year Grand Prize (announced Jan 2020) [S] | — | none recorded | 3,5 |
| Randy M. Mastro | `gibson_dunn__randy_mastro` | Litigation partner (returned 1998); co-chair of litigation [S] | New York [S] | Trial and commercial litigation | elite [D] | band: not found | Former NYC Deputy Mayor for Operations (to 1998) [S] | none in 2005–2015 (moved to King & Spalding Aug 2022) [S] | 6,7 |
| Barbara L. Becker | `gibson_dunn__barbara_becker` | M&A partner [A: NYU JD 1988; co-chaired M&A "for over a decade" before 2021] | New York [S] | M&A | leading [D] | Chambers USA/Global ranked (band not given) [S]; The Deal "Powerhouse 20" 2018 [S] | — | Co-chair of M&A practice (dates not found); Chair and MP from 1 May 2021 [S] | 2,8 |
| Dennis J. Friedman | `gibson_dunn__dennis_friedman` | M&A partner, head of M&A practice [A: leads practice "for many years"] | New York [S] | M&A, corporate governance | leading [D] | Chambers USA/Global ranked (band not given) [S]; Best Lawyers since 2006 [S] | — | none recorded | 9 |

1. Gibson Dunn bio, Kenneth M. Doran: https://www.gibsondunn.com/lawyer/doran-kenneth-m/
2. Lawdragon press release, "Gibson Dunn elects Barbara Becker as Chair and Managing Partner", 5 Mar 2021: https://www.lawdragon.com/press-releases/2021-03-05-gibson-dunn-elects-barbara-becker-as-chair-and-managing-partner
3. LawFuel, Gibson Dunn press release, 7 Jul 2004: https://www.lawfuel.com/?p=2826
4. Wikipedia, "Theodore Olson" (professional facts only): https://en.wikipedia.org/wiki/Theodore_Olson
5. Gibson Dunn bio, Theodore J. Boutrous Jr.: https://www.gibsondunn.com/lawyer/boutrous-jr-theodore-j/ ; Gibson Dunn release, 2 Jan 2020: https://gibsondunn.com/?p=52348
6. Federalist Society bio, Randy Mastro (returned 1998; used for career dates only): https://fedsoc.org/bio/randy-mastro
7. Law.com, "Randy Mastro moves to King & Spalding after more than 20-year run at Gibson Dunn", 17 Aug 2022: https://www.law.com/therecorder/2022/08/17/randy-mastro-moves-to-king-spalding-after-more-than-20-year-run-at-gibson-dunn/
8. Gibson Dunn bio, Barbara L. Becker: https://www.gibsondunn.com/lawyer/becker-barbara-l/
9. Gibson Dunn bio, Dennis J. Friedman: https://www.gibsondunn.com/lawyer/friedman-dennis-j/

### Sullivan & Cromwell (`sullivan_cromwell`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| H. Rodgin Cohen | `sullivan_cromwell__rodgin_cohen` | Chairman (1 Jul 2000 – 31 Dec 2009); HLS 1968 | New York [S] | Bank M&A, financial regulation | elite [D] | Chambers Band 1, Corporate/M&A and FI M&A (current) [S]; 2005 band: not found | Adviser in Sept 2008 crisis to Bear Stearns, Lehman, AIG, Wachovia, JPMorgan (WaMu) [S] | Senior Chairman from 1 Jan 2010 [S] | 1,2 |
| Joseph C. Shenker | `sullivan_cromwell__joseph_shenker` | Partner (since 1986); head of global real estate practice; Columbia JD 1980 | New York [S] | Real estate, M&A | leading [D] | Chambers: real estate, "eminent practitioner" (current) [S]; NYLJ Lifetime Achievement 2023 [S] | Pioneered real-estate securitisation; work for Goldman Sachs / Whitehall [S] | Vice Chairman Feb 2006; Chair 2010–2022 [S] | 3,4,5 |
| Robert J. Giuffra Jr. | `sullivan_cromwell__robert_giuffra` | Litigation partner (joined 1989 after Rehnquist clerkship) | New York [S] | Securities, white-collar and bet-the-company litigation | elite [D] | Chambers Star Individual, NY Securities Litigation (2024) [S]; 2005 band: not found | — | Management Committee from 2007 [S] | 6 |
| Francis J. (Frank) Aquila | `sullivan_cromwell__frank_aquila` | M&A partner [A: long-serving S&C M&A partner] | New York [S] | M&A | elite [D] | Am Law Dealmaker of the Year 2009 [S]; Atlas Award Global M&A Lawyer of the Year 2010 [S] | Lead counsel to InBev on its unsolicited acquisition of Anheuser-Busch (2008) [S] | none recorded | 7,8 |
| Penny Shane | `sullivan_cromwell__penny_shane` | Litigation partner [A: now of counsel; partner status in 2005 assumed] | New York [A] | Financial-institution and securities litigation | strong [D] | Benchmark "Litigation Star" (year not given) [S] | — | none recorded | 9 |

1. S&C bio, H. Rodgin Cohen: https://sullcrom.com/lawyers/HRodgin-Cohen
2. Chambers department page, S&C FI M&A: https://chambers.com/department/sullivan-cromwell-llp-financial-services-regulation-financial-institutions-ma-usa-5:714:12788:1:3663 ; Law.com International, "New book highlights Sullivan lawyer's central role in bank bailouts", 21 Oct 2009: https://law.com/international-edition/2009/10/21/new-book-highlights-sullivan-lawyers-central-role-in-bank-bailouts
3. Law.com Legal Week, "S&C names Shenker as chief in waiting", 22 Feb 2006: https://www.law.com/legal-week/sites/legalweek/2006/02/22/sc-names-shenker-as-chief-in-waiting/
4. S&C bio, Joseph C. Shenker: https://www.sullcrom.com/Lawyers/Joseph-C-Shenker ; Chambers: https://chambers.com/lawyer/joseph-c-shenker-usa-5:139594
5. S&C, "Senior Chair Joe Shenker recognized for Lifetime Achievement", Aug 2023: https://www.sullcrom.com/About/Rankings/2023/August/S-C-Senior-Chair-Joe-Shenker-Recognized-for-Lifetime-Achievement-by-New-York-Law-Journal
6. S&C bio, Robert J. Giuffra Jr.: https://www.sullcrom.com/Lawyers/Robert-J-Giuffra-Jr ; Chambers: https://chambers.com/lawyer/robert-j-giuffra-jr-usa-5:195916
7. S&C bio, Francis J. Aquila: https://www.sullcrom.com/Lawyers/Francis-J-Aquila
8. Wikipedia, "Frank J. Aquila": https://en.wikipedia.org/wiki/Frank_J._Aquila
9. S&C bio, Penny Shane: https://www.sullcrom.com/Lawyers/Penny-Shane

### Cravath Swaine & Moore (`cravath`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Robert D. Joffe | `cravath__robert_joffe` | Presiding Partner (1999–2006); first litigator in the post | New York [S] | Antitrust, corporate governance litigation | elite [D] | band: not found | Lead outside counsel to Time Warner: Time v Paramount 1989, Time–Turner 1996, AOL merger; IBM antitrust team [S] | Presiding partner to Dec 2006, then returned to full-time practice [S] | 1,2,3 |
| Evan R. Chesler | `cravath__evan_chesler` | Head of Litigation Department (from 1996); presiding partner-elect (voted Nov 2005) | New York [S] | Antitrust and business trial litigation | elite [D] | band: not found; Chambers USA Award for Business Trial Litigation 2012 [S]; Lawdragon "Legend" 2015 [S] | IBM matters (e.g. Neon Enterprise Software suit) [S] | Presiding Partner 2007–2012; Chairman 2013–2021 [S] | 2,4,5 |
| Faiza J. Saeed | `cravath__faiza_saeed` | Corporate partner (partner 1998); HLS JD 1991 | New York [S] | M&A, corporate governance | elite [D] | Am Law Dealmaker of the Year 2000, 2005, 2011 [S]; Chambers Band 1 Corporate/M&A NY (current) [S]; 2005 band: not found | Media, technology and energy transactions [S] | Elected Presiding Partner Jul 2016 (from 1 Jan 2017) [S] | 6,7 |
| Kris F. Heinzelman | `cravath__kris_heinzelman` | Head of Corporate Department (2002–2008); partner 1983 | New York [S] | Corporate finance, securities offerings | leading [D] | band: not found; Lawdragon Hall of Fame 2018 [S] | — | Head of Corporate to 2008; retired Dec 2016 [S] | 8 |
| Ronald S. Rolfe | `cravath__ronald_rolfe` | Litigation partner (partner 1977) | New York [S] | Litigation, domestic and international arbitration | leading [D] | band: not found | — | Retired from Litigation Department Dec 2010 [S] | 9 |
| William P. Rogers Jr. | `cravath__william_rogers` | Head of London office (2001–2007); partner 1985 | London [S] | Corporate | leading [D] | band: not found | — | Returned from London leadership 2007; retired Dec 2015 [S] | 10 |

1. Cravath, "Presiding Partners" history page: https://www.cravath.com/our-story/history/presiding-partners.html
2. Law.com International, "Cravath votes in head of litigation to lead firm", 15 Nov 2005: https://www.law.com/international-edition/2005/11/15/cravath-votes-in-head-of-litigation-to-lead-firm/
3. Wikipedia, "Robert Joffe" (career facts only): https://en.wikipedia.org/wiki/Robert_Joffe ; Harvard Law Today: https://hls.harvard.edu/today/robert-d-joffe-67-1943-2010
4. Wikipedia, "Evan Chesler": https://en.wikipedia.org/wiki/Evan_Chesler
5. Cravath news, "Evan Chesler receives Chambers USA Award for Business Trial Litigation", Jun 2012: https://www.cravath.com/news-insights/evan-chesler-receives-chambers-usa-award-for-business-trial-litigation.html
6. Lawdragon press release, "Cravath elects Faiza J. Saeed next presiding partner", 14 Jul 2016: https://www.lawdragon.com/press-releases/2016-07-14-cravath-elects-faiza-j-saeed-next-presiding-partner
7. Chambers profile, Faiza J. Saeed: https://chambers.com/lawyer/faiza-j-saeed-usa-5:29215
8. Cravath bio, Kris F. Heinzelman: https://www.cravath.com/people/kris-f-heinzelman.html
9. Cravath bio, Ronald S. Rolfe: https://www.cravath.com/people/ronald-s-rolfe.html
10. Cravath bio, William P. Rogers Jr.: https://www.cravath.com/people/william-p-rogers-jr.html

### Wachtell Lipton Rosen & Katz (`wachtell`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Martin Lipton | `wachtell__martin_lipton` | Founding partner (1965); NYU LLB 1955 | New York | M&A, takeover defence, governance | elite [D] | band: not found; NLJ "100 Most Influential Lawyers" [S] | Devised the "poison pill" defence (1982; client memo 1983) [S] | Executive committee member [S] | 1,2 |
| Herbert M. Wachtell | `wachtell__herbert_wachtell` | Founding partner (1965); NYU LLB 1954 | New York | Litigation | elite [D] | Chambers Lifetime Achievement Award, Litigation, 2006 [S] | Delaware takeover litigation incl. Time–Warner and Paramount [S] | Executive committee member [S] | 3,4 |
| Edward D. Herlihy | `wachtell__edward_herlihy` | Partner (since 1984); co-chairman of executive committee (from 2006 per Bloomberg; Lawdragon's dates for Neff imply 2003) [S, sources conflict] | New York | Bank and financial-institution M&A | elite [D] | Chambers ranked (band and year not found) [S] | NationsBank–BankAmerica 1998; Bank of America–Merrill Lynch 2008 [S] | Co-chairman 2006–2023 [S] | 5,6,7 |
| Daniel A. Neff | `wachtell__daniel_neff` | Partner (joined 1977); co-chairman of executive committee (from 2006 per Bloomberg; Lawdragon says 20 years to Oct 2023) [S, sources conflict] | New York | Corporate, M&A | elite [D] | Chambers Band 1 Corporate/M&A (current) [S]; Am Law Dealmaker of the Year 2001, 2012, 2015 [S] | Verizon's $130bn acquisition of Verizon Wireless (2013–14) [S; year D] | Co-chairman to 2023 [S] | 5,8 |
| Theodore N. Mirvis | `wachtell__theodore_mirvis` | Litigation partner [A: 45+ years at firm per bio] | New York | Takeover and securities litigation | leading [D] | Chambers Senior Statespeople, Securities Litigation (2023) [S]; 2005 band: not found | Airgas in Air Products takeover fight (2010–11) [S; year D]; "Mirvis bylaw" [S] | none recorded | 9,10 |

1. Wikipedia, "Martin Lipton": https://Www.wikipedia.org/wiki/Martin_Lipton
2. NYU Law Magazine, "Partner for Life": https://blogs.law.nyu.edu/magazine/?p=6621
3. Wikipedia, "Herbert Wachtell": https://en.wikipedia.org/wiki/Herbert_Wachtell
4. Best Lawyers, Herbert M. Wachtell: https://www.bestlawyers.com/lawyers/herbert-m-wachtell/27221
5. Bloomberg Law, "Wachtell names new leaders William Savitt and Andrew Nussbaum" (2023): https://news.bloomberglaw.com/business-and-practice/wachtell-names-new-leaders-william-savitt-and-andrew-nussbaum
6. Wachtell bio, Edward D. Herlihy: https://wlrk.com/?p=803
7. ABA Journal, "Wachtell and Shearman advised on Bank of America deal" (2008): https://abajournal.com/news/article/wachtell_and_shearman_advised_on_bank_of_america_deal ; Gawker archives profile (secondary): https://gawkerarchives.com/550521/edward-d-herlihy
8. Wachtell bio, Daniel A. Neff: https://www.wlrk.com/attorney/daneff/ ; Lawdragon profile: https://www.lawdragon.com/lawyers/wachtell-lipton-rosen-katz/daniel-a-neff ; Chambers: https://chambers.com:443/lawyer/daniel-a-neff-usa-5:139663
9. Lawdragon, "Lawyer Limelight: Ted Mirvis", 22 Jan 2017: https://www.lawdragon.com/2017/01/22/lawyer-limelight-ted-mirvis/
10. Chambers profile, Theodore N. Mirvis: https://chambers.com/lawyer/theodore-n-mirvis-usa-5:156988

---

### Gaps

- **Chambers USA 2005/2006 bands: not found for anyone.** Archived Chambers editions were not reachable. Every band shown above is a later or current band, marked with its year. A later pass could derive the 2005 band from Chambers' "years ranked" counts (as I did for Kasner) or from archived Chambers PDFs.
- **Search budget ran out mid-session.** The shared WebSearch limit (200 calls per turn) was hit after about 55 of my searches. The rest of the work used direct fetches of firm bios and Wikipedia pages. As a result:
  - **White & Case (3), Baker & McKenzie (4), Jones Day (4), Sidley (4) and Morgan Lewis (4)** are below the 5–7 target. Candidates I could not check: Paul Friedland (W&C arbitration; the bio page returned 403), David Heiman (Jones Day restructuring; the bio URL returned 404), Robert Kreitman (Sidley securitisation), and further Baker and Morgan Lewis band-1 names.
  - Not confirmed: **Eduardo Leite's** office and practice in 2005, **Hugh Verrier's** office and practice, and **Barbara Becker's / Dennis Friedman's** partner start dates. All are marked [A].
- **Paywalled or blocked:** Law.com and Legal Week archives (only headlines and leads readable: the Jones Day 2002 Brogan item and the Mayer Brown Oct 2006 item), Law360 (Fraidin's Pershing Square date), Chambers individual band history, whitecase.com bios (403), the Mayer Brown, Morgan Lewis and Baker McKenzie bio URLs (404 when fetched; facts came from search snippets of those same URLs).
- **Conflicts recorded rather than resolved:**
  - Wachtell's Herlihy/Neff co-chairmanship start: 2006 (Bloomberg) versus about 2003 (Lawdragon).
  - Fahner's chairmanship: sole chair from 2001 (firm bio) versus "Chairman since 1998" (2006 press release, which counts the co-chair years).
  - White & Case handover: Verrier elected Aug 2007; Wall's term ran to 31 Mar 2008 per Law.com, but the chronology starts the new structure 1 Oct 2007.
  - Charles Nathan's retirement: Dec 2009 (Latham) versus 2012 (Above the Law).
- **Deliberately left out:** Harvey Miller (at Greenhill, not Weil, in 2005) and Al Pfeiffer (joined Latham after 2005). Content outside ADR PT-0013's allowed professional facts was omitted wherever sources carried it.
- **Standing values** are my judgement [D]. Calibrate them against the other notables parts before mapping them to attributes.

## Notables, part 2: 14 New York and Boston rivals (2005 start)

Research for Partner Track's `notables.yaml` (ADR PT-0013). Compiled 2026-11-19.

### Rules applied

- Only **public professional standing** is recorded: name, role in 2005, office, practice, directory standing and honours, notable matters with years, and professional moves 2005–2015 (lateral moves, government posts, chairs, leaving the partnership).
- **Nothing** about private life, family, health, age or birth date, death, politics, donations, misconduct, discipline, lawsuits against the person, scandals, workplace conduct or criticism. Where a person left practice, the entry says only "left the firm (YYYY)" or "retired from partnership (YYYY)".
- For **Dewey Ballantine** and **LeBoeuf**, only practising partners are chosen, not the 2007–2012 leadership of the merged firm. Moves are given only as "joined X (2012)".
- Candidates mainly known for a controversy were left out without comment.
- Directory bands for 2005/2006 were rarely findable. Where none was found the cell says **band: not found**. A later band is given only with its year, or marked "(current)" where the year was not shown.
- `standing` is a suggested skill range derived from public standing, never from personality: **elite** (firm leader of a top-tier firm, or a dominant name in a practice), **leading** (directory-ranked, award-winning or a practice head), **strong** (well-regarded partner with less directory evidence).

#### Tag legend

- **[S]**: sourced this session (the page or search result cited says it).
- **[D]**: derived from sourced facts (for example, a start year worked back from "chairman for 17 years").
- **[A]**: assumed. The basis is stated, usually "recall; not verified this session". Every [A] row needs checking before it goes into `notables.yaml`.

#### Count

**70 people** across 14 firms: Davis Polk 6, Simpson Thacher 7, Paul Weiss 6, Cleary 6, Debevoise 5, Shearman 6, Milbank 5, Fried Frank 5, Cadwalader 5, Willkie 5, Proskauer 5, Ropes & Gray 4, Dewey Ballantine 4, LeBoeuf 1.

**Coverage warning.** The shared web-search budget ran out partway through (after Shearman). Most rows for Milbank, Fried Frank, Cadwalader, Willkie, Proskauer, Ropes & Gray, Dewey Ballantine and LeBoeuf therefore rest on a few fetched pages plus **[A]** recall. Treat those firms as drafts. See "Gaps".

---

### Davis Polk & Wardwell (`davis_polk`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| John R. Ettinger | `davis_polk__john_ettinger` | Managing partner (1999–2011) [S] | New York | M&A | elite [D] | band: not found | Partner 1986; led the firm 12 years [S] | Stepped down as MP Apr 2011 and stayed a partner; succeeded by Thomas Reid [S] | 1, 2, 3 |
| Phillip R. Mills | `davis_polk__phillip_mills` | Partner | New York | M&A | leading [D] | 2005 band: not found. Chambers USA: 23 years ranked in NY Corporate/M&A; band 5 (current) [S] | US and cross-border public M&A [S] | none found | 4 |
| Marshall S. Huebner | `davis_polk__marshall_huebner` | Partner (since 2002) [S] | New York | Restructuring | leading [D] | 2005 band: not found. Chambers band 1 Bankruptcy/Restructuring (current) [S] | Adelphia, Enron, Loral, Polaroid, Collins & Aikman, Meridian Automotive [S] | Co-head of Restructuring (later; date not found) [S] | 5, 6 |
| Denis J. McInerney | `davis_polk__denis_mcinerney` | Partner (since 1997) [S] | New York | White collar, litigation | leading [D] | band: not found | n/a | Chief, DOJ Criminal Division Fraud Section (Jan 2010–2013); Deputy Assistant AG (2013–14); rejoined Davis Polk (Oct 2014) [S] | 7, 8 |
| Carey R. Dunne | `davis_polk__carey_dunne` | Partner, litigation [S] | New York | Litigation | leading [D] | band: not found | Head of litigation; member of the 3-person Management Committee (by 2012) [S] | President, New York City Bar Association (May 2012) [S] | 9 |
| Richard D. Truesdell Jr. | `davis_polk__richard_truesdell` | Partner [A: recall] | New York | Capital markets | elite [D] | 2005 band: not found. Chambers "Star Individual", high-yield debt (current) [S] | Global chair of capital markets (current) [S] | none found | 10 |

1. Communities in Schools profile, https://www.communitiesinschools.org/about-us/our-leadership/profile/john-r-ettinger
2. Legal Week (Law.com), 2011-02-09, https://www.law.com/legal-week/sites/legalweek/2011/02/09/davis-polk-managing-partner-announces-intention-to-step-down-from-top-role/
3. Business Wire, 2011-04-07, https://businesswire.com/news/home/20110407006001/en/Davis-Polk-Elects-New-Management-Team-Led-by-Tom-Reid-as-Managing-Partner
4. Chambers USA profile, https://chambers.com/lawyer/phillip-r-mills-usa-5:33075
5. Chambers USA profile, https://chambers.com/lawyer/marshall-s-huebner-usa-5:200459
6. Davis Polk bio, https://www.davispolk.com/lawyers/marshall-huebner
7. Davis Polk bio, https://davispolk.com/lawyers/denis-mcinerney
8. Compliance Week, "DOJ names new chief of fraud", https://complianceweek.com/doj-names-new-chief-of-fraud/19676.article ; JD Journal, 2014-10-15, https://old.jdjournal.com/2014/10/15/davis-polk-welcomes-denis-j-mcinerney-in-return-to-the-firm/amp
9. NYC Bar "In the News", https://www.nycbar.org/in-the-news/davis-polk-partner-set-to-lead-city-bar/ ; probono.net, https://www.probono.net/asylum/news/article.433388-Carey_Dunne_Elected_New_President_New_York_City_Bar_Association?print=1
10. Chambers department page, https://chambers.com/department/davis-polk-wardwell-llp-capital-markets-high-yield-debt-usa-5:3082:12788:1:3833

### Simpson Thacher & Bartlett (`simpson_thacher`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Philip T. Ruegger III | `simpson_thacher__philip_ruegger` | Chair of the Executive Committee (elected Mar 2004); before that head of corporate [S] | New York | Corporate / M&A | elite [D] | band: not found | n/a | Succeeded as chair by William Dougherty (Mar 2013) [S] | 1, 2 |
| Richard I. Beattie | `simpson_thacher__richard_beattie` | Chairman of the firm (exec committee chair 1991–2004) [S] | New York | M&A, governance, private equity | elite [D] | AmLaw Lifetime Achiever (2011); AmLaw Top 50 Innovator (2013) [S]; band: not found | KKR / RJR Nabisco; JPMorgan Chase / Bank One ($58bn, 2004); AOL / Time Warner; Anthem / WellPoint; Dow Jones / News Corp (independent directors) [S; years A] | Senior Chairman (later) [S] | 3, 4 |
| Charles "Casey" Cogut | `simpson_thacher__casey_cogut` | Partner (1980–2012) [S] | New York | M&A, private equity | elite [D] | Lawdragon "Dealmaker" limelight (2012) [S]; band: not found | Microsoft / Skype ($8.5bn, 2011); Sealed Air / Diversey ($2.9bn, 2011); Eaton / Cooper ($11.8bn, 2012) [S] | Became senior M&A counsel (2012) [S] | 5 |
| Barry R. Ostrager | `simpson_thacher__barry_ostrager` | Head of Litigation (1999–2011) [S] | New York | Insurance and commercial trial work | elite [D] | Chambers "Leading U.S. Litigation Business Trial Lawyer" (Jun 2006) [S]; Legal 500 top-ten trial lawyer (2007) [S] | Swiss Re, World Trade Center coverage trial (NLJ top defence win, 2004) [S]; *Handbook on Insurance Coverage Disputes* treatise [S] | Justice, NY Supreme Court Commercial Division (c. mid-2015) [D: "8½ years" to Dec 2023] | 6, 7, 8 |
| Lee A. Meyerson | `simpson_thacher__lee_meyerson` | Partner [S] | New York | Financial institutions M&A | leading [D] | band: not found | JPMorgan Chase / Bank One ($58bn, 2004) [S] | none found | 9, 10 |
| John G. Finley | `simpson_thacher__john_finley` | Partner; later head / co-head of global M&A [S] | New York | M&A, private equity | leading [D] | band: not found | n/a | Chief Legal Officer, Blackstone (Sep 2010) [S] | 11, 12 |
| Michael J. Chepiga | `simpson_thacher__michael_chepiga` | Partner; Executive Committee; led securities litigation [S] | New York | Securities litigation | leading [D] | Chambers USA first tier, securities litigation, "for over a decade" (to 2012) [S]; 2005 band: not given by year | Lead counsel for Stanley O'Neal, Merrill Lynch securities / derivative / ERISA litigation (AmLaw "Big Suits", 2009) [S] | Retired from partnership (1 Jan 2012); joined BlackRobe Capital (2012) [S] | 13, 14 |

1. Law.com International, 2004-08-25, https://www.law.com/international-edition/2004/08/25/chief-takes-backseat-in-simpson-re-jig/ (teaser only; details via search summary)
2. Legal Week, 2013-03-08, https://www.law.com/legal-week/sites/legalweek/2013/03/08/simpson-thacher-names-long-serving-corporate-partner-as-new-leader/
3. STB bio, https://www.stblaw.com/our-team/partners/richard-i-beattie (fetched)
4. Law.com, 2004-01-14, https://www.law.com/legal-week/sites/legalweek/2004/01/14/jp-calls-in-simpson-thacher-on-60bn-bank-job/
5. Lawdragon, 2012-06-11, https://lawdragon.com/lawyer-limelights/2012-06-11-charles-casey-cogut
6. STB news, 2005-03-28, https://stblaw.com/about-us/news/view/2005/03/28/nlj-names-simpson-thacher-wtc-victory-among-top-defense-wins-of-2004-
7. STB news, 2007-05-25, https://www.stblaw.com/about-us/news/view/2007/05/25/barry-ostrager-named-best-us-trial-lawyer- (fetched)
8. PADRE profile, https://phillipsadr.com/our-team/barry-r-ostrager/ ; FedArb, https://fedarb.bonfirela.com/professionals/justice-barry-r-ostrager/
9. STB bio, https://www.stblaw.com/our-team/news/our-team/pdf/pdf/lee-a-meyerson
10. Legal 500 profile, https://legal500.com/firms/50916-simpson-thacher-bartlett-llp/global/lawyers/679521-lee-meyerson
11. Blackstone press release (2010), https://www.blackstone.com/news/press/john-finley-to-join-blackstone-as-chief-legal-officer/
12. Blackstone 8-K exhibit, https://www.sec.gov/Archives/edgar/data/0001393818/000119312510154619/dex991.htm
13. STB news, 2009-04-03, https://www.stblaw.com/about-us/news/view/2009/04/03/partners-michael-j-chepiga-and-paul-c-curnin-featured-in-amlaw-big-suits-column
14. PR Newswire (2012), https://prnewswire.com/news-releases/prominent-corporate-litigator-michael-j-chepiga-joins-blackrobe-capital-146663185.html

### Paul, Weiss, Rifkind, Wharton & Garrison (`paul_weiss`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Alfred D. Youngwood | `paul_weiss__alfred_youngwood` | Chairman (1999–2008); re-elected 2004 [S] | New York | Tax | elite [D] | band: not found | Partner 1970; first democratically elected chair (1999) [S] | Stepped down as chair at end of 2008; stayed a tax partner [S] | 1, 2, 3 |
| Theodore V. Wells Jr. | `paul_weiss__ted_wells` | Partner; co-chair of Litigation [S] | New York | White collar, trial work | elite [D] | NLJ "100 Most Influential Lawyers" (2006); NLJ "Decade's Most Influential Lawyers" (2010); NLJ winning litigator four times (to 2011) [S]; 2005 band: not found | White-collar and complex civil trials [S] | none found | 4, 5 |
| Martin Flumenbaum | `paul_weiss__martin_flumenbaum` | Partner (since 1983) [S] | New York | Commercial litigation, appellate | leading [D] | Chambers General Commercial Litigation (years not given) [S]; Benchmark National Litigation Star [S] | Chaired the Litigation Dept for 6 years [S]; NYLJ "Second Circuit Review" columnist [S] | none found | 6, 7 |
| Robert B. Schumer | `paul_weiss__robert_schumer` | Partner; head of corporate team (early 2000s) [S] | New York | M&A | elite [D] | AmLaw Dealmaker of the Year (2011) [S]; band: not found | Warner Music Group auction (37 bidders) [S; year A: 2011] | Chair, Corporate Dept (2008–2020) [S] | 8, 9 |
| Alan W. Kornberg | `paul_weiss__alan_kornberg` | Partner; chair of bankruptcy and corporate reorganisation [S] | New York | Restructuring | leading [D] | Chambers Global band 1 (year not given) [S]; NYLJ Lifetime Achievement (2021) [S] | Founded and led the restructuring practice for 30+ years [S] | none found | 10, 11 |
| Toby S. Myerson | `paul_weiss__toby_myerson` | Partner; co-head of global M&A [S] | New York | M&A, Japan / cross-border | leading [D] | band: not found | Citi / Nikko Cordial ($14bn) [S; year A: 2007–08] | Left the firm to found Longsight Strategic Advisors (end 2016; outside the window) [S] | 12, 13 |

1. Paul Weiss firm news page (2025), https://www.paulweiss.com/insights/firm-news/in-memoriam-alfred-d-youngwood-1938-2025 (professional facts only used)
2. Law.com International, 2004-05-09, https://www.law.com/international-edition/2004/05/09/paul-weiss-chairman-gets-second-term/
3. The Lawyer, 5 May 2008, https://www.thelawyer.com/issues/5-may-2008/mars-is-sweet-on-simpson-thacher/
4. Paul Weiss bio, https://www.paulweiss.com/professionals/partners-and-counsel/theodore-v-wells-jr
5. Paul Weiss award note, https://www.paulweiss.com/practices/litigation/litigation/awards-and-rankings/ted-wells-selected-as-a-winning-litigator-for-the-fourth-time-by-the-national-law-journal?id=9126
6. Paul Weiss bio, https://www.paulweiss.com/professionals/partners-and-counsel/martin-flumenbaum
7. Lawdragon, https://lawdragon.com/attorneys/martin-flumenbaum
8. Paul Weiss bio, https://paulweiss.com/professionals/partners-and-counsel/robert-b-schumer
9. Paul Weiss news, https://paulweiss.com/practices/transactional/mergers-acquisitions/news/bob-schumer-named-dealmaker-of-the-year-by-the-american-lawyer?id=8072
10. American College of Bankruptcy directory, https://www.americancollegeofbankruptcy.com/directory/alan-w-kornberg-233/
11. NYLJ, 2021-10-07, https://law.com/newyorklawjournal/2021/10/07/lifetime-achievement-alan-kornberg
12. Bloomberg Law (Oct 2016), https://news.bloomberglaw.com/business-and-practice/m-a-lawyer-leaving-paul-weiss-to-be-an-entrepreneur-at-67 (age in headline not used)
13. CPI / PYMNTS, https://www.competitionpolicyinternational.com/us-leading-ma-partner-starting-boutique-firm/

### Cleary Gottlieb Steen & Hamilton (`cleary`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mark A. Walker | `cleary__mark_walker` | Partner; elected Managing Partner May 2005 (to end 2010) [S] | New York | Sovereign and corporate finance | elite [D] | band: not found | Joined 1966; partner 1975 [S] | Succeeded as MP by Mark Leddy (1 Jan 2011); joined Lazard as senior adviser, sovereign advisory (Jun 2011) [S] | 1, 2, 3 |
| Victor I. Lewkow | `cleary__victor_lewkow` | Partner (since 1982) [S] | New York | M&A, governance, activism | elite [D] | 2005 band: not found. Chambers Senior Statesperson, NY Corporate/M&A (current) [S] | n/a (role in deals listed by aggregators not verified) | Senior counsel (2019; outside the window) [S] | 4, 5 |
| Lee C. Buchheit | `cleary__lee_buchheit` | Partner [S] | New York | Sovereign debt restructuring | elite [D] | band: not found | Uruguay (2003): two-limb collective action clause design [S, partial]; advised 23 countries over his career [S] | none in window; retired from Cleary Mar 2019 [S] | 6, 7 |
| Jonathan I. Blackman | `cleary__jonathan_blackman` | Partner (since 1985) [S] | New York | Litigation, sovereign / FSIA | leading [D] | band: not found | Counsel to Argentina in sovereign-debt litigation from 2002, incl. *Aurelius v. Argentina* (2d Cir.) and the 2013 2d Cir. argument [S] | Later relocated to London (date not found) [S] | 8, 9 |
| Mark Leddy | `cleary__mark_leddy` | Partner (since 1986) [S] | Washington, DC | Antitrust | leading [D] | band: not found | 14 years at the DOJ before joining [S] | Managing Partner (1 Jan 2011–2016) [S] | 10, 11 |
| Edward J. Rosen | `cleary__edward_rosen` | Partner [S; 2005 tenure A: recall] | New York | Derivatives, financial regulation | leading [D] | band: not found | Past member, ISDA Regulatory Advisory Committee; past FIA Board [S] | none found | 12 |

1. The Lawyer, 2 May 2005, https://www.thelawyer.com/issues/2-may-2005/cleary-gottlieb-elects-new-chief/ (blocked; via search summary)
2. Legal Week, 2005-05-11, https://www.law.com/legal-week/sites/legalweek/2005/05/11/cleary-elects-new-chief-in-uncontested-election/
3. Lazard press release (2011), https://ca.marketscreener.com/quote/stock/LAZARD-13358/news/LAZARD-LT-Mark-A-Walker-to-Join-Lazard-as-a-Senior-Advisor-to-Global-Sovereign-Advisory-Group-PD-13654723/
4. Cleary bio, https://www.clearygottlieb.com/professionals/victor-lewkow
5. Chambers USA, https://chambers.com/lawyer/victor-i-lewkow-usa-5:33079
6. Axios, 2019-02-10, https://www.axios.com/2019/02/10/the-doyen-of-sovereign-debt-lee-buchheit
7. IMF seminar paper, https://imf.org/-/media/Files/News/Seminars/2018/091318SovDebt-conference/chapter-8-the-debt-restructuring-process.ashx
8. Cleary bio, https://www.clearygottlieb.com/professionals/jonathan-i-blackman
9. Daily Business Review (Law.com), https://www.law.com/dailybusinessreview/almID/1202582479577/
10. Cleary news, https://www.clearygottlieb.com/news-and-insights/news-listing/cleary-gottlieb-elects-mark-leddy-managing-partner4
11. Legal Week, 2010-12-20, https://www.law.com/legal-week/sites/legalweek/2010/12/20/cleary-votes-in-antitrust-specialist-as-us-firms-new-managing-partner/
12. Legal 500 profile, https://legal500.com/firms/51353-cleary-gottlieb-steen-hamilton/global/lawyers/225891-edward-rosen

### Debevoise & Plimpton (`debevoise`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Martin Frederic "Rick" Evans | `debevoise__rick_evans` | Presiding Partner (Jul 1998–Jun 2011) [S] | New York | Corporate [A: recall] | elite [D] | band: not found | n/a | Retired as Presiding Partner (Jun 2011) [S] | 1, 2 |
| Michael W. Blair | `debevoise__michael_blair` | Chair / co-chair of the Corporate Department (14 years to 2011) [S] | New York | M&A | elite [D] | band: not found | Large M&A of the 1990s and 2000s [S] | Presiding Partner (1 Jul 2011) [S] | 2, 3 |
| Mary Jo White | `debevoise__mary_jo_white` | Chair of Litigation (2002–2013) [S] | New York | White collar, securities enforcement | elite [D] | band: not found | n/a | Chair, US SEC (Apr 2013–Jan 2017) [S]; returned to Debevoise as senior chair (Feb 2017) [S] | 4, 5 |
| Franci J. Blassberg | `debevoise__franci_blassberg` | Partner; co-founder and co-chair of the Private Equity Group [S] | New York | Private equity M&A | elite [D] | AmLaw Dealmaker of the Year (2006, for Hertz) [S]; Chambers USA lifetime achievement (2017) [S]; 2005 band: not found | $15bn acquisition of Hertz (2005) [S] | Later retired from partnership (date not found) [S] | 6, 7 |
| David W. Rivkin | `debevoise__david_rivkin` | Partner; co-chair of International Dispute Resolution [S] | New York | International arbitration | elite [D] | band: not found | n/a | President, International Bar Association (2015–2016) [S] | 8, 9 |

1. Debevoise bio, https://www.debevoise.com/martinevans?tab=biography
2. Debevoise news (Jun 2011), https://www.debevoise.com/news/2011/06/debevoise--plimpton-names-michael-w-blair-presid__
3. Debevoise bio, https://www.debevoise.com/michaelblair
4. SEC press release 2013-56, https://www.sec.gov/news/press/2013/2013-56.htm
5. Debevoise news (Feb 2017), https://debevoise.com/news/2017/02/mary-jo-white-returns-to-debevoise ; Wikipedia, https://en.wikipedia.org/wiki/Mary_Jo_White
6. Debevoise news (May 2017), https://debevoise.com/news/2017/05/debevoise-franci-blassberg-recognized_lifetime
7. Debevoise bio, https://www.debevoise.com/franciblassberg ; Cornell profile, https://www.as.cornell.edu/people/franci-blassberg
8. Debevoise news (Jan 2015), https://debevoise.com/news/2015/01/rivkin-iba
9. Wikipedia, https://en.wikipedia.org/wiki/David_W._Rivkin

### Shearman & Sterling (`shearman`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| David W. Heleniak | `shearman__david_heleniak` | Senior Partner (2001–May 2005) [S] | New York | M&A | elite [D] | band: not found | Joined 1974 [S] | Vice chairman, Morgan Stanley (May 2005) [S] | 1, 2 |
| Rohan S. Weerasinghe | `shearman__rohan_weerasinghe` | Partner (since 1985); Senior Partner (Jun 2005–2012) [S] | New York | Capital markets, governance | elite [D] | band: not found | n/a | General Counsel, Citigroup (Jun 2012) [S] | 3, 4, 5 |
| Creighton Condon | `shearman__creighton_condon` | Partner; co-head of global M&A [S] | New York | M&A | leading [D] | band: not found | Clients incl. Cadbury, Citigroup, Georgia-Pacific, Viacom, WebMD [S] | European Managing Partner, London (3 years, c. 2008–11) [S/D]; Senior Partner (May 2012) [S] | 6, 7 |
| Emmanuel Gaillard | `shearman__emmanuel_gaillard` | Partner; global head of international arbitration [S; 2005 role A] | Paris | International arbitration | elite [D] | band: not found | Yukos majority shareholders v. Russia, ~$50bn awards (Jul 2014) [S] | none found in window | 8, 9 |
| Clare O'Brien | `shearman__clare_obrien` | Partner [A: 2005 partnership not confirmed] | New York | M&A | strong [D] (leading from c. 2020) | AmLaw Dealmaker of the Year (2021) [S]; band: not found | Raytheon / United Technologies (2020) [S] | none found | 10 |
| Linda E. Rappaport | `shearman__linda_rappaport` | Partner (since 1985); practice group leader [S] | New York | Executive compensation, benefits | leading [D] | Chambers USA band 1, Employee Benefits & Exec Comp, NY (year not shown) [S] | n/a | Elected to the Policy Committee, 4-year term (2010) [S] | 11, 12 |

1. Law.com International, 2005-05-03, https://www.law.com/international-edition/2005/05/03/shearman-senior-partner-quits-for-morgan-stanley/
2. LawFuel, 2005-05-04, https://www.lawfuel.com/?p=4788 ; University of Michigan LSA profile, https://prod.lsa.umich.edu/lsa/faculty-staff/office-of-the-dean/dean-s-advisory-council/david-heleniak.html
3. Legal Week, 2005-06-07, https://www.law.com/legal-week/sites/legalweek/2005/06/07/shearman-confirms-securities-veteran-as-new-head/
4. PLI faculty page, https://www.pli.edu/faculty/rohan-s.-weerasinghe-i220444
5. Law.com International, 2012-04-03, https://www.law.com/international-edition/2012/04/03/shearman-senior-partner-quits-firm-to-head-up-citis-legal-team/
6. PR Newswire (May 2012), https://prnewswire.com/news-releases/creighton-condon-elected-senior-partner-at-shearman--sterling-149835485.html (fetched)
7. Law.com International, 2008-10-16, https://law.com/international-edition/2008/10/16/shearman-names-ny-ma-partner-as-new-euro-chief
8. Law.com International, 2014-07-28, https://law.com/international-edition/2014/07/28/shearman-defeats-cleary-and-baker-botts-in-50bn-yukos-arbitration
9. Kluwer Arbitration Blog, https://legalblogs.wolterskluwer.com/arbitration-blog/gaillard-and-banifatemi-on-strategy-insights-into-the-yukos-arbitration-at-harvard-law-school/
10. A&O Shearman bio, https://www.aoshearman.com/en/people/clare-obrien (fetched; NY bar 1986)
11. Chambers USA, https://chambers.com/lawyer/linda-e-rappaport-usa-5:198055
12. Law.com International, 2010-05-19, https://law.com/international-edition/2010/05/19/shearman-appoints-london-partner-to-top-level-policy-board ; Glass Hammer (2011), https://theglasshammer.com/2011/03/voice-of-experience-linda-rappaport-partner-shearman-sterling/

### Milbank, Tweed, Hadley & McCloy (`milbank`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Mel M. Immergut | `milbank__mel_immergut` | Chairman (c. 1996–2013) [D: "17 years" in Mar 2013] | New York | Litigation [A: recall] | elite [D] | band: not found | n/a | Retired as chairman (Mar 2013) [S] | 1 |
| Scott A. Edelman | `milbank__scott_edelman` | Partner; Executive Committee (since 2003) [S] | New York | Litigation and arbitration, white collar | leading [D] | band: not found | Joined 1994 after 4 years as an AUSA, SDNY [S] | Vice Chairman (2009); Chairman (Mar 2013) [S] | 1, 2 |
| Luc A. Despins | `milbank__luc_despins` | Partner; head of financial restructuring [A: recall] | New York | Restructuring | leading [A] | band: not found | Creditor-side work in large Chapter 11 cases [A] | Joined Paul Hastings (c. 2007) [A] | n/a (fetch rate-limited) |
| Dennis F. Dunne | `milbank__dennis_dunne` | Partner [A: recall] | New York | Restructuring | leading [A] | band: not found | n/a | Later chair of financial restructuring [A] | n/a |
| Paul S. Aronzon | `milbank__paul_aronzon` | Partner; restructuring co-head [A: recall] | Los Angeles | Restructuring | strong [A] | band: not found | n/a | none known | n/a |

1. Milbank news, 2013-03-18, https://milbank.com/en/news/milbank-elects-scott-a-edelman-new-chairman-succeeding-mel.html (fetched)
2. Law.com (NYLJ), https://www.law.com/newyorklawjournal/almID/1202590447749/

### Fried, Frank, Harris, Shriver & Jacobson (`fried_frank`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Valerie Ford Jacob | `fried_frank__valerie_jacob` | Co-head of corporate (from 2003) [S]; firm chair (Lawdragon gives 2003–2014; others call her the firm's longest-serving chair by 2013) [S, conflicting] | New York | Capital markets | elite [D] | band: not found | IPOs for Snapple and Royal Caribbean; Penske Automotive [S; years not given] | Senior partner (Mar 2014); joined Freshfields (Sep 2014) [S] | 1, 2, 3 |
| Justin N. Spendlove | `fried_frank__justin_spendlove` | Took "the helm" in the Jan–Feb 2005 reshuffle; one summary says firm-wide managing partner, a headline says European [S, unclear] | London [A] | Corporate [A] | leading [D] | band: not found | n/a | none found | 4, 5 |
| Paul M. Reinstein | `fried_frank__paul_reinstein` | Co-head of corporate (from 2003) [S] | New York | Corporate / M&A [A] | leading [D] | band: not found | n/a | none found | 1 |
| Arthur Fleischer Jr. | `fried_frank__arthur_fleischer` | Senior M&A partner [A: recall] | New York | M&A, takeover defence | elite [A] | band: not found | Co-author of the treatise *Takeover Defense* [A] | none known | n/a |
| Stephen Fraidin | `fried_frank__stephen_fraidin` | M&A partner [A: recall] | New York | M&A | elite [A] | band: not found | n/a | Joined Kirkland & Ellis (c. 2006) [A] | n/a |

1. Law.com International, 2003-02-25, https://law.com/international-edition/2003/02/25/fried-frank-appoints-new-joint-heads
2. Lawdragon, 2018-11-19, https://www.lawdragon.com/2018/11/19/lawyer-limelight-valerie-ford-jacob/ (fetched)
3. Law.com International, 2014-09-19, https://law.com/international-edition/2014/09/19/freshfields-continues-ny-hiring-spree-with-fried-frank-senior-partner-valerie-jacob ; Law360, https://www.law360.com/articles/518676/fried-frank-co-chair-hands-off-reins-early-to-goldman-vet
4. Legal Week, 2005-01-26, https://www.law.com/legal-week/sites/legalweek/2005/01/26/spendlove-takes-lead-in-fried-frank-shake-up/ (404 on fetch; search summary only)
5. Legal Week, 2005-02-02, https://www.law.com/legal-week/sites/legalweek/2005/02/02/fried-franks-euro-shake-up-sees-spendlove-take-the-helm/ (404 on fetch)

### Cadwalader, Wickersham & Taft (`cadwalader`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Robert O. Link Jr. | `cadwalader__robert_link` | Chairman and managing partner ("long-time incumbent") [S] | New York | Capital markets [A: recall] | elite [D] | band: not found | n/a | Gave up chairmanship (Mar 2008) and stayed MP; head of London office (Jan 2009); left the firm (c. 2009) [S] | 1, 2, 3 |
| W. Christopher White | `cadwalader__christopher_white` | Partner; chair of the global finance group [S] | New York | Finance | leading [D] | band: not found | n/a | Chairman (1 Mar 2008) [S] | 1, 2 |
| Dennis J. Block | `cadwalader__dennis_block` | Partner [A: recall; bio URL still at the firm, S] | New York | M&A, corporate governance | elite [A] | band: not found | n/a | not verified | 4 |
| Michael E. Horowitz | `cadwalader__michael_horowitz` | Partner, white collar [A: recall; Wikipedia lists him as notable staff, S] | Washington, DC | White collar, investigations | leading [A] | band: not found | n/a | Inspector General, US DOJ (2012) [A] | 5 |
| John J. Rapisardi | `cadwalader__john_rapisardi` | Partner; restructuring [A: recall] | New York | Restructuring | leading [A] | band: not found | n/a | none verified | n/a |

1. Law.com International, 2008-02-28, https://www.law.com/international-edition/2008/02/28/cadwalader-in-top-level-management-shake-up/ (fetched)
2. ABA Journal, https://www.abajournal.com/news/article/cadwalader_splits_job_of_managing_partner_and_chairman
3. Law.com International, 2009-01-15, https://www.law.com/international-edition/2009/01/15/cadwaladers-link-to-head-up-firms-city-recovery/ ; ABA Journal, https://abajournal.com/news/article/ex-cadwalader_chairman_retires_at_55_with_no_plans_to_resume_law_practice (used only for "left the firm")
4. Cadwalader profile URL (redirects to the successor firm's site), https://www.cadwalader.com/professionals/dennis-block
5. Wikipedia, https://en.wikipedia.org/wiki/Cadwalader,_Wickersham_%26_Taft (fetched; notable staff list)

### Willkie Farr & Gallagher (`willkie`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Jack H. Nusbaum | `willkie__jack_nusbaum` | Chairman (c. 1987–2009) [D: "23 years" by Jan 2010] | New York | Corporate / M&A [A: recall] | elite [D] | band: not found | n/a | Stepped down as chairman (Jan 2010) and stayed active at the firm [S] | 1, 2 |
| Thomas M. Cerabino | `willkie__thomas_cerabino` | Partner [S] | New York | M&A, corporate [A: recall] | leading [D] | band: not found | n/a | Vice chairman (Apr 2008); co-chairman (1 Jan 2010) [S] | 1, 3 |
| Steven J. Gartner | `willkie__steven_gartner` | Partner [S] | New York | Banking and finance [A: recall] | leading [D] | band: not found | n/a | Vice chairman (Apr 2008); co-chairman (1 Jan 2010) [S] | 1, 3 |
| Benito Romano | `willkie__benito_romano` | Litigation partner [A: recall]; former US Attorney, SDNY [S] | New York | White collar, litigation | leading [A] | band: not found | n/a | none known | 4 |
| Rose F. DiMartino | `willkie__rose_dimartino` | Partner, asset management [A: recall] | New York | Investment funds / '40 Act | strong [A] | band: not found | n/a | none known | n/a |

1. Willkie news, 2010-01, https://www.willkie.com/news/2010/01/willkie-announces-new-co-chairs (PDF not machine-readable; facts via search summary)
2. Willkie news, 2021-01, https://www.willkie.com/news/2021/01/willkie-mourns-loss-of-former-chairman (used only for chair tenure)
3. Law.com International, 2008-04-25, https://www.law.com/international-edition/2008/04/25/willkie-farr-eyes-succession-with-vice-chair-duo/
4. Wikipedia, https://en.wikipedia.org/wiki/Willkie_Farr_%26_Gallagher (fetched; notable people list)

### Proskauer Rose (`proskauer`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Allen I. Fagin | `proskauer__allen_fagin` | Chairman (2005–2010; maximum six-year term) [S] | New York | Labor and employment [A: recall] | elite [D] | band: not found | Led the move to Eleven Times Square (Jan 2011) [S] | Chair term ended Dec 2010 [S] | 1, 2 |
| Joseph M. Leccese | `proskauer__joseph_leccese` | Corporate partner [S] | New York | Corporate, sports transactions [A: sports] | leading [D] | band: not found | n/a | Elected chairman Oct 2010, in office Jan 2011; youngest chair in the firm's history [S] | 1, 3 |
| Bettina B. Plevan | `proskauer__bettina_plevan` | Partner (since 1980) [S] | New York | Employment litigation [A: practice not stated on page] | elite [D] | President, NYC Bar Association (2004–2006) [S]; Fellow, ACTL [S]; AmLaw Lifetime Achievement [S] | First woman on the firm's Executive Committee (two terms) [S] | ABA Board of Governors (2006–09) [S] | 4 |
| Bradley I. Ruskin | `proskauer__bradley_ruskin` | Partner; sports litigation [A: recall] | New York | Sports, commercial litigation | leading [A] | band: not found | n/a | none known | n/a |
| Edward A. Brill | `proskauer__edward_brill` | Partner, labor and employment [A: recall] | New York | Labor and employment | leading [A] | band: not found | n/a | none known | n/a |

1. Legal Week, 2010-10-05, https://www.law.com/legal-week/sites/legalweek/2010/10/05/proskauer-appoints-new-chairman-in-latest-twist-in-sjb-merger-saga/ (404 on fetch; search summary)
2. Algemeiner, 2011-01-25, https://www.algemeiner.com/2011/01/25/proskauer-rose-goes-west-mayor-celebrates-the-move/
3. Leaders magazine (2014), https://leadersmag.com/issues/2014.4_Oct/PDFs/LEADERS-Joseph-Leccese-Proskauer-Rose.pdf
4. Proskauer page, https://www.proskauer.com/professionals/bettina-plevan (fetched; professional facts only used)

### Ropes & Gray (`ropes_gray`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| R. Bradford Malt | `ropes_gray__brad_malt` | Chair (2004–2019) [S] | Boston | Private equity (founded the practice) [S] | elite [D] | band: not found | Leveraged buyouts and PE deals [S] | none (chair throughout) [S] | 1, 2 |
| David C. Chapin | `ropes_gray__david_chapin` | Partner; Policy Committee (2004–2019) [S] | Boston | Private equity [A: recall] | leading [D] | band: not found | n/a | Managing partner (2013–2019) [S] | 3 |
| Keith F. Higgins | `ropes_gray__keith_higgins` | Partner [A: recall] | Boston | Securities, corporate governance | leading [A] | band: not found | n/a | Director, SEC Division of Corporation Finance (2013) [A] | n/a |
| Jesse J. Jenner | `ropes_gray__jesse_jenner` | IP litigation partner, from Fish & Neave in the 2005 combination [A: recall; the 2005 Fish & Neave deal is S] | New York | Patent litigation | leading [A] | band: not found | n/a | none known | 4 |

1. Wikipedia, https://en.wikipedia.org/wiki/R._Bradford_Malt (fetched; political content ignored)
2. Ropes & Gray bio, https://www.ropesgray.com/biographies/m/r-bradford-malt.aspx
3. Ropes & Gray bio, https://www.ropesgray.com/en/people/c/david-c-chapin (403 on fetch; search summary)
4. Wikipedia, https://en.wikipedia.org/wiki/Ropes_%26_Gray (fetched; 2005 Fish & Neave acquisition)

### Dewey Ballantine (`dewey_ballantine`)

Practising partners only. Moves are stated without comment.

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Morton A. Pierce | `dewey_ballantine__morton_pierce` | Chairman of Dewey Ballantine; M&A dealmaker [S] | New York | M&A | elite [D] | band: not found | Wells Fargo / First Interstate (1996); Disney / Marvel (2009) [S; years A] | Joined White & Case (May 2012) [S] | 1, 2, 3 |
| Alan Wm. Wolff | `dewey_ballantine__alan_wolff` | Managing partner, Washington DC office (1991–Sep 2007) [S] | Washington, DC | International trade | elite [D] | band: not found | Founded a trade practice described as the world's largest; principal counsel in major trade cases [S] | Chairman, National Foreign Trade Council (2011) [S] | 4, 5 |
| Jeffrey L. Kessler | `dewey_ballantine__jeffrey_kessler` | Partner (joined 2003 from Weil) [S] | New York | Antitrust, sports and labour litigation | elite [D] | band: not found | NFLPA and NBPA representation; Pistorius pro bono (CAS) [S] | Joined Winston & Strawn (May 2012); co-executive chairman there (Oct 2012) [S] | 6 |
| John R. Ragosta | `dewey_ballantine__john_ragosta` | Partner, trade [A: recall] | Washington, DC | International trade | strong [A] | band: not found | n/a | none verified | n/a |

1. ABA Journal (May 2012), https://www.abajournal.com/news/article/top_ma_partner_exits_dewey_leboeuf_for_white_case_as_tally_of_2012_departed (move only)
2. White & Case bio, https://whitecase.com/people/morton-pierce
3. Chambers USA, https://chambers.com:443/lawyer/morton-pierce-usa-5:33081
4. US-China Commission bio, https://www.uscc.gov/sites/default/files/Alan%20Wolff.pdf
5. NFTC, https://www.nftc.org/nftc-welcomes-new-chairman-ambassador-alan-wolff/
6. Wikipedia, https://en.wikipedia.org/wiki/Jeffrey_L._Kessler (fetched)

### LeBoeuf, Lamb, Greene & MacRae (`leboeuf`)

Practising partners only. The firm's energy, utilities and insurance focus is sourced [S: Wikipedia]. No 2005 partner roster could be sourced before the search budget ran out.

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Ralph C. Ferrara | `leboeuf__ralph_ferrara` | Partner, securities enforcement [A: recall] | Washington, DC | Securities enforcement and litigation | leading [A] | band: not found | Former General Counsel of the SEC [A] | Joined Proskauer (2012) [A] | n/a (Wikipedia page 404) |

1. Wikipedia (firm), https://en.wikipedia.org/wiki/LeBoeuf,_Lamb,_Greene_%26_MacRae

---

### Gaps

- **Search budget.** The shared web-search budget (200 calls per turn, shared by all agents) ran out after the Shearman searches. Later work used WebFetch on known URLs only, and many of those returned 404, 403 or 429. As a result:
  - **[A]-only rows (19):** Despins, Dunne, Aronzon (Milbank); Fleischer, Fraidin (Fried Frank); Block, Horowitz, Rapisardi (Cadwalader); Romano, DiMartino (Willkie); Ruskin, Brill (Proskauer); Higgins, Jenner (Ropes & Gray); Ragosta (Dewey Ballantine); Ferrara (LeBoeuf); plus the practice cells for Evans, Immergut, Nusbaum, Fagin and Link. All of these need verifying.
  - **Below the 5-person target:** Ropes & Gray (4), Dewey Ballantine (4) and LeBoeuf (1). LeBoeuf in particular needs a fresh pass for insurance, energy and utilities partners.
- **Directory bands for 2005/2006:** none found for any of the 70. Chambers archive pages are not on the open web. The later bands given are Huebner (band 1), Mills (band 5), Rappaport (band 1, year not shown), Kornberg (Chambers Global band 1, year not shown), Lewkow (Senior Statesperson) and Truesdell (Star Individual). Chepiga's "first tier for over a decade" (to 2012) implies band 1 in 2005/06 [D], but no 2005 page was seen.
- **Leadership conflicts to resolve:**
  - **Fried Frank, 2005:** sources disagree on whether Valerie Jacob was firm chair from 2003 (Lawdragon) or co-head of corporate (Law.com, 2003). They also disagree on whether Justin Spendlove's 2005 role was firm-wide or European.
  - **Cleary, Jan–Apr 2005:** the managing partner before Mark Walker's May 2005 election was Peter Karasz. He is not included.
  - **Shearman, Jan–May 2005:** Heleniak was senior partner, then Weerasinghe from June 2005. Both rows are included.
- **Blocked or paywalled:** Legal Week / Law.com 2004–2005 archive articles (404 or teaser only), The Lawyer (403), Ropes & Gray bios (403), Paul Hastings (429), Willkie's 2010 PDF (not readable), Milbank people pages (404).

## Notable lawyers, part 3 (15 firms, January 2005 start)

Research dossier for `notables.yaml` (Partner Track, ADR PT-0013). Compiled 2026-11-19.

### Rules applied (ADR PT-0013)

- Only **public professional standing** is recorded: role in 2005, office, practice, directory listings, honours, notable matters, and professional moves from 2005 to 2015.
- **Nothing** about private life, family, health, age or birth date, death, politics, donations, misconduct, discipline, sanctions, malpractice, suits against the person, scandals, workplace conduct or criticism. Where a source mentioned any of these, it was dropped. If a lawyer was mainly known for a controversy, they were not picked.
- Clients' controversies are not attached to their lawyers. Matters are given as client, forum, year and outcome as reported.
- For firms that dissolved (Heller Ehrman 2008, Howrey 2011, Bingham 2014), only moves are recorded ("joined X (year)"). Nothing is said about causes.
- Government appointments are recorded as professional moves only, with no political characterisation.
- `standing` (elite | leading | strong) is **always [D]**: it is derived from the directory and honours evidence in the row and is not a claim about the person. There are no personality or hidden traits.

### Tag legend

- **[S]**: sourced this session (URL in the firm's footnotes).
- **[D]**: derived from sourced facts. For example, "at firm 2005" may be inferred from a tenure range, or a start date from a term length.
- **[A]**: assumed from general knowledge and not verified this session. The basis is stated. **Verify every [A] before it goes into the YAML.**
- "band: not found" means no 2005 or 2006 Chambers band was located. A Chambers USA *listing* without a band is written as "Chambers USA 2006: ranked (band not given)".

### Count

**74 people** across 15 firms. WilmerHale 7, Covington 5, Hogan & Hartson 4, Greenberg Traurig 5, DLA Piper 6, Quinn Emanuel 5, Williams & Connolly 7, Boies Schiller 5, Wilson Sonsini 4, Cooley 2, Heller Ehrman 5, Howrey 5, Bingham 4, Reed Smith 3, K&L 7.

Coverage is thinner than the target of 5–7 for Cooley, Reed Smith, Hogan & Hartson, Wilson Sonsini and Bingham, because the shared web-search budget ran out partway through. See **Gaps**.

---

### Wilmer Cutler Pickering Hale and Dorr (`wilmerhale`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| William F. Lee | `wilmerhale__william_lee` | Co-managing partner (from merger, 1 Jun 2004) [S] | Boston [S] | IP / patent trial [S] | elite [D] | Chambers USA 2006: IP, ranked (band not given) [S]; Am Law Litigator of the Year finalist 2012 [S]; Law360 IP MVP (several years to 2015) [S] | Pfizer patent settlement with generics, $2.15bn [S]; Federal Circuit wins for Nintendo and Broadcom (c.2012) [S] | Co-MP term ended 31 Dec 2011 [S] | 1,2,3,4 |
| William J. Perlstein | `wilmerhale__william_perlstein` | Co-managing partner [S] | Washington DC [S] | Bankruptcy / restructuring [S] | leading [D] | Chambers USA 2006: Bankruptcy/Restructuring, ranked (band not given) [S] | Led the 2004 Hale and Dorr / Wilmer Cutler merger [S] | Co-MP term ended 31 Dec 2011 [S] | 1,2,3 |
| Seth P. Waxman | `wilmerhale__seth_waxman` | Partner, head of appellate practice [S] | Washington DC [S] | Appellate & Supreme Court [S] | elite [D] | Chambers USA 2006: Litigation: Appellate, ranked (band not given) [S]; Am Law Lifetime Achievement (2021, later) [S] | US Solicitor General 1997–2001 [S]; 80+ Supreme Court arguments (career) [S] | Remained at firm [D] | 2,5 |
| Jamie Gorelick | `wilmerhale__jamie_gorelick` | Partner [S] | Washington DC [S] | Regulatory, white-collar, securities enforcement [S] | elite [D] | Chambers USA 2006: White-Collar Crime & Govt; Securities Enforcement, ranked (band not given) [S]; Best Lawyers 2005–2025 [S]; Am Law Lifetime Achievement 2018 [S] | Former US Deputy Attorney General [S] | Chair, Regulatory & Government Affairs Department (title date not found) [S] | 2,6 |
| William R. McLucas | `wilmerhale__william_mclucas` | Partner [S] | Washington DC [A: practice is DC-based] | Securities enforcement [S] | leading [D] | Chambers USA 2006: Financial Services Reg. Enforcement; Securities Enforcement, ranked (band not given) [S] | Former SEC Director of Enforcement [A: general knowledge] | not found | 2 |
| Charlene Barshefsky | `wilmerhale__charlene_barshefsky` | Senior international partner [A: general knowledge] | Washington DC [A] | International trade [S] | elite [D] | Chambers USA 2006: International Trade, ranked (band not given) [S] | Former US Trade Representative [A: general knowledge] | not found | 2 |
| Mark G. Borden | `wilmerhale__mark_borden` | Partner [S] | Boston [A: Hale and Dorr legacy] | Corporate/M&A, private equity / VC [S] | leading [D] | Chambers USA 2006: Corporate/M&A; PE Buyouts & VC, ranked (band not given) [S] | not found | not found | 2 |

1. "WilmerHale Completes Merger of Equals", WilmerHale, 1 Jun 2004. https://www.wilmerhale.com/en/insights/news/wilmerhale-completes-merger-of-equals-june-1-2004 ; "WilmerHale Opens California Office", 27 Jun 2005. https://www.wilmerhale.com/en/sitecore/content/whlaunch/home/research/news-publications/wilmerhale-opens-california-office-june-27-2005
2. "Chambers USA 2006 Ranks WilmerHale A Leader In 28 Practice Areas; 88 Lawyers…", WilmerHale, 2 Jun 2006 (lists names and practices, no bands). https://www.wilmerhale.com/en/insights/news/chambers-usa-2006-ranks-wilmerhale-a-leader-in-28-practice-areas-88-lawyers-at-the-top-of-their-practice-june-2-2006
3. "WilmerHale Elects Managing Partners for Three-Year Term", 22 Nov 2010 (successors from 1 Jan 2012). https://www.wilmerhale.com/insights/news/wilmerhale-elects-managing-partners-for-three-year-term-november-22-2010
4. Bill Lee news items, WilmerHale: "Bill Lee Named Litigator of the Week for a $2.15 Billion Patent Litigation Settlement" https://www.wilmerhale.com/en/insights/news/bill-lee-named-litigator-of-the-week-for-a-2-15-billion-patent-litigation-settlement ; Am Law IP Litigation Department finalist, 3 Jan 2012 https://www.wilmerhale.com/en/sitecore/content/whlaunch/home/research/news-publications/the-american-lawyer-recognizes-wilmerhale-as-ip-litigation-department-of-the-year-finalist-january-3-2012 ; Law360 IP MVP 2015 https://www.wilmerhale.com/en/insights/news/2015-11-26-bill-lee-recognized-among-law360s-ip-mvps-of-the-year-for-fifth-consecutive-year
5. Seth Waxman firm bio https://www.wilmerhale.com/en/people/seth-waxman ; Wikipedia, "Seth P. Waxman" (SG dates) https://en.wikipedia.org/wiki/Seth_P._Waxman ; "The American Lawyer Honors Seth Waxman for Lifetime Achievement", 30 Nov 2021 https://www.wilmerhale.com/en/sitecore/content/whlaunch/home/research/news-publications/20211130-the-american-lawyer-honors-seth-waxman-for-lifetime-achievement
6. Jamie Gorelick firm bio https://wilmerhale.com/Jamie_Gorelick ; "Jamie Gorelick Honored for Lifetime Achievement by The American Lawyer", 23 Aug 2018 https://www.wilmerhale.com/en/insights/news/20180823-jamie-gorelick-honored-for-lifetime-achievement-by-the-american-lawyer

---

### Covington & Burling (`covington`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Stuart C. Stock | `covington__stuart_stock` | Chairman [S] | Washington DC [D] | not found (corporate/financial institutions [A]) | leading [D] | band: not found | Chairman for six years; firm revenue and profits more than doubled [S] | Re-elected for a term from 2006 and said he would serve two years of it [S]; succeeded by Hester on 1 Jan 2008 [D]; later senior counsel [S] | 1,2 |
| Timothy C. Hester | `covington__timothy_hester` | Partner [D] | Washington DC [D] | Antitrust litigation & counselling [S] | leading [D] | band: not found | not found | Elected chairman by consensus partner vote, from 1 Jan 2008 [D]; chairman until end 2019 [S] | 1,2,3 |
| Eric H. Holder Jr. | `covington__eric_holder` | Litigation partner (2001–2009) [S] | Washington DC [S] | Complex civil & criminal litigation, internal investigations [S] | elite [D] | band: not found | Former Deputy AG and US Attorney for DC (before 2001) [S] | US Attorney General, confirmed 2 Feb 2009 [S]; returned to Covington 2015 [S] | 4,5 |
| Lanny A. Breuer | `covington__lanny_breuer` | Partner, co-chair White Collar Defense & Investigations [S] | Washington DC [S] | White-collar defence [S] | leading [D] | band: not found | not found | Assistant AG, Criminal Division, confirmed 20 Apr 2009 [S]; returned as Vice Chair of the firm, Mar 2013 [S] | 6,7 |
| Peter Barton Hutt | `covington__peter_barton_hutt` | Senior counsel [S] | Washington DC [S] | Food & drug law [S] | elite [D] | Chambers: Food & Beverages Regulatory, "Senior Statesperson" (current listing; 2005 band not found) [S]; called "dean of the food-and-drug bar" by Legal Times [S] | FDA Chief Counsel 1971–75 [S]; teaches food & drug law at Harvard since 1994 [S] | not found | 8 |

1. "Covington Poised to Grow With New Chairman", ABA Journal (election of Hester to replace Stock on 1 Jan; undated in snippet). https://abajournal.com/news/article/covington_poised_to_grow_with_new_chairman ; law.com almID 900005492531. https://www.law.com/almID/900005492531/
2. Hester firm bio https://cov.com/en/professionals/h/timothy-hester ; Stuart C. Stock, Best Lawyers https://www.bestlawyers.com/lawyers/stuart-c-stock/22439
3. "Covington Names Douglas Gibson… as New Chairman", National Law Journal, 6 Nov 2019 (Hester first named in 2008 and stepped down at end of 2019). https://law.com/nationallawjournal/2019/11/06/covington-names-douglas-gibson-top-sports-industry-lawyer-as-new-chairman ; "Covington elects Doug Gibson as chair", Nov 2019 https://www.cov.com/en/news-and-insights/news/2019/11/covington-elects-doug-gibson-as-chair
4. "Eric Holder confirmed as new US Attorney General", law.com, 3 Feb 2009. https://law.com/international-edition/2009/02/03/eric-holder-confirmed-as-new-us-attorney-general
5. "Eric Holder to Return to Covington & Burling", Bloomberg Law, 2015. https://news.bloomberglaw.com/business-and-practice/eric-holder-to-return-to-covington-burling ; NBC News, 2015 https://www.nbcnews.com/news/us-news/eric-holder-former-attorney-general-returning-covington-burling-law-firm-n387331
6. DOJ, "Lanny A. Breuer" (Criminal Division history). https://www.justice.gov/criminal/history/assistant-attorneys-general/lanny-a-breuer ; Wikipedia https://en.wikipedia.org/wiki/Lanny_A._Breuer
7. "DOJ Criminal Division Head Lanny A. Breuer Returns to Covington As Vice Chair", PR Newswire, Mar 2013. https://prnewswire.com/news-releases/doj-criminal-division-head-lanny-a-breuer-returns-to-covington-as-vice-chair-200434171.html
8. Peter Hutt firm bio https://cov.com/en/professionals/h/peter-hutt ; Chambers profile https://chambers.com/lawyer/peter-barton-hutt-usa-5:33826

---

### Hogan & Hartson (`hogan_hartson`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| J. Warren Gorrell Jr. | `hogan_hartson__warren_gorrell` | Chairman (2001–2010) [S] | Washington DC [D] | Corporate / real estate finance [A: general knowledge] | leading [D] | band: not found; Am Law "Distinguished Leader" (2018) [S] | Led the Hogan & Hartson + Lovells combination (2010) [S] | Chairman / co-CEO of Hogan Lovells from 2010 [S] | 1,2 |
| Christine A. Varney | `hogan_hartson__christine_varney` | Partner; head of Internet Practice Group (partner since 1997) [S] | Washington DC [S] | Antitrust, privacy, internet [S] | elite [D] | band: not found | Former FTC Commissioner [S] | Assistant AG, Antitrust Division, confirmed 20 Apr 2009 [S]; left DOJ 2011 for a New York firm [S] (Cravath [A: general knowledge]) | 3,4 |
| Ty Cobb | `hogan_hartson__ty_cobb` | Partner (c.29 years at firm) [S] | Washington DC [S] | White-collar, FCPA, FDA crimes [S] | leading [D] | band: not found; Lawdragon Hall of Fame (2022) [S] | Former AUSA, District of Maryland, 1981–86 [S] | Elected to firm Executive Committee [S]; left firm Jul 2017 for a government counsel post [S] | 5,6 |
| Catherine E. Stetson | `hogan_hartson__catherine_stetson` | Partner (since 2002; joined 1997) [S] | Washington DC [S] | Appellate [S] | strong [D] (rising; leading by 2010s [D]) | band: not found; Chambers ranked (current) [S] | Worked with John Roberts on *Smith v. Doe* (2003) [S] | Later co-director, Hogan Lovells Appellate Practice [S] | 7,8 |

1. "Law Firm Distinguished Leader: Warren Gorrell, Hogan Lovells", law.com / American Lawyer, 22 Aug 2018. https://www.law.com/2018/08/22/law-firm-distinguished-leader-warren-gorrell-hogan-lovells/
2. "'The best idea I had was this merger': ex-Hogan chief Gorrell…", law.com International, 2 Jan 2017. https://law.com/international-edition/2017/01/02/the-best-idea-i-had-was-this-merger-ex-hogan-chief-gorrell-on-the-lovells-tie-up-and-life-after-a-long-career-at-the-top ; Washingtonian, "House of 1000 Lawyers", Sep 2004 https://washingtonian.com/2004/09/01/house-of-1000-lawyers/
3. DOJ, "Attorney General Eric Holder Welcomes Assistant Attorneys General…", 2009. https://www.justice.gov/opa/pr/attorney-general-eric-holder-welcomes-assistant-attorneys-general-antitrust-civil-and
4. Wikipedia, "Christine A. Varney". https://en.wikipedia.org/wiki/Christine_A._Varney ; Fox Business, "Varney to step down as top antitrust official" (2011) https://www.foxbusiness.com/markets/varney-to-step-down-as-top-antitrust-official
5. "Hall of Fame Lawyer Limelight: Ty Cobb", Lawdragon, 3 Jan 2022. https://lawdragon.com/lawyer-limelights/2022-01-03-hall-of-fame-lawyer-limelight-ty-cobb
6. Wikipedia, "Ty Cobb (attorney)". https://en.wikipedia.com/wiki/Ty_Cobb_(attorney) ; BuzzFeed News, 2017 (departure date) https://www.buzzfeednews.com/article/zoetillman/trump-is-hired-a-veteran-white-collar-defense-lawyer-to
7. "Q&A With Hogan & Hartson's Cate Stetson", Law360. https://law360.com/appellate/articles/121889/q-a-with-hogan-hartson-s-cate-stetson ; "Q&A With Hogan Lovells' Cate Stetson", Law360, 2013 https://law360.com/articles/417173/q-a-with-hogan-lovells-cate-stetson
8. Chambers profile https://chambers.com/lawyer/catherine-e-stetson-usa-5:285241 ; NLJ, 18 Mar 2020 https://www.law.com/2020/03/18/hogan-lovells-partner-cate-stetson-looks-ahead-to-milestone-of-100-appellate-arguments/

---

### Greenberg Traurig (`greenberg_traurig`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Cesar L. Alvarez | `greenberg_traurig__cesar_alvarez` | CEO (1996–2009) [S] | Miami [S] | Corporate [A: general knowledge] | leading [D] | band: not found | not found | Executive Chairman from Jan 2010 [S]; later Senior Chairman [S] | 1,2,3 |
| Richard A. Rosenbaum | `greenberg_traurig__richard_rosenbaum` | President, overseeing 15 offices [S] | New York [A: general knowledge] | not found | leading [D] | band: not found | not found | CEO from Jan 2010 [S]; Executive Chairman 2016 [S] | 1,2 |
| Matthew B. Gorson | `greenberg_traurig__matthew_gorson` | Chair, national Real Estate Practice (15 years) [S]; joined 1973 [S] | Miami [S] | Real estate [S] | leading [D] | band: not found; Chambers ranked (current) [S] | Downtown Miami / Brickell development work [S] | Former firm President and Chairman; later Senior Chairman [S] | 3,4 |
| Hilarie Bass | `greenberg_traurig__hilarie_bass` | Chair, Global Litigation Practice (c.2005–2013) [D] | Miami [S] | Litigation [S] | leading [D] | band: not found | not found | Co-President 2013 [S]; ABA President (2017–18) [S]; left firm end 2018 [S] | 5,6 |
| Larry J. Hoffman | `greenberg_traurig__larry_hoffman` | Founding Chairman (co-founder 1967) [S] | Miami [S] | not found | leading [D] | band: not found | Co-founded Greenberg, Traurig and Hoffman, Miami, 1967 [S] | Held Chairman title to 2013 [S] (sources differ) | 7 |

1. "Greenberg Traurig Implements Strategic Succession", GT press release, Jan 2010. https://www.gtlaw.com/en/news/2010/1/greenberg-traurig-implements-strategic-succession
2. "Greenberg Traurig Announces Plan for Strategic Succession Starting in 2010", Jan 2009. https://www.gtlaw.com/en-gb/news/2009/1/greenberg-traurig-announces-plan-for-strategic-succession-starting-in-2010 ; "Greenberg Traurig Expands Senior Leadership Team", Jul 2015 https://www.gtlaw.com/ar/news/2015/7/greenberg-traurig-expands-senior-leadership-team
3. Chambers firm page (current leadership titles). https://www.chambers.com/office/greenberg-traurig-pa-miami-usa-5:3579
4. Gorson firm bio https://www.gtlaw.com/en/professionals/g/gorson-matthew-b ; Best Lawyers https://www.bestlawyers.com/lawyers/matthew-b-gorson/8674 ; Chambers https://www.chambers.com/lawyer/matthew-b-gorson-usa-5:157498
5. "Bye Bye Big Law: Greenberg Traurig Co-President Hilarie Bass Is Stepping Down…", American Lawyer, 12 Sep 2018. https://www.law.com/2018/09/12/bye-bye-big-law-greenberg-traurig-co-president-hilarie-bass-is-stepping-down-to-start-a-nonprofit/
6. Stanford FutureLaw 2018 speaker bio (eight years as litigation chair before co-presidency in 2013). https://conferences.law.stanford.edu/futurelaw2018/speakers/hilarie-bass/
7. Hoffman firm bio https://gtlaw.com/es/professionals/h/hoffman-larry-j ; Martindale https://www.martindale.com/attorney/larry-j-hoffman-805322/

---

### DLA Piper Rudnick Gray Cary (`dla_piper`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Francis B. "Frank" Burch Jr. | `dla_piper__frank_burch` | Co-chair (Piper Rudnick) / joint CEO of the combined firm [S] | Baltimore [A: Piper & Marbury legacy] | not found | leading [D] | band: not found | Architect of the three-way merger effective 1 Jan 2005 [S] | not found | 1,2 |
| Lee I. Miller | `dla_piper__lee_miller` | Co-chair / joint CEO [S] | Chicago [S] | not found | leading [D] | band: not found | Helped engineer the 1999 Rudnick & Wolfe / Piper & Marbury merger [S] | Global co-chair until 31 Dec 2014, then senior adviser [S] | 1,3 |
| Sir Nigel Knowles | `dla_piper__nigel_knowles` | Managing partner, DLA (1996–2015); joint CEO [S] | London / Sheffield [S] | not found | leading [D] | band: not found | Drove the 2005 three-way merger [S] | Global co-chair from 1 Jan 2015 [S]; retired 2016 [S] | 1,3,4 |
| George J. Mitchell | `dla_piper__george_mitchell` | Partner; chairman of the Global Board (2003–2008) [S] | Washington DC / New York [A] | International dispute resolution, public policy [A] | elite [D] | band: not found | Former US Senate Majority Leader [A: general knowledge] | Left firm Jan/Feb 2009 to serve as US Special Envoy for Middle East Peace (2009–2011) [S]; returned 2011 as chairman emeritus [S] | 5,6 |
| J. Terence O'Malley | `dla_piper__terence_omalley` | Chairman & CEO, Gray Cary (to merger) [S] | San Diego / Palo Alto [A] | not found | strong [D] | band: not found | Announced Piper Rudnick / Gray Cary merger, Oct 2004 [S] | not found | 7 |
| John Allcock | `dla_piper__john_allcock` | Partner; global co-chair, IP & Technology (by 2006) [S] | San Diego [S] | Patent litigation [S] | leading [D] | band: not found; Super Lawyers IP litigation 2007–2021 [S] | Defence win for Apple against patent claims of more than $500m [S] (year not found) | not found | 8,9 |

1. "DLA and Piper Rudnick Combine to Create a Leading Global Legal Services Provider" (press release, Dec 2004). https://www.ryt9.com/en/anpi/34999 ; Mondaq press release https://www.mondaq.com/pressrelease/1555/piper-rudnick-and-dla-combine-to-create-a-global-legal-services-organization-merged-firm-to-have-2700-lawyers-in-49-offices-in-18-countries
2. "Empire builder: Frank Burch, DLA Piper", ABA Journal Legal Rebels. https://www.abajournal.com/legalrebels/article/empire_builder_frank_burch_dla_piper ; "Frankly speaking…", law.com, 16 Nov 2011 https://law.com/international-edition/2011/11/16/frankly-speaking-frank-burch-lays-out-the-dla-playbook
3. "DLA Piper Announces New Global Leadership", Lawdragon, 5 Feb 2014. https://www.lawdragon.com/press-releases/2014-02-05-dla-piper-announces-new-global-leadership ; law.com, 4 Feb 2014 https://law.com/international-edition/2014/02/04/dla-chairman-angel-to-be-replaced-by-knowles-in-management-shake-up
4. "Sir Nigel Knowles retires from Sheffield law firm DLA Piper", The Star. https://www.thestar.co.uk/news/sir-nigel-knowles-retires-from-sheffield-law-firm-dla-piper-459588 ; Wikipedia, "DLA Piper" https://en.wikipedia.org/wiki/DLA_Piper
5. Mitchell firm bio https://dlapiper.com/people/m/mitchell-george-j ; Wikipedia https://en.wikipedia.org/wiki/George_J._Mitchell
6. "US senator returns to DLA Piper", Lawyers Weekly (AU), 2011. https://www.lawyersweekly.com.au/news/8598-us-senator-returns-to-dla-piper
7. "Piper Rudnick and Gray Cary Announce Merger", Mondaq press release, Oct 2004. https://www.mondaq.com/pressrelease/1519/piper-rudnick-and-gray-cary-announce-merger
8. "John Allcock", Daily Journal, Apr 2011. https://dailyjournal.com/article/281543-john-allcock ; Daily Journal https://dailyjournal.com/article/330109-john-allcock
9. LawFuel, Jul 2006 (Allcock quoted as global co-chair, IP). https://www.lawfuel.com/experienced-patent-litigator-joins-growing-patent-litigation-pract/ ; Super Lawyers profile https://profiles.superlawyers.com/california/san-diego/lawyer/john-allcock/cdecf0ae-05bf-4c63-8c4e-643e0c4dd847.html

---

### Quinn Emanuel Urquhart Oliver & Hedges (`quinn_emanuel`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| John B. Quinn | `quinn_emanuel__john_quinn` | Co-founder (1986), managing partner [S] | Los Angeles [S] | Business trial litigation [S] | elite [D] | band: not found | Mattel v. MGA (Bratz), C.D. Cal., c.$100m jury verdict for Mattel (2008) [S] (year [A]) | Remained managing partner [D] | 1,2 |
| A. William Urquhart | `quinn_emanuel__william_urquhart` | Name partner (joined 1988) [S] | Los Angeles [A] | Trial litigation [S] | leading [D] | band: not found | not found | not found | 1,2 |
| Eric J. Emanuel | `quinn_emanuel__eric_emanuel` | Co-founder (1986), name partner [S] | Los Angeles [A] | Litigation [S] | leading [D] | band: not found | not found | Retired from the firm 2019 (after 32 years) [S] | 1,3 |
| Kathleen M. Sullivan | `quinn_emanuel__kathleen_sullivan` | Partner, founding chair of national appellate practice (joined 2005) [S] | New York / Silicon Valley [A] | Appellate [S] | elite [D] | band: not found; NYLJ Lifetime Achievement (2015) [S] | Dean, Stanford Law School 1999–2004 [S] | Name partner Mar 2010 (firm renamed Quinn Emanuel Urquhart & Sullivan) [S]; retired 2025 [S] | 4,5 |
| Charles K. Verhoeven | `quinn_emanuel__charles_verhoeven` | Partner [A: at firm before 2005, partnership date not found] | San Francisco [A] | Patent trial [S] | elite [D] | band: not found; Law360 IP MVP (2012) [S], Trials MVP (2016) [S] | Lead counsel for Samsung v. Apple trial, N.D. Cal. (2012) [S]; Google defence wins, E.D. Tex. (2020) [S]; Waymo v. Uber (2018) [S] | not found | 6,7 |

1. Wikipedia, "Quinn Emanuel Urquhart & Sullivan" (founders 1986, Urquhart 1988, Sullivan name 2010). https://en.wikipedia.org/wiki/Quinn_Emanuel_Urquhart_%26_Sullivan
2. Wikipedia, "John B. Quinn". https://en.wikipedia.com/wiki/John_B._Quinn ; Quinn Emanuel law.com profile PDF https://www.quinnemanuel.com/media/gdgngofg/jbq-law-com-profile.pdf
3. "After 32 Years With Quinn, Co-Founder Emanuel Bows Out for Retirement", The Recorder, 17 Jan 2019. https://law.com/therecorder/2019/01/17/after-32-years-with-quinn-co-founder-emanuel-bows-out-for-retirement-403-28609
4. Sullivan firm bio https://www.quinnemanuel.com/attorneys/sullivan-kathleen-m/ ; "Quinn Emanuel Adds Sullivan's Name To Door", Stanford Law https://law.stanford.edu/press/quinn-emanuel-adds-sullivans-name-to-door/
5. "Lifetime Achievement: Kathleen Sullivan", NYLJ, 13 Oct 2015. https://law.com/newyorklawjournal/2015/10/13/lifetime-achievement-kathleen-sullivan ; Harvard Law historical faculty https://hls.harvard.edu/historical-faculty/kathleen-marie-sullivan-b-1955
6. "IP MVP: Quinn Emanuel's Charles Verhoeven", Law360 (2012). https://law360.com/articles/295611 ; "Trials MVP: Quinn Emanuel's Charles Verhoeven", Law360 (2016) https://law360.com/articles/874310 ; "MVP: Quinn Emanuel's Charles K. Verhoeven", Law360 (2018) https://law360.com/articles/1094307/mvp-quinn-emanuel-s-charles-k-verhoeven
7. "Litigators of the Week: the Quinn Emanuel duo who scored an East Texas win for Google", Litigation Daily, 13 Nov 2020. https://www.law.com/litigationdaily/2020/11/13/litigators-of-the-week-the-quinn-emanuel-duo-who-scored-an-east-texas-win-for-google-with-a-streamlined-defense/

---

### Williams & Connolly (`williams_connolly`)

The 2005 chairman was **not found**. The firm is run by an Executive Committee; Dane Butswinkas was chairman until 2018 and Joseph Petrosinelli after him [S, fn 1].

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Brendan V. Sullivan Jr. | `williams_connolly__brendan_sullivan` | Partner; Executive Committee member (25 years) [S] | Washington DC [S] | White-collar & trial [S] | elite [D] | Chambers USA 2014: Trial Lawyers (nationwide) "Star Individual"; White-Collar (DC) "Star Individuals" [S]; 2005 band not found; Lawdragon Hall of Fame (2015) [S] | not found this session | Remained at firm [D] | 2,3,4 |
| Robert B. Barnett | `williams_connolly__robert_barnett` | Partner (joined 1975, partner 1978); Executive Committee [S] | Washington DC [S] | Media & entertainment, book-deal negotiation [S] | elite [D] | Chambers USA 2014: Media & Entertainment (DC), ranked [S]; 2005 band not found | Represented prominent public and literary figures in publishing negotiations [S] | Remained at firm [D] | 2,5 |
| David E. Kendall | `williams_connolly__david_kendall` | Partner [A: long-time partner] | Washington DC [S] | Commercial litigation, media [S] | elite [D] | Chambers USA 2014: General Commercial Lit.; Media & Ent. (DC), ranked [S]; 2005 band not found | Personal counsel to President Clinton in the 1990s [A: general knowledge] | not found | 2 |
| Kevin T. Baine | `williams_connolly__kevin_baine` | Partner [A] | Washington DC [S] | First Amendment / media [S] | leading [D] | Chambers USA 2014: Media & Ent. (DC) "Star Individuals"; First Amendment Lit. (nationwide) [S]; 2005 band not found | not found | not found | 2 |
| John K. Villa | `williams_connolly__john_villa` | Partner [A] | Washington DC [S] | Securities lit., banking enforcement [S] | leading [D] | Chambers USA 2014: 4 listings (Gen. Commercial, Securities Lit. DC; Banking Enforcement, Securities Lit. nationwide) [S]; 2005 band not found | not found | not found | 2 |
| Douglas R. Marvin | `williams_connolly__douglas_marvin` | Partner [A] | Washington DC [S] | Products liability: pharmaceutical [S] | leading [D] | Chambers USA 2014: Products Liability & Mass Torts; Pharma Products Liability "Spotlight Table" [S]; 2005 band not found | not found | not found | 2 |
| Bruce R. Genderson | `williams_connolly__bruce_genderson` | Partner [A] | Washington DC [S] | IP litigation [S] | strong [D] | Chambers USA 2014: IP Litigation (DC), ranked [S]; 2005 band not found | not found | not found | 2 |

1. "Williams & Connolly Names New Leader After Tesla Taps Butswinkas", law.com, 7 Dec 2018. https://law.com/2018/12/07/petrosinelli-poised-to-lead-williams-connolly-after-tesla-taps-butswinkas
2. "Williams & Connolly Practice Areas and Lawyers Earn Top Rankings in the 2014 Edition of Chambers USA", W&C. https://www.wc.com/News/87879/Williams-Connolly-Practice-Areas-and-Lawyers-Earn-Top-Rankings-in-the-2014-Edition-of-Chambers-USA
3. Brendan Sullivan firm bio https://www.wc.com/Profiles/Brendan-V-Sullivan ; Chambers https://chambers.com/lawyer/brendan-v-sullivan-jr-usa-5:160499
4. "Lawdragon 2015 Hall of Fame" reprint, W&C. https://www.wc.com/portalresource/lookup/poid/Z1tOl9NPluKPtDNIqLMRVPMQiLsSw4ZDn03!/document.name=/REPRINT - Lawdragon 2015 Hall of Fame.pdf ; "Five Williams & Connolly Partners Recognized in 2015 Edition of Lawdragon" https://www.wc.com/News/87712/Five-Williams-Connolly-Partners-Recognized-in-2015-Edition-of-Lawdragon-Magazine
5. Barnett firm bio https://www.wc.com/rbarnett ; Chambers https://chambers.com/lawyer/robert-b-barnett-usa-5:160494

---

### Boies Schiller & Flexner (`boies_schiller`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| David Boies | `boies_schiller__david_boies` | Co-founder (May 1997), chairman [S] | Armonk / New York [A] | Trial & antitrust [S] | elite [D] | Time "Lawyer of the Year" 2000 [S]; band: not found | *US v. Microsoft* for DOJ, trial win upheld on liability (2001) [S]; C.V. Starr / AIG settlement (2006) [S]; American Express antitrust settlements with Visa $2.25bn and MasterCard $1.8bn (2008) [S]; *Perry v. Brown* for plaintiffs, district court win 2010, left in place by the Supreme Court 2013 [S]; *Oracle v. Google*, lead for Oracle (2012) [S] | Remained chairman [S] | 1,2 |
| Jonathan D. Schiller | `boies_schiller__jonathan_schiller` | Co-founder (1997), managing partner [S] | New York [A] | Commercial litigation, arbitration [A] | elite [D] | band: not found | not found | Chair, Columbia University Board of Trustees 2013–2018 [S] | 1 |
| Donald L. Flexner | `boies_schiller__donald_flexner` | Name partner (joined 1999 from Crowell & Moring) [S] | Washington DC / New York [A] | Antitrust litigation [A] | leading [D] | band: not found | not found | not found | 1 |
| Stephen N. Zack | `boies_schiller__stephen_zack` | Partner [S] | Miami [A] | Commercial litigation [A] | leading [D] | band: not found | not found | ABA President 2010–2011 [S] | 1 |
| William A. Isaacson | `boies_schiller__william_isaacson` | Partner [A: general knowledge, DC office] | Washington DC [A] | Antitrust [A] | leading [D] | band: not found | not found | not found | (none: assumed) |

1. Wikipedia, "Boies Schiller Flexner". https://en.wikipedia.org/wiki/Boies_Schiller_Flexner
2. Wikipedia, "David Boies" (Yale JD 1966; Cravath 1966–1997). https://en.wikipedia.org/wiki/David_Boies

---

### Wilson Sonsini Goodrich & Rosati (`wilson_sonsini`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Larry W. Sonsini | `wilson_sonsini__larry_sonsini` | Chairman; CEO until Feb 2005 (joined 1966) [S] | Palo Alto [S] | Corporate / securities, tech [S] | elite [D] | band: not found | Firm advised Google on its $2.7bn IPO (2004) [S]; firm advised Netscape IPO (1994) [S] (personal lead role [A]) | Gave up CEO role 7 Feb 2005; remained chairman [S] | 1,2,3 |
| John V. Roos | `wilson_sonsini__john_roos` | CEO from Feb 2005; previously managing director of professional services (joined 1985) [S] | Palo Alto [S] | Emerging-company corporate [S] | leading [D] | band: not found | Led representation of young companies and entrepreneurs [S] | US Ambassador to Japan (2009) [S] | 1,2 |
| Jeff Saper | `wilson_sonsini__jeff_saper` | Vice chairman from Feb 2005 (joined 1979) [S] | Palo Alto [S] | Corporate [A] | leading [D] | band: not found; described by Sonsini as "one of the firm's top rainmakers" [S] | not found | not found | 2 |
| Steven E. Bochner | `wilson_sonsini__steven_bochner` | Partner [S] | Palo Alto [A] | Corporate / securities [A] | leading [D] | band: not found | not found | CEO 2009 (succeeded Roos) [S] | 1 |

1. Wikipedia, "Wilson Sonsini Goodrich & Rosati". https://en.wikipedia.org/wiki/Wilson_Sonsini_Goodrich_%26_Rosati
2. LawFuel press release, "PALO ALTO, Calif., Feb. 7 2005…". https://www.lawfuel.com/?p=3996
3. "Wilson Sonsini veteran steps down after two-decade reign", law.com International, 9 Feb 2005. https://www.law.com/international-edition/2005/02/09/wilson-sonsini-veteran-steps-down-after-two-decade-reign/

---

### Cooley Godward (`cooley`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Stephen C. Neal | `cooley__stephen_neal` | Chairman & CEO (c.2001–2007) [S] | Palo Alto [A] | Litigation / trial [A: general knowledge] | leading [D] | band: not found | Brokered the Cooley Godward / Kronish Lieb merger (announced Aug 2006, effective 1 Oct 2006) [S] | Gave up the CEO role 1 Jan 2008; remained chairman [S] | 1,2,3 |
| Joseph W. Conroy | `cooley__joe_conroy` | Partner (joined 1999 from Hunton & Williams) [S] | Reston VA [S] | Business / corporate [S] | strong [D] | band: not found | Led opening of Cooley's Boston office [S] | CEO from 1 Jan 2008 [S] | 3 |

1. "Silicon Valley legend Cooley secures surprise NY merger", law.com International, 21 Aug 2006. https://law.com/international-edition/2006/08/21/silicon-valley-legend-cooley-secures-surprise-ny-merger
2. LawFuel merger press release, Aug 2006 (Neal as chairman & CEO). https://www.lawfuel.com/?p=10145
3. "Cooley Godward Kronish Names Joe Conroy Chief Executive Officer", press release, Nov 2007 (Marketwired, now GlobeNewswire; 403 on fetch, content from search snippet). https://www.marketwired.com/press-release/cooley-godward-kronish-names-joe-conroy-chief-executive-officer-790882.htm

---

### Heller Ehrman (`heller_ehrman`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Matthew L. Larrabee | `heller_ehrman__matthew_larrabee` | Chairman from Mar 2005 (joined 1980) [S] | San Francisco [S] | Litigation [S] | leading [D] | band: not found | not found | Moved to New York as chairman [S]; joined Dechert (2008) [S]; later JAMS neutral [S] | 1,2,3 |
| Barry Levin | `heller_ehrman__barry_levin` | Chairman (c.1999) until Mar 2005, then partner [S] | San Francisco [A] | not found | strong [D] | band: not found | not found | not found | 1 |
| E. Joshua Rosenkranz | `heller_ehrman__joshua_rosenkranz` | Partner [S] | New York [A] | Appellate / Supreme Court [S] | leading [D] | band: not found | *Merck KGaA v. Integra Lifesciences*, US Supreme Court (2005), lead litigation counsel [S] | Joined Orrick (2008) [A: general knowledge] | 4 |
| James Czaban | `heller_ehrman__james_czaban` | Partner [S] | Washington DC [A] | FDA regulatory [S] | strong [D] | band: not found | *Merck v. Integra* (2005), FDA regulatory lead [S] | not found | 4 |
| Steven Bomse | `heller_ehrman__steven_bomse` | Shareholder [S] | San Francisco [A] | Antitrust / IP litigation [A] | leading [D] | band: not found | Represented Hoffmann-La Roche against the University of California (interferon), 1983 [S] | not found | 4 |

1. "Heller Ehrman chair hands over reins", Legal Week, 16 Mar 2005. https://www.law.com/legal-week/sites/legalweek/2005/03/16/heller-ehrman-chair-hands-over-reins/ ; Daily Journal, 16 Mar 2005 (403 on fetch; content from search snippet) https://dailyjournal.com/article/284109-new-heller-ehrman-chairman-is-career-litigator-at-s-f-firm
2. "Heller's Chairman is Headed to Dechert", ABA Journal (2008). https://www.abajournal.com/news/article/hellers_chairman_is_headed_to_dechert ; "Heller Ehrman Sends Chairman to New York", ABA Journal https://abajournal.com/news/article/heller_ehrman_sends_chairman_to_new_york_in_something_of_a_trend
3. UC Law SF alumni profile, "Matthew Larrabee, Class of 1980". https://cbl.uclawsf.edu/featured-alumni/matthew-larrabee-class-of-1980/ ; JAMS https://www.jamsadr.com/neutrals/larrabee
4. Wikipedia, "Heller Ehrman". https://en.wikipedia.org/wiki/Heller_Ehrman

---

### Howrey (`howrey`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Robert F. Ruyak | `howrey__robert_ruyak` | Managing partner, CEO and chairman (2000–2011) [S] | Washington DC [S] | Litigation [A] | leading [D] | band: not found | Led the 2000 Arnold, White & Durkee combination [D] | Joined Winston & Strawn (5 Sep 2011) [S]; later opened his own boutique [S] | 1,2,3 |
| Henry C. Bunsow | `howrey__henry_bunsow` | Partner [S] | San Francisco [A] | Patent trial [A] | leading [D] | band: not found | not found | Joined Dewey & LeBoeuf (date not found; 2009 [A]) [S] | 4 |
| Margaret M. Zwisler | `howrey__margaret_zwisler` | Partner (early 2005) [S] | Washington DC [A] | Antitrust [A] | leading [D] | band: not found | not found | Joined Latham & Watkins (2005/early 2006) [S] | 4 |
| Karen L. Manos | `howrey__karen_manos` | Partner (early 2005) [S] | Washington DC [A] | Government contracts [A] | strong [D] | band: not found | not found | Joined Gibson Dunn (2005/early 2006) [S] | 4 |
| Alan M. Fisch | `howrey__alan_fisch` | Partner (early 2005) [S] | Washington DC [A] | Patent litigation [A] | strong [D] | band: not found | not found | Joined Kaye Scholer (2005/early 2006) [S] | 4 |

1. "Ex-Howrey chief Ruyak lands new role at Winston…", law.com International, 12 Sep 2011. https://law.com/international-edition/2011/09/12/ex-howrey-chief-ruyak-lands-new-role-at-winston-following-firms-fall ; ABA Journal https://www.abajournal.com/news/article/former_howrey_chairman_will_join_winstons_dc_office
2. Washingtonian, "A Tale of Two Law Firms", 8 Dec 2011 (Ruyak led from 2000). https://washingtonian.com/2011/12/08/a-tale-of-two-law-firms/
3. "Former Howrey Chair Hangs Up Shingle", Bloomberg Law. https://news.bloomberglaw.com/business-and-practice/former-howrey-chair-hangs-up-shingle ; Larson LLP bio https://www.larsonllp.com/people/robert-f-ruyak/
4. Washingtonian, "The Howrey Nosedive: A Timeline", 11 Apr 2011 (used **only** for partner names and destination firms). https://www.washingtonian.com/2011/04/11/the-howrey-nosedive-a-timeline

---

### Bingham McCutchen (`bingham`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Jay S. Zimmerman | `bingham__jay_zimmerman` | Chairman (since 1994; joined 1982); re-elected to a 4th term Oct 2005 [S] | Boston [S] | not found | leading [D] | band: not found | McCutchen Doyle merger (2002) [S]; Swidler Berlin merger, letter of intent Dec 2005 [S]; One Federal Street lease, Boston (Nov 2005) [S] | Handed over the chairmanship under a succession plan (date not found) [S] | 1,2,3,4 |
| Steven C. Browne | `bingham__steven_browne` | Partner, corporate (joined 19 Jan 2005 from Testa Hurwitz, where he chaired the Business Practice Group) [S] | Boston [S] | M&A, buyouts, PE [S] | strong [D] | band: not found | not found | not found | 5 |
| Sabin Willett | `bingham__sabin_willett` | Partner [S] | Boston [A] | Litigation / restructuring [A] | strong [D] | band: not found | Pro bono habeas representation of Uighur detainees at Guantánamo, with Susan Baker Manning (from 2005) [S] | Joined Morgan Lewis (Nov 2014) [A: most Bingham partners moved then] | 6 |
| Edwin E. Smith | `bingham__edwin_smith` | Partner [A: general knowledge] | Boston [A] | Bankruptcy / UCC finance [A] | leading [D] | band: not found | not found | Joined Morgan Lewis (2014) [A] | (none: assumed) |

1. "Bingham re-elects veteran chairman", law.com International, 19 Oct 2005. https://law.com/international-edition/2005/10/19/bingham-re-elects-veteran-chairman ; 16 Oct 2005 https://www.law.com/international-edition/2005/10/16/bingham-re-elects-veteran-head/
2. "Bingham McCutchen and Swidler Berlin Sign Letter of Intent to Merge", Mondaq press release, Dec 2005. https://www.mondaq.com/pressrelease/1704/bingham-mccutchen-and-swidler-berlin-sign-letter-of-intent-to-merge
3. LawFuel, Boston, 28 Nov 2005 (lease). https://www.lawfuel.com/?p=7874
4. BCG Search, "Bingham McCutchen Chairman Hands Over Duties Following Succession Plan". https://www.bcgsearch.com/bcgnews/900041498/Bingham-McCutchen-Chairman-Hands-Over-Duties-Following-Succession-Plan/
5. LawFuel, Boston, 19 Jan 2005, "Recent Hires, Including Chairman of Business Practice Group…". https://www.lawfuel.com/?p=3837
6. Wikipedia, "Bingham McCutchen" (also gives the 2014 destinations: Morgan Lewis took 227 partners in Nov 2014). https://en.wikipedia.org/wiki/Bingham_McCutchen

---

### Reed Smith (`reed_smith`)

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Gregory B. Jordan | `reed_smith__gregory_jordan` | Global managing partner from 1 Jan 2001; chairs Senior Management Team and Executive Committee [S] | Pittsburgh [D] | Financial-services, securities and media litigation [S] | leading [D] | band: not found; Best Lawyers since 1995 [S]; Am Law top 45 under 45 (2003) [S]; Pitt Law 1984 (cum laude), joined Reed Smith 1984 [S] | Grew the firm from 9 to 20 offices and from about 500 to about 1,400 lawyers (2001–06) [S] | Re-elected 2006 (3rd term) and 2009 (4th term) [S]; left Oct 2013 to become General Counsel of PNC [S] | 1,2,3 |
| Alexander "Sandy" Thomas | `reed_smith__sandy_thomas` | Partner; head of litigation department [A: held that role by 2013, 2005 not verified] | not found | Litigation [S] | leading [D] | band: not found | not found | Global managing partner, Oct 2013 [S] | 3 |
| Daniel I. Booker | `reed_smith__daniel_booker` | Partner; former managing partner (1990s) [A: general knowledge] | Pittsburgh [A] | not found | strong [D] | band: not found | not found | not found | (none: assumed) |

1. LawFuel, Reed Smith release, 4 Oct 2006 (Jordan's 3rd term; background). https://www.lawfuel.com/blog/contact-jamie-moss-newspros-201-493-1027-october-4-2006
2. "Reed Smith re-elects Jordan for fourth term as managing partner", Legal Week, 23 Sep 2009. https://www.law.com/legal-week/2009/09/23/reed-smith-re-elects-jordan-for-fourth-term-as-managing-partner/ ; "Reed Smith names 27 new partners", Dec 2005 https://www.reedsmith.com/es/news/2005/12/reed-smith-names-27-new-partners
3. "Reed Smith's global managing partner leaves to become PNC general counsel", ABA Journal, Oct 2013. https://abajournal.com/news/article/reed_smiths_global_managing_partner_leaves_to_become_pnc_general_counsel ; Reed Smith release https://www.reedsmith.com/de/news/2013/10/reed-smiths-greg-jordan-to-join-pnc-in-senior-exec

---

### Kirkpatrick & Lockhart Nicholson Graham (`kl_gates`)

The firm was formed on 1 Jan 2005 by the merger of K&L and Nicholson Graham & Jones. It combined with Preston Gates & Ellis in 2007 to become K&L Gates [S, fn 1–2].

| name | notable_key | role 2005 | office | practice | standing [tag] | directory / honours [tag] | notable matters [tag] | moves 2005–2015 [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|
| Peter J. Kalis | `kl_gates__peter_kalis` | Chairman of the Management Committee; chairs the Executive Committee [S] | New York / Pittsburgh [S] | Litigation (insurance coverage) [A] | leading [D] | band: not found | Led the Nicholson Graham (2005) and Preston Gates (2007) mergers [S] | Chairman & global managing partner of K&L Gates to 2016 [S] | 1,2,3 |
| Charles J. Queenan Jr. | `kl_gates__charles_queenan` | Chairman emeritus [S] (title in 2005 [A]) | Pittsburgh [A] | not found | strong [D] | band: not found | not found | not found | 3 |
| Michael Johns | `kl_gates__michael_johns` | London senior partner; Executive Committee (former chair, Nicholson Graham & Jones) [S] | London [S] | not found | strong [D] | band: not found | not found | not found | 1,4 |
| Tony Griffiths | `kl_gates__tony_griffiths` | London administrative partner (former MP, Nicholson Graham) [S] | London [S] | not found | strong [D] | band: not found | not found | not found | 1,4 |
| Janice Hartman | `kl_gates__janice_hartman` | Executive Committee member [S] | Pittsburgh [S] | not found | strong [D] | band: not found | not found | not found | 4 |
| Chuck Miller | `kl_gates__chuck_miller` | Executive Committee member [S] | Washington DC [S] | not found | strong [D] | band: not found | not found | not found | 4 |
| Paul Sweeney | `kl_gates__paul_sweeney` | Executive Committee member [S] | Los Angeles [S] | not found | strong [D] | band: not found | not found | not found | 4 |

1. "Kirkpatrick-Nicholson tie-up gets official stamp of approval", law.com International, 22 Sep 2004. https://law.com/international-edition/2004/09/22/kirkpatricknicholson-tie-up-gets-official-stamp-of-approval
2. "Kirkpatrick votes through Preston Gates tie-up", law.com International, 14 Dec 2006. https://law.com/international-edition/2006/12/14/kirkpatrick-votes-through-preston-gates-tie-up ; Daily Journal https://www.dailyjournal.com/article/335512-kirkpatrick-preston-partners-approve-k-l-gates-merger
3. Wikipedia, "K&L Gates". https://en.wikipedia.org/wiki/K%26L_Gates
4. LawFuel, "5 January 2005… New York and London" (merger completion release; names the Executive Committee). https://www.lawfuel.com/5-january-2005-lawfuel-best-for-law-news-new-york-and-london-u

---

### Gaps

- **Chambers bands for 2005/2006: none found for any person.** WilmerHale's June 2006 release gives Chambers USA 2006 *listings* without bands. Williams & Connolly's release gives the **2014** tiers ("Star Individual", "Senior Statesmen"), marked with that year. Every other cell reads "band: not found". The 2005 and 2006 Chambers USA editions are not online in searchable form. A paid Chambers archive or the firms' own 2005–06 press releases (hhlaw.com, cov.com and others, largely offline now) would close this.
- **Search budget ran out** (the shared 200-search turn limit) partway through Quinn Emanuel. After that, only direct page fetches were used (Wikipedia, firm and press pages already found). This is why the following are thin:
  - **Cooley** (2 people). Its best-known 2005 dealmakers and litigators were not identified.
  - **Reed Smith** (3; 2 of them [A]).
  - **Hogan & Hartson** (4).
  - **Wilson Sonsini** (4; no litigators).
  - **Bingham** (4; 1 [A]).
  - Practices are missing for most **K&L** Executive Committee members.
- **2005 leadership not found:** the Williams & Connolly chairman (2005).
- **[A] items to verify:** Barshefsky and McLucas (prior government roles), Gorrell (practice), Neal (practice), the Mattel verdict year, the Verhoeven partnership date, Kendall's Clinton representation, Isaacson (whole row), Rosenkranz's move to Orrick (2008), Bunsow's Dewey year, Edwin Smith (whole row), Booker (whole row), Sandy Thomas's 2005 role, Queenan's 2005 title, Varney's 2011 firm (Cravath).
- **Blocked or paywalled:** dailyjournal.com (403), the Marketwired/GlobeNewswire Cooley release (403), the Legal Week 2006 Reed Smith article (404). Law.com, Law360 and Am Law items were read only as search snippets.
- **Deliberately excluded:** Greenberg Traurig candidates known mainly for a controversy were not picked. Robert Mueller (WilmerHale) was in government in 2005 and is out of scope. Paul Tagliabue (Covington) rejoined only in 2006. Thomas Barnett (Covington) joined only in 2008. Tina Brozman (Bingham) was not picked so that no restricted event would be recorded. Several Bingham candidates were left out because they are known mainly as political figures.
- **Not recorded by rule:** deaths reported in sources (for example Hoffman, Barnett and Hutt) were left out under ADR PT-0013.


## Gaps closed (PT-M5 sub-task 1a, 2026-11-20)

The review notes' three gaps (an end year for everyone who stopped practising by 2025, a career-start year for every row, and an [S] source for every 2005 role) were closed in three research passes, one per part of this dossier. Each pass re-checked every row against firm biographies, Wikipedia, directory pages, press releases, NY attorney registrations (NYREG, part 2) and SEC EDGAR filings that name the person as counsel at the firm in 2005. Each row was then marked keep, DROP or ADD. The passes' tables, copied in full below, override the rows above where they differ, and `backend/data/notables.yaml` is built from them. The rules of ADR PT-0013 still apply: end years are years with no cause, and nothing about age, birth date, family, health, politics or controversy was recorded, even where a source carried it.

### Counts

| Part | Rows before | Kept | Dropped | Added | Rows in `notables.yaml` |
| --- | --- | --- | --- | --- | --- |
| 1 (14 firms) | 68 | 67 | 1 | 0 | 67 |
| 2 (14 firms) | 70 | 64 | 6 | 2 | 66 |
| 3 (15 firms) | 74 | 71 | 3 | 0 | 71 |
| **Total** | **212** | **202** | **10** | **2** | **204** |

The two additions are `debevoise__ralph_ferrara` (moved from LeBoeuf: he was Debevoise's Washington managing partner in January 2005 and joined LeBoeuf in November 2005) and `cadwalader__michael_gambro` (capital markets partner, sourced from a 2005 SEC filing).

### Rows dropped

- `sullivan_cromwell__penny_shane`: no [S] source for a 2005 partner role (now of counsel; no partner election found).
- `fried_frank__stephen_fraidin`: he left Fried Frank for Kirkland in May 2003; he stays in the game as `kirkland__stephen_fraidin`.
- `cadwalader__john_rapisardi`: he was at Weil Gotshal in 2005 and joined Cadwalader about 2007.
- `cadwalader__christopher_white`: no [S] source for a 2005 role (the first dated source is from 2008).
- `proskauer__edward_brill`: no [S] source for a 2005 role.
- `dewey_ballantine__john_ragosta`: no source links him to Dewey Ballantine in 2005.
- `leboeuf__ralph_ferrara`: not at LeBoeuf in January 2005; re-added as `debevoise__ralph_ferrara`.
- `quinn_emanuel__charles_verhoeven`: no [S] source for a 2005 role at the firm (bio unreachable). Re-add if a source confirms partnership before 2005.
- `heller_ehrman__steven_bomse`: the only source is from 1983 (directories spell the name "Stephen").
- `kl_gates__charles_queenan`: the only source has him Chairman Emeritus from October 2013, which contradicts the dossier's 2005 title.

### Career-start tags (204 rows in `notables.yaml`)

| Tag | Part 1 | Part 2 | Part 3 | Total |
| --- | --- | --- | --- | --- |
| [S] | 58 | 63 | 46 | 167 |
| [D] | 8 | 2 | 8 | 18 |
| [A] with a stated basis | 1 (Holzhauer) | 1 (Spendlove) | 2 (Ruyak, C. Miller) | 4 |
| [A] no source (1980, the 2005 role year minus 25) | 0 | 0 | 15 | 15 |

The 15 rows with no source are Burch, L. Miller, O'Malley and Allcock (DLA Piper), Schiller, Flexner and Isaacson (Boies Schiller), Levin and Czaban (Heller Ehrman), Bunsow and Fisch (Howrey), Browne (Bingham), and Johns, Hartman and Sweeney (K&L). Fraidin's career start uses part 2's NY admission (1965 [S]) instead of part 1's derived 1970. 68 rows carry a `left_practice` year.

### Corrections to the dossier

- **Moves re-dated:** Fraidin's move to Pershing Square is January 2015, not "c. 2014". Bunsow joined Dewey & LeBoeuf in January 2011, not 2009. Despins moved to Paul Hastings in November 2008, not "c. 2007". Ferrara moved from Debevoise to LeBoeuf in November 2005.
- **Leadership dates:** Immergut was Milbank's chairman from 1995, not "c. 1996". Leddy's term as Cleary managing partner ran to 2017 (his bio), not 2016. Queenan was Chairman Emeritus only from 2013. No source supports Griffiths' "former MP".
- **Practices:** Evans (Debevoise) is complex financial litigation and antitrust, not corporate. Immergut (Milbank) is corporate finance and investment counsel, not litigation. Link (Cadwalader) is capital markets and real estate. Fagin (Proskauer) is labour and employment. Gorrell (Hogan & Hartson) is corporate and securities. Neal (Cooley) is a trial lawyer.
- **[A] items now sourced:** Barshefsky's and McLucas's government roles, Varney's move to Cravath (2011), Kendall's impeachment-trial work, the Isaacson, Edwin Smith and Booker rows, Willett's and Smith's moves to Morgan Lewis, O'Brien's 2005 partnership, and the 2005 roles of the part 2 rows that were [A]-only (Despins, Dunne, Aronzon, Fleischer, Block, Horowitz, Romano, DiMartino, Ruskin, Higgins, Jenner).
- **Unsupported claim removed:** Dunne's "later chair of restructuring" (Milbank).

### Remaining weaknesses

- **Weak or snippet-only sources for the 2005 role:** Leite (one snippet of an undated speaker bio), Douglas and Lamm (snippets), Radke (snippet), Goldstein (snippet), Allcock (nearest source July 2006), Marvin (nearest source Chambers 2007), Levin (the Legal Week page now returns 404), Kathleen Sullivan (joined Quinn Emanuel during 2005, month not found), Bass (derived from a 2018 speaker page), and Borden's career start and end (MarketScreener only). Part 2's search-summary-only facts (Fagin's retirement, Despins' move, Romano's moves, Weerasinghe's later career, Chapin's admission, Jenner's and Ferrara's law-school years) were not read directly.
- **Status assumed:** about 25 rows are "practising" or "not found" on [A] grounds only (for example Wall, Verrier, Holzhauer, Radke, Herbert Wachtell, Rosen, DiMartino, Higgins, Ferrara, Spendlove and most DLA Piper, Howrey, Bingham and K&L rows). The engine retires them by age from `career_start`. Sheehan, Yannucci, Fahner, Jenner and Johns are known to have stopped practising, but no year was found.
- **Unresolved conflicts:** Wachtell's co-chair start (2003 or 2006; `notables.yaml` takes 2003, so Herlihy and Neff are chairs in January 2005), Fried Frank's 2005 leadership (Jacob as chair or co-head of corporate; Spendlove's title), Aquila's, Ring's, Lamm's and Verrier's start years, and Fagin's chair end year.
- **LeBoeuf has no notables** at turn 0. A 2005 EDGAR scan found only names with no standing evidence; LeBoeuf needs its own pass (energy and insurance partners).
- **Firms short of 5:** LeBoeuf 0, Cooley 2, White & Case 3, Dewey Ballantine 3, Reed Smith 3, and 4 each at Baker & McKenzie, Jones Day, Sidley, Morgan Lewis, Sullivan & Cromwell, Fried Frank, Cadwalader, Proskauer, Ropes & Gray, Hogan & Hartson, Quinn Emanuel, Wilson Sonsini, Heller Ehrman and Bingham.

### Part 1 gaps closed

Research pass 2026-11-20 for PT-M5 sub-task 1a, covering every row of `docs/research/notables-2005.md` part 1 (14 firms, 68 rows). Nothing in `/home/user/LawGame` was edited.

Rules (ADR PT-0013): public professional facts only. End-of-practice entries give a **year only**, never a cause. Moves into government or onto the bench are recorded as professional moves. `standing` is unchanged and not repeated here.

**Tags:** **[S]** stated by the cited page (fetched this session, or quoted from a search-engine snippet of that URL when the page itself was blocked; snippets are marked "snippet"). **[D]** derived, with the derivation given. **[A]** assumed, with the basis given.

**Move kinds:** lateral, government, judiciary, in_house, chair_role, of_counsel, left_practice. Format: (YYYY or YYYY-MM, kind, destination or role).

---

#### Skadden Arps (`skadden`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `skadden__robert_sheehan` | keep | Executive Partner Apr 1994 to Apr 2009 [S]: https://skadden.com/about/news-and-rankings/news/2009/04/eric-friedman-becomes-executive-partner-bob-sheeha ; third 5-year term from 2004 [S]: https://www.law.com/legal-week/sites/legalweek/2004/06/23/skadden-arps-chief-gets-third-term/ | 1969 [S] (Penn Law 1969: https://www.skadden.com/professionals/s/sheehan-robert-c) | left practice (year not found) [A] (Skadden bio lists him as "Retired Partner"; LittleSis, a secondary source, has him of counsel from 2010; no retirement date found) | (2009-04, chair_role, stepped down as Executive Partner, stayed as pro bono partner) [S]; (2010, of_counsel, Skadden) [A: LittleSis, secondary] |
| `skadden__joseph_flom` | keep | Partner from 1954 and still at the firm into the 2000s; advised InBev on Anheuser-Busch, 2008 [S]: https://en.wikipedia.org/wiki/Joe_Flom | 1948 [S] (HLS 1948: https://en.wikipedia.org/wiki/Joe_Flom) | left practice (2011) [D] (Wikipedia: his Skadden career ran until 2011) | none [S] |
| `skadden__peter_atkins` | keep | Partner from 1968 summer-associate start; "longest-tenured partner" [S]: https://www.skadden.com/about/news-and-rankings/news/2022/01/longest-tenured-partner-peter-atkins-shares-thoughts | 1968 [S] (LL.B. Harvard 1968: https://www.skadden.com/professionals/a/atkins-peter-a) | practising [S] (of counsel, M&A, at https://www.skadden.com/professionals/a/atkins-peter-a) | none (of counsel from 31 Dec 2021, outside the window) [S] |
| `skadden__eric_friedman` | keep | M&A partner; "practiced for 35 years" at Skadden before retiring at the end of 2024 [S]: https://news.bloomberglaw.com/business-and-practice/ex-skadden-chair-friedman-retiring-to-join-legal-tech-boards | 1989 [S] (J.D. Penn 1989: https://www.skadden.com/professionals/f/friedman-eric-j) | left practice (2024) [S] (Bloomberg Law, 2 Dec 2024, retiring at year end; Skadden bio "Retired Partner") | (2009-04, chair_role, Executive Partner of Skadden) [S] |
| `skadden__sheila_birnbaum` | keep | Chair of Skadden's product liability and mass torts group before moving to Quinn Emanuel [S]: https://www.dechert.com/people/b/sheila-l--birnbaum.html ; 33 years at Skadden to 2013 [S]: https://www.abajournal.com/news/article/skaddens_long-time_mass_torts_leader_jumps_to_quinn_emanuel | 1965 [S] (LL.B. NYU 1965: https://www.dechert.com/people/b/sheila-l--birnbaum.html) | practising [S] (special counsel, Dechert, same URL) | (2011, government, Special Master of the September 11th Victim Compensation Fund, held alongside practice) [S]; (2013-04, lateral, Quinn Emanuel) [S]; later moved to Dechert (year not found) |
| `skadden__jay_kasner` | keep | At Skadden since 1980 [S]: https://www.lawdragon.com/lawyer-limelights/2014-05-29-jay-kasner ; head of securities litigation, ranked by Chambers for 22 years [S]: https://www.skadden.com/professionals/k/kasner-jay-b ; partner in 2005 [D] | 1980 [S] (J.D. Boston University 1980: https://www.skadden.com/professionals/k/kasner-jay-b) | practising [S] (Partner, National Head of Securities Litigation, same URL) | none [S] |

#### Baker & McKenzie (`baker_mckenzie`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `baker_mckenzie__john_conroy` | keep | Chairman of the Executive Committee for two terms, 2004–2010 [S]: https://www.law.com/international-edition/2004/10/10/bakers-names-new-chair-as-turnover-surges/ ; https://www.bakermckenzie.com/en/in-memoriam-john-conroy | 1979 [S] (Northwestern law 1979; career began at Baker McKenzie Chicago; partner 1987: https://www.bakermckenzie.com/en/in-memoriam-john-conroy) | left practice (2024) [D] (the firm's 2024 notice still calls him a partner of the firm) | (2007-10, chair_role, re-elected Chairman) [S]; (2010, chair_role, term ended, succeeded by Eduardo Leite) [S] |
| `baker_mckenzie__christine_lagarde` | keep (low weight: leaves in month 6) | Chairman of the Global Policy Committee until June 2005 [S]: https://www.lawfuel.com/blog/chicago-3-june-2005-lawfuel-the-law-news-network-baker ; https://en.wikipedia.org/wiki/Christine_Lagarde | 1981 [S] (admitted to the Paris Bar, joined Baker & McKenzie as an associate in 1981: https://en.wikipedia.org/wiki/Christine_Lagarde) | government (2005), did not return to practice [S] (same URL) | (2005-06, government, French Minister for Foreign Trade) [S]; (2007-06, government, Minister of the Economy and Finance) [S]; (2011-07, government, IMF Managing Director) [S] |
| `baker_mckenzie__paul_rawlinson` | keep | Partner since 1996; head of the Global IP practice group 2004–2010 [S]: https://en.wikipedia.org/wiki/Paul_Rawlinson | 1985 [D] (law degree Kent 1984, then Paris XI and College of Law, Guildford; joined Baker McKenzie 1986: https://en.wikipedia.org/wiki/Paul_Rawlinson) | left practice (2019) [D] (same URL; Global Chair from Oct 2016, career ends 2019) | (2013, chair_role, London Managing Partner) [S]; (2016-10, chair_role, Global Chair; outside window) [S] |
| `baker_mckenzie__eduardo_leite` | keep (weak source) | Managing partner of the firm's four Brazil offices for seven years before becoming chairman in 2010 (so c. 2003–2010) [S, snippet; page returned 403]: https://www.as-coa.org/speakers/eduardo-leite ; São Paulo partner when named chair [S]: https://www.jdjournal.com/?p=23889 | 1980 [D] (partner since 1986 per the AS/COA bio; career start taken as about 6 years earlier) | practising [A] (the AS/COA bio, undated, calls him Chairman Emeritus and Senior Partner) | (2010, chair_role, Global Chair, to 2016) [S] |

#### Jones Day (`jones_day`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `jones_day__stephen_brogan` | keep | Managing Partner 2002–2022 [S]: https://www.jonesday.com/en/lawyers/b/stephen-brogan | 1977 [S] (J.D. Notre Dame 1977, same URL) | practising [S] (listed as Partner, Washington, same URL) | none (MP throughout; to 2022) [S] |
| `jones_day__patrick_mccartan` | keep | Joined 1960, 54 years with the firm; Managing Partner for nine years from 1993 [S]: https://www.jonesday.com/en/insights/2025/12/15-fascinating-facts-about-pat-mccartan | 1959 [S] (Notre Dame Law School 1959, same URL) | left practice (2014) [D] (54 years from 1960, same URL) | (2014, left_practice) [D] |
| `jones_day__robert_profusek` | keep | "Partner in Jones Day ... a Jones Day lawyer since 1975, except May 2000 through August 2002" (CTS Corp proxy, Mar 2005) [S]: https://www.sec.gov/Archives/edgar/data/26058/000095013705003755/c93123def14a.htm | 1975 [S] (J.D. NYU 1975: https://www.jonesday.com/en/lawyers/p/robert-profusek ; at Jones Day since 1975 per the proxy) | practising [S] (Jones Day bio, chairs global M&A practice) | none in the move kinds (Global Chair of M&A, date not found) |
| `jones_day__corinne_ball` | keep | Jones Day counsel for the Dana Corp debtors (8-K, Aug 2006) [S]: https://www.sec.gov/Archives/edgar/data/26780/000095015206006886/l21877aexv99w1.htm ; and for earlier Chapter 11 debtors (court opinion quoted in an 8-K of Mar 2005) [S]: https://www.sec.gov/Archives/edgar/data/911004/000095017205000656/ny975081.txt ; partner in 2005 [D] | 1978 [S] (J.D. George Washington 1978: https://www.jonesday.com/en/lawyers/b/corinne-ball) | practising [S] (Partner, New York, same URL) | none [S] |

#### Latham & Watkins (`latham`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `latham__robert_dell` | keep | Elected firmwide Chair and Managing Partner in 1994 (took office 1995), served to 2014 [S]: https://www.lw.com/people/robert-dell | 1977 [S] (J.D. Illinois 1977, same URL) | left practice (2014) [S] (retired Dec 2014: https://www.dailyjournal.com/article/301831-latham-names-successor-to-robert-dell ; Latham bio "Retired Partner") | (2014-12, chair_role, term ended, succeeded by William Voge) [S]; (2014-12, left_practice) [S] |
| `latham__charles_nathan` | keep | Global Co-Chair, M&A from Oct 2001 [S]: https://www.law.com/international-edition/2001/10/24/lathams-nathan-made-ma-chief/ ; Latham partner to Dec 2009 [S]: https://www.lw.com/en/people/charlesmnathan | 1965 [S] (J.D. Yale 1965; career began at Cleary 1966, same URL) | left practice (2009) [S] (retired from partnership Dec 2009, same URL; the 2012 RLM Finsbury role is not law practice) | (2009-12, left_practice) [S] |
| `latham__kirk_davenport` | keep | Signs SEC correspondence as "Kirk A. Davenport II of LATHAM & WATKINS LLP", Oct 2005 [S]: https://www.sec.gov/Archives/edgar/data/1333513/000095012305011772/filename1.txt | 1984 [S] (J.D. Michigan 1984: https://www.lw.com/en/people/kirk-davenport) | left practice (2016) [S] (retired from partnership Dec 2016, same URL) | none in 2005–2015 [S] |
| `latham__mark_gerstein` | keep | SEC letter addressed to "Mark D. Gerstein, Esq., Latham & Watkins LLP", Chicago, Nov 2005 (Georgia-Pacific tender offer) [S]: https://www.sec.gov/Archives/edgar/data/41077/000000000005059690/filename1.txt | 1984 [S] (J.D. Chicago 1984: https://www.lw.com/en/people/mark-gerstein) | left practice (2022) [S] (retired from partnership Dec 2022, same URL) | none in the move kinds (Global Co-Chair of M&A, dates not found) |
| `latham__maureen_mahoney` | keep | Rejoined Latham in 1993 after serving as Deputy Solicitor General; partner to 2015 [S]: https://www.lw.com/en/people/maureen-mahoney ; https://en.wikipedia.org/wiki/Maureen_Mahoney | 1978 [S] (J.D. Chicago 1978: https://www.lw.com/en/people/maureen-mahoney) | left practice (2015) [S] (retired from partnership Dec 2015, same URL) | (2015-12, left_practice) [S] |
| `latham__william_voge` | keep | Joined the firm in 1983; partner until he retired in March 2018 (so a partner in 2005) [S]: https://www.lw.com/en/people/william-voge | 1983 [S] (J.D. Berkeley 1983, same URL) | left practice (2018) [S] (retired from partnership Mar 2018, same URL) | (2014-07, chair_role, elected Chair and Managing Partner) [S]; (2015-01, chair_role, took office) [S] |

#### Sidley Austin Brown & Wood (`sidley`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `sidley__charles_douglas` | keep | Chair of the Management Committee 1999–2014 [S, snippet]: https://sidley.com/ja/people/d/douglas-charles-w ; named in role Jun 2005 [S, dossier source]: https://www.lawfuel.com/chicago-and-new-york-june-29-lawfuel-the-law-news-network/ | 1974 [S, snippet] (Harvard Law 1974: https://profiles.superlawyers.com/illinois/chicago/lawyer/charles-w-douglas/4ed0e4ce-b1a9-4ac6-9e28-23cd9d77fc74.html) | left practice (2023) [D] (Law360 Sept 2023 gives his Sidley tenure as nearly five decades, ending 2023: https://law360.com/articles/1720068) | (2014, chair_role, term as Management Committee Chair ended) [S] |
| `sidley__thomas_cole` | keep | Partner 1981–2016 and on the Executive Committee 1987–2014 [S]: https://www.sidley.com/en/people/c/cole-thomas-a | 1975 [S] (J.D. Chicago 1975, same URL) | left practice (2022) [S] (retired from the practice of law 31 Dec 2022, same URL) | (2013-04, chair_role, stepped down as Executive Committee chair) [S]; (2014, chair_role, left the Executive and Management Committees) [S] |
| `sidley__carter_phillips` | keep | Managing partner of the Washington office 1995–2012 [S]: https://en.wikipedia.org/wiki/Carter_G._Phillips | 1977 [S] (J.D. Northwestern 1977, same URL) | practising [S] (Partner: https://www.sidley.com/en/people/p/phillips-carter-g) | (2012, chair_role, Chair of the Executive Committee, to 2017) [S] |
| `sidley__virginia_seitz` | keep | Joined Sidley in 1998 as a partner in the Washington office [S]: https://en.wikipedia.org/wiki/Virginia_A._Seitz | 1985 [S] (J.D. Buffalo 1985, same URL) | practising [S] (current Sidley bio: https://www.sidley.com/en/people/s/seitz-virginia-a) | (2011-09, government, Assistant Attorney General, DOJ Office of Legal Counsel) [S]; (2013-12, lateral, returned to Sidley Austin) [S] |

#### White & Case (`white_case`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `white_case__duane_wall` | keep | Managing partner for terms from Apr 2000 and Apr 2004 [S]: https://history.whitecase.com/senior-leadership-chronology | 1965 [S, snippet] (J.D. Oklahoma 1965: https://www.martindale.com/attorney/duane-dennis-wall-512242/) | practising [A] (Martindale lists him as a New York partner, possibly out of date; no retirement found) | (2007-10, chair_role, MP term ended when the new chair structure began; Law.com gives 31 Mar 2008) [S]; (2008-07, chair_role, head of the bank advisory practice; Law.com Legal Week snippet) [S, snippet] |
| `white_case__hugh_verrier` | keep | Member of the management board for Wall's second term (from Apr 2004) [S]: https://history.whitecase.com/senior-leadership-chronology ; executive partner, Moscow (Aug 2007) [S]: https://law.com/international-edition/2007/08/06/verrier-to-succeed-wall-at-white-case-helm | 1983 [D] (joined W&C in 1983 per firm profile snippet, 403: https://www.whitecase.com/people/hugh-verrier ; a 2023 Law.com piece says 1985) | practising [A] (chair until Sept 2023: https://www.law.com/americanlawyer/2023/06/27/white-case-names-ny-litigation-partner-mcdevitt-as-next-leader/ ; no retirement found) | (2007-10, chair_role, Chair of the Firm) [S]; (2011-09, chair_role, re-elected) [S]; (2015-09, chair_role, re-elected) [S] |
| `white_case__carolyn_lamm` | keep | W&C counsel in ICSID matters including Fraport v. Philippines (ARB/03/25, 2003–2007) [S, snippet]: https://www.italaw.com/counsel/carolyn-lamm ; partner in 2005 [D] (on the partnership committee from Oct 2007: https://history.whitecase.com/senior-leadership-chronology) | 1973 [S] (J.D. Miami 1973: https://en.wikipedia.org/wiki/Carolyn_Lamm; one directory gives 1975) | practising [S] (Wikipedia, present tense; W&C people page lists her as Partner) | none in the move kinds (ABA President 2009–2010, held alongside practice) [S] |

#### Weil Gotshal & Manges (`weil`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `weil__stephen_dannhauser` | keep | Executive Partner 1989; Chairman 2002 to end-2012 [S]: https://www.weil.com/people/stephen-dannhauser | 1975 [S] (J.D. Brooklyn 1975; joined Weil 1975, same URL) | left practice (2015) [D] (consulting role through 2015, same URL) | (2009-12, chair_role, handed the Executive Partner role to Barry Wolf) [S]; (2012-12, chair_role, Chairman term ended) [S]; (2015, left_practice) [D] |
| `weil__ira_millstein` | keep | At Weil from 1951 for the rest of his career [S]: https://en.wikipedia.org/wiki/Ira_Millstein | 1949 [S] (J.D. Columbia 1949, same URL) | left practice (2024) [D] (same URL) | none [S] |
| `weil__marcia_goldstein` | keep | Partner from 1983 (associate 1975–83) [S, snippet]: https://lawyers.justia.com/lawyer/marcia-goldstein-1465023 ; senior restructuring partner [S]: https://www.weil.com/people/marcia-goldstein | 1975 [S] (J.D. Cornell 1975: https://www.weil.com/people/marcia-goldstein) | left practice (2020) [S] (retired from the partnership 2020, same URL) | none in the move kinds (chaired the department, dates not found) |
| `weil__howard_chatzinoff` | keep | Notices to "WEIL, GOTSHAL & MANGES LLP ... Attention: Howard Chatzinoff" in a Genworth agreement filed Mar 2005 [S]: https://www.sec.gov/Archives/edgar/data/1276520/000119312505039516/dex1057.htm ; partner in 2005 [D] | 1977 [S] (J.D. Virginia 1977: https://www.weil.com/people/howard-chatzinoff ; NY bar 1978 per Martindale snippet) | left practice (2020) [S] (retired from the partnership 2020, same URL) | none [S] |
| `weil__barry_wolf` | keep | Joined Weil as an associate in 1984, partner from 1992; co-chair of the corporate practice in 2009 [S]: https://jdjournal.com/2009/12/10/new-leadership-at-weil-gotshal | 1984 [S] (J.D. Michigan 1984: https://www.weil.com/people/barry-wolf) | practising [S] (Executive Partner, same URL) | (2009-12, chair_role, named Executive Partner) [S] |

#### Mayer Brown Rowe & Maw (`mayer_brown`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `mayer_brown__tyrone_fahner` | keep | Chairman since 1998, stepping down spring 2007 (Oct 2006 release) [S]: https://www.lawfuel.com/blog/october-3-2006-chicago-international-law-firm-mayer-brown-rowe | 1968 [S] (J.D. Wayne State 1968: https://en.wikipedia.org/wiki/Tyrone_Fahner) | left practice (year not found; no later than 2024) [A] (Wikipedia; no retirement date found) | (2007, chair_role, stepped down as Chairman) [S] |
| `mayer_brown__james_holzhauer` | keep | The firm's General Counsel (Oct 2006 release; GC 1992–2007) [S]: https://www.lawfuel.com/blog/october-3-2006-chicago-international-law-firm-mayer-brown-rowe ; https://abajournal.com/news/article/mayer_brown_chair_to_step_down | 1974 [A] (clerked for Chief Justice Burger early in his career and joined the firm in 1988 from the Chicago law faculty, per the 2006 release; J.D. year not found; MarketScreener's "Michigan 1980" does not fit) | practising [A] (to remain a partner after 2009 per ABA Journal; no later status found) | (2007-06, chair_role, Chairman, Office of the Chairman) [S]; (2009, chair_role, stepped down as chair, stayed a partner) [S] |
| `mayer_brown__kenneth_geller` | keep | Partner-in-charge of the Washington office 1995–2007 [S]: https://en.wikipedia.org/wiki/Kenneth_Geller ; also the Oct 2006 release [S] | 1971 [S] (Harvard Law 1971, same URL; clerkship 1971–72 per https://www.mayerbrown.com/en/people/g/geller-kenneth-s) | practising [S] (Senior Counsel: https://www.mayerbrown.com/en/people/g/geller-kenneth-s) | (2007-06, chair_role, Vice Chairman) [S]; (2009, chair_role, Managing Partner) [S] |
| `mayer_brown__paul_maher` | keep | "Senior Partner in London since 2003" (Oct 2006 release) [S]: https://www.lawfuel.com/blog/october-3-2006-chicago-international-law-firm-mayer-brown-rowe | 1984 [D] (in-house lawyer at ICI 1984–1990; LL.B. Bristol, year not given: https://www.gtlaw.com/en/professionals/m/maher-paul) | practising [S] (Greenberg Traurig London bio, same URL) | (2007-06, chair_role, global Vice Chairman) [S]; (2009-05, lateral, Greenberg Traurig) [S]: https://law.com/international-edition/2009/06/15/greenberg-secures-trophy-hire-of-maher-for-london-launch |
| `mayer_brown__richard_ben_veniste` | keep | Partner at Mayer Brown 2002 to Jan 2023 [S]: https://en.wikipedia.org/wiki/Richard_Ben-Veniste | 1967 [S] (LL.B. Columbia 1967, same URL) | left practice (2023) [A] (left Mayer Brown Jan 2023; no later firm found) | none [S] |

#### Morgan Lewis & Bockius (`morgan_lewis`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `morgan_lewis__francis_milone` | keep | Chair 1999–2014 [S]: https://www.morganlewis.com/documents/m/Newsletters/2016/Alumni/161877_AlumniNews-vol5/HTML/161877_Alumni-Awards_page.html ; https://www.law.com/international-edition/2004/05/10/morgan-lewis-restates-belief-in-chairman/ | 1974 [D] (joined Morgan Lewis in 1977 as an associate after "several years" at Montgomery McCracken, per the firm's history page snippet: https://anniversary.morganlewis.com/chapterthree) | left practice (2016) [D] (featured as a former chair in the 2016 Alumni News, same URL; exact year not found) | (2014-10, chair_role, term ended, succeeded by Jami McKeon) [S] |
| `morgan_lewis__jami_mckeon` | keep | Partner at the firm, which she joined in 1981 [S]: https://en.wikipedia.org/wiki/Morgan,_Lewis_%26_Bockius ; https://www.inquirer.com/philly/business/20131002_Morgan_Lewis___Bockius_names_a_woman_as_chair.html | 1981 [S] (J.D. Villanova 1981: https://www.morganlewis.com/bios/jmckeon) | practising [S] (same URL; due to retire at the end of 2026 per a 2026 firm-hosted Law360 PDF, snippet: https://www.morganlewis.com/-/media/files/news/2026/law360-incoming-outgoing-morgan-lewis-chairs-on-transition-plans.pdf) | (2013-10, chair_role, elected chair) [S]; (2014-10, chair_role, Chair) [S] |
| `morgan_lewis__philip_miscimarra` | keep | Joined Morgan Lewis in May 2005 from Seyfarth Shaw [S]: https://en.wikipedia.org/wiki/Philip_Miscimarra | 1982 [S] (J.D. Penn 1982, same URL) | practising [S] (returned to Morgan Lewis Feb 2018, same URL) | (2005-05, lateral, Morgan Lewis) [S]; (2013-08, government, NLRB member) [S] |
| `morgan_lewis__john_ring` | keep | Partner from 1999; his whole career at the firm until 2018 [S]: https://en.wikipedia.org/wiki/John_F._Ring | 1989 [S] (J.D. Catholic University 1989: https://www.morganlewis.com/bios/jring ; Wikipedia says he started as an associate in 1988) | practising [S] (rejoined Morgan Lewis Jan 2023: https://www.morganlewis.com/news/2023/01/former-nlrb-chairman-john-ring-returns-to-morgan-lewis-preeminent-us-labor-management-relations-team) | none in 2005–2015 [S] (government 2018, return 2023) |

#### Kirkland & Ellis (`kirkland`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `kirkland__thomas_yannucci` | keep | Chair of the firmwide Management Committee from 2001, three terms [S]: https://www.kirkland.com/lawyers/y/yannucci-thomas-d-pc ; quoted as chair, Jul 2005 [S]: https://www.kirkland.com/news/press-release/2005/07/leading-international-arbitration-lawyer-joins-kir | 1976 [S] (J.D. Notre Dame 1976; Ohio bar 1977: https://www.kirkland.com/lawyers/y/yannucci-thomas-d-pc) | left practice (year not found) [A] (Kirkland bio lists him as a retired partner, undated) | (2010-01, chair_role, term ended, succeeded by Jeffrey Hammes) [S] |
| `kirkland__jeffrey_hammes` | keep | Joined 1985; partner from 1991 until he retired at the end of 2019 [S]: https://www.kirkland.com/lawyers/h/hammes-jeffrey-c-pc | 1985 [S] (J.D. Northwestern 1985; Illinois bar 1985, same URL) | left practice (2019) [S] (same URL) | (2010-01, chair_role, Chair of the Management Committee; named Dec 2009) [S] |
| `kirkland__kirk_radke` | keep | Kirkland partner (New York from 1990) until he moved to Willkie in 2014 [S, snippet]: https://www.willkie.com/news/2013/12/leading-private-equity-lawyer-kirk-a-radke-joini__ | 1984 [D] (joined Kirkland as an associate in Chicago in 1984, same snippet) | practising [A] (no later status found; Willkie bio URL now 404) | (2014-02, lateral, Willkie Farr & Gallagher) [S] |
| `kirkland__richard_godfrey` | keep | At Kirkland 1979–2023 ("44-year tenure") [S]: https://www.law.com/2023/03/13/longtime-kirkland-executive-committee-leader-heads-to-quinn-emanuel/ | 1979 [D] (44-year Kirkland tenure ending 2023, same URL; law school year not found) | practising [S] (chair of Quinn Emanuel's MDL practice from 2023, same URL) | none in 2005–2015 [S] |
| `kirkland__stephen_fraidin` | keep | Kirkland & Ellis senior partner from 2003 to Jan 2015 [S]: https://pershingsquareholdings.com/wp-content/uploads/2019/12/Farewell-Release-1.20.15.pdf ; acting for the Net2Phone committee, Sept 2005 [S]: https://www.sec.gov/Archives/edgar/data/1086472/000112528205004785/b4087774_ex99-1.txt | 1970 [D] (LL.B. Yale, per the same release; Yale granted the LL.B. until 1971, so he graduated by about 1970) | practising [A] (joined Cadwalader in 2018: https://law.com/newyorklawjournal/2018/06/04/cadwalader-picks-up-ex-kirkland-partner-pershing-square-vice-chair ; the Legal 500 lists him as a Cadwalader partner; no later status found) | (2015-01, in_house, Vice Chairman, Pershing Square Capital Management) [S] (the dossier's "c. 2014" corrected) |

#### Gibson Dunn & Crutcher (`gibson_dunn`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `gibson_dunn__kenneth_doran` | keep | Chairman and Managing Partner 2002–2021 [S]: https://www.gibsondunn.com/lawyer/doran-kenneth-m/ | 1981 [S] (J.D. USC 1981, same URL) | practising [S] (Partner, Los Angeles, same URL) | none (chair throughout; to 2021) [S] |
| `gibson_dunn__theodore_olson` | keep | Returned to Gibson Dunn's Washington office in Jul 2004 [S]: https://en.wikipedia.org/wiki/Theodore_Olson ; co-chair, appellate group [S]: https://www.lawfuel.com/?p=2826 | 1965 [S] (Berkeley law 1965, Order of the Coif; joined Gibson Dunn 1965, same Wikipedia URL) | left practice (2024) [D] (same Wikipedia URL) | none [S] |
| `gibson_dunn__theodore_boutrous` | keep | Co-chair of the Appellate and Constitutional Law Group (Jul 2004 announcement) [S]: https://www.lawfuel.com/?p=2826 | 1987 [S] (J.D. San Diego 1987: https://www.gibsondunn.com/lawyer/boutrous-jr-theodore-j/) | practising [S] (same URL) | none [S] |
| `gibson_dunn__randy_mastro` | keep | Returned to Gibson Dunn in 1998, a 20-plus-year run to 2022 [S]: https://fedsoc.org/bio/randy-mastro ; https://www.law.com/therecorder/2022/08/17/randy-mastro-moves-to-king-spalding-after-more-than-20-year-run-at-gibson-dunn/ | 1981 [D] (Penn J.D., then a clerkship, then a Cravath associate from 1982: https://fedsoc.org/bio/randy-mastro) | government (2025) [S] (First Deputy Mayor of New York City Mar–Dec 2025; joined Dechert Jan 2026: https://en.wikipedia.org/wiki/Randy_Mastro) | none in 2005–2015 [S] |
| `gibson_dunn__barbara_becker` | keep | SEC letter copied to "Barbara L. Becker, Esquire, Gibson, Dunn & Crutcher LLP", Jul 2005 [S]: https://www.sec.gov/Archives/edgar/data/1268671/000000000005034687/filename1.txt ; joined from Chadbourne & Parke in 2000 [S, snippet]: https://news.bloomberglaw.com/business-and-practice/at-gibson-dunn-sebastian-fains-speed-spurs-growth-of-m-a-group | 1988 [S] (J.D. NYU 1988: https://www.gibsondunn.com/lawyer/becker-barbara-l/) | practising [S] (Chair and Managing Partner, same URL) | none in 2005–2015 (chair from 2021) [S] |
| `gibson_dunn__dennis_friedman` | keep | Joined Gibson Dunn in 2000 as co-chair of M&A [S]: https://www.gibsondunn.com/wp-content/uploads/2025/09/Friedman-Lifetime-Achievement-Honorees-Dennis-Friedman-Gibson-Dunn-and-Crutcher-New-York-Law-Journal-9.9.25.pdf ; named as counsel in a Nov 2005 filing [S]: https://www.sec.gov/Archives/edgar/data/1091667/000109166705000228/body.htm | 1969 [S] (J.D. Georgetown 1969; Shearman associate 1969: same NYLJ PDF and https://www.gibsondunn.com/lawyer/friedman-dennis-j/) | practising [S] (Partner, New York, same bio; "still an active partner", NYLJ 2025) | none [S] |

#### Sullivan & Cromwell (`sullivan_cromwell`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `sullivan_cromwell__rodgin_cohen` | keep | Chairman 1 Jul 2000 – 31 Dec 2009 [S, dossier source]: https://www.sullcrom.com/lawyers/HRodgin-Cohen ; joined S&C 1970 [S]: https://en.wikipedia.org/wiki/H._Rodgin_Cohen | 1968 [S] (LL.B. Harvard 1968: https://www.sullcrom.com/Lawyers/H-Rodgin-Cohen) | practising [S] (Senior Chair, same URL) | (2010-01, chair_role, Senior Chairman) [S] |
| `sullivan_cromwell__joseph_shenker` | keep | Partner since 1986; led global real estate; Management Committee since 1996 [S]: https://www.sullcrom.com/Lawyers/Joseph-C-Shenker | 1980 [S] (J.D. Columbia 1980; joined S&C 1980, same URL) | practising [S] (same URL) | (2006-02, chair_role, Vice Chairman) [S]; (2010-01, chair_role, Chair) [S] |
| `sullivan_cromwell__robert_giuffra` | keep | Joined S&C in 1989 after the Rehnquist clerkship [S]: https://www.sullcrom.com/Lawyers/Robert-J-Giuffra-Jr ; partner in 2005 [D] | 1987 [S] (J.D. Yale 1987, same URL) | practising [S] (same URL) | (2007, chair_role, Management Committee) [S, dossier] |
| `sullivan_cromwell__frank_aquila` | keep | Joined S&C 1983, partner 1992 [S]: https://en.wikipedia.org/wiki/Frank_J._Aquila | 1983 [S] (J.D. Brooklyn 1983: https://www.sullcrom.com/Lawyers/Francis-J-Aquila ; Wikipedia gives 1984) | practising [S] (Partner, same URL) | none [S] |
| `sullivan_cromwell__penny_shane` | **DROP** | No [S] for a 2005 partner role: the S&C bio shows S&C matters from 1999 to 2009 but gives no title or partnership year, her current title is Of Counsel, and no partner election was found (EDGAR full-text 2001–2009: 0 hits) | 1988 [S] (J.D. NYU 1988; clerkship 1988–1990: https://www.sullcrom.com/Lawyers/Penny-Shane) | practising [S] (Of Counsel, same URL) | none |

#### Cravath Swaine & Moore (`cravath`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `cravath__robert_joffe` | keep | Presiding Partner 1999–2006 [S]: https://www.cravath.com/our-story/history/presiding-partners.html | 1967 [S] (HLS class of 1967, per the Harvard Law Today item headed "Robert D. Joffe '67": https://hls.harvard.edu/today/robert-d-joffe-67-1943-2010 ; page not re-read) | left practice (2010) [D] (https://en.wikipedia.org/wiki/Robert_Joffe ; still acting for Bank of America in 2008) | (2007-01, chair_role, presiding-partner term ended, returned to full-time practice) [S] |
| `cravath__evan_chesler` | keep | Head of Litigation from 1996; elected deputy presiding partner Nov 2005 [S]: https://en.wikipedia.org/wiki/Evan_Chesler | 1975 [S] (J.D. NYU 1975: https://www.cravath.com/people/evan-r-chesler.html) | left practice (2023) [S] (retired from Cravath's Litigation Department Dec 2023, same URL) | (2005-11, chair_role, elected deputy presiding partner) [S]; (2007-01, chair_role, Presiding Partner) [S]; (2013-01, chair_role, Chairman) [S] |
| `cravath__faiza_saeed` | keep | Partner since 1998 [S]: https://www.cravath.com/people/faiza-j-saeed.html | 1991 [S] (J.D. Harvard 1991; joined Cravath 1991, same URL) | practising [S] (same URL) | none in 2005–2015 (presiding partner from 2017) [S] |
| `cravath__kris_heinzelman` | keep | Head of the Corporate Department 2002–2008 [S]: https://www.cravath.com/people/kris-f-heinzelman.html | 1976 [S] (J.D. Yale 1976; joined Cravath 1976, same URL) | left practice (2016) [S] (retired Dec 2016, same URL) | (2008, chair_role, head-of-department term ended) [S] |
| `cravath__ronald_rolfe` | keep | Partner from 1977 to his retirement in 2010 [S]: https://www.cravath.com/people/ronald-s-rolfe.html | 1969 [S] (J.D. Columbia 1969, same URL) | left practice (2010) [S] (retired Dec 2010, same URL) | (2010-12, left_practice) [S] |
| `cravath__william_rogers` | keep | Head of the London office 2001–2007 [S]: https://www.cravath.com/people/william-p-rogers-jr.html | 1978 [S] (J.D. Case Western 1978; joined Cravath 1979, same URL) | left practice (2015) [S] (retired Dec 2015, same URL) | (2007, chair_role, London head term ended) [S]; (2015-12, left_practice) [S] |

#### Wachtell Lipton Rosen & Katz (`wachtell`)

| notable_key | keep/DROP | role_2005 [S] source URL (or drop reason) | career_start YYYY [tag] (source) | status_by_2025 [tag] (source) | moves 2005–2015 normalised [tag] |
|---|---|---|---|---|---|
| `wachtell__martin_lipton` | keep | Founding partner (1965), still a partner [S]: https://en.wikipedia.org/wiki/Martin_Lipton | 1955 [S] (LL.B. NYU, after editing the Law Review 1954–55, same URL) | practising [S] (Wikipedia, present tense "works as a partner") | none in the move kinds [S] |
| `wachtell__herbert_wachtell` | keep | Co-founder (1965) [S]: https://en.wikipedia.org/wiki/Herbert_Wachtell ; Chambers Lifetime Achievement, Litigation, 2006 [S, dossier]: https://www.bestlawyers.com/lawyers/herbert-m-wachtell/27221 | 1954 [S] (LL.B. NYU 1954; AUSA from 1955, same Wikipedia URL) | practising [A] (Lawdragon lists him at WLRK, undated: https://www.lawdragon.com/lawyers/wachtell-lipton-rosen-katz/herbert-m-wachtell ; no retirement found) | none [S] |
| `wachtell__edward_herlihy` | keep | Partner since 1984 [S]: https://chambers.com/lawyer/edward-d-herlihy-usa-5:33047 ; co-chair "since 2006" [S]: https://news.bloomberglaw.com/business-and-practice/wachtell-names-new-leaders-william-savitt-and-andrew-nussbaum | 1972 [S] (J.D. George Washington 1972: https://chambers.com/lawyer/edward-d-herlihy-usa-5:33047 ; began at the SEC: https://gawkerarchives.com/550521/edward-d-herlihy) | practising [S] (Partner: https://www.lawdragon.com/lawyers/wachtell-lipton-rosen-katz/edward-d-herlihy) | (2006, chair_role, co-chairman of the Executive Committee; Lawdragon's dates imply 2003) [S, sources conflict] |
| `wachtell__daniel_neff` | keep | Joined Wachtell 1977; co-chairman of the Executive Committee for 20 years to Oct 2023 [S]: https://chambers.com/lawyer/daniel-a-neff-usa-5:139663 ; counsel to Unocal, Jun 2005 [S]: https://www.sec.gov/Archives/edgar/data/716039/000103100705000002/jun24992.htm | 1977 [S] (J.D. Columbia 1977, same Chambers URL) | practising [S] (Partner and still on the Executive Committee: https://www.lawdragon.com/lawyers/wachtell-lipton-rosen-katz/daniel-a-neff) | (2003 or 2006, chair_role, co-chairman; Lawdragon implies 2003, Bloomberg says 2006) [S, sources conflict] |
| `wachtell__theodore_mirvis` | keep | Joined Wachtell 1976, partner in the early 1980s, litigating continuously at the firm (2017 interview) [S]: https://www.lawdragon.com/2017/01/22/lawyer-limelight-ted-mirvis/ | 1976 [S] (J.D. Harvard 1976: https://www.lawdragon.com/lawyers/wachtell-lipton-rosen-katz/theodore-n-mirvis) | practising [S] (Of Counsel, Litigation Department, same URL) | none in the move kinds (later moved to of counsel, year not found) |

---

#### Method and weaknesses

- **Sources.** Pages were fetched directly where possible: firm bios (Skadden, Jones Day, Latham, Sidley, Weil, Kirkland, Gibson Dunn, S&C, Cravath, Morgan Lewis, Mayer Brown, Dechert, Greenberg Traurig), Wikipedia, Chambers and Lawdragon profiles, and press releases. **SEC EDGAR full-text search (2005 filings)** gave dated [S] evidence of 2005 firm roles for Davenport, Gerstein, Chatzinoff, Profusek, Ball (2006), Becker, D. Friedman, Fraidin and Neff. About 35 web searches were used, mainly where firm bios were blocked.
- **Blocked or missing:** wlrk.com (403; Wachtell facts came from Chambers and Lawdragon), whitecase.com and as-coa.org (403; firm-profile facts for Verrier and Leite come only from search snippets), Martindale (403; Wall's J.D. and Chatzinoff's bar year are snippets), Mayer Brown bios for Fahner, Holzhauer and Ben-Veniste (404), Willkie's Radke bio (404), Baker McKenzie's Conroy bio (404; the firm's 2024 notice was used), Law360 and most Law.com archive articles (paywalled; headlines and leads only), and Wayback (no connection).
- **Weakest rows:**
  - Leite's 2005 role rests on one search snippet of an undated speaker bio.
  - Wall, Verrier, Holzhauer, Radke, Fraidin and Herbert Wachtell have [A] "practising" status with no current source, so they should be retired by the engine's age rule.
  - Sheehan, Yannucci and Fahner are known to have stopped practising, but no year was found.
  - Holzhauer's career start is [A].
  - Ball's and Kasner's 2005 roles are bracketed: Ball by 2002–03 and 2006 filings, Kasner by "at Skadden since 1980" plus his current partnership.
- **Conflicts recorded, not resolved:**
  - Aquila's J.D.: 1983 (S&C bio) vs 1984 (Wikipedia).
  - Ring: J.D. 1989 (bio) vs associate from 1988 (Wikipedia).
  - Verrier joined W&C in 1983 (firm) vs 1985 (Law.com).
  - Lamm's J.D.: 1973 (Wikipedia) vs 1975 (one directory).
  - Herlihy and Neff's co-chair start: 2003 vs 2006.
  - Fraidin's move to Pershing Square: the dossier's "c. 2014" is corrected to Jan 2015 [S].
- **Derived end years:** for Flom, Millstein, Olson, Joffe, Conroy, Douglas, Rawlinson and McCartan the year is the end of the person's documented career in the cited source. No cause is recorded anywhere, as ADR PT-0013 requires.
- **Excluded content:** sources for several rows mention ages, birth dates, family, health, politics or the circumstances of a departure. None of it was recorded. Search results and filings that held personal financial data (for example a shareholder list in an SEC filing) were not used.
- **One DROP:** `sullivan_cromwell__penny_shane`. She can be reinstated if an S&C partner-election notice or a 2005 filing naming her as an S&C partner is found.

### Part 2 gaps closed

Compiled 2026-11-20 for `docs/research/notables-2005.md`, part 2 (14 New York and Boston rivals). Research only. No file in the repository was changed.

**Tags.** [S] = a page fetched or a search result read this session states it. [D] = derived from [S] facts (the method is given). [A] = assumed (the basis is given).

**Shared sources** (cited by key in the tables):

- **NYREG** = NYS Attorney Registrations, NY Unified Court System open data: `https://data.ny.gov/resource/eqw2-r5nb.json?last_name=<SURNAME>`. Only the year of NY admission and the current employer field are used. NY admission year is the career-start year unless a JD year was found.
- **EDGAR** = an SEC filing from the year shown, naming the person as counsel at the firm (a notice copy, a signed letter or an opinion). The URL is given in the row.
- **D#n** = source *n* of that firm's list in the existing dossier (`notables-2005.md`, part 2).

**Moves format.** (YYYY or YYYY-MM, kind, destination). The kinds are lateral, government, judiciary, in_house, chair_role, of_counsel and left_practice. A firm merger is written as "lateral (X, by merger)". A move outside 2005–2015 is shown only when it sets the status.

**Totals.** 64 rows kept, 6 dropped, 2 added, giving 66 rows. Career start: 63 [S], 2 [D], 1 [A].

---

#### Davis Polk & Wardwell (`davis_polk`) — 6 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `davis_polk__john_ettinger` | keep | John R. Ettinger | MP 1999–2011, partner 1986–2011: DP bio https://www.davispolk.com/lawyers/john-ettinger ; D#3 | 1979 [S] (NYREG: Harvard) | practising [S] (DP bio: senior counsel after 25 years as a partner) | (2011-04, chair_role, stepped down as MP) [S]; (2011, of_counsel, senior counsel at Davis Polk) [S] |
| `davis_polk__phillip_mills` | keep | Phillip R. Mills | EDGAR 2005-01, DP partner on a Cinemark notice: https://www.sec.gov/Archives/edgar/data/1173463/000095013405000086/d21358exv10w1.txt | 1987 [S] (NYREG: Univ. of Queensland) | practising [S] (DP bio https://www.davispolk.com/lawyers/phillip-mills : senior counsel after 32 years as a partner; EDGAR 2025-04) | none |
| `davis_polk__marshall_huebner` | keep | Marshall S. Huebner | EDGAR 2005-09, DP counsel in the Delta filing: https://www.sec.gov/Archives/edgar/data/27904/000116796605001353/ex99-1.txt | 1994 [S] (NYREG; clerkship 1993–94 per DP bio) | practising [S] (DP bio https://www.davispolk.com/lawyers/marshall-huebner ; EDGAR 2025-08) | none dated (co-head of restructuring later, date not found) |
| `davis_polk__denis_mcinerney` | keep | Denis J. McInerney | DP bio: "Partner, Davis Polk, 1997-2010 and 2014-2019": https://www.davispolk.com/lawyers/denis-mcinerney | 1985 [S] (NYREG; clerkship 1984–86 per DP bio) | practising [S] (DP bio: senior counsel 2023–present) | (2010-01, government, DOJ Criminal Division Fraud Section chief) [S]; (2013, government, Deputy Assistant AG) [S]; (2014-10, lateral, Davis Polk, return) [S] |
| `davis_polk__carey_dunne` | keep | Carey R. Dunne | At DP from 1987 for about 30 years; litigation chair; management committee: https://en.wikipedia.org/wiki/Carey_Dunne | 1984 [S] (Wikipedia: Harvard JD 1984; NYREG 1985) | practising [S] (NYREG: Free and Fair Litigation Group) | (2012-05, chair_role, president of the NYC Bar Association) [S, D#9]. Outside the window: (2017-01, government, Manhattan DA's office general counsel); returned to private practice in 2022 [S, Wikipedia] |
| `davis_polk__richard_truesdell` | keep | Richard D. Truesdell Jr. | EDGAR 2005-06, a letter signed by Truesdell at DP for Marsh & McLennan: https://www.sec.gov/Archives/edgar/data/62709/000095010305001611/filename1.htm | 1987 [S] (NYREG: Columbia) | practising [S] (DP bio; EDGAR 2025-12) | none |

#### Simpson Thacher & Bartlett (`simpson_thacher`) — 7 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `simpson_thacher__philip_ruegger` | keep | Philip T. Ruegger III | Chair of the Executive Committee from 2004 until he retired in 2013. Travelers DEF 14A (2015): https://www.sec.gov/Archives/edgar/data/86312/000110465915025716/a15-1593_2def14a.htm | 1974 [S] (same filing: joined STB in 1974; NYREG 1975) | left practice (2013) [S] (same filing) | (2013, left_practice) [S]. The chair passed to Dougherty in Mar 2013 [S, D#2] |
| `simpson_thacher__richard_beattie` | keep | Richard I. Beattie | STB bio (exec committee chair 1991–2004, later Senior Chairman): https://www.stblaw.com/our-team/partners/richard-i-beattie ; EDGAR 2005-03 (Fox, STB): https://www.sec.gov/Archives/edgar/data/1068002/000119312505056869/dsc14d9a.htm | 1968 [S] (STB bio: Penn LLB 1968; NY 1969) | left practice (2025) [D] (the STB bio page was changed in mid-2025) | none dated (Senior Chairman, date not found) |
| `simpson_thacher__casey_cogut` | keep | Charles I. "Casey" Cogut | EDGAR 2005-03 (Fox, STB): the URL above | 1973 [S] (STB page: Penn JD 1973; Lawdragon: "practicing since 1973") | left practice (2013) [S] (STB: "Partner ... until his retirement in 2013"; https://www.stblaw.com/our-team/senior-counsel/charles-i-cogut ) | (2012, of_counsel, senior M&A counsel) [S, D#5]; (2013, left_practice) [S] |
| `simpson_thacher__barry_ostrager` | keep | Barry R. Ostrager | Head of Litigation [S, D#7]. FedArb profile: "40 years at Simpson Thacher" before the bench: https://fedarb.bonfirela.com/professionals/justice-barry-r-ostrager/ | 1972 [S] (FedArb: NYU JD 1972) | practising [S] (arbitrator and mediator; NYREG: Barry R. Ostrager ADR LLC) | (2015, judiciary, NY Supreme Court Commercial Division) [D: "8½ years" to 31 Dec 2023]. Outside the window: back in practice as a neutral (2024) [S] |
| `simpson_thacher__lee_meyerson` | keep | Lee A. Meyerson | EDGAR 2005-01 (TD/Banknorth, STB): https://www.sec.gov/Archives/edgar/data/947263/000095012305000249/y01239fffv4za.htm | 1981 [S] (STB bio: NYU JD 1981, joined STB 1981) https://www.stblaw.com/our-team/partners/lee-a-meyerson | practising [S] (STB bio; EDGAR 2025-04) | none |
| `simpson_thacher__john_finley` | keep | John G. Finley | EDGAR 2005-03 (Kmart/Sears S-4, STB): https://www.sec.gov/Archives/edgar/data/1310067/000104746905007549/a2154352zs-4mef.htm | 1982 [S] (NYREG: Harvard) | practising, in-house [S] (NYREG: Blackstone) | (2010-09, in_house, Blackstone chief legal officer) [S, D#11] |
| `simpson_thacher__michael_chepiga` | keep | Michael J. Chepiga | STB partner; ranked by Chambers in 2005 [S, PR Newswire 2012]: https://prnewswire.com/news-releases/prominent-corporate-litigator-michael-j-chepiga-joins-blackrobe-capital-146663185.html | 1980 [S] (NYREG; clerkships 1979–81 per PR Newswire) | left practice (2012) [D] (retired from the partnership on 1 Jan 2012; full-time managing director at a litigation-finance firm from Apr 2012) | (2012-01, left_practice) [S] |

#### Paul, Weiss (`paul_weiss`) — 6 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `paul_weiss__alfred_youngwood` | keep | Alfred D. Youngwood | Chairman 1999–2008 [S, D#1, D#2] | 1962 [S] (D#1: Harvard Law 1962; joined PW 1964; NYREG 1962) | left practice (2025) [D] (D#1, Sep 2025: at the firm for his whole career) | (2008-12, chair_role, stepped down as chairman; stayed a tax partner) [S] |
| `paul_weiss__ted_wells` | keep | Theodore V. Wells Jr. | Co-chair of Litigation [S, D#4]; PW bio https://www.paulweiss.com/professionals/partners-and-counsel/theodore-v-wells-jr | 1976 [S] (PW bio: Harvard JD 1976) | practising [S] (PW bio) | none |
| `paul_weiss__martin_flumenbaum` | keep | Martin Flumenbaum | Partner since 1983 [S, D#6] | 1974 [S] (PW bio: Harvard JD 1974) https://www.paulweiss.com/professionals/partners-and-counsel/martin-flumenbaum | practising [S] (PW bio: of counsel) | none dated (of counsel, date not found) |
| `paul_weiss__robert_schumer` | keep | Robert B. Schumer | EDGAR 2005-04 (Time Warner/Adelphia, PW): https://www.sec.gov/Archives/edgar/data/1105705/000095014405004379/g94681exv99w10.txt | 1982 [S] (PW bio: Columbia JD 1982) https://paulweiss.com/professionals/partners-and-counsel/robert-b-schumer | practising [S] (PW bio; EDGAR 2025-08) | (2008, chair_role, chair of the Corporate Department, to 2020) [S] |
| `paul_weiss__alan_kornberg` | keep | Alan W. Kornberg | EDGAR 2005-09 (Friedman's, PW): https://www.sec.gov/Archives/edgar/data/911004/000095017205003153/ex99order.txt ; ACB directory "Partner, Paul, Weiss (1990-)": https://www.americancollegeofbankruptcy.com/directory/alan-w-kornberg-233/ | 1977 [S] (ACB: NYU JD 1977) | practising, in-house [S] (NYREG: Marsh McLennan; ACB listing per search). Year of the move not found | none in the window |
| `paul_weiss__toby_myerson` | keep | Toby S. Myerson | EDGAR 2005-06 (Sprint/Nextel, PW): https://www.sec.gov/Archives/edgar/data/101830/000119312505123260/filename62.htm | 1977 [S] (NYREG: Harvard) | left practice (2016) [D] (left PW at the end of 2016 to found an advisory firm [S, D#12, D#13]; NYREG: Longsight Strategic Advisors) | none in the window |

#### Cleary Gottlieb (`cleary`) — 6 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `cleary__mark_walker` | keep | Mark A. Walker | MP from May 2005 [S, D#2]; EDGAR 2005-09 (Republic of Korea, Cleary): https://www.sec.gov/Archives/edgar/data/873465/000119312505194598/dposam.htm | 1966 [S] (joined Cleary 1966, D#1/D#2; NYREG 1967) | left practice (2011) [D] (senior adviser at Lazard from Jun 2011 [S, D#3]; NYREG: own advisory LLC) | (2005-05, chair_role, managing partner) [S]; (2011-01, chair_role, MP term ended) [S]; (2011-06, left_practice, Lazard) [S] |
| `cleary__victor_lewkow` | keep | Victor I. Lewkow | EDGAR 2005-11 (Capital One opinion, "a Partner"): https://www.sec.gov/Archives/edgar/data/927628/000090342305000951/caponeex5-1_1121.htm | 1973 [S] (Cleary bio: Penn JD 1973) https://www.clearygottlieb.com/professionals/victor-lewkow | practising [S] (Cleary bio: senior counsel 2019; partner emeritus 2026) | none in the window |
| `cleary__lee_buchheit` | keep | Lee C. Buchheit | EDGAR 2004-03 (Uruguay opinion signed "Lee C. Buchheit, a Partner"): https://www.sec.gov/Archives/edgar/data/102385/000095012304003482/y95339exv99wfw5.htm ; D#6 | 1985 [S] (NYREG; possibly admitted elsewhere earlier) | left practice (2019) [S] (retired from Cleary Mar 2019, D#6) | none in the window |
| `cleary__jonathan_blackman` | keep | Jonathan I. Blackman | Cleary bio: joined 1977, partner 1985: https://www.clearygottlieb.com/professionals/jonathan-i-blackman | 1977 [S] (Cleary bio: Harvard JD 1977) | practising [S] (Cleary bio: senior counsel since 2020) | none of the listed kinds (resident in NY and London from 2009 [S]) |
| `cleary__mark_leddy` | keep | Mark Leddy | Cleary bio: joined as a partner in 1986: https://www.clearygottlieb.com/professionals/mark-leddy | 1971 [S] (Cleary bio: Boston College JD 1971; DOJ from 1972) | practising [S] (Cleary bio: senior counsel) | (2011-01, chair_role, managing partner to 2017) [S] (the bio gives 2017, not D#10's 2016) |
| `cleary__edward_rosen` | keep | Edward J. Rosen | EDGAR 2005-10 (iShares GSCI S-1, Cleary): https://www.sec.gov/Archives/edgar/data/1332174/000119312505211303/filename3.htm | 1983 [S] (NYREG: Columbia) | practising [A] (latest EDGAR mention 2018; Cleary bio no longer online by 2026; no end year found) | none |

#### Debevoise & Plimpton (`debevoise`) — 5 kept, 1 added

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `debevoise__rick_evans` | keep | Martin F. "Rick" Evans (correct the practice to complex financial litigation and antitrust [S]; it was "Corporate [A]") | Presiding Partner Jul 1998–Jun 2011: https://www.debevoise.com/martinevans?tab=biography | 1972 [S] (same: Yale JD 1972, joined 1972) | left practice (2011) [S] ("until his retirement in June 2011") | (2011-06, left_practice) [S] |
| `debevoise__michael_blair` | keep | Michael W. Blair | EDGAR 2005-08 (Acadia 13D/A, Debevoise): https://www.sec.gov/Archives/edgar/data/899629/000095012305010426/y12354sc13dza.txt | 1981 [S] (bio: Chicago JD 1981) https://www.debevoise.com/michaelblair | practising [S] (bio: of counsel) | (2011-07, chair_role, Presiding Partner to Jun 2022) [S] |
| `debevoise__mary_jo_white` | keep | Mary Jo White | Chair of Litigation before 2013 [S]: SEC release https://www.sec.gov/news/press/2013/2013-56.htm | 1974 [S] (SEC release: Columbia law degree 1974) | practising [S] (Debevoise bio https://www.debevoise.com/maryjowhite ) | (2013-04, government, SEC chair) [S]; returned to Debevoise (2017-02) [S] |
| `debevoise__franci_blassberg` | keep | Franci J. Blassberg | EDGAR 2005-05 (VWR, Debevoise): https://www.sec.gov/Archives/edgar/data/1300446/000110465905024123/a05-9572_1ex99d1.htm | 1977 [S] (bio: Cornell JD 1977) https://www.debevoise.com/franciblassberg | practising [S] (bio title: of counsel) | (year not found, of_counsel, Debevoise) [S] |
| `debevoise__david_rivkin` | keep | David W. Rivkin | Co-chair of International Dispute Resolution for over 20 years: https://en.wikipedia.org/wiki/David_W._Rivkin | 1980 [S] (Wikipedia: Yale JD 1980) | practising [S] (retired from Debevoise at the end of 2022; now a full-time arbitrator, Wikipedia; NYREG: Arbitration Chambers) | (2015-01, chair_role, President of the International Bar Association 2015–16) [S] |
| `debevoise__ralph_ferrara` | **ADD** (moved from LeBoeuf) | Ralph C. Ferrara. Role 2005: Debevoise Washington DC managing partner until he moved in Nov 2005. Practice: securities enforcement and litigation (former SEC General Counsel). Standing: leading [D] | Law.com, 2005-11-02: LeBoeuf hires "Debevoise & Plimpton's Washington DC managing partner Ralph Ferrara ... after 23 years with ... Debevoise": https://law.com/international-edition/2005/11/02/veteran-debevoise-head-joins-leboeuf-dc-arm | 1970 [S] (Martindale via search: Cincinnati JD 1970; NYREG NY 1982) | practising [A] (Proskauer partner per search results; EDGAR mentions at Proskauer to 2017; no end found) | (2005-11, lateral, LeBoeuf, Lamb, Greene & MacRae, head of the DC office) [S]; (2007-10, lateral, Dewey & LeBoeuf, by merger) [D: EDGAR 2009 Dewey]; (c. 2012, lateral, Proskauer) [D: EDGAR 2015–17, year A] |

#### Shearman & Sterling (`shearman`) — 6 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `shearman__david_heleniak` | keep | David W. Heleniak | Senior Partner to May 2005: LawFuel 2005-05-04 https://www.lawfuel.com/?p=4788 | 1974 [S] (LawFuel: joined Shearman 1974; NYREG 1975) | left practice (2005) [D] (moved to a Morgan Stanley vice chairman role, a non-legal role) | (2005-05, left_practice, Morgan Stanley vice chairman) [S] |
| `shearman__rohan_weerasinghe` | keep | Rohan S. Weerasinghe | EDGAR 2005-06 (Lincoln Educational, Shearman counsel): https://www.sec.gov/Archives/edgar/data/1286613/000104746905017602/filename1.htm ; D#3 | 1979 [S] (NYREG: Harvard) | practising [S] (rejoined Shearman as of counsel Sep 2023, law.com via search: https://law.com/americanlawyer/2023/09/05/former-citigroup-gc-rejoins-shearman-ahead-of-proposed-merger ) | (2005-06, chair_role, Senior Partner) [S]; (2012-06, in_house, Citigroup general counsel) [S]. Outside the window: left Citi at the end of 2021; (2023-09, of_counsel, Shearman) |
| `shearman__creighton_condon` | keep | Creighton O. Condon | EDGAR 2006-03 (Viacom/DreamWorks notice, Shearman): https://www.sec.gov/Archives/edgar/data/1297401/000119312506051169/dex1035.htm ; D#6 (co-head of M&A) | 1983 [S] (NYREG: Columbia) | practising [S] (EDGAR 2025-12, Shearman counsel on the Versant 10-12B) | (2008-10, chair_role, European Managing Partner, London) [S]; (2012-05, chair_role, Senior Partner) [S] |
| `shearman__emmanuel_gaillard` | keep | Emmanuel Gaillard | Founded Shearman's arbitration practice (1987) and led it for 33 years; acted for the Yukos majority shareholders from 2005: https://en.wikipedia.org/wiki/Emmanuel_Gaillard | 1982 [D] (Wikipedia: professor of law after the agrégation, 1982; Paris bar year not found) | left practice (2021) [D] (Wikipedia) | none in the window. Outside it: (2021-02, lateral, Gaillard Banifatemi Shelbaya Disputes) [S] |
| `shearman__clare_obrien` | keep (2005 partnership now sourced) | Clare O'Brien | Partner since Jan 1995 (ICJ-USA bio): https://icj-usa.org/clare_obrien/ ; EDGAR 2005-04: https://www.sec.gov/Archives/edgar/data/1115255/000094787105000795/toc_041305.txt ; AmLaw Dealmakers of the Year 2005 for SunGard [S via search: Glass Hammer] | 1985 [S] (A&O Shearman bio: Law Society of Ireland 1985; NY 1986) | practising [S] (EDGAR 2025-12; NYREG: A&O Shearman) | none. Standing: consider leading [D] from the 2005 AmLaw award |
| `shearman__linda_rappaport` | keep | Linda E. Rappaport | Partner since 1985 [S, D#11]; Glass Hammer 2011: https://theglasshammer.com/2011/03/voice-of-experience-linda-rappaport-partner-shearman-sterling/ | 1978 [S] (NYREG: NYU) | practising [S] (NYREG: A&O Shearman) | (2010-05, chair_role, Policy Committee, 4-year term) [S] |

#### Milbank (`milbank`) — 5 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `milbank__mel_immergut` | keep (correct the practice to corporate finance / investment counsel [D]; it was "Litigation [A]") | Mel M. Immergut | Chairman 1995–2013 (D's "c. 1996" becomes 1995): https://en.wikipedia.org/wiki/Mel_Immergut ; D#1 | 1972 [S] (NYREG: Columbia) | practising [S, weak] (Wikipedia, present tense: "has been a partner ... since 1980") | (2013-03, chair_role, stepped down as chairman) [S] |
| `milbank__scott_edelman` | keep | Scott A. Edelman | Executive Committee since 2003; joined 1994: https://milbank.com/en/news/milbank-elects-scott-a-edelman-new-chairman-succeeding-mel.html | 1989 [S] (NYREG: Harvard) | practising [S] (NYREG: Milbank) | (2009, chair_role, Vice Chairman) [S]; (2013-03, chair_role, Chairman) [S] |
| `milbank__luc_despins` | keep (was [A]-only) | Luc A. Despins | EDGAR 2005-06 (Satmex, Milbank counsel to the noteholders' committee): https://www.sec.gov/Archives/edgar/data/1063131/000095012305007751/y10192exv99w1.htm ; senior partner in Milbank's restructuring group before 2008 [S via search, Paul Hastings release] | 1986 [S] (NYREG: Harvard; Best Lawyers https://www.bestlawyers.com/lawyers/luc-a-despins/44970 ) | practising [S] (NYREG: Paul Hastings) | (2008-11, lateral, Paul Hastings, chair of global restructuring) [S] (corrects D's "c. 2007 [A]"). Standing: leading [D] |
| `milbank__dennis_dunne` | keep (was [A]-only) | Dennis F. Dunne | EDGAR 2005-04 (TBS International, Milbank counsel to the committee): https://www.sec.gov/Archives/edgar/data/1065648/000095013605002171/file002.htm | 1991 [S] (NYREG: NYU) | practising [S] (NYREG: Milbank; EDGAR 2025-03) | none sourced (D's "later chair of restructuring" is unsourced, so drop that claim). Standing: leading [D] |
| `milbank__paul_aronzon` | keep (was [A]-only) | Paul S. Aronzon | EDGAR 2005-05 (Milbank LA, notice copy): https://www.sec.gov/Archives/edgar/data/943323/000119312505115760/dex1010.htm ; co-chair of financial restructuring before 2006 [S via search, GlobalCapital] | 1979 [S] (State Bar of California: admitted Nov 1979, now inactive; https://apps.calbar.ca.gov/attorney/LicenseeSearch/QuickSearch?FreeText=Aronzon ) | left practice (2019) [D] (a profile found by search gives consulting from 2019; CalBar status inactive) | (2006, left_practice, Imperial Capital, investment bank) [S]; (2008, lateral, Milbank, return; co-MP in LA) [S] |

#### Fried Frank (`fried_frank`) — 4 kept, 1 dropped

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `fried_frank__valerie_jacob` | keep | Valerie Ford Jacob | Chair from 2003 (Lawdragon, D#2) or co-head of corporate (D#1): still conflicting. EDGAR 2005-10 (Fried Frank letter, School Specialty): https://www.sec.gov/Archives/edgar/data/1055454/000089271205000967/exh991.htm | 1979 [S] (NYREG: Cornell) | practising [S] (EDGAR 2025-04, Freshfields counsel on BuzzFeed's S-8) | (2014-03, chair_role, ended; senior partner) [S]; (2014-09, lateral, Freshfields) [S] |
| `fried_frank__justin_spendlove` | keep | Justin N. Spendlove | Joined as European MP in Apr 2004 from Ashurst, then worldwide MP (Law Gazette via search); "Managing Partner Justin Spendlove", LawFuel 2006-09: https://www.lawfuel.com/blog/london-4-september-2006-lawfuel-london-law-news-fried-frank-ann ; D#4, D#5 | c. 1980 [A] (he was Ashurst's managing partner before 2004; no admission year found; no NYREG entry) | practising [A] (no evidence either way) | none found |
| `fried_frank__paul_reinstein` | keep | Paul M. Reinstein | Co-head of corporate from 2003 [S, D#1]; EDGAR 2006-05 (Allied World, Fried Frank): https://www.sec.gov/Archives/edgar/data/1163348/000095012306005810/y15272a1exv10w13.txt | 1977 [S] (NYREG: Yale) | practising [S] (NYREG: Fried Frank) | none |
| `fried_frank__arthur_fleischer` | keep (was [A]-only) | Arthur Fleischer Jr. | EDGAR 2005-02 (Grey Global, Fried Frank notice copy): https://www.sec.gov/Archives/edgar/data/43952/000095012305002266/y06158exv10w1.txt ; Yale CCL page "Senior Partner, Fried Frank": https://www.ccl.yale.edu/simeon-baldwin-award/fleischer-arthur | 1958 [S] (Yale Law '58; joined Fried Frank 1958 per search; NYREG 1959) | left practice (2025) [D] (a 2025 career summary found by search describes a 65-year career at the firm) | none |
| `fried_frank__stephen_fraidin` | **DROP** | Stephen Fraidin | He left Fried Frank for Kirkland & Ellis in May 2003: Law.com https://www.law.com/international-edition/2003/05/12/fried-frank-loses-fraidin-to-kirkland-ellis/ ; EDGAR 2006-12 shows him at Kirkland. In 2005 he was at Kirkland, not Fried Frank. A Kirkland notables row could take him (NY 1965 [S]; Kirkland 2003; later Pershing Square, Cadwalader 2018, White & Case 2026; NYREG: White & Case) | | | |

#### Cadwalader (`cadwalader`) — 3 kept, 2 dropped, 1 added

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `cadwalader__robert_link` | keep (practice: capital markets and real estate [S, ABA Journal]) | Robert O. Link Jr. | Chairman and MP, "long-time incumbent" (law.com 2008-02-28, D#1); firm leader from 1994, formalised 1998 (ABA Journal): https://abajournal.com/news/article/ex-cadwalader_chairman_retires_at_55_with_no_plans_to_resume_law_practice | 1985 [S] (NYREG: Univ. of Tennessee) | left practice (2010) [S] (ABA Journal, Sep 2010: retired in the summer of 2010, no plans to practise) | (2008-03, chair_role, gave up the chairmanship and stayed MP) [S]; (2009-01, chair_role, head of the London office) [S]; (2010, left_practice) [S] |
| `cadwalader__dennis_block` | keep (was [A]-only) | Dennis J. Block | EDGAR 2005-11 (Irwin Financial letter on Cadwalader letterhead): https://www.sec.gov/Archives/edgar/data/52617/000091412105002226/filename1.txt | 1968 [S] (NYREG: Brooklyn Law) | practising [S] (NYREG: Greenberg Traurig) | (2012, lateral, Greenberg Traurig) [D: EDGAR shows him at Cadwalader through 2011 and at Greenberg Traurig from Jun 2012] |
| `cadwalader__michael_horowitz` | keep (was [A]-only) | Michael E. Horowitz | Cadwalader partner from 2002 (white collar); also a US Sentencing Commission commissioner from 2003: https://en.wikipedia.org/wiki/Michael_E._Horowitz | 1988 [S] (NYREG: Harvard) | government (2012) [S]; no return to practice (Wikipedia: now Inspector General of the Federal Reserve Board and CFPB) | (2012-04, government, DOJ Inspector General) [S] |
| `cadwalader__john_rapisardi` | **DROP** | John J. Rapisardi | He joined Cadwalader from Weil Gotshal about 2007 ("joined Cadwalader six years ago from Weil", ABA Journal, May 2013): https://abajournal.com/news/article/bankruptcy_co-chairs_leap_from_cadwalader_to_omelveny_along_with_another_pa . He was at Weil in 2005, and a Weil row could take him (NY 1983 [S]; O'Melveny 2013-05 [S]) | | | |
| `cadwalader__christopher_white` | **DROP** | W. Christopher White | No [S] for a 2005 role was found (no EDGAR hits; the first dated source is law.com 2008-02-28, "finance chief"). The facts found are chairman 2008-03 to 2014 [S, Cadwalader succession release via search] and NY 1981 [S, NYREG]. Re-add if a 2005 source turns up | | | |
| `cadwalader__michael_gambro` | **ADD** | Michael S. Gambro. Role 2005: Cadwalader partner, capital markets (CMBS and securitisation). Standing: strong [D] (signs SEC correspondence for major CMBS issuers; no directory band seen) | EDGAR 2005-09 (JPMorgan Chase Commercial Mortgage Securities letter signed by Gambro, Cadwalader): https://www.sec.gov/Archives/edgar/data/1013611/000091412105001732/filename1.txt | 1981 [S] (NYREG: Columbia) | practising [S] (NYREG: Hogan Lovells Cadwalader) | none found |

#### Willkie Farr & Gallagher (`willkie`) — 5 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `willkie__jack_nusbaum` | keep | Jack H. Nusbaum | Chairman 1987–2009 [S] (Willkie firm news, Jan 2021, D#2) | 1965 [S] (same: Columbia JD 1965; associate 1965, partner 1971) | left practice (2021) [D] (D#2: still contributing at the firm until Jan 2021) | (2010-01, chair_role, stepped down as chairman) [S] |
| `willkie__thomas_cerabino` | keep | Thomas M. Cerabino | EDGAR 2005-01 (Exide 13D/A, Willkie): https://www.sec.gov/Archives/edgar/data/813781/000089914005000020/s2743103.txt | 1981 [S] (Willkie bio: St. John's JD 1981; NY 1982) https://www.willkie.com/professionals/c/cerabino-thomas-m | practising [S] (Willkie bio; NYREG: Willkie) | (2008-04, chair_role, vice chairman) [S]; (2010-01, chair_role, co-chairman) [S] |
| `willkie__steven_gartner` | keep | Steven J. Gartner | EDGAR 2005-12 (TD Holding S-1, Willkie): https://www.sec.gov/Archives/edgar/data/1260221/000104746905028453/filename10.htm ; Willkie bio "partner of the firm from 1993": https://www.willkie.com/professionals/g/gartner-steven | 1984 [S] (bio: started as a firm associate in 1984; NYREG 1985) | left practice (2020) [S] (bio: retired at the end of 2020) | (2008-04, chair_role, vice chairman) [S]; (2010-01, chair_role, chairman to 2020) [S] |
| `willkie__benito_romano` | keep (was [A]-only) | Benito Romano | EDGAR 2005-01 (Hollinger agreement, Romano at Willkie): https://www.sec.gov/Archives/edgar/data/868512/000095012305000415/y67702exv10w21.txt ; a Willkie partner for 20 years and head of white collar: https://en.wikipedia.org/wiki/Benito_Romano | 1976 [S] (Wikipedia: Columbia JD 1976; NYREG 1977) | practising [D] (Freeh Sporkin & Sullivan from May 2018 per its bio via search; NYREG same) | (2009-01, lateral, Freshfields) [S] (Legal Week 2009-01-22 via search). Outside the window: (2018-05, lateral, Freeh Sporkin & Sullivan) [S] |
| `willkie__rose_dimartino` | keep (was [A]-only) | Rose F. DiMartino | EDGAR 2005-08 (Credit Suisse Opportunity Funds letter, Willkie): https://www.sec.gov/Archives/edgar/data/946110/000089180405002513/filename1.txt | 1982 [S] (NYREG: St. John's) | practising [A] (the latest EDGAR mention at Willkie is 2019; no end year found) | none |

#### Proskauer Rose (`proskauer`) — 4 kept, 1 dropped

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `proskauer__allen_fagin` | keep (practice labour and employment [S], listed in the labour section of the same release) | Allen I. Fagin | "Allen I. Fagin, chairman of Proskauer Rose", Proskauer press release, 25 Jan 2005: https://www.proskauer.com/insights/get-pdf/2587 | 1976 [S] (practised at Proskauer from 1976 per OU announcement via search; NYREG 1976) | left practice (2013) [S] (retired from the firm at the end of 2013, per search results) | (2010-12, chair_role, term ended) [S] (sources give 2005–2010 or 2005–2011); (2013-12, left_practice) [S] |
| `proskauer__joseph_leccese` | keep | Joseph M. Leccese | Named in the same 25 Jan 2005 release; Chambers Sports Law band 1 "2005–2025" on his bio: https://www.proskauer.com/professionals/joseph-leccese | 1986 [S] (NYREG; Virginia Law Review 1983–85, so JD 1985 [D]; joined Proskauer 1986 [S, Leaders 2014]) | practising [S] (bio, Chambers 2026) | (2011-01, chair_role, chairman) [S] |
| `proskauer__bettina_plevan` | keep | Bettina B. Plevan | Named in the 25 Jan 2005 release; NYC Bar president 2004–06 [S] | 1970 [S] (Wikipedia: Boston University JD 1970) https://en.wikipedia.org/wiki/Bettina_Plevan | left practice (2021) [D] (Wikipedia / Proskauer page) | (2006, chair_role, ABA Board of Governors 2006–09) [S] |
| `proskauer__bradley_ruskin` | keep (was [A]-only) | Bradley I. Ruskin | Proskauer bio: Chambers "Nationwide: Sports Law 2005–2026 (Band 1)": https://www.proskauer.com/professionals/bradley-ruskin ; EDGAR 2006-05 (Proskauer notice copy): https://www.sec.gov/Archives/edgar/data/785959/000101297506000218/e8538612.txt | 1982 [S] (NYREG: NYU) | practising [S] (bio) | none |
| `proskauer__edward_brill` | **DROP** | Edward A. Brill | No [S] for a 2005 role was found (no EDGAR hits; he is not in the 25 Jan 2005 release; the current bio has no dates). The facts found are Yale JD 1972 and NY 1973 [S] | | | |

#### Ropes & Gray (`ropes_gray`) — 4 kept

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `ropes_gray__brad_malt` | keep | R. Bradford Malt | Chairman 2004–2019, partner 1987–2019 (MassMutual trust 497, 2022): https://www.sec.gov/Archives/edgar/data/916053/000110465922073825/tm2219173-1_497.htm ; https://en.wikipedia.org/wiki/R._Bradford_Malt | 1979 [S] (Wikipedia: Harvard Law 1979; associate 1979) | left practice (2019) [S] (same 497; R&G 2018 release: retired at the start of 2020) | none (chair throughout) |
| `ropes_gray__david_chapin` | keep | David C. Chapin | EDGAR 2005-01 (Dovrat 13D/A, Ropes & Gray attention line): https://www.sec.gov/Archives/edgar/data/1314246/000095017205000168/ex1ny13848.txt ; Policy Committee 2004–2019 [S] | 1980 [S] (Massachusetts admission 1980, Justia via search) | left practice (2019) [S] (R&G 2018 release: https://www.ropesgray.com/en/newsroom/news/2018/04/Ropes-Gray-Leadership-Transition-on-Course ) | (2013, chair_role, managing partner to 2019) [S] |
| `ropes_gray__keith_higgins` | keep (was [A]-only) | Keith F. Higgins | EDGAR 2005-06 (BTU International S-8, Higgins at Ropes & Gray): https://www.sec.gov/Archives/edgar/data/840883/000095013505003387/b55514a1sv8pos.htm | ≤1983 [D] (SEC release 2016-258: practised "more than 30 years at Ropes & Gray" before May 2013) | practising [A] (rejoined R&G Jun 2017; no later evidence found) | (2013-05, government, SEC Division of Corporation Finance director) [S]; returned to Ropes & Gray (2017-06) [S] |
| `ropes_gray__jesse_jenner` | keep (was [A]-only) | Jesse J. Jenner | EDGAR 2003-12 (Fish & Neave counsel, Stamps.com): https://www.sec.gov/Archives/edgar/data/1082923/000095015003001441/a95348exv10w25.htm ; Fish & Neave's IP practice combined with Ropes & Gray in 2005 [S, D#4]; R&G IP litigation partner (2012): https://www.ropesgray.com/en/newsroom/news/2012/12/jesse-jenner-discusses-jerome-lemelson-the-original-patent-troll-in-iforbesi . The 2005 role is [S/D] | 1972 [S] (Martindale via search: Harvard JD 1972; NYREG 1973) | left practice (year not found) [S] (the R&G page lists him as "Retired Partner") | (2005-01, lateral, Ropes & Gray, by merger with Fish & Neave) [S/D] |

#### Dewey Ballantine (`dewey_ballantine`) — 3 kept, 1 dropped

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `dewey_ballantine__morton_pierce` | keep | Morton A. Pierce | EDGAR 2005-01 (LifePoint letter signed by Pierce, Dewey Ballantine): https://www.sec.gov/Archives/edgar/data/1074772/000095012305000036/y01634rwrw.htm ; "longtime chair of predecessor firm Dewey Ballantine" (Law.com 2012 via search) | 1975 [S] (NYREG: Penn) | practising [S] (NYREG: Fried Frank) | (2007-10, lateral, Dewey & LeBoeuf, by merger) [D]; (2012-05, lateral, White & Case) [S]. Later: Fried Frank, date not found |
| `dewey_ballantine__alan_wolff` | keep | Alan Wm. Wolff | DC office MP 1991–Sep 2007: NFTC https://www.nftc.org/nftc-welcomes-new-chairman-ambassador-alan-wolff/ ; USCC bio https://www.uscc.gov/sites/default/files/Alan%20Wolff.pdf | 1966 [S] (NYREG: Columbia; government lawyer from 1968 per USCC) | left practice (2017) [D] (WTO Deputy Director-General, then PIIE senior fellow from 2021: https://www.piie.com/experts/senior-research-staff/alan-wm-wolff ) | (2007-10, lateral, Dewey & LeBoeuf, by merger) [S]; (2011-03, chair_role, chairman of the National Foreign Trade Council) [S]. Outside the window: (2017, government, WTO Deputy Director-General) [S] |
| `dewey_ballantine__jeffrey_kessler` | keep | Jeffrey L. Kessler | Joined Dewey Ballantine in 2003: https://en.wikipedia.org/wiki/Jeffrey_L._Kessler | 1977 [S] (Wikipedia: Columbia Law 1977; began at Weil 1977) | practising [S] (NYREG; Winston & Strawn co-executive chairman per Wikipedia) | (2007-10, lateral, Dewey & LeBoeuf, by merger) [S]; (2012-05, lateral, Winston & Strawn) [S]; (2012-10, chair_role, co-executive chairman) [S] |
| `dewey_ballantine__john_ragosta` | **DROP** | John A. Ragosta | No source links him to Dewey Ballantine in 2005: a web search, EDGAR and NYREG all returned nothing, and italaw (403) lists trade cases only | | | |

#### LeBoeuf, Lamb, Greene & MacRae (`leboeuf`) — 0 rows after this pass

| notable_key | keep/DROP/ADD | name | role_2005 [S] source | career_start | status_by_2025 | moves 2005–2015 |
| --- | --- | --- | --- | --- | --- | --- |
| `leboeuf__ralph_ferrara` | **DROP** (moved to Debevoise as an ADD) | Ralph C. Ferrara | Law.com 2005-11-02: he joined LeBoeuf from Debevoise in Nov 2005. In Jan 2005 he was Debevoise's DC managing partner, not at LeBoeuf. See `debevoise__ralph_ferrara`, which carries the lateral move into LeBoeuf in 2005-11 | | | |

LeBoeuf now has no notables at turn 0. An EDGAR scan of 2005 LeBoeuf notice copies found only lesser-known names (Gordon H. Hayes, Joseph L. Seiler, Michael Groll). None was added, because no standing evidence was found. LeBoeuf needs its own pass, for example on energy and insurance partners in Chambers 2006 archives, if any can be reached.

---

#### Method and weaknesses

**Method.** Six kinds of source were used, in this order.

1. **Firm biographies, fetched directly.** These came from Davis Polk, STB, Paul Weiss, Cleary, Debevoise, A&O Shearman, Willkie and Proskauer. Ropes & Gray, White & Case, Blackstone, Axios and Martindale returned 403. Milbank and Fried Frank returned 404.
2. **NYREG, the NY Unified Court System's open attorney-registration data.** It gave a career-start year for most rows. Only the NY admission year and the employer field were read from it.
3. **SEC EDGAR full-text search.** It supplied the [S] 2005-role proofs for transactional lawyers: the person is named as counsel at the firm in a 2005 filing. It also showed recent activity for status. The requests used a generic client identifier.
4. **State Bar of California lookup** (for Aronzon only).
5. **Wikipedia and Wikimedia pages,** fetched until the API rate limit was reached.
6. **21 web searches,** used only where the other sources failed.

**Weaknesses.**

- **NY admission is not graduation.** Where no JD year was found, the NY admission year is used. It can be a year or more after law school (McInerney, Huebner), or much later where a lawyer was first admitted in another state. That applies to Wells (NY 2001, so his 1976 JD is used), Buchheit (NY 1985, which may be late) and Link (NY 1985).
- **"Practising" with no end found.** Several rows say "practising" on registration or recent-filing evidence only. Rosen, DiMartino, Higgins, Ferrara and Spendlove are [A]. A current NY registration does not prove someone is practising.
- **Years derived from firm pages.** Some "left practice" years for people no longer active come from the date of a firm page or a career summary, with no cause stated: Beattie, Youngwood, Nusbaum, Plevan, Gaillard and Fleischer. Each is [D] and good to about ±1 year.
- **Search-summary-only facts.** Several facts came only from search-result summaries, because the pages were blocked. They are tagged [S] with the URL from the result, but they were not read directly. They cover Fagin's retirement, Despins' move, Romano's moves, Weerasinghe's later career, Chapin's MA admission, Jenner's JD and Ferrara's JD. Verify them before relying on them.
- **Unresolved conflicts.** Fried Frank's 2005 leadership (Jacob as chair or as co-head of corporate; Spendlove's title) is still in conflict. Fagin's chair end year (2010 or 2011) and Leddy's MP end year (2016 in D#10, 2017 in his bio) differ by source.
- **Firms now short of rows.** Fried Frank has 4, Cadwalader 4 (with Gambro), Dewey Ballantine 3 and LeBoeuf 0. Fraidin (Kirkland) and Rapisardi (Weil) belong to other rivals' lists if those firms are in the game.
- **No 2005 directory bands were found.** The exceptions are Ruskin's and Leccese's Chambers Sports Law band 1 from 2005, shown on their Proskauer bios. Chepiga's 2005 Chambers ranking is cited only in a 2012 release.
- **Restricted content was left out.** Sources also carried political, personal, age and controversy content, and none of it was recorded.

### Part 3 gaps closed

Compiled 2026-11-20 for PT-M5 sub-task 1a. Research only; nothing in /home/user/LawGame was edited.
Rules (ADR PT-0013) applied: professional facts only. End years are given as a year with no cause. Where a source gave a reason for an end of practice, the reason was left out. Sources that mention age, family or criticism were used only for the professional fact cited.

Tags: **[S]** a page states it (URL given); **[D]** derived (method stated); **[A]** assumed (basis stated); **nf** = not found this session.
Move format: `(YYYY[-MM], kind, destination)`, where kind is one of lateral, government, judiciary, in_house, chair_role, of_counsel or left_practice.

---

#### WilmerHale (`wilmerhale`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `wilmerhale__william_lee` | keep | Co-managing partner from merger, 1 Jun 2004: https://www.wilmerhale.com/en/insights/news/wilmerhale-completes-merger-of-equals-june-1-2004 ; listed in Chambers USA 2006: https://www.wilmerhale.com/en/insights/news/chambers-usa-2006-ranks-wilmerhale-a-leader-in-28-practice-areas-88-lawyers-at-the-top-of-their-practice-june-2-2006 | 1976 [S] (JD Cornell 1976) https://www.wilmerhale.com/en/people/william-lee | practising [S] (current partner bio, same URL) | (2011-12, chair_role, co-MP term ends) [S] |
| `wilmerhale__william_perlstein` | keep | Co-managing partner from merger, 2004: WilmerHale 2004 merger release (above); BNY release https://wilmerhale.com/insights/news/2015-05-12-former-co-managing-partner-william-j-perlstein-to-join-bny-mellon-as-senior-deputy-general-counsel | c.1975 [D] ("nearly 40 years" at the firm by 2015, per the BNY release; Yale JD, year not stated https://www.fticonsulting.com/our-people/william-j-perlstein) | left practice (2019) [D] (joined FTI Consulting, a consulting firm, as Senior Managing Director, Nov 2019; FTI URL) | (2011-12, chair_role, co-MP term ends) [S]; (2015-06, in_house, BNY Mellon, Senior Deputy GC) [S] |
| `wilmerhale__seth_waxman` | keep | Chambers USA 2006 listing (URL above) | 1977 [S] (JD Yale 1977) https://www.wilmerhale.com/en/people/seth-waxman | practising [S] (current partner, co-chair Appellate; same URL) | none |
| `wilmerhale__jamie_gorelick` | keep | Chambers USA 2006 listing (above); "partner at WilmerHale since 2003" https://en.wikipedia.org/wiki/Jamie_Gorelick | 1975 [S] (JD Harvard 1975) https://www.wilmerhale.com/en/people/jamie-gorelick | practising [S] (senior counsel; same URL) | none dated (later senior counsel; date nf) |
| `wilmerhale__william_mclucas` | keep | Chambers USA 2006 listing (above); bio says he joined the firm after 8+ years as SEC Enforcement Director (this sources the [A] item) https://www.wilmerhale.com/en/people/william-mclucas | 1975 [S] (JD Temple 1975; same URL) | practising [S] (senior counsel, DC; same URL, which also sources the DC office) | none dated |
| `wilmerhale__charlene_barshefsky` | keep | Chambers USA 2006 listing, International Trade (above); "Senior International Partner" https://www.wilmerhale.com/en/people/charlene-barshefsky ; former USTR (this sources the [A] item) https://en.wikipedia.org/wiki/Charlene_Barshefsky | 1975 [S] (JD Catholic University 1975; firm URL) | left practice (2021) [S] ("retired from the firm in 2021"; firm URL) | none |
| `wilmerhale__mark_borden` | keep | Chambers USA 2006 listing, Corporate/M&A (above); "Best Corporate Lawyer of the Year" 2008 https://wilmerhale.com/insights/news/mark-borden-named-bostons-best-corporate-lawyer-of-the-year-july-28-2008 | 1976 [S, weak] (graduate degree Harvard 1976; partner 1976-2020 per MarketScreener) https://ch.marketscreener.com/insider/MARK-G-BORDEN-A0665M | left practice (2020) [S, weak] (MarketScreener gives the firm tenure as ending 2020; no firm confirmation) | none |

#### Covington & Burling (`covington`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `covington__stuart_stock` | keep | Chairman: ABA Journal https://abajournal.com/news/article/covington_poised_to_grow_with_new_chairman | 1971 [S] (JD Harvard 1971) https://www.cov.com/en/professionals/s/stuart-stock | practising [S] (senior counsel; same URL) | (2008-01, chair_role, hands chair to Hester) [D]; later of_counsel (senior counsel; date nf) |
| `covington__timothy_hester` | keep | Management Committee from 1998 (bio) https://www.cov.com/en/professionals/h/timothy-hester | 1982 [S] (JD Michigan 1982; same URL) | practising [S] (senior counsel; same URL) | (2008-01, chair_role, Chair of Management Committee 2008-2019) [S] |
| `covington__eric_holder` | keep | At Covington 2001-2009 https://en.wikipedia.org/wiki/Eric_Holder | 1976 [S] (JD Columbia 1976) https://www.cov.com/en/professionals/e/eric-holder | practising [S] (senior counsel; same URL) | (2009-02, government, US Attorney General) [S]; (2015, lateral, returned to Covington) [S] |
| `covington__lanny_breuer` | keep | Partner and co-chair, White Collar, before 2009 https://en.wikipedia.org/wiki/Lanny_A._Breuer | 1985 [S] (JD Columbia 1985) https://www.cov.com/en/professionals/b/lanny-breuer | practising [S] (Vice Chair; same URL) | (2009-04, government, AAG Criminal Division) [S]; (2013-03, lateral, returned to Covington as Vice Chair) [S] |
| `covington__peter_barton_hutt` | keep | Covington since 1960 except 4 years at FDA (Covington profile, per search snippet; https://cov.com/en/professionals/h/peter-hutt now 404); "worked at Covington for more than five decades" (2013) https://hls.harvard.edu/today/peter-barton-hutt-celebrating-20-years-at-harvard-law-video | 1959 [S] (Harvard LL.B. '59; same HLS URL) | practising (to 2025) [D] (HLS lists him as Lecturer on Law for 2026-27: https://hls.harvard.edu/faculty/peter-barton-hutt/ ; any end year falls after 2025 and is not recorded here) | none |

#### Hogan & Hartson (`hogan_hartson`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `hogan_hartson__warren_gorrell` | keep | Chairman from 2001 https://www.law.com/2018/08/22/law-firm-distinguished-leader-warren-gorrell-hogan-lovells/ ; "firm chair Warren Gorrell" (Sep 2004) https://washingtonian.com/2004/09/01/house-of-1000-lawyers/ (also: from 1998 he advised investment banks on SEC compliance, which sources the [A] practice: corporate/securities) | 1979 [S] (JD Virginia 1979, Best Lawyers) https://www.bestlawyers.com/lawyers/j-warren-warren-gorrell-jr/45369 | left practice (2016) [S] (retired end 2016) https://www.globallegalpost.com/news/longtime-hogan-lovells-leader-gorrell-announces-retirement-aged-62-64934468 | (2010-05, chair_role, co-CEO Hogan Lovells) [S]; (2013/2014, chair_role, steps down as co-CEO; sources differ) [S] |
| `hogan_hartson__christine_varney` | keep | Hogan & Hartson partner, chaired Internet practice https://en.wikipedia.org/wiki/Christine_A._Varney | 1986 [S] (JD Georgetown 1986) https://www.cravath.com/people/christine-a-varney.html | left practice (2025) [S] ("retired from Cravath's Litigation Department in December 2025"; Cravath URL) | (2009-04, government, AAG Antitrust) [S]; (2011-08, left government) [S]; (2011-09, lateral, Cravath Swaine & Moore) [S] (Wikipedia; this sources the [A] item) |
| `hogan_hartson__ty_cobb` | keep | Hogan partner for 29 years, joined c.1988 https://en.wikipedia.org/wiki/Ty_Cobb_(attorney) ; https://lawdragon.com/lawyer-limelights/2022-01-03-hall-of-fame-lawyer-limelight-ty-cobb | c.1980 [D] (federal clerkship after law school, then AUSA from 1981; JD year nf) | practising [D] (opened his own practice after 2018, per Lawdragon) | none in window (government 2017-07 to 2018-05 falls outside it) |
| `hogan_hartson__catherine_stetson` | keep | Partner since 2002, joined 1997 https://law360.com/appellate/articles/121889/q-a-with-hogan-hartson-s-cate-stetson | 1994 [S] (UVA Law '94) https://www.law.virginia.edu/news/201908/appellate-litigator-cate-stetson-94-welcome-class-2022 | practising [S] (Chambers USA 2026, co-director of appellate) https://chambers.com/lawyer/catherine-e-stetson-usa-5:285241 | none (co-director of appellate, date nf) |

#### Greenberg Traurig (`greenberg_traurig`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `greenberg_traurig__cesar_alvarez` | keep | CEO since 1996 https://www.gtlaw.com/en/news/2010/1/greenberg-traurig-implements-strategic-succession | 1972 [S] (JD Florida 1972) https://www.gtlaw.com/en/professionals/a/alvarez-cesar-l | practising [S] (Senior Chairman; same URL) | (2010-01, chair_role, Executive Chairman) [S] |
| `greenberg_traurig__richard_rosenbaum` | keep | Joined 1985; President "in his prior role", before 2010 (2010 release, above) | 1982 [S] (JD St John's 1982) https://www.gtlaw.com/en/professionals/r/rosenbaum-richard-a | practising [S] (Executive Chairman; same URL) | (2010-01, chair_role, CEO) [S] |
| `greenberg_traurig__matthew_gorson` | keep | Joined 1973; President in Jan 2010 (2010 release) https://www.gtlaw.com/en/professionals/g/gorson-matthew-b | 1973 [S] (JD Chicago 1973; same URL) | practising [S] (Senior Chairman; same URL) | none dated |
| `greenberg_traurig__hilarie_bass` | keep | Whole 37-year career at GT, to 2018 https://www.law.com/2018/09/12/bye-bye-big-law-greenberg-traurig-co-president-hilarie-bass-is-stepping-down-to-start-a-nonprofit/ ; litigation chair for 8 years before 2013 [D] https://conferences.law.stanford.edu/futurelaw2018/speakers/hilarie-bass/ | 1981 [D] (2018 minus a 37-year career at one firm, per law.com) | left practice (2018) [D] (left GT at end 2018 to found a nonprofit; no later practice found) | (2013, chair_role, Co-President) [S] |
| `greenberg_traurig__larry_hoffman` | keep | Chairman, Jan 2010 ("will remain in [his] current role") (2010 release); co-founder 1967 https://en.wikipedia.org/wiki/Greenberg_Traurig | 1967 or earlier [D] (co-founded the firm in 1967) | left practice (2025) [S] (end year in https://en.wikipedia.org/wiki/Greenberg_Traurig ; cause not recorded) | (2013, chair_role, Chairman title ends; sources differ) [S] |

#### DLA Piper (`dla_piper`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `dla_piper__frank_burch` | keep | Burch, Miller and O'Malley "held the office of chair since DLA Piper was created in 2005" https://www.jdjournal.com/?p=25597 ; https://www.abajournal.com/legalrebels/article/empire_builder_frank_burch_dla_piper | nf (DLA bio removed) | nf, practising [A: no evidence of leaving found; this needs checking] | (2005-01, chair_role, joint CEO / co-chair) [S]; (2011, chair_role, Tony Angel joins as co-chair; Burch's later title nf) [S] https://www.abajournal.com/news/article/dla_piper_partners_ok_hiring_of_former_linklaters_mp_as_global_co-chairman |
| `dla_piper__lee_miller` | keep | Office of chair from 2005 (jdjournal, above) | nf | nf, practising [A: senior adviser from 2015; no end found] | (2005-01, chair_role, co-chair) [S]; (2014-12, chair_role, global co-chair ends, becomes senior adviser) [S] https://www.lawdragon.com/press-releases/2014-02-05-dla-piper-announces-new-global-leadership |
| `dla_piper__nigel_knowles` | keep | Joint CEO of DLA Piper from 2005 https://en.wikipedia.org/wiki/Nigel_Knowles | 1978 [S] (articled clerk 1978; same URL) | practising [S, weak] (Chairman of the law firm DWF from 2017; same URL; end nf) | (2005-01, chair_role, joint CEO) [S]; (2015-01, chair_role, global co-chair) [S] (Lawdragon 2014); (2016, lateral, left DLA Piper) [S]; (2017, chair_role, DWF chairman) [S] |
| `dla_piper__george_mitchell` | keep | "Partner and chairman of the Global Board of DLA Piper"; Preti Flaherty senior counsel "until 2005" https://en.wikipedia.org/wiki/George_J._Mitchell | 1961 [S] (LL.B. Georgetown 1961; same URL) | practising [A] (chairman emeritus from 2011; no end found) | (2009-01, government, Special Envoy for Middle East Peace, to 2011-05) [S]; (2011, lateral, returned to DLA Piper as chairman emeritus) [S] https://www.lawyersweekly.com.au/news/8598-us-senator-returns-to-dla-piper |
| `dla_piper__terence_omalley` | keep | Office of chair from 2005 (jdjournal, above); Gray Cary chairman and CEO in the 2004 merger release https://www.mondaq.com/pressrelease/1519/piper-rudnick-and-gray-cary-announce-merger | nf | nf, practising [A: "continue[s] in an advisory role" from 2015 (Lawdragon 2014)] | (2005-01, chair_role, office of chair / global co-CEO) [S]; (2014-12, chair_role, co-CEO ends) [S] |
| `dla_piper__john_allcock` | keep (weak) | Global co-chair IP & Technology in Jul 2006 (nearest [S] to 2005) https://www.lawfuel.com/experienced-patent-litigator-joins-growing-patent-litigation-pract/ | nf (Harvard Law per Justia snippet; year nf) | practising [A: Justia lists DLA Piper San Diego, current CA bar] | none found |

#### Quinn Emanuel (`quinn_emanuel`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `quinn_emanuel__john_quinn` | keep | Co-founder 1986 https://en.wikipedia.org/wiki/John_B._Quinn | 1976 [S] (JD Harvard 1976) https://www.quinnemanuel.com/attorneys/quinn-john-b/ | practising [S] (same URL) | none |
| `quinn_emanuel__william_urquhart` | keep | Joined 1988; Best Lawyers "since 2006", Super Lawyers 2004-2013 https://www.quinnemanuel.com/attorneys/urquhart-a-william-in-memoriam/ | 1977 [S] (JD Fordham 1977; same URL) | left practice (2019) [S] (end year in the firm's 2019 notice, https://www.quinnemanuel.com/the-firm/news-events/firm-mourns-death-of-bill-urquhart-name-partner-and-visionary-who-drove-growth/ ; cause not recorded) | none |
| `quinn_emanuel__eric_emanuel` | keep | 32 years with the firm to 2019 https://law.com/therecorder/2019/01/17/after-32-years-with-quinn-co-founder-emanuel-bows-out-for-retirement-403-28609 | 1986 or earlier [D] (co-founded the firm in 1986; JD nf) | left practice (2019) [S] (retired from the firm 2019; Recorder URL) | none |
| `quinn_emanuel__kathleen_sullivan` | keep (from 2005, month nf) | "In 2005, she joined Quinn Emanuel" https://en.wikipedia.org/wiki/Kathleen_Sullivan_(lawyer) ; Stanford dean to 2004 https://www.quinnemanuel.com/attorneys/sullivan-kathleen-m/ | 1981 [S] (JD Harvard 1981; NY bar 1982; QE URL) | practising [S] in 2025; she retired from the firm during 2025 (QE URL), so the engine may use left practice (2025) | (2005, lateral, joined QE from academia) [S]; (2010-03, chair_role, name partner) [S] |
| `quinn_emanuel__charles_verhoeven` | **DROP** (pending) | No [S] found for a 2005 role at QE: the firm bio is unreachable (404 at every URL tried), and the earliest sourced fact is Law360 IP MVP 2012. Re-add if a bio confirms partnership before 2005. | nf (Iowa law degree per Justia snippet; year nf) | practising [A: Law360 MVP 2018, Litigation Daily 2020] | none found |

#### Williams & Connolly (`williams_connolly`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `williams_connolly__brendan_sullivan` | keep | Senior partner at W&C https://en.wikipedia.org/wiki/Brendan_Sullivan_(lawyer) ; Chambers: White-Collar DC "22 years ranked" https://chambers.com/lawyer/brendan-v-sullivan-jr-usa-5:160499 | 1967 [S] (JD Georgetown 1967; Wikipedia) | practising [S] (Chambers USA 2026) | none |
| `williams_connolly__robert_barnett` | keep | Joined 1975 https://en.wikipedia.org/wiki/Robert_B._Barnett (redirects to his article) | 1971 [S] (JD Chicago 1971; same URL) | left practice (2025) [S] (end year from the same page; cause not recorded) | none |
| `williams_connolly__david_kendall` | keep | "At W&C since 1978, and a partner from 1981 to 2014" https://www.wc.com/attorney/david-e-kendall/ | 1971 [S] (JD Yale 1971) https://en.wikipedia.org/wiki/David_E._Kendall | practising [S] (senior counsel; W&C URL) | (2014, of_counsel, senior counsel at W&C) [S]. The [A] Clinton item: Wikipedia says he represented Clinton in the impeachment trial [S], so it is now sourced |
| `williams_connolly__kevin_baine` | keep | Firm bio lists Best Lawyers 1991-2021 and firm matters including Agostini v. Felton (1997) https://www.wc.com/attorney/kevin-t-baine/ | 1974 [S] (JD Penn 1974; same URL) | practising [S] (senior counsel; same URL) | none dated |
| `williams_connolly__john_villa` | keep | Listed "of Williams & Connolly" in PLC Global Counsel Dispute Resolution Handbook 2004-2005 https://www.wc.com/attorney/john-k-villa/ | 1973 [S] (JD Michigan 1973; same URL) | practising [S] (partner; same URL) | none |
| `williams_connolly__douglas_marvin` | keep (weak) | Firm bio: Chambers USA Products Liability 2007-2018 (nearest [S] to 2005) https://www.wc.com/attorney/douglas-r-marvin/ | 1972 [S] (JD Virginia 1972; same URL) | practising [S] (senior counsel; same URL) | none dated |
| `williams_connolly__bruce_genderson` | keep | Joined W&C 1978; built the patent practice from the mid-1990s; Executive Committee https://www.wc.com/attorney/bruce-r-genderson/ | 1977 [S] (JD Penn 1977; same URL) | practising [S] (senior counsel from 2023; same URL) | none in window |

#### Boies Schiller & Flexner (`boies_schiller`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `boies_schiller__david_boies` | keep | "From 1997-2024, David served as Chairman" https://www.bsfllp.com/lawyers/david-boies.html | 1966 [S] (LL.B. Yale 1966; same URL) | practising [S] (current bio; chairmanship ended 2024) | none |
| `boies_schiller__jonathan_schiller` | keep | Founding partner 1997, permanent Executive Committee member https://www.bsfllp.com/lawyers/jonathan-d-schiller.html | nf (JD Columbia; year not shown) | practising [S] (same URL) | (2013, chair_role, Columbia trustees chair; external, not a firm role) [S] |
| `boies_schiller__donald_flexner` | keep | Named partner from Dec 1999 https://www.bsfllp.com/lawyers/donald-l-flexner.html ; managing partner per a 2007 firm announcement (search snippet) | nf (LL.B. NYU; year not shown) | left practice (2023) [D] (the firm's 2023 notice gives the end year; Best Lawyers listings to 2023 on the same URL; cause not recorded) | none |
| `boies_schiller__stephen_zack` | keep | Merged his firm into BSF c.2002, founding the Florida base https://www.superlawyers.com/articles/florida/the-incredible-journey-of-stephen-zack | 1989 or earlier [D] (Florida Bar President 1989-90, per https://www.bsfllp.com/lawyers/stephen-n-zack.html ; JD year nf) | practising [S] (partner, Miami; same URL) | (2010-08, chair_role, ABA President 2010-11; external role, not a firm role) [S] |
| `boies_schiller__william_isaacson` | keep | Founding member of BSF 1997 (from Kaye Scholer); this sources the [A] row https://www.lawdragon.com/2016/01/11/lawyer-limelight-william-isaacson/ | nf | practising [S] (joined Paul Weiss Jun 2020) https://news.bgov.com/antitrust/boies-schiller-d-c-leaders-dunn-isaacson-jump-to-paul-weiss | none in window (lateral to Paul Weiss 2020-06) |

#### Wilson Sonsini (`wilson_sonsini`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `wilson_sonsini__larry_sonsini` | keep | https://www.lawfuel.com/?p=3996 (Feb 2005 release) | 1966 [S] (JD Berkeley 1966) https://en.wikipedia.org/wiki/Larry_Sonsini | practising [S, weak] (Wikipedia: "senior partner") | (2005-02, chair_role, gives up CEO; remains chairman) [S] |
| `wilson_sonsini__john_roos` | keep | CEO from Feb 2005 (LawFuel, above) | 1980 [S] (JD Stanford 1980) https://en.wikipedia.org/wiki/John_Roos | left practice (2009) [D] (went into government 2009 and did not return to practice; founded Geodesic Capital, a VC firm, after 2013; same URL) | (2005-02, chair_role, CEO) [S]; (2009-08, government, US Ambassador to Japan, to 2013-08) [S] |
| `wilson_sonsini__jeff_saper` | keep | Vice chairman from Feb 2005, joined 1979 (LawFuel, above) | 1979 or earlier [D] (joined WSGR 1979; NYU JD year not shown at https://www.wsgr.com/print/v2/content/1008/Jeffrey-D.-Saper.pdf) | practising [S] (current WSGR bio PDF, same URL) | (2005-02, chair_role, vice chairman) [S] |
| `wilson_sonsini__steven_bochner` | keep | "a 28 year veteran partner" when he succeeded Roos in 2009 https://en.wikipedia.org/wiki/Wilson_Sonsini_Goodrich_%26_Rosati | 1981 [S] (JD Berkeley 1981) https://www.wsgr.com/print/v2/content/1013/Steve-E.-Bochner.pdf | practising [S] (Chambers USA 2026) https://chambers.com/lawyer/steven-bochner-usa-5:159535 | (2009, chair_role, CEO) [S] |

#### Cooley (`cooley`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `cooley__stephen_neal` | keep | Chairman and CEO (Aug 2006 release) https://www.lawfuel.com/?p=10145 ; joined Cooley 1995 from Kirkland & Ellis; trial lawyer, ACTL Fellow (this sources the [A] practice) https://www.cooley.com/people/stephen-neal/in-depth | 1973 [S] (JD Stanford 1973; same URL) | practising [S, weak] (chairman emeritus on the current site; same URL) | (2008-01, chair_role, gives up CEO; remains chairman) [S] |
| `cooley__joe_conroy` | keep | Joined from Hunton & Williams (bio) https://www.cooley.com/people/joe-conroy/in-depth ; 1999 join date per Nov 2007 release (dossier fn 3) | 1986 [S] (JD Boston University 1986; same URL) | practising [S] (Partner and Chairman; CEO for 16 years; same URL) | (2008-01, chair_role, CEO) [S] |

#### Heller Ehrman (`heller_ehrman`, dissolved 2008)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `heller_ehrman__matthew_larrabee` | keep | "Firm Chair, 2005-2008"; Heller 1980-2008 https://www.jamsadr.com/neutrals/larrabee | 1980 [S] (JD Hastings 1980; same URL) | practising [S] (Dechert partner 2008-2023, then JAMS neutral; same URL) | (2005-03, chair_role, firm chair) [S]; (2008, lateral, Dechert, San Francisco; New York from 2012) [S]; (2015, chair_role, Dechert global litigation chair) [S] |
| `heller_ehrman__barry_levin` | keep (weak) | Chair until Mar 2005: Legal Week, 16 Mar 2005, as cited in the dossier (https://www.law.com/legal-week/sites/legalweek/2005/03/16/heller-ehrman-chair-hands-over-reins/ now returns 404; not re-verified) | nf | nf | (2005-03, chair_role, steps down as chair) [S per dossier]; post-2008 destination nf |
| `heller_ehrman__joshua_rosenkranz` | keep | Lead counsel in Merck KGaA v. Integra (2005) https://en.wikipedia.org/wiki/Heller_Ehrman | 1986 [S] (JD Georgetown 1986) https://en.wikipedia.org/wiki/E._Joshua_Rosenkranz | practising [S] (heads Orrick's Supreme Court practice; same URL) | (2008, lateral, Orrick) [D] (now at Orrick [S]; the year comes from Heller's 2008 dissolution and Orrick's Oct 2008 intake of Heller partners; no individual dated source) |
| `heller_ehrman__james_czaban` | keep | FDA lead in Merck KGaA v. Integra (2005) https://en.wikipedia.org/wiki/Heller_Ehrman | nf | nf, practising [A: no end found] | post-2008 destination nf |
| `heller_ehrman__steven_bomse` | **DROP** | No 2005 source: the only [S] is a 1983 matter. The name appears as "Stephen V. Bomse" in directories, which also needs checking. | nf | nf | nf |

#### Howrey (`howrey`, dissolved 2011)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `howrey__robert_ruyak` | keep | Led Howrey from 2000 https://washingtonian.com/2011/12/08/a-tale-of-two-law-firms/ | c.1975 [A] (Georgetown JD, year not shown; a 1974 article in a Georgetown journal is listed at https://www.larsonllp.com/people/robert-f-ruyak/) | practising [S] (Larson LLP partner; same URL) | (2011-09, lateral, Winston & Strawn) [S]; later co-founded a boutique, then Larson [S] (dates nf) |
| `howrey__henry_bunsow` | keep | Vice chairman; Northern California regional MP for 9 years to 2011 https://jdjournal.com/2011/01/20/vice-chairman-at-howrey-departs-for-dewey-leboeuf-2 | nf | nf, practising [A] | (2011-01, lateral, Dewey & LeBoeuf, SF; co-chair IP litigation) [S]; this corrects the dossier's "2009 [A]" |
| `howrey__margaret_zwisler` | keep | Departed Howrey 2005 to early 2006 https://www.washingtonian.com/2011/04/11/the-howrey-nosedive-a-timeline | 1976 [S] (JD George Washington 1976) https://www.lw.com/en/people/margaret-zwisler | left practice (2019) [S] ("retired from the partnership in December 2019"; Latham URL) | (2005/2006, lateral, Latham & Watkins) [S] |
| `howrey__karen_manos` | keep | Led Howrey's government contracts practice for an 11-year tenure https://www.lawfuel.com/?p=8594 | 1986 [S] (Duke Law 1986; same URL) | practising [A: no end found] | (2006-01, lateral, Gibson Dunn) [D] (release dated "Jan. 17"; the year follows from 11 years at Howrey after USAF 1986-95, and Washingtonian's "2005 to early 2006") |
| `howrey__alan_fisch` | keep | Departed Howrey 2005 to early 2006 (Washingtonian, above) | nf | nf, practising [A] | (2005, lateral, Kaye Scholer) [S]; later firm nf (fischsigler.com unreachable from this session) |

#### Bingham McCutchen (`bingham`, dissolved 2014)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `bingham__jay_zimmerman` | keep | Chairman since May 1994 https://www.bcgsearch.com/bcgnews/900041498/Bingham-McCutchen-Chairman-Hands-Over-Duties-Following-Succession-Plan/ ; re-elected Oct 2005 https://law.com/international-edition/2005/10/19/bingham-re-elects-veteran-chairman | 1982 or earlier [D] (joined Bingham 1982, per dossier fn 1) | nf, left practice (2015) [A: no practice found after Bingham closed in 2015] | (2014-06, chair_role, hands daily management to Browne) [S]; post-2014 destination nf |
| `bingham__steven_browne` | keep | Joined 19 Jan 2005 from Testa Hurwitz https://www.lawfuel.com/?p=3837 | nf | nf | (2014-06, chair_role, managing partner of the firm) [S] (BCG); post-2014 destination nf |
| `bingham__sabin_willett` | keep | Bingham partner; led the pro bono Uighur team https://en.wikipedia.org/wiki/Bingham_McCutchen | 1983 [S] (JD Harvard 1983) https://en.wikipedia.org/wiki/Sabin_Willett | practising [S, weak] (Wikipedia: Morgan Lewis partner) | (2014-11, lateral, Morgan Lewis) [S] (Wikipedia; this sources the [A] item) |
| `bingham__edwin_smith` | keep | "Partner/Financial Institutions Area Co-Chair, Bingham McCutchen LLP (1974-2014)"; this sources the [A] row https://lawyers.law.cornell.edu/lawyer/edwin-smith-1468066 | 1974 [S] (JD Harvard 1974) https://www.morganlewis.com/bios/edwinsmith | practising [S] (Morgan Lewis, now "Senior Consultant"; same URL) | (2014-11, lateral, Morgan Lewis) [D] (Bingham tenure ends 2014; now at Morgan Lewis) |

#### Reed Smith (`reed_smith`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `reed_smith__gregory_jordan` | keep | Managing partner from 1 Jan 2001 https://www.lawfuel.com/blog/contact-jamie-moss-newspros-201-493-1027-october-4-2006 | 1984 [S] (Pitt Law 1984; same URL) | practising [D] (in-house at PNC from 2013; no end found) | (2007-01, chair_role, 3rd term) [S]; (2010-01, chair_role, 4th term) [S]; (2013-10, in_house, PNC General Counsel) [S] |
| `reed_smith__sandy_thomas` | keep | Joined Reed Smith 1999 through the Hazel & Thomas merger; at the firm until 2023 https://www.reedsmith.com/en/news/2014/06/reed-smith-elects-sandy-thomas-as-global-managing ; https://virginiabusiness.com/a-naturally-inclusive-leader/ . His 2005 title (litigation head) stays [A]. | 1993 [S] (JD Washington & Lee 1993; virginiabusiness URL, per search snippet) | practising [S] (in-house, Chief Legal Officer of KIND, from 2023) https://ccbjournal.com/news/reed-smiths-sandy-thomas-will-join-kind-as-chief-legal-officer-catherine-casey-ryan-chosen-to-succeed-thomas-as-firms-global-managing-partner | (2013-10, chair_role, Global Managing Partner) [S]; re-elected 2014 [S] |
| `reed_smith__daniel_booker` | keep | Firmwide MP 1992-2001; current Reed Smith partner; Best Lawyers 1993-2027; this sources the [A] row https://www.reedsmith.com/en/professionals/b/booker-daniel-i | 1971 [S] (JD Chicago 1971; same URL) | practising [S] (partner, Pittsburgh; same URL) | none |

#### Kirkpatrick & Lockhart Nicholson Graham (`kl_gates`)

| notable_key | keep/DROP | role_2005 [S] source URL | career_start | status_by_2025 | moves 2005-2015 |
|---|---|---|---|---|---|
| `kl_gates__peter_kalis` | keep | Chairman of the Management Committee (5 Jan 2005 release) https://www.lawfuel.com/5-january-2005-lawfuel-best-for-law-news-new-york-and-london-u | 1978 [S] (JD Yale 1978) https://klgates.com/Peter-J-Kalis | left practice (2021) [S] (retired from the firm Feb 2021) https://www.klgates.com/KL-Gates-Honors-Longtime-Leader-Peter-Kalis-with-Chairman-Emeritus-Status-3-23-2021 | (2007-01, chair_role, chairman and later also global MP of K&L Gates) [S]; leadership ended early 2017 (outside window) |
| `kl_gates__charles_queenan` | **DROP** | No 2005 source. The only [S] says he was named Chairman Emeritus in **Oct 2013** (Kalis 2021 release), so the dossier's "chairman emeritus in 2005" is contradicted. | nf | nf | nf |
| `kl_gates__michael_johns` | keep | London senior partner; Executive Committee (2005 release, above) | nf | nf ("now retired" per a K&L Gates page seen only as a search snippet; year nf) | none found |
| `kl_gates__tony_griffiths` | keep | London Administrative Partner (2005 release, above) | 1989 [S] ("qualified as a lawyer in 1989"; LL.B. 1985) https://www.klgates.com/tony-griffiths | practising [S] (partner, London; same URL) | none. **Correction:** no source supports the dossier's "former MP"; remove it |
| `kl_gates__janice_hartman` | keep | Executive Committee, Pittsburgh (2005 release, above) | nf | nf | none found |
| `kl_gates__chuck_miller` | keep | Executive Committee, Washington (2005 release, above) | 1985 [A] (Justia lists an R. Charles Miller, K&L Gates partner, Penn JD 1985; identity not confirmed) | nf, practising [A] (same Justia basis) | none found |
| `kl_gates__paul_sweeney` | keep | Executive Committee, Los Angeles (2005 release, above) | nf | nf | none found |

---

#### Method and weaknesses

- **Method.** Firm biographies, Wikipedia and the URLs already cited in the dossier were fetched directly with curl and converted to text for grepping. About 28 web searches were used, only where no direct page worked (W&C, DLA Piper, K&L Gates, Hogan Lovells and Morgan Lewis bios are partly blocked or removed). For the 2005 role, a source dated in 2005 was preferred; otherwise a source giving a tenure that spans January 2005 (for example "joined 1985", "partner 1981-2014") counts as [S] for presence at the firm.
- **Weak 2005-role rows, kept and flagged:** Allcock (nearest source Jul 2006), Marvin (nearest source Chambers 2007), Levin (the Legal Week source now 404), K. Sullivan (joined QE during 2005, month nf, so possibly not at the firm in January 2005), and Borden's career and status, which rest on MarketScreener only.
- **Dropped (3):** Verhoeven (no 2005 source reachable), Bomse (only a 1983 source), Queenan (the source contradicts the dossier's 2005 title).
- **End years recorded with no cause:** Barshefsky 2021, Borden 2020 (weak), Perlstein 2019 (moved to consulting), Gorrell 2016, Varney 2025, Bass 2018, Hoffman 2025, Urquhart 2019, Emanuel 2019, Barnett 2025, Flexner 2023, Roos 2009 (government, then not law), Zwisler 2019, Kalis 2021. Several of these sources also state a cause; none was recorded. Hutt is recorded as practising to 2025: HLS lists him on the 2026-27 faculty, and any end year falls after 2025.
- **Dossier corrections:** Bunsow moved to Dewey in Jan 2011, not 2009. Queenan was Chairman Emeritus only from 2013. Griffiths "former MP" is unsupported. Mitchell was at Preti Flaherty "until 2005" per Wikipedia, so check his Piper Rudnick start against the dossier's "chairman 2003-2008". Bomse's first name is spelled "Stephen" in directories. [A] items now sourced: Barshefsky, McLucas, Gorrell's practice, Neal's practice, Varney's move to Cravath (2011), Kendall's Clinton work, Isaacson's row, Edwin Smith's row, Booker's row, Willett's and Smith's moves to Morgan Lewis.
- **Still open (nf):** career_start for 18 rows (Burch, L. Miller, O'Malley, Allcock, Verhoeven, Schiller, Flexner, Isaacson, Levin, Czaban, Bomse, Bunsow, Fisch, Browne, Queenan, Johns, Hartman, Sweeney). Status is nf or [A] for Burch, L. Miller, O'Malley, Allcock, Mitchell, Levin, Czaban, Bunsow, Manos, Fisch, Zimmerman, Browne, Johns, Hartman, C. Miller and Sweeney. DLA Piper has removed former leaders' bios. Hogan Lovells (hlc.com), Justia, Martindale, ACTL and Super Lawyers block automated fetches, and fischsigler.com and biglaw.org are outside this session's network. The ages and birth years that several sources print were never used to derive career_start, per the ADR.
