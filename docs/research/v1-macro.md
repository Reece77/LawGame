# V1 macro dossier: the US cycle 2005–2015 and the real clients history fails

| Item | Value |
| --- | --- |
| Purpose | Inputs for PT-M7's `macro_history.yaml` (the macro and legal indices, spec 6 and 14) and `clients.yaml`'s dated failures. |
| Compiled | 21 November 2026, a short research pass (the product manager's addition to the PT-M7 brief, 2026-11-20). |
| Scope | US, calendar or fiscal years 2005–2015 as each row says. |

**Tags.** **[S]** seen in the cited source this session; **[A]** approximate or from memory (check before treating as canonical); **[D]** derived from [S] figures.

Sections: **s1** corporate failures (Part A below), **s2** annual indices (Part B below), **s3** how the game's indices are derived from s2.

## s1. Corporate failures (Part A)

Kinds used below:
- **ch11**: a Chapter 11 filing. Pre-petition unsecured creditors, such as law firms with unpaid bills, become general unsecured claimants and are typically impaired.
- **363**: a §363 sale, in which the good assets go to a new company and old unsecured claims stay behind in the bankrupt estate.
- **seizure**: a government seizure or conservatorship.
- **rescue**: a distressed acquisition. The acquirer takes on the target as a going concern and its debts are honoured.

| Company | Failure event (date) | Kind | Unsecured pre-failure creditors | Exit / close (if 2005-15) | Tag | Source |
|---|---|---|---|---|---|---|
| Lehman Brothers Holdings | 15 Sep 2008 | ch11 (largest ever, ~$639bn assets). Barclays bought the US broker-dealer via a 363 sale that closed 22 Sep 2008 | Left unpaid (estate paid cents on the dollar over years) | Plan effective 6 Mar 2012 | [A] | https://en.wikipedia.org/wiki/Bankruptcy_of_Lehman_Brothers |
| Bear Stearns | Announced 16 Mar 2008 ($2/sh, raised to $10 on 24 Mar), with Fed backstop | rescue by JPMorgan Chase | Assumed by acquirer | Closed 30 May 2008 | [A] | https://en.wikipedia.org/wiki/Bear_Stearns |
| General Motors | 1 Jun 2009 | ch11 + 363 sale to "New GM" | Left behind in Motors Liquidation Co (old GM); most trade creditors critical to operations were assumed | 363 sale closed 10 Jul 2009 | [A] | https://en.wikipedia.org/wiki/General_Motors_Chapter_11_reorganization |
| Chrysler LLC | 30 Apr 2009 | ch11 + 363 sale to Chrysler Group LLC (Fiat) | Left behind in Old Carco LLC (except assumed contracts) | 363 sale closed 10 Jun 2009 | [A] | https://en.wikipedia.org/wiki/Chrysler_Chapter_11_reorganization |
| Washington Mutual Bank | 25 Sep 2008 | seizure by OTS, with FDIC receivership; deposits and most assets sold to JPMorgan Chase the same night | Bank-level liabilities assumed by JPMorgan; holding-company creditors not covered | n/a | [A] | https://en.wikipedia.org/wiki/Washington_Mutual |
| Washington Mutual Inc (WMI holding co) | 26 Sep 2008 | ch11 | Left unpaid / impaired | Plan effective 19 Mar 2012 (became WMI Holdings) | [A] | https://en.wikipedia.org/wiki/Washington_Mutual |
| Merrill Lynch | Announced 14-15 Sep 2008 | rescue by Bank of America | Assumed | Closed 1 Jan 2009 | [A] | https://en.wikipedia.org/wiki/Merrill_Lynch |
| Wachovia | Wells Fargo deal announced 3 Oct 2008. Citigroup's FDIC-assisted bid of 29 Sep was superseded | rescue | Assumed | Closed 31 Dec 2008 | [A] | https://en.wikipedia.org/wiki/Wachovia |
| Countrywide Financial | Announced 11 Jan 2008 | rescue by Bank of America | Assumed | Closed 1 Jul 2008 | [A] | https://en.wikipedia.org/wiki/Countrywide_Financial |
| National City | Announced 24 Oct 2008 (TARP-funded) | rescue by PNC | Assumed | Closed 31 Dec 2008 | [A] | https://en.wikipedia.org/wiki/National_City_Corp. |
| Fannie Mae and Freddie Mac | Announced 7 Sep 2008 (effective 6-7 Sep) | seizure (FHFA conservatorship; Treasury preferred-stock backstop) | Paid: debts continued to be honoured, and only equity was wiped | Still in conservatorship | [A] | https://en.wikipedia.org/wiki/Federal_takeover_of_Fannie_Mae_and_Freddie_Mac |
| AIG | 16 Sep 2008 ($85bn Fed loan for 79.9% equity) | government rescue, closest to "seizure". No bankruptcy | Paid; counterparties were made whole | Treasury exited Dec 2012 | [A] | https://en.wikipedia.org/wiki/American_International_Group |
| General Growth Properties | 16 Apr 2009 | ch11 (then largest US real-estate bankruptcy) | Paid in full: an unusual solvent-debtor outcome with full recovery for unsecured creditors | Emerged Nov 2010 (about 9 Nov) | Filing [S], emergence date [A] | https://en.wikipedia.org/wiki/General_Growth_Properties |
| Visteon | 28 May 2009 | ch11 | Impaired | Emerged 1 Oct 2010 | [S] | https://en.wikipedia.org/wiki/Visteon |
| Lear | 7 Jul 2009 | ch11 (prepackaged, ~$3.6bn debt) | Trade creditors generally paid in prepack; bondholders impaired | Emerged 9 Nov 2009 | [S] | https://www.sec.gov/Archives/edgar/data/0000842162/000095012311011395/k50033e10vk.htm |
| Delphi | 8 Oct 2005 | ch11 | Impaired | Emerged 6 Oct 2009 (assets sold to lenders' DPH and to GM) | [A] | https://en.wikipedia.org/wiki/Delphi_Automotive |
| Delta Air Lines | 14 Sep 2005 | ch11 | Impaired (paid in new stock) | Emerged 30 Apr 2007 | [A] | https://en.wikipedia.org/wiki/Delta_Air_Lines |
| Northwest Airlines | 14 Sep 2005 (same day as Delta) | ch11 | Impaired | Emerged 31 May 2007 | [A] | https://en.wikipedia.org/wiki/Northwest_Airlines |
| Dana Corporation | 3 Mar 2006 | ch11 (~$3bn of unsecured claims resolved) | Impaired | Emerged 31 Jan 2008 as Dana Holding Corp | [S] | https://www.sec.gov/Archives/edgar/data/26780/000095015208001968/l30266ae10vk.htm |
| AMR (American Airlines) | 29 Nov 2011 | ch11 | Ultimately paid near-par in merged-company stock, which was unusual | Emerged 9 Dec 2013 with the US Airways merger | [S] | https://en.wikipedia.org/wiki/AMR_Corporation |
| HBOS (UK) | Announced 18 Sep 2008 | rescue by Lloyds TSB, with government-brokered competition waiver and recapitalisation | Assumed (HBOS became a Lloyds Banking Group subsidiary) | Completed 19 Jan 2009 | [S] | https://en.wikipedia.org/wiki/HBOS |

**Chrysler Group 2005 revenue (DaimlerChrysler segment): about €50.1bn, roughly US$62bn** at the 2005 average rate of ~1.24 $/€. The euro figure is [S], read from a scrambled key-figures table in the annual report. The dollar conversion is [A]. Source: https://group.mercedes-benz.com/documents/investors/berichte/geschaeftsberichte/daimlerchrysler/daimler-ir-annualreport-2005.pdf

## s2. Annual US indices 2005-2015 (Part B)

| Series (units) | 2005 | 2006 | 2007 | 2008 | 2009 | 2010 | 2011 | 2012 | 2013 | 2014 | 2015 | Tag / source |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1. US announced M&A value (US$tn, US targets) | 1.2 | 1.6 | 1.6 | 0.9 | 0.7 | 0.9 | 1.25 | 1.0 | 1.2 | 1.6 | 2.3 | [A]; 2011 [S] IMAA (10,536 deals, $1,247bn). 2015 was a record year. Check against IMAA (imaa-institute.org) or Dealogic |
| 2a. US PE deal value (US$bn, PitchBook-style) | 300 | 580 | 700 | 300 | 120 | 300 | 360 | 410 | 400 | 520 | 560 | [A]. Shape is reliable (2007 peak, 2009 trough), levels are not. Source: PitchBook Annual US PE Breakdown (files.pitchbook.com) |
| 2b. US PE fundraising (US$bn) | 130 | 220 | 300 | 290 | 125 | 95 | 115 | 120 | 185 | 200 | 190 | [A]. Source: PitchBook |
| 3. US IPOs (count) | 159 | 157 | 159 | 21 | 41 | 91 | 81 | 93 | 158 | 206 | 118 | [S] Jay Ritter, IPO Statistics (operating-company IPOs, ex-SPACs, units, REITs, penny stocks): https://site.warrington.ufl.edu/ritter/files/IPO-Statistics.pdf |
| 3b. US IPO proceeds (US$bn) | 28.2 | 30.5 | 35.7 | 22.8 | 13.2 | 29.8 | 27.0 | 31.1 | 41.6 | 42.2 | 22.0 | [S] Ritter, same |
| 4. US leveraged loan issuance (US$bn, S&P LCD) | 480 | 480 | 535 | 170 | 77 | 234 | 370 | 465 | 605 | 535 | 440 | 2009 and 2010 [S] (LCD via Fortune: https://fortune.com/2010/12/22/dividends-were-the-years-big-leveraged-loan-story/). 2013 ">$600bn pace" [S] (Fed, Powell 2015: https://www.federalreserve.gov/newsevents/speech/powell20150218a1.htm). Other years [A] |
| 5a. Moody's global spec-grade default rate (%, issuer-weighted, year-end) | 1.8 | 1.6 | 0.9 | 4.1 | 13.1 | 3.2 | 1.8 | 2.6 | 2.8 | 2.0 | 3.4 | 2005, 2006, 2009, 2010 and 2015 [S] (Moody's / press: https://www.moodys.com/sites/products/DefaultResearch/2006400000429618.pdf; https://investmentexecutive.com/?p=304688). 2007, 2008 and 2011-14 [A]. US-only rates run similar, with 2009 at ~14% |
| 5b. US business Chapter 11 filings (count) | 6,800 | 5,200 | 6,400 | 9,300 | 15,000 | 13,700 | 11,500 | 10,000 | 9,000 | 7,300 | 7,200 | [A]. Source: US Courts bankruptcy statistics (Table F-2) or Epiq/ABI |
| 6. Civil cases filed, US district courts (count, FY to 30 Sep) | 253,300 | 259,500 | 257,500 | 267,300 | 276,400 | 282,895 | 289,300 | 278,400 | 284,600 | 295,310 | 279,036 | 2010, 2014 and 2015 [S] (uscourts.gov Judicial Business: https://www.uscourts.gov/data-news/reports/statistical-reports/judicial-business-united-states/judicial-business-2014). Other years [A], consistent with the [S] points |
| 7a. SEC enforcement actions (count, FY) | 630 | 574 | 655 | 671 | 664 | 681 | 735 | 734 | 676 | 755 | 807 | [S] SEC enforcement statistics, https://www.sec.gov/news/newsroom/images/enfstats.pdf, and FY2015 release https://www.sec.gov/news/press-release/2015-245 |
| 7b. FCPA enforcement actions, DOJ+SEC (count) | 12 | 15 | 38 | 33 | 40 | 74 | 48 | 23 | 22 | 26 | 23 | [A]. Shape: surge 2007-10, peak 2010. Source: Stanford FCPA Clearinghouse, https://fcpa.stanford.edu/statistics-analytics.html |
| 8. Big-law billing/worked rate growth (%) | 6.0 | 6.5 | 6.5 | 6.0 | 2.5 | 3.0 | 4.0 | 3.4 | 3.3 | 3.3 | 3.0 | 2012 [S] (Peer Monitor, firms raised rates 3.4%: Georgetown/Thomson Reuters 2013 Report on the State of the Legal Market, https://archive.annual-report.thomsonreuters.com/2012/_files/pdf/2013ReportLegalIndustryPMGeorgetown.pdf). Pre-2008 "6 to 8%" a year [S] same report. Other years [A] |
| 9. Lateral partner moves, Am Law 200 (count, year to 30 Sep) | ~2,300 | ~2,350 | ~2,450 | 2,509 | 2,775 | ~2,015 | ~2,453 | 2,691 | 2,522 | 2,736 | 2,890 | 2008, 2009 and 2012-15 [S] (Am Law Lateral Report via ABA Journal / ALM). 2010 and 2011 [D] from 2012's "+33.6% vs 2010, +9.7% vs 2011". 2005-07 [A]. The 2009 record was driven by collapses (Thelen, Heller, WolfBlock); 2012 includes 280 from Dewey |
| 10a. Am Law 100 gross revenue growth (%, fiscal year) | +7.5 | +12.4 | +11.7 | +3.5 | -4.1 | +1.3 | +4.3 | +3.4 | +5.3 | +4.9 | +4.3 | 2012 [S] (Am Law 2013 via Above the Law: https://abovethelaw.com/2013/04/the-2013-am-law-100-a-year-of-slow-growth/). Others [A]. 2009 was the first revenue decline in Am Law 100 history |
| 10b. Large-firm demand (billable hours) growth (%, Peer Monitor/Citi) | +2.5 | +2.5 | +2.0 | -0.5 | -5.0 | -0.7 | +0.4 | +0.5 | -0.5 | +0.5 | +0.2 | 2012 +0.5% [S] (Georgetown 2013). 2009 by segment [S]: Am Law 50 -5.5%, Am Law 51-100 -3.2%, Second Hundred -1.0% (Citi/Peer Monitor). The 2009 segment drops from 2008 imply 2008 at about +2.6% (Am Law 50) and +2.8% (Am Law 51-100) [D], though the industry-wide 2008 figure was about flat [A]. 2015 nine-month figure +0.6% [S] (Citi 2016 Client Advisory). Others [A]. Eight straight negative quarters ran 2008Q4-2010Q3 [S] |
| 11. US commercial real estate sales volume (US$bn, RCA, deals ≥$2.5m) | 400 | 430 | 570 | 230 | 65 | 135 | 215 | 295 | 355 | 440 | 550 | [A]. 2015 is [D] from 2016 = $489bn, down 11% [S] (GlobeSt: https://www.globest.com/2018/01/25/cre-volume-dips-amid-buyerseller-pricing-gap). 2007 Q1-Q3 was $448bn [S] (Bisnow) |
| 12. US unemployment rate (%, annual average) | 5.1 | 4.6 | 4.6 | 5.8 | 9.3 | 9.6 | 8.9 | 8.1 | 7.4 | 6.2 | 5.3 | [A], high confidence. Source: BLS CPS LNU04000000, https://data.bls.gov/timeseries/LNU04000000 |

## Caveats

- **Series 2, 4, 8, 10 and 11 are mostly [A].** Their direction and turning points are reliable: a 2007 peak, a 2009 trough, recovery from 2010 and records in 2014-15. Their exact levels are not. Normalise them to index form, with 2007 = 100, rather than relying on absolute values.
- **Periods differ by series.** SEC, civil-filing and Lateral Report figures are fiscal-year or year-to-30-Sep. The others are calendar years.
- **The Part A dates tagged [A] are standard, widely reported dates from memory.** Their Wikipedia URLs were not re-fetched in this session.

## s3. From s2 to `macro_history.yaml`

- Every index is 1.0 at the 2005 average. Mid-year points (July) carry each year's figure; points in October 2008 and April 2009 carry the crash's timing (demand fell in eight straight quarters from 2008 Q4, s2 row 10b [S]).
- **Damping [D/A].** Legal work follows deal counts and hours more than deal values, so dollar-volume series enter as about the square root of their ratio to 2005: `ma` (row 1), `pe` (row 2a), `lending` (row 4), `real_estate` (row 11). `issuance` blends IPO counts (row 3 [S]) with the 2009–2015 debt-issuance boom [A].
- **credit** = sqrt(2005's default rate / the year's) (row 5a), held at 1.25 at most (2007's 0.9% would otherwise give 1.41), so restructuring (beta −1.2, spec 6) roughly doubles in 2009.
- **cycle** [A]: real activity relative to 2005; litigation (beta −0.2) and employment (beta −0.3) move slightly against it. Row 6 (civil filings +12% by 2010) supports litigation's mild counter-cyclical rise.
- **enforcement** [D]: SEC actions (row 7a [S]) and the FCPA surge of 2007–2010 (row 7b [A]), blended.
- **ip** [A]: patent suits roughly doubled 2009–2013 (not in s2; widely reported), damped.
- **lateral_heat** [D/A]: associates' moves are what it scales most (resignations), so it follows hiring, not the 2009 partner-move record (which collapses drove, row 9): low in 2009–2010, back to 2005's by 2011.
- **collections** [A]: lockup rose through 2009 as clients slowed payment; +20% days to pay at the trough.
- **rate_rise** = row 8.
- **growth** (G in spec 6) [A]: the trend of large-firm hours net of the cycle the drivers carry (row 10b's +2–2.5% before 2008, flat after).
- **Failures** (s1): a Chapter 11 filing or seizure is `bankruptcy` (the firm's open bills are lost; the estate instructs restructuring work); a distressed sale is `rescue` (bills paid, the wallet moves to the buyer). Fannie Mae, Freddie Mac and AIG kept operating and paying, so they do not fail in the game. UAL was already in Chapter 11 in January 2005 and is left out. Chrysler is added to `clients.yaml` (appended).
