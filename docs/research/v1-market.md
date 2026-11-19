# V1 market dossier: US and New York large-firm legal spend, practice split, rates and pay (2005 base)

## 1. Header

| Item | Value |
| --- | --- |
| Purpose | Inputs for PT-M3a's `practices.yaml`: the 2005 demand base by practice for the New York home market, and the 2005 rate cards. Also checks spec §5.4 (salary history) and §6 (placeholder partner rates). |
| Compiled | 19 November 2026 |
| Scope | Year 2005, nominal US dollars. New York means the New York City large-firm market unless stated. |

**Tags.**
- **[S]**: sourced. I saw the figure in the cited source this session.
- **[D]**: derived from [S] figures. The arithmetic is shown.
- **[A]**: assumed. A reasoned estimate with no direct source; the basis is given.

**Method notes.**
- Search was cut short. The WebSearch budget is shared by every agent in the turn, and it ran out after about 15 searches (the plan was 40–60). After that I used only direct fetches of known primary URLs: Census, US Courts, SIFMA and a few known pages. I did not use any search engine, archive or proxy workaround. Many intended proxies were therefore not checked this session: PwC patent study, EEOC charges, ICC/ICDR caseloads, leveraged-loan volume, Moody's US default rate, NLJ 2005 New York rate table, bankruptcy fee applications, Hildebrandt/Citi realisation, NALP attrition. Each is marked "not found" below, with the reason.
- Most of the practice split is [A]. I anchored it top-down on the Am Law and Census totals, then checked it against activity proxies where I had them.
- Primary data I downloaded and parsed myself:
  - Census Service Annual Survey 2005 PDF
  - Census County Business Patterns 2005 flat files (US, state, county, MSA)
  - US Courts Table C-2 (FY2005) and Table F-2 (CY2005)
  - SIFMA 2006 Fact Book Addendum
- Spec context: the game starts January 2005 with a New York firm (spec §1). In the spec §6 table, the partner-rate column is the "Partner rate 2005 (NY, top firm) *(dossier)*" placeholder. The §5.4 salary history line is also marked *(dossier)*.

**Blocked, paywalled or unavailable sources this session.**

| Site | Result |
| --- | --- |
| law.com (NLJ billing surveys, Am Law tables, all `almID` links) | HTTP 403 |
| lawgazette.co.uk | HTTP 405 |
| lawcrossing.com, abovethelaw.com (2014 rates page partly readable through WebFetch), globallegalpost.com, lawdepartmentmanagementblog.com | HTTP 403 |
| lawjournalnewsletters.com | paywall after the introduction |
| api.census.gov | now requires an API key; I used the www2.census.gov flat files instead |
| eeoc.gov charge-statistics pages | the URL patterns I tried returned 404 |
| fulbright.com/litigationfindings | not reached; I used secondary coverage in Insurance Journal |

## 2. Total US large-firm legal spend, 2005

| Measure | Figure | Tag | Source |
| --- | --- | --- | --- |
| Legal services (NAICS 5411), revenue of taxable employer firms, 2005 | $221.6bn (2004: $209.5bn; +5.8%) | [S] | US Census Bureau, *Service Annual Survey 2005*, Table 6.1/6.2 (pub. Jan 2007), https://www2.census.gov/services/pdf/sas/data/Historical/2005_sas54.pdf |
| Offices of lawyers (NAICS 54111), same basis, 2005 | $208.0bn (2004: $197.4bn; +5.4%) | [S] | same, Table 6.1 |
| Offices of lawyers, total expenses, 2005 | $152.8bn | [S] | same, Table 6.18 |
| Nonemployer legal-services receipts, 2005 (sole practitioners without staff) | $15.1bn | [S] (secondary: search snippet of the Statistical Abstract table; not opened) | Census *Statistical Abstract 2008*, https://webarchive.library.unt.edu/web/20081105102821/http://www.census.gov/compendia/statab/tables/08s1249.pdf |
| Am Law 100, FY2005 ("2006 Am Law 100") gross revenue | $51.2bn; 70,161 lawyers; average PPP $1.06m | [S] (secondary: blog reproducing The American Lawyer) | Bruce MacEwen, *Adam Smith, Esq.*, 17 May 2006, https://adamsmithesq.com/?p=781 |
| Same, summed from the firm-by-firm table | $50.91bn; 70,160 lawyers | [D] (sum of 100 rows) | *Adam Smith, Esq.*, Apr 2006, https://adamsmithesq.com/2006/04/the_2006_amlaw_100_ranked/ |
| Am Law 100, FY2005 revenue per lawyer | about $730k | [D] $51.2bn ÷ 70,161 | as above |
| Am Law 100, FY2004 | $46bn (+10%), PPP $960k | [S] (secondary) | search summary of law trade press, 2005 list; same figure in *Adam Smith, Esq.* coverage |
| Am Law 100, FY2006 | average revenue +11.4%; RPL +7.3%; 59 firms with PEP over $1m | [S] (secondary) | Kinney Recruiting, 30 Apr 2007, https://www.kinneyrecruiting.com/global/legal-news/2006-profitable-year-for-equity-partners-at-top-firms |
| Am Law Second Hundred (firms 101–200), average revenue, FY2007 | $170.5m (+8%) | [S] | ABA Journal, 30 May 2008, https://www.abajournal.com/news/article/in_the_second_tier_law_firms_post_8_percent_revenue_gains |
| Am Law Second Hundred, FY2005 total | about $14.5bn (range $13–16bn) | [A] | FY2007 average $170.5m deflated two years at about 8% a year gives about $146m × 100. The FY2005 total itself was not found (law.com 403). |
| Am Law 200, FY2005 | about $65.7bn (range $64–67bn) | [D/A] | $51.2bn + $14.5bn |
| Am Law 100 share of offices-of-lawyers revenue | 24.6% | [D] | $51.2bn ÷ $208.0bn. Overstated, because Am Law revenue includes foreign offices (e.g. Baker & McKenzie, $1.35bn, mostly non-US). |
| Large-company legal budgets, 2006 | US large companies average $34.2m total legal spend, of which $19.8m (58%) is litigation | [S] (secondary) | Fulbright & Jaworski 2006 *Litigation Trends Survey*, via Insurance Journal, Nov 2006, https://www.insurancejournal.com/magazines/features/2006/11/05/152902.htm |
| Litigation share, 2005 survey | 12% of respondents put litigation above 50% of the legal budget; about 25% put it at 21–50% | [S] (secondary) | F&J 2005 survey, via Insurance Journal, 7 Nov 2005, https://www.insurancejournal.com/magazines/mag-features/2005/11/07/62401.htm |
| BTI Consulting / ACC–Serengeti 2005 total corporate legal spend | not found | — | search budget exhausted |

**Recommended sizing.**
- Size the "US large-firm" market to Am Law 200 revenue: **about $66bn in FY2005** ([D/A]).
- Cut that to **about $56bn of US-sourced work** ([A]: about 15% of Am Law revenue is foreign-office revenue, based on the Baker & McKenzie, White & Case and Clifford-style global footprints).
- Why Am Law 200 rather than all of NAICS 5411 ($208bn):
  - Most of NAICS 5411 is personal, small-firm and local work, where a New York large firm does not compete.
  - The Am Law 200 total grows with the same macro drivers the game models.
- The game's whole-economy "legal spend" should sit at about $208bn only if smaller rivals and regional markets are simulated too.

## 3. New York home market size

| Measure | Figure | Tag | Source |
| --- | --- | --- | --- |
| US offices of lawyers (541110): establishments, employees, annual payroll, 2005 | 174,938; 1,102,715; $76.98bn | [S] | Census *County Business Patterns 2005*, US file, https://www2.census.gov/programs-surveys/cbp/datasets/2005/cbp05us.txt |
| New York State offices of lawyers | 13,522 est.; 122,852 emp.; $10.23bn payroll | [S] | CBP 2005 state file, https://www2.census.gov/programs-surveys/cbp/datasets/2005/cbp05st.zip |
| Manhattan (New York County, FIPS 36061) offices of lawyers | 3,976 est.; 74,232 emp.; $7.86bn payroll | [S] | CBP 2005 county file, https://www2.census.gov/programs-surveys/cbp/datasets/2005/cbp05co.zip |
| New York–Newark MSA (35620), legal services (5411) | 15,571 est.; 139,735 emp.; $11.84bn payroll | [S] | CBP 2005 MSA file, https://www2.census.gov/programs-surveys/cbp/datasets/2005/cbp05msa.zip |
| Payroll shares of the US | NY State 13.3%; Manhattan 10.2%; NY MSA (5411) 14.6% | [D] | $10.23bn / $7.86bn / $11.84bn ÷ $76.98bn (541110) or $81.29bn (5411) |
| Payroll per employee | Manhattan $105.9k vs US $69.8k | [D] | payroll ÷ employees |
| Very large law offices in Manhattan | 11 of the 18 US law offices with 1,000+ employees; 16 of 62 with 500–999; 33 of 215 with 250–499 | [S] (counts) / [D] (shares: 61% of 1,000+ offices, 34% of 500+) | CBP 2005 county and US size-class counts |
| Offices-of-lawyers revenue in NY State | about $27.7bn | [D] | 13.3% × $208.0bn. Assumes NY revenue/payroll equals the US ratio. Probably low for NY, where equity-partner profit, which is not payroll, is a larger share. |
| Offices-of-lawyers revenue in Manhattan | about $21.2bn | [D] | 10.2% × $208.0bn, same caveat |
| New York–headquartered Am Law 100 firms, FY2005 | 27 firms; $14.74bn revenue (29.0% of the Am Law 100); 16,361 lawyers (23.3%) | [D] | Sum over firms I classed as NY-headquartered in the *Adam Smith, Esq.* table: Wachtell, Sullivan & Cromwell, Cravath, Davis Polk, Simpson Thacher, Paul Weiss, Milbank, Skadden, Shearman, Weil, Cadwalader, Debevoise, Cleary, Cahill, Fried Frank, Willkie, Kaye Scholer, Kramer Levin, Dewey Ballantine, Stroock, Hughes Hubbard, Proskauer, LeBoeuf, Chadbourne, White & Case, Wilson Elser, and row 19 ($321m, 371 lawyers), which the blog mislabels "Seyfarth Shaw" (Seyfarth also appears at row 90). Classification is mine ([A]). |
| Revenue per lawyer, NY elite firms, FY2005 | Wachtell $2.40m; Sullivan & Cromwell $1.63m; Cravath $1.28m; Davis Polk $1.14m; Simpson Thacher $1.12m; Paul Weiss $1.03m; Am Law 100 overall about $0.73m | [S] | *Adam Smith, Esq.*, RPL table (above) |
| NY share of Am Law 100 lawyers by office location | not found | — | NLJ 250 / NYLJ 100 2005 office counts are behind law.com (403) |

**New York large-firm market estimate, FY2005: about $14bn (range $11–17bn)** ([D/A]). Three cross-checks:

| Route | Arithmetic | Result |
| --- | --- | --- |
| A. Firms' NY offices | (i) NY-headquartered Am Law 100 firms' NY offices: $14.74bn × 65% NY-office share [A] = $9.6bn. (ii) Non-NY Am Law 100 firms' NY offices (Latham, Kirkland, Sidley, Jones Day, Greenberg, DLA and others): $36.2bn × 8% [A] = $2.9bn. (iii) NY-based Second Hundred firms: about $1.5bn [A]. | about $14.0bn |
| B. Manhattan Census share | $21.2bn Manhattan offices-of-lawyers revenue × 60–75% in large offices [A] (Manhattan holds 61% of the nation's 1,000+ employee law offices) | $12.7–15.9bn |
| C. Payroll ratio | NY MSA 5411 payroll share 14.6% × Am Law 200 US-sourced revenue $56bn | about $8.2bn. A floor: big firms' revenue/payroll is far higher in NY than the US average. |

The game's NY region demand base should total **about $14bn a year in 2005** for all practices. The v1 ten practices carry about 83% of it (§4).

## 4. Spend by practice, New York large-firm market, 2005

**Practice list.** The spec does not name v1's ten practices. This dossier assumes the first ten rows of spec §6's table. That is a default for the owner (Reece) to confirm.

**Method.**
- Shares of the $14bn NY total are [A]. They reflect:
  - NY's transactional bias: the NY elite are deal and finance houses.
  - Survey evidence that litigation is 58% of large-company spend (F&J 2006). That figure is national and includes non-elite firms, so NY elite litigation shares are lower.
  - The activity proxies below.
- Ranges are judgement bands. Totals are kept coherent: the ten v1 practices plus "other" sum to 100%.

**Activity proxies found (2005).**

| Proxy | Figure | Tag | Source |
| --- | --- | --- | --- |
| US announced M&A | above $1.1tn (+30% from $886.2bn in 2004; highest since 2000) | [S] (secondary) | Dealogic via CFO.com, Dec 2005, https://www.cfo.com/news/ma-activity-highest-since-dotcom-days/677474/ |
| Worldwide announced M&A | $2,706.3bn, 32,726 deals (Thomson); Dealogic $2.9tn | [S] | SIFMA *2006 Fact Book Addendum*, https://www.sifma.org/wp-content/uploads/2017/05/us-factbook-addendum-2006.pdf ; CFO.com as above |
| US buyout and mezzanine fundraising | about $86.2bn, a record (+67% from $51.6bn in 2004); 17 megafunds raised 67% | [S] (secondary) | Thomson Venture Economics / NVCA release (Jan 2006), as summarised in search results from https://truthonthemarket.com/2006/01/18/record-year-for-private-equity-fundraising and https://www.buyoutsinsider.com/a-bumper-year-for-private-equity-fundraising/ |
| Largest 2005 fund | Blackstone about $11bn (Q4) | [S] (secondary) | same |
| US debt and equity underwriting | record $3.2tn (+12%) | [S] | SIFMA 2006 Fact Book Addendum |
| US bond issuance (incl. government) | $5,596bn | [S] | same, "World Bond Market Issuance" table |
| US IPOs | 158 IPOs, $26.2bn (WilmerHale basis); Dealogic 226 IPOs, $38.7bn | [S] (secondary) | WilmerHale *2005 IPO Report*, https://www.wilmerhale.com/-/media/files/wilmerhale_shared_content/files/editorial/publication/2005_ipo_report.pdf (figures from the search summary; PDF not opened) |
| Global corporate default rate | 0.56%; speculative grade 1.40% (2004: 2.00%) | [S] | SIFMA 2006 Fact Book Addendum |
| US bankruptcy filings, CY2005 | 2,078,415 total (consumer spike before the BAPCPA reform of October 2005); 39,201 business; **6,800 Chapter 11** | [S] | US Courts Table F-2, 12 months to 31 Dec 2005, https://www.uscourts.gov/sites/default/files/statistics_import_dir/1205_f2.xls |
| Chapter 11 in SDNY (Manhattan), CY2005 | 790 cases (of 6,800 nationally: 11.6% [D]) | [S] | same |
| Federal civil filings, FY to 30 Sep 2005 | total 253,273; contract 28,020; securities 2,038; antitrust 818; patent 2,720; copyright 5,796; trademark 3,668; civil rights–employment 16,930; labour laws 18,322 | [S] | US Courts Table C-2, https://www.uscourts.gov/sites/default/files/statistics_import_dir/c2_1.pdf |
| US leveraged-loan volume 2005 | not found | — | search budget exhausted |
| PwC patent study counts | not found (US Courts patent filings used instead) | — | search budget exhausted |
| EEOC charges FY2005 | not found (eeoc.gov URLs 404) | — | federal employment civil-rights suits used instead |
| ICC / AAA-ICDR caseloads 2005 | not found | — | search budget exhausted |
| Enforcement intensity (SEC/DOJ) | not found | — | — |

**Practice sizes, NY large-firm market, 2005.**

| # | Practice | Share | Central | Range | Reasoning (all [A] unless tagged) |
| --- | --- | --- | --- | --- | --- |
| 1 | Corporate and M&A | 17% | $2.4bn | $1.9–3.0bn | US M&A of $1.1tn [S] × total legal fees of about 0.15–0.35% of deal value, all sides [A], gives $1.7–3.9bn nationally. NY firms advise on about 50–60% of US deal value by league-table credit [A], so $0.8–2.3bn is deal work. Add general corporate, governance and securities advice. |
| 2 | Private equity and funds | 8% | $1.1bn | $0.8–1.5bn | Record buyout fundraising of $86bn [S] and an LBO boom. Fund formation is concentrated at a few NY firms (Simpson Thacher, Debevoise, Kirkland NY, Ropes NY). Includes buyout M&A not counted in row 1. |
| 3 | Capital markets | 9% | $1.3bn | $1.0–1.7bn | Record US underwriting of $3.2tn [S], mostly debt and asset-backed. Issuer and underwriter counsel fees of about 0.03–0.05% of proceeds [A] gives $1.0–1.6bn nationally, about 70% NY [A]. Add 34-Act and SOX compliance advice. |
| 4 | Banking and finance | 8% | $1.1bn | $0.8–1.4bn | Leveraged lending boom (volume not found); acquisition finance runs with the LBO boom. NY is the lender-counsel centre (Cahill, Simpson Thacher, Davis Polk, Milbank). |
| 5 | Restructuring and insolvency | 5% | $0.7bn | $0.5–1.0bn | Low defaults (1.40% speculative grade [S]), but SDNY hosted 790 Chapter 11 cases in 2005 [S], including large airline and broker cases. Counter-cyclical: should be at a cyclical low in 2005 and roughly double by 2009. |
| 6 | Commercial litigation | 18% | $2.5bn | $2.0–3.2bn | Litigation is 58% of large-company spend nationally [S]. NY elite firms are transaction-heavy, so all disputes here (rows 6–9 litigation parts and 10) come to about 36%. Commercial contract and securities suits dominate (contract filings 28,020; securities 2,038 [S]). |
| 7 | White collar and investigations | 6% | $0.85bn | $0.6–1.2bn | Post-Enron and SOX era. SDNY and EDNY prosecutions; internal investigations; FCPA beginning to rise. Policy-driven. |
| 8 | International arbitration | 2% | $0.3bn | $0.2–0.5bn | Small in 2005 NY: concentrated at White & Case, Freshfields NY, Debevoise, Shearman, Cleary, Skadden. Caseloads not found. |
| 9 | IP (patent litigation, prosecution, transactional) | 6% | $0.85bn | $0.6–1.1bn | NY is not the IP hub (East Texas, Delaware, California). 2,720 federal patent suits and 5,796 copyright suits nationally in FY2005 [S]; NY is strong on copyright, trademark and media. Prosecution is mostly at specialist firms. |
| 10 | Employment and labour | 4% | $0.55bn | $0.4–0.8bn | 16,930 federal employment civil-rights suits and 18,322 labour-law suits nationally [S]. At NY large firms this is mostly defence and executive compensation; much of it goes to specialists (e.g. Proskauer, Jackson Lewis). |
| — | **v1 subtotal** | **83%** | **$11.65bn** | $8.8–15.4bn | [D] sum of rows 1–10 |
| — | Other practices (tax, real estate, antitrust, financial regulation, healthcare, energy, technology, private client, insurance, mass torts) | 17% | $2.35bn | $1.8–3.0bn | Remainder. Tax and real estate are large in NY (the 2005 property boom). |
| — | **Total NY large-firm market** | **100%** | **$14.0bn** | $11–17bn | §3 |

**For `practices.yaml`.** If v1 has only ten practices, there are two options:
- Scale the ten up to the full $14bn, multiplying each by 1/0.83.
- Keep $11.65bn and treat the rest as unserved demand.

I would keep $11.65bn, so that later practices add demand rather than redistribute it ([A]; for the owner to decide).

## 5. Billing rates 2005 at top New York firms

**What was found.**

| Item | Figure | Tag | Source |
| --- | --- | --- | --- |
| First four-figure hourly rate reported to the NLJ, 2005 | $1,000: Benjamin Civiletti, Venable (Baltimore), up from $810 in 2004 | [S] (secondary) | NLJ Dec 2005 survey, via blog posts dated 12 and 14 Dec 2005: https://www.indianabarrister.com/?p=181 ; https://lgles.blogspot.com/2005/12/hourly-billing-rates-continue-to-rise.html |
| NLJ 2005 survey coverage | 116 of the 250 largest firms gave rates. Of 102 firms reporting both years, 79 raised partner high rates (10 cut, 13 flat) and 76 raised partner low rates. | [S] (secondary) | lgles.blogspot.com, 14 Dec 2005 (as above) |
| NLJ average billing rate, all reporting firms | 2006: $321; 2007: $348 (+7.7%) | [S] | ABA Journal, 11 Dec 2007, https://www.abajournal.com/news/article/big_firm_hourly_billing_rates_up_almost_8_average_is_348 |
| $1,000/hour partners by 2007 | WilmerHale (range $475–$1,000); Simpson Thacher, Cadwalader and Fried Frank previously reported at $1,000 | [S] | same |
| NY averages, 2013 (late anchor) | partners $882, associates $520 (national averages $604 and $370; NY premium ×1.46 and ×1.41 [D]) | [S] (secondary) | NLJ Jan 2014 survey via MarketScreener press release, 13 Jan 2014, https://marketscreener.com/news/latest/The-National-Law-Journal-Reports-That-1-in-5-of-the-Largest-U-S-Law-Firms-Employ-Partners-Who-Charg-17807800 |
| NY partner low rates, 2013, selected firms | Proskauer and Hughes Hubbard $725; Kaye Scholer $715; White & Case $700 | [S] (secondary) | Above the Law, Jan 2014, https://abovethelaw.com/2014/01/the-biglaw-firms-with-the-highest-partner-billing-rates/ |
| NLJ 2005 New York firm-by-firm table | not found | — | law.com 403 |
| Bankruptcy fee applications, 2005 (Delta, Refco, Calpine, Northwest) | not found | — | search budget exhausted; court dockets not reachable without search |

**Derived 2005 rate card, top NY firm ([D/A]).**
- **Back-cast.** I worked back from the 2013 NY averages with these growth rates ([A], consistent with the NLJ's +7.7% for 2007 [S]): about 7% a year for 2006–2008, about 1% in 2009, about 3.5% a year for 2010–2013. Cumulative factor 1.07³ × 1.01 × 1.035⁴ = 1.42.
- **Result.** NY average partner rate in 2005 ≈ $882 ÷ 1.42 = **$620**. NY average associate rate ≈ $520 ÷ 1.42 = **$365**.
- **Elite premium.** Top NY firms sat above the NY average by about 10–15% ([A]).

| Role | Low | Median | High | Tag and basis |
| --- | --- | --- | --- | --- |
| Partner | $525 | $700 | $950 (very rare $1,000) | [D/A]: NY average about $620 × 1.1–1.15 elite premium. $1,000 was a 2005 outlier outside NY [S]; NY elite firms reached $1,000 by 2007 [S]. |
| Counsel | $475 | $575 | $700 | [A]: about 80% of partner median |
| Senior associate (6th–8th year) | $450 | $500 | $575 | [A]: about 1.35 × the associate average |
| Mid-level associate (3rd–5th year) | $350 | $410 | $475 | [A] |
| Junior associate (1st–2nd year) | $225 | $265 | $310 | [A]: about 0.7 × the associate average |
| Paralegal | $140 | $185 | $240 | [A]: typical 2005 range from memory, not verified |

**Rate growth by year** (spec §14 says "rate rises 6–8% a year" for 2005–2007):

| Year | Growth | Tag |
| --- | --- | --- |
| 2005 | about 6–7% (most firms raised both ends of their ranges) | [A]; [S] for direction only |
| 2006 | about 7% (2005 average ≈ $321 ÷ 1.07 = $300 [D/A]) | [A] |
| 2007 | +7.7% | [S] |
| 2008 | about 6–7% (rates set in January, before Lehman) | [A] |
| 2009 | about 0–2%: freeze announcements and discounts | [A]; freeze stories not verified this session |

**Comparison with spec §6 placeholders.**
- The spec's $550–$850 range sits well with a top-NY-firm partner range of $525–$950. The flags:

| Practice | Spec | Dossier view | Flag |
| --- | --- | --- | --- |
| Corporate and M&A | $750 | median $700–750 | OK |
| Private equity and funds | $800 | $725–800 | OK, slightly high |
| Capital markets | $750 | $700–750 | OK |
| Banking and finance | $700 | $650–700 | OK |
| Restructuring | $850 | $750–850 | High-end but plausible (bankruptcy partners were among the highest-rate lawyers); not verified against 2005 fee applications |
| Commercial litigation | $700 | $650–725 | OK |
| White collar | $800 | $700–800 | Slightly high for 2005 |
| International arbitration | $700 | $650–700 | OK |
| IP | $650 | $575–650 | OK |
| Employment | $550 | $475–575 | OK |

- Main caveat: the spec values read as **senior or star partner** rates at the elite. If `practices.yaml` uses them as the average partner rate, they are about 5–10% high ([A]).

## 6. First-year associate salary scale 2005–2015 (big-firm New York)

**Main source.** Biglaw Investor, "Biglaw Salary Scale" (secondary; page current as of Nov 2026), https://www.biglawinvestor.com/biglaw-salary-scale/ . Supporting:
- Wikipedia "Big Law": Cravath $180k in summer 2016; Milbank $190k (2018) and $215k (2022). https://en.wikipedia.org/wiki/Big_Law
- Wikipedia "Big Law" (citing NALP): 2006 median starting pay at firms of over 501 lawyers was $160k. That figure is inconsistent with the $145k scale for 2006; it probably reflects the class starting in autumn 2007 or NALP's survey timing ([A] explanation).

**First-year base and changes.**

| Year | First-year base | Change date | Tag |
| --- | --- | --- | --- |
| 2000–2005 | $125,000 | from 2000 | [S] |
| 2006 | $145,000 | effective 1 Jan 2006. Leader not stated by the source; the brief's "Simpson Thacher" is unverified. | [S] amount; [A] leader |
| 2007–2015 | $160,000 | effective 1 Jan 2007; flat through 2015 | [S] |
| 2016 (beyond range) | $180,000 | effective 1 July 2016 (Cravath, summer 2016) | [S] |

**Class-year scale (base).**

| Class year | 2005 | 2006 | 2007–2015 |
| --- | --- | --- | --- |
| 1st | 125,000 | 145,000 | 160,000 |
| 2nd | 135,000 | 155,000 | 170,000 |
| 3rd | 150,000 | 170,000 | 185,000 |
| 4th | 170,000 | 190,000 | 210,000 |
| 5th | 190,000 | 200,000 | 230,000 |
| 6th | 205,000 | 210,000 | 250,000 |
| 7th | 215,000 | 220,000 | 265,000 |
| 8th | 225,000 | 220,000 | 280,000 |

All [S] (Biglaw Investor). Flag: the source's 2006 8th-year figure ($220k) is lower than its 2005 figure ($225k). That is probably an error on the page; treat 2006 senior years as unverified.

**Year-end bonus by class year (regular bonus; special bonuses excluded by the source).**

| Bonus year | 1st | 2nd | 3rd | 4th | 5th | 6th | 7th | 8th |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2005 | 30,000 | 35,000 | 40,000 | 45,000 | 50,000 | 55,000 | 60,000 | 60,000 |
| 2006 | 30,000 | 35,000 | 40,000 | 45,000 | 50,000 | 55,000 | 65,000 | 65,000 |
| 2007 | 45,000 | 55,000 | 65,000 | 80,000 | 95,000 | 110,000 | 110,000 | 110,000 |
| 2008 | 35,000 | 40,000 | 45,000 | 50,000 | 55,000 | 60,000 | 60,000 | 60,000 |
| 2009 | 7,500 | 10,000 | 15,000 | 20,000 | 25,000 | 30,000 | 30,000 | 30,000 |
| 2010 | 7,500 | 10,000 | 15,000 | 20,000 | 25,000 | 30,000 | 35,000 | 35,000 |
| 2011 | 7,500 | 10,000 | 15,000 | 20,000 | 25,000 | 30,000 | 37,500 | 37,500 |
| 2012 | 10,000 | 14,000 | 20,000 | 27,000 | 34,000 | 40,000 | 50,000 | 60,000 |
| 2013 | 10,000 | 14,000 | 20,000 | 27,000 | 34,000 | 40,000 | 50,000 | 60,000 |
| 2014 | 15,000 | 25,000 | 40,000 | 55,000 | 70,000 | 85,000 | 100,000 | 100,000 |
| 2015 | 15,000 | 25,000 | 50,000 | 65,000 | 80,000 | 90,000 | 100,000 | 100,000 |

All [S] (Biglaw Investor), with these flags:
- The 2007 row likely folds in the 2007 special bonus.
- The 2008 row ($35k for first years) conflicts with the widely reported halving of 2008 bonuses. That report is my recollection ([A]), not verified this session.
- Some 2009–2011 figures are pro-rated or "spring bonus" amounts at some firms.
- Verify against Above the Law's bonus tracker (blocked: 403) before treating 2008–2011 as final.

**2008–2009 deferrals and layoffs.**
- "Major firms cut over 10,000 jobs nationally" in 2009; about 700 jobs were cut in one day in February 2009 [S] (secondary: Wikipedia "Big Law" citing the Denver Post and Bloomberg).
- Deferred start dates for the 2009 entering class (many pushed to 2010, some with stipends): [A] from memory. Not verified this session.

**Comparison with spec §5.4 history line.**

| Spec says | Dossier | Flag |
| --- | --- | --- |
| $125,000 in 2005 | $125,000 (2000–2005) | OK |
| (no 2006 step) | $145,000 from 1 Jan 2006 | **Missing step**: add $145k for 2006 |
| $160,000 from 2007 | $160,000 from 1 Jan 2007 | OK |
| $180,000 from 2016 | $180,000 effective 1 July 2016 | OK; mid-year change |
| $190,000 from 2018 | $190,000 effective 1 July 2018 | OK |
| "$202,500 then $215,000 in 2021–22" | $205,000 (effective 1 July 2021), then $215,000 (announced 20 Jan 2022, Milbank) | **Disagreement**: source says $205k, not $202.5k (2021 is outside this dossier's 2005–2015 range; re-check) |
| $225,000 from 2024 | $225,000 effective 1 Jan 2024 (Milbank, announced 7 Nov 2023) | OK |
| (end of history) | Source also lists $235,000 effective 1 Jan 2027 (Cravath, announced 17 Nov 2026) | Note for the seeded era; outside the 2025 history window |

## 7. Other useful 2005 norms

| Norm | Figure | Tag | Source or basis |
| --- | --- | --- | --- |
| Revenue per lawyer, Am Law 100 | about $730k | [D] | §2 |
| Profit per (equity) partner, Am Law 100 average | $1.06m | [S] (secondary) | *Adam Smith, Esq.*, 17 May 2006 |
| Collection, late anchor (2013) | 83.5 cents per dollar billed | [S] (secondary) | Georgetown Center for the Study of the Legal Profession, cited in the NLJ Jan 2014 release (MarketScreener, above) |
| Realisation / collection, 2005 | not found | — | Citi / Wells Fargo LSG / Hildebrandt: search budget exhausted. Spec §6's 85–95% realisation and 93–98% collection remain [A]. Pre-2008 realisation was roughly 90%+ ([A]); the 2013 anchor of 83.5% is all-in. |
| Leverage (associates per partner) | not found | — | Elite NY lockstep firms ran roughly 3–5 associates per partner; spec §6's norms (2.0–4.5) are consistent ([A]). |
| Billable-hour targets | not found | — | 1,950–2,100 at NY firms in 2005 is the commonly cited norm ([A]; not verified) |
| Associate attrition | not found | — | NALP Foundation attrition studies not reached; about 18–20% a year in boom years ([A]) |
| Lawyer pay level, Manhattan law offices | about $106k payroll per employee, all staff | [D] | CBP 2005 (§3) |

## 8. Gaps and open questions

1. **Practice list.** The spec does not name v1's ten practices. This dossier assumed the first ten rows of §6. Owner to confirm.
2. **Demand for non-v1 practices.** Should the v1 demand base be $11.65bn (unserved rest) or the full $14bn? See §4 for my default.
3. **Am Law Second Hundred FY2005 total.** Not found (law.com 403). The $14.5bn is [A].
4. **NY office-level revenue or lawyer counts** (NLJ 250 / NYLJ 100, 2005). Not found. The NY market of $14bn rests on [A] office shares (65% / 8%).
5. **NLJ December 2005 and 2006 New York rate tables, and 2005 bankruptcy fee applications** (Delta, Refco, Calpine, Northwest). Not found. The whole §5 rate card is back-cast [D/A] from 2013. This is the most important gap for rate cards.
6. **2009 rate-freeze stories and 2008–2011 bonus figures.** Not verified. The Biglaw Investor 2008 bonus row is suspect.
7. **Activity proxies not checked:**
   - leveraged-loan volume 2005
   - Moody's US default rate
   - PwC patent study
   - EEOC FY2005 charges
   - ICC / AAA-ICDR 2005 caseloads
   - SEC / DOJ enforcement counts
   - BTI / ACC total corporate legal spend
   - NY State Economic Census 2007 revenue (needs a Census API key or the 2007 EC geographic PDFs)
8. **Spec §5.4.** Add the 2006 $145k step; check $202.5k against $205k for 2021.
9. **Spec §6 restructuring ($850) and white collar ($800).** Plausible high-end rates but unverified. If `practices.yaml` means average partner rate, reduce by 5–10%.
10. **Next step.** A follow-up session with a fresh search budget should target items 3–7, in that order.
