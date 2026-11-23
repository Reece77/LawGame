# London, UK rivals and six US cities: research dossier (PT-M11 sub-task 1)

**Status:** compiled 2026-11-23 for PT-M11 (`cities.yaml`, `bar_rules.yaml`, the UK rivals in `firms.yaml`, their notables in `notables.yaml`, London's clients in `clients.yaml`, the `uk` series in `macro_history.yaml`). Research only. It is kept in two parts as the research ran:

- **Part A**: the London large-firm market by practice in 2005 and its path to 2025 (2008, the 2016 referendum, 2020); London rates against New York; trainee and NQ salaries; 19 UK rivals at FY2005/06 with their paths and dated events to 2025; GBP/USD; the UK rules (SRA, indemnity insurance, client money, LLPs, foreign lawyers, ABSs); six US cities against New York; US admission on motion and pro hac vice.
- **Part B**: 78 notable lawyers at 18 UK rivals under ADR PT-0013's rules (professional standing only; "left practice (YYYY)" with no cause; a career-start year; an [S] source for each January 2005 role, or the row was dropped).

**Tags** (both parts): **[S]** seen in the cited source this session (**[S·snip]** seen only in an excerpt), **[D]** derived with the arithmetic shown, **[A]** assumed with the basis given. "not found" means not found, never zero.

**How the game reads it (PT-M11).** UK firms' fiscal years end in April; the game's fiscal-year points are the year the fiscal year ends (FY2005/06 is 2006's point, at the year's GBP/USD from part A §5, which the game's history pin compares in US dollars). Sterling's moves are part of the path, as published dollar figures would show them. Section references in the data files' `src` fields name this file's part and section (for example "A s4.2", "B clifford_chance").

---

## Part A — London market, UK rivals and six US cities: research dossier, part A

**Status:** first pass, compiled 2026-11-23 for Partner Track. This is research only: no code or data YAML was changed.

**Tags:** **[S]** means seen in the cited source this session. **[S·snip]** means seen only in a search-result excerpt or a paywalled lead paragraph, so it is weaker. **[D]** means derived from [S] figures, with the arithmetic shown. **[A]** means assumed, with the basis given. "not found" means not found this session, never zero. UK firms' fiscal years end on **30 April** unless stated otherwise (Slaughter and May also ends on 30 April; DLA Piper, Hogan Lovells, Norton Rose Fulbright and Eversheds Sutherland report calendar years from their US mergers). "FY2005/06" means the year to April 2006.

**Read this first: known weaknesses.**
- **FY2005/06 revenue is solid for all 19 firms:** The Lawyer UK100 2006, via an archived Wikipedia table.
- **The best single-year table is FY2008/09:** the full Legal Week UK Top 50 PDF, with revenue, PEP, revenue per lawyer, total partners and equity partners.
- **FY2005/06 PEP was found for only 8 firms.** Lawyer and equity-partner counts for FY2005/06 are mostly [A] or [D], back-cast from FY2008/09.
- **The practice-area split is mostly [A].**
- **US-city 2005 headcounts by city were not found;** 2025 figures stand in.
- **Rents are sourced for Q4 2005 only** (INDEX Rent Monitor, CBD Class A asking rent). London versus New York uses CBRE's 2006 occupancy cost, from an excerpt.
- **Paywalls:** law.com, The Lawyer, Legal Business and the Law Society Gazette are mostly paywalled or CAPTCHA-blocked. Many of their figures are therefore [S·snip].

---

### Source key

| Key | Source |
| --- | --- |
| L1 | Wayback snapshot (13 Sep 2006) of Wikipedia "List of largest UK law firms" (source: The Lawyer 100, 2005, i.e. FY2004/05). https://web.archive.org/web/20060913000000/http://en.wikipedia.org/wiki/List_of_largest_UK_law_firms |
| L2 | Wayback snapshot (25 Mar 2008) of the same page: The Lawyer UK100 2007 and 2006 turnover (FY2006/07 and FY2005/06), all 100 firms. https://web.archive.org/web/20080325144806/http://en.wikipedia.org/wiki/List_of_largest_UK_law_firms |
| L3 | Legal Week, "Top 50 special: 2008-09 in numbers: firm by firm", 30 Jul 2009 (PDF reproduction). https://pravo.ru/store/doc/doc/UK_Top50_2009.pdf |
| L4 | Wayback snapshot (28 Feb 2010) of the Wikipedia page: UK200 totals for 2009, plus 2009 turnover and PEP. https://web.archive.org/web/20100228023200/http://en.wikipedia.org/wiki/List_of_largest_UK_law_firms |
| L5 | Wayback snapshot (3 Nov 2011): FY2009/10 turnover and PEP. https://web.archive.org/web/20111103081117/http://en.wikipedia.org/wiki/List_of_largest_UK_law_firms |
| L6 | Wayback snapshot (21 Nov 2015): FY2014/15 and FY2013/14 turnover, FY2014/15 PEP, partners/lawyers and margin. https://web.archive.org/web/20151121200132/http://en.wikipedia.org/wiki/List_of_largest_UK_law_firms |
| L7 | Legal Week / law.com, "UK Top 50 2017-18" PDF: revenue, PEP, partners, equity partners, RPL, totals. https://images.law.com/contrib/content/uploads/documents/378/UK-Top50_2017-18_v2_Small.pdf |
| L8 | Wikipedia, "List of largest United Kingdom–based law firms" (live page, FY2023/24 in US$), plus the Wayback copy of 22 Jun 2025 that holds the FY2022 US$ table. https://en.wikipedia.org/wiki/List_of_largest_United_Kingdom%E2%80%93based_law_firms ; https://web.archive.org/web/20250622040745/http://en.wikipedia.org/wiki/List_of_largest_UK_law_firms |
| L9 | Adam Smith, Esq., 24 Aug 2005: Bloomberg survey of London top 20 (FY2004/05 revenue and total staff), with The Lawyer UK revenue figures. https://adamsmithesq.com/?p=589 |
| L10 | Adam Smith, Esq., Oct 2006: Am Law Global 100 2006, top 10 by gross revenue. https://adamsmithesq.com/2006/10/98_of_the_global_100_are/ |
| L11 | Above the Law, "The 2026 UK Top 50" (Law.com UK revenue, FY2025), Jun 2026. https://abovethelaw.com/2026/06/the-2026-uk-top-50-the-richest-biglaw-firms-across-the-pond/ |
| L12 | Law Society Gazette, "Top-50 financial results table 2025: updated live" (Wayback 26 Jul 2025). https://web.archive.org/web/20250726053639/https://www.lawgazette.co.uk/news/top-50-financial-results-table-2025-updated-live/5123259.article |
| L13 | Law.com / Legal Week UK Top 50 headlines **(excerpts)**: 2009 https://law.com/international-edition/2009/07/30/uk-law-leaders-suffer-pep-plunge-but-revenues-hold-steady ; 2010 https://law.com/international-edition/2010/07/14/uk-law-leaders-see-profits-revival-as-revenues-slide-across-the-top-50 ; 2011 https://law.com/international-edition/2011/07/20/uk-top-50-law-firms-endure-gloom-to-post-best-growth-figures-since-2008 ; 2012 https://law.com/international-edition/2012/07/26/uk-top-50-law-firms-drive-profits-back-towards-boom-time-high-3 ; 2014 https://law.com/international-edition/2014/08/31/uk-top-50-leading-firms-put-economic-woes-behind-them-as-revenues-hit-14bn-high ; 2017 https://law.com/international-edition/2017/08/31/uk-top-50-push-total-revenues-past-20bn-as-currency-gains-mask-market-uncertainty ; 2015 practice mix https://law.com/international-edition/2015/09/22/disputes-work-drives-turnover-growth-at-uk-top-50-firms |
| L14 | Birmingham Post / Legal Business, "Lawyers take £3.5bn profit" (2006 top 100) **(excerpt)**. https://www.birminghampost.co.uk/business/lawyers-take-35bn-profit-3980026 |
| L15 | LawFuel, 22 Jul 2007, citing Legal Week 2006-07 results. https://www.lawfuel.com/blog/london-based-magic-circle-law-firms-had-a-break-through-year-with-the-second-year-of-double-digit-growth-and-record-earnings-as-they-make-their-mark-in-the-international-legal-world/ |
| L16 | Evelyn Partners, Top 50 LLP accounts analyses **(excerpts)**. https://evelyn.com/insights-and-events/insights/top-50-llp-accounts-revenue-or-profit |
| L17 | Legal Business, "The £40bn club: LB100 push revenues to new high" (2025) **(excerpt)**. https://www.legalbusiness.co.uk/law-firms/the-40bn-club-lb100-push-revenues-to-new-high/ |
| L18 | TheCityUK, UK legal services reports 2019–2025 **(excerpts)**. https://www.thecityuk.com/our-work/uk-legal-services-2025/ ; https://www.lawgazette.co.uk/practice/summit-law-firm-income-topped-32bn-in-2014-thecityuk/5047064.article |
| L19 | PwC Law Firms' Survey 2025 press release **(excerpt)**. https://www.pwc.co.uk/press-room/press-releases/research-commentary/2025/top-law-firms-widen-lead-as-profit-gap-across-legal-sector-expan0.html |
| P1 | The Lawyer, "CC receives post-audit profit boost", 18 Sep 2006 **(excerpt)**. https://www.thelawyer.com/issues/18-september-2006/cc-receives-post-audit-profit-boost-2/ |
| P2 | Law.com, "Linklaters reports surge in partner profits", 24 May 2006 **(excerpt)**. https://www.law.com/international-edition/2006/05/24/linklaters-reports-surge-in-partner-profits/ |
| P3 | Legal Week, "Freshfields results lag magic circle rivals", 7 Jun 2006 **(excerpt)**. https://www.law.com/legal-week/sites/legalweek/2006/06/07/freshfields-results-lag-magic-circle-rivals/ |
| P4 | LawFuel, A&O results press release (year to 30 Apr 2006) **(excerpt)**. https://www.lawfuel.com/14-july-lawfuel-the-law-news-network-allen-overy-today-announ/ |
| P5 | Law.com, "Ashurst reveals solid partner profits growth", 21 Jun 2006 **(excerpt)**. https://www.law.com/international-edition/2006/06/21/ashurst-reveals-solid-partner-profits-growth/ |
| P6 | Law Society Gazette, "Bumper year for commercial firms as Eversheds posts strongest results yet" (2006) **(excerpt)**. https://www.lawgazette.co.uk/news/bumper-year-for-commercial-firms-as-eversheds-posts-strongest-results-yet/44596.article |
| P7 | Law.com, "PEP up 15% as Norton Rose unveils '07 results", 21 May 2007 **(excerpt)**. https://www.law.com/international-edition/2007/05/21/pep-up-15-as-norton-rose-unveils-07-results/ |
| P8 | Law.com, "Partner profits at Lovells plunge by 20%", 5 Jul 2005 **(excerpt)**. https://www.law.com/international-edition/2005/07/05/partner-profits-at-lovells-plunge-by-20-2/ |
| WA | Wayback copies of each firm's Wikipedia page, 2006–2012 (e.g. https://web.archive.org/web/20070125134545/http://en.wikipedia.org/wiki/Clifford_Chance ; …/20060913000000/…/Freshfields_Bruckhaus_Deringer ; …/Herbert_Smith ; …/Lovells ; …/Pinsent_Masons ; …/Addleshaw_Goddard ; …/20071123091335/…/Allen_&_Overy ; …/20090302062429/…/Simmons_&_Simmons ; …/20081018010459/…/Travers_Smith ; …/20120720051607/…/SJ_Berwin ; …/20120825154720/…/Macfarlanes) |
| W | English Wikipedia firm pages, fetched 2026-11-23 (https://en.wikipedia.org/wiki/<Firm>): Hogan_Lovells, Norton_Rose_Fulbright, Herbert_Smith_Freehills_Kramer, A%26O_Shearman, CMS_(law_firm), Bryan_Cave_Leighton_Paisner, Eversheds_Sutherland, King_%26_Wood_Mallesons, Ashurst_LLP, Addleshaw_Goddard, Pinsent_Masons, DWF_Group, Slater_and_Gordon, Keystone_Law, Clifford_Chance, Linklaters, Freshfields, Slaughter_and_May, Simmons_%26_Simmons, Macfarlanes, Travers_Smith, DLA_Piper |
| N1 | nonbillable.co.uk, "A&O Shearman's debut results: £2.9bn revenue, £2m PEP" **(excerpt)**. https://www.nonbillable.co.uk/news/ao-shearman-financial-results-2025 |
| N2 | Search excerpts: HSF 2024/25 (Law Gazette 2025 table); Hogan Lovells FY2024/FY2025 (https://www.hlc.com/en/news/hogan-lovells-reports-record-results-for-the-third-consecutive-year ; https://www.legalcheek.com/2025/03/hogan-lovells-nears-3-billion-revenue-milestone/); Freshfields 2024/25 accounts (https://www.legalbusiness.co.uk/law-firms/freshfields-accounts-reveal-6-revenue-rise-for-2024-25-as-us-sees-fastest-growth/); Clifford Chance 2024/25 (https://www.lawgazette.co.uk/news/magic-circle-firms-report-record-year/5124000.article) |
| R1 | Judiciary, "Previous Guideline Hourly Rates" (2024 rates with 2021 rates in brackets). https://www.judiciary.uk/wp-content/uploads/2025/03/Previous-Guideline-Hourly-Rates_.pdf |
| R2 | Civil Justice Council Costs Committee, GHR final report (2014), with the 2010 London 1 rates. https://www.judiciary.uk/wp-content/uploads/2014/07/ghr-final-report.pdf |
| R3 | Search excerpts: GHR 2025 (£566) and 2026 (£579) (https://judiciary.uk/guideline-hourly-rates-2026/); ACCC Dec 2007 letter (Central London Grade A £304) (https://www.newlawjournal.co.uk/content/2008-guideline-rates-and-fees) |
| R4 | Search excerpts of Jim Diamond's hourly-rate surveys: Law Gazette table "City of London (magic circle) law firms – hourly rates" (2003/2005/2007); The Lawyer, "Revealed: hourly rates rocket by 67 per cent", 19 Nov 2007 (https://www.thelawyer.com/issues/19-november-2007/revealed-hourly-rates-rocket-by-67-per-cent-2/); Legal Week 23 Nov 2011 (https://law.com/international-edition/2011/11/23/city-elite-give-a-little-ground-on-fees-but-some-firms-still-hiking-rates); Law Society Gazette (Ireland) 2022 (https://www.lawsociety.ie/gazette/top-stories/2022/august/top-london-firms-hourly-rates-top-1000/); Feb 2025 (https://www.lawsociety.ie/gazette/top-stories/2025/february/hourly-lawyer-rates-in-britain-now-at-1600/) |
| R5 | US partner rates by city **(excerpts)**: CEB TyMetrix 2012 averages (https://calattorneysfees.com/?p=4233); LexisNexis CounselLink 2021 (https://legaldive.com/news/large-cities-saw-highest-law-firm-rate-hikes-in-the-us/626573); Above the Law 2023 (https://abovethelaw.com/2023/05/the-cities-where-biglaw-partner-billing-rates-now-cost-even-more-money/2) |
| T1 | Personnel Today, "Starting salaries for City lawyers soar as firms fight for top talent", 4 May 2006. https://www.personneltoday.com/hr/starting-salaries-for-city-lawyers-soar-as-firms-fight-for-top-talent |
| T2 | Law.com / Legal Week salary items **(excerpts)**: 3 May 2006 £55k (https://law.com/international-edition/2006/05/03/top-london-firms-hike-starting-rates-to-55000); 8 May 2008 Linklaters £66.6k (https://www.law.com/international-edition/2008/05/08/linklaters-adds-4-to-nq-pay-despite-sweeping-predictions-of-salary-freeze/); A&O trainee pay Apr 2013 (https://law.com/international-edition/2013/04/23/ao-increases-trainee-pay-rates-for-first-time-in-three-years); Freshfields bands May 2013 (https://law.com/international-edition/2013/05/10/freshfields-holds-associate-and-trainee-pay-bands-at-2012-rates); Freshfields freeze 9 Jun 2015 (https://law.com/international-edition/2015/06/09/freshfields-freezes-junior-lawyer-salary-bands); A&O £81k 2 Oct 2017 (https://law.com/2017/10/02/allen-overy-boosts-associate-pay-to-81000); CC £100k 10 Jun 2019 (https://law.com/international-edition/2019/06/10/cc-boosts-nq-pay-to-100000-amid-associate-pay-war) |
| T3 | Legal Cheek / City AM / TargetJobs salary items **(excerpts)**: CC NQ £87.3k and trainee pay, Sep 2017 (https://www.legalcheek.com/2017/09/clifford-chance-boosts-nq-pay-to-87300); Magic Circle trainee pay tables 2018–19 (https://www.legalcheek.com/2019/08/clifford-chance-tops-magic-circle-trainee-pay-table-with-fresh-rises); £125k in 2022 (https://www.cityam.com/all-magic-circle-law-firms-now-pay-newly-qualified-lawyers-125000-but-still-lag-us-rivals/); £150k in 2024 (https://www.legalcheek.com/2024/05/freshfields-sets-down-magic-circle-salary-marker-as-its-ups-nq-lawyer-pay-by-20-to-150k/ ; https://www.legalcheek.com/2024/09/slaughter-and-may-raises-newly-qualified-lawyer-pay-to-150000/ ; https://www.legalcheek.com/2025/05/slaughter-and-may-keeps-nq-pay-at-150k); trainees £56k/£61k (https://targetjobs.co.uk/careers-advice/law/law-trainee-salary-guide); US firms in London: Akin £127k 2016 (https://www.legalcheek.com/2016/06/akin-gump-london-office-latest-to-up-nq-pay-to-127k-and-beyond), £143k 2018 (https://www.legalcheek.com/2018/06/akin-gump-ups-london-nq-pay-to-coveted-143000), Milbank 2023 (https://www.legalcheek.com/2023/11/milbank-ups-newly-qualified-lawyer-salaries-to-market-leading-record-high), 2024 table (https://www.legalcheek.com/2024/11/revealed-what-100-top-law-firms-pay-newly-qualified-solicitors-with-some-earning-180k-straight-from-their-tcs/amp/) |
| U1 | Wikipedia, "Solicitors Regulation Authority". https://en.wikipedia.org/wiki/Solicitors_Regulation_Authority |
| U2 | Wikipedia, "Qualified Lawyers Transfer Scheme". https://en.wikipedia.org/wiki/Qualified_Lawyers_Transfer_Scheme |
| U3 | SRA, Qualifying work experience. https://www.sra.org.uk/become-solicitor/sqe/qualifying-work-experience/ |
| U4 | SRA Indemnity Insurance Rules, and a broker summary **(excerpt)**. https://www.sra.org.uk/solicitors/standards-regulations/indemnity-insurance-rules ; https://global.lockton.com/gb/en/news-insights/how-to-choose-the-right-level-of-pii-cover ; SIF closure: https://www.solicitorsjournal.com/sjarticle/sif-closure-leaves-law-firms-exposed-to-claims |
| U5 | SRA Accounts Rules 2019 (Kingsley Napley, 13 Nov 2019; Armstrong Watson) **(excerpt)**. https://www.kingsleynapley.co.uk/insights/blogs/regulatory-blog/the-new-solicitors-accounts-rules-what-has-changed |
| U6 | SRA practising fee determinations **(excerpts)**: 2019 (https://guidance.sra.org.uk/globalassets/documents/sra/board-meetings/2019/item-8-annexes-1---5.pdf), 2021, 2022 (https://legalservicesboard.org.uk/wp-content/uploads/2022/07/SRA-TLS-to-LSB-Section-51-Application-2022-Final.pdf), 2024/25 (https://www.sra.org.uk/mysra/fees/fee-policy-24-25/), 2025/26 (https://www.sra.org.uk/mysra/fees/current-fees/) |
| U7 | First ABS licences, 28 Mar 2012 (Legal Week) **(excerpt)**. https://www.law.com/legal-week/sites/legalweek/2012/03/28/sra-confirms-debut-trio-of-licensed-alternative-business-structures/ |
| U8 | LLP conversions **(excerpts)**: CC Dec 2006 (https://www.law.com/international-edition/2006/12/06/clifford-chance-paves-way-for-new-wave-of-magic-circle-llps/); Linklaters on ice Mar 2006 (https://law.com/international-edition/2006/03/22/city-heavyweights-put-llp-switch-on-ice); Freshfields/Macfarlanes/Hammonds May 2008 (https://www.law.com/legal-week/sites/legalweek/2008/05/08/uk-trio-become-llps-with-only-two-top-10-firms-yet-to-convert/); Simmons Nov 2010 (https://law.com/international-edition/2010/11/01/simmons-confirms-conversion-to-llp-status); Ince Mar 2011 (https://law.com/international-edition/2011/03/30/ince-switches-to-llp-in-one-of-last-top-50-conversions) |
| U9 | Gateley IPO, 8 Jun 2015 (Legal Week) **(excerpt)**. https://law.com/legal-week/sites/legalweek/2015/06/08/gateley-shares-open-10-up-on-asking-price-as-firm-raises-30m-in-first-ever-uk-ipo ; https://gateleyplc.com/insight/market-announcements/announcement-of-intention-to-float-on-aim/ |
| FX | FRED series AEXUSUK (Federal Reserve Board, annual average, US$ per £). https://fred.stlouisfed.org/data/AEXUSUK |
| C1 | NALP Bulletin, Sep 2009, Table 2: "Median Starting Salaries for First-Year Associates in Firms of 251 or More Lawyers — Chicago, Los Angeles, New York, and Washington, DC" (Wayback). https://web.archive.org/web/2012/http://www.nalp.org/2009septnewassocsalaries |
| C2 | NALP, "Salaries Up at Largest Firms for First Time Since 2000", 1 Aug 2006 (Wayback). https://web.archive.org/web/2012/http://www.nalp.org/2006salariesupatlargestfirms |
| C3 | INDEX / Global Real Analytics, *Rent Monitor* vol. 83, Q1 2006 (CBD office: Class A asking and effective rent, $/sf/yr, for Q4 2005, Q1 2005 and Q1 2006). https://www.bus.umich.edu/KresgePublic/Journals/nre/rm2006-1.pdf |
| C4 | Pirical, "Inside the Numbers: The US Legal Market in 2025", 6 May 2025 (Am Law 200 lawyers by city). https://www.pirical.com/data-insights/the-us-legal-market-in-2025 |
| C5 | Above the Law, "Top U.S. legal markets by headcount" (Aug 2016) and Jun 2025 (largest office per city). https://abovethelaw.com/2016/08/stat-of-the-week-top-u-s-legal-markets-by-headcount/ ; https://abovethelaw.com/2025/06/the-cities-with-the-most-lawyers-in-america/2/ |
| C6 | Lateral Link, NY legal market report (NLJ 500, Dec 2024) **(excerpt)**. https://laterallink.com/the-new-york-city-legal-market-analysis-report/ |
| C7 | CBRE occupancy-cost surveys, 2006 (via GlobeSt) **(excerpt)**. https://globest.com/2006/11/20/office-rents-rise-worldwide ; https://globest.com/2006/05/31/occupancy-costs-rise-globally |
| C8 | NCBE Comprehensive Guide, Chart 14 (admission on motion). https://reports.ncbex.org/charts/chart-14/ |
| C9 | Wikipedia, "Admission on motion". https://en.wikipedia.org/wiki/Admission_on_motion |
| C10 | Pro hac vice fee items **(excerpts)**: Boston Bar Association 2018 (https://bostonbar.org/policies/sjc-approves-pro-hac-vice-fee-increase/); State Bar of California (https://www.calbar.ca.gov/es/node/5919); FJC federal courts (https://fjc.gov/sites/default/files/materials/53/Admission-Fees.pdf) |
| C11 | NALP associate salary reports 2019–2025 **(excerpts)**. https://www.nalp.org/associatesalarysurvey2019 ; https://www.nalp.org/0623research ; https://www.nalp.org/0625research |
| C12 | 2024 rent excerpts: Colliers Manhattan Q1 2024 (https://statista.com/statistics/605986/average-class-a-asking-rent-manhattan-by-submarket); Cresa Chicago Q1 2024 (https://cresa.com/-/media/Cresa/Files/PDF-Market-Reports/Chicago/2024/Chicago_Office_Q1_2024.ashx) |

---

#### 1. London large-firm legal market, 2005 by practice, and its path to 2025

#### 1.1 Size in 2005

| Measure | Value | Tag | Source / arithmetic |
| --- | --- | --- | --- |
| The Lawyer UK top 50, FY2004/05 turnover (global) | £8.37bn (top 10: £4.92bn) | D | sum of the 50 firms listed in L1 |
| The Lawyer UK100, FY2005/06 turnover (global) | £10.81bn | D | sum of the "2006 turnover" column for all 100 firms in L2 |
| — of which the top 50 (by 2007 rank) | £9.33bn | D | L2 |
| — of which the top 10 | £5.50bn | D | L2 |
| — of which the Magic Circle (CC, Links, Freshfields, A&O, Slaughters) | £3.17bn (29% of UK100) | D | L2: 1,030 + 935.3 + 882 + 736 + 321 |
| Legal Business top 100, calendar 2006 | £10.8bn (+12%) | S·snip | L14 |
| Legal Week top 50, FY2005/06 growth | turnover +13.1%, PEP +19% | S·snip | Legal Week Jul 2006 (L13 search) |
| Total UK legal services revenue, 2005 | not found; ≈£20–22bn | A | basis: TheCityUK puts UK law-firm fee income at £32.4bn in 2014 (L18 snip); back-cast at ≈4.5%/yr nominal |
| **London/UK-sourced large-firm fee spend, 2005 (game anchor)** | **≈£7.5bn/yr** | A | £10.81bn UK100 × ≈60% UK-sourced (the Magic Circle earned roughly half abroad; national firms nearly all in the UK) ≈ £6.5bn, plus ≈£1.0bn for US and other foreign firms' London offices (Bloomberg/L9 shows the larger US offices were not yet in the top 20) |

#### 1.2 Split by practice (London large firms)

The only sourced split is Legal Week's analysis of FY2014/15 for the 35 UK top 50 firms that gave a breakdown. It found litigation 27.9%, corporate ≈26% and finance 12.8% of revenue [S·snip, L13 2015 item]. Disputes were "more than a quarter" [S, L13]. The 2005 column below tilts toward corporate and finance, because 2005 was a boom year for M&A and leveraged finance.

| Practice (game key suggestion) | Share 2005 [A] | Share 2014/15 | Notes |
| --- | --- | --- | --- |
| Corporate/M&A (incl. private equity) | 28% | ≈26% [S·snip] | the boom peaked in 2006–07 |
| Banking & finance (incl. structured, projects) | 18% | 12.8% "finance" [S·snip] | collapsed in 2008–09; this is why finance shrank by 2014 |
| Capital markets (debt/equity/securitisation) | 7% | in finance/corporate | [A] |
| Commercial litigation/disputes (incl. arbitration) | 20% | 27.9% [S·snip] | grew counter-cyclically after 2008 |
| Real estate | 11% | not found (≈10%) [A] | |
| Employment/pensions | 5% | not found | [A] |
| IP/technology | 3% | not found | [A] |
| Tax | 3% | not found | [A] |
| Restructuring/insolvency | 2% (rising to ≈5% in 2009) | not found | [A] counter-cyclical |
| Regulatory/white collar (FSA, SFO) | 2% | not found | [A] |
| Antitrust/competition | 2% | not found | [A] |

Basis for the [A] column: the same 2014/15 split, adjusted toward deal work for 2005; there is no 2005 source. The total is 101% because of rounding.

#### 1.3 Path to 2025, with the shocks

| Year (FY to April) | Total | Basis | Tag / source |
| --- | --- | --- | --- |
| 2004/05 | £8.37bn | The Lawyer top 50 | D, L1 |
| 2005/06 | £9.33bn top 50; £10.81bn top 100 | The Lawyer | D, L2 |
| 2006/07 | £10.75bn top 50; £12.39bn top 100 | The Lawyer | D, L2 |
| 2006/07 | £10.5bn (+14%); the Magic Circle "big four" £4.18bn | Legal Week top 50 | S, L15 |
| 2008/09 | **£12.3bn (+2%)**; average PEP −17.3%; average revenue growth 2.9% | Legal Week top 50 | S, L3 |
| 2008/09 (calendar 2009 label) | £15.614bn UK200; £14.395bn top 100; Magic Circle £5.442bn | The Lawyer UK200 | S, L4 |
| 2009/10 | £11.9bn (revenues "slide £461m") | Legal Week top 50 | S·snip, L13 |
| 2010/11 | £12.33bn | Legal Week top 50 | S·snip, L13 |
| 2011/12 | "nearly £13bn" | Legal Week top 50 | S·snip, L13 |
| 2013/14 | "£14bn high" (≈£14.4bn) | Legal Week top 50 | S·snip, L13 |
| 2014/15 | £17.5bn (boosted by the NRF and HSF mergers) | Legal Week top 50 | S·snip (low confidence) |
| 2016/17 (Brexit-vote year) | "past £20bn as currency gains mask market uncertainty" | Legal Week top 50 | S·snip, L13 |
| 2017/18 | **£22.49bn**; average revenue +9.9%, average PEP £719k | Legal Week top 50 (DLA, HL, NRF and ES at global calendar-2017 revenue, converted at $1.2827/£) | S, L7 |
| 2019/20 (pandemic onset) | a "slump in both revenue and PEP growth rates" (Brexit + Covid) | Law.com | S·snip |
| 2020/21 | top 50 "first broke through £20bn" | Evelyn, filed LLP accounts (a different basis from Legal Week) | S·snip, L16 |
| 2021 (boom) | UK legal services revenue £41.4bn (+12.5%) | TheCityUK | S·snip, L18 |
| 2022/23 | top 50 "just under £24bn" (+8.5%); LB100 £33.8bn | Evelyn; Legal Business | S·snip, L16/L17 |
| 2023/24 | LB100 £37bn; UK legal services £47.1bn (+7.7%, calendar 2023); Law.com UK Top 50 +9.7% | | S·snip |
| 2024/25 | **LB100 £40.15bn**; top 10 hold 51% of top-100 fee income (up from 45% two years earlier) | Legal Business; PwC | S·snip, L17/L19 |
| 2024/25, UK revenue only (Law.com UK Top 50 2026) | Linklaters £1,059m; A&O Shearman £981m; **Kirkland £914m**; CC £901m; Freshfields £829m; **Latham £811m**; Slaughter and May £746m; HSF £617m; CMS £598m; Eversheds £583m (top 10 ≈ £8.04bn) | US firms' UK revenue +14.7% vs UK firms +7.1% | S, L11 |

**Shock calibration notes** (from the rows above):
- **2008–09 crash:** revenues were roughly flat (+2–3% nominal; sterling's fall flattered overseas income), PEP fell −17% on average, and transactional firms such as SJ Berwin (PEP −48.8%), CC (PEP −36.6%), Travers (revenue −20.4%) and Macfarlanes (revenue −10.8%) were hit hardest [S, L3]. The top 50 total then fell about 3% in FY2009/10 [S·snip].
- **2016 Brexit vote:** no fall in sterling revenue. The weak pound (average $1.36 in 2016, against $1.53 in 2015 [S, FX]) inflated the overseas revenue of UK firms.
- **2020 pandemic:** a slowdown in growth, not a fall in total revenue. This is followed by the 2021 boom (+12.5% sector revenue [S·snip]).

---

#### 2. London rates

#### 2.1 Guideline hourly rates (court summary assessment; a floor, well below City market rates)

| Period | Band | Grade A (8+ yrs) | B (4+ yrs) | C (other solicitors) | D (trainees/paralegals) | Tag |
| --- | --- | --- | --- | --- | --- | --- |
| ≈2007 | Central London (W1, WC1, WC2, SW1) | £304 | £231 | £189 | £121 | S·snip, R3 (Dec 2007 ACCC letter; rates in force before the 2008 uplift) |
| 2005 | City of London band | not found (≈£300–£340) | | | | A: the 2007 Central London figure less ≈2 years of uplift; the City band ran higher |
| 2010 – 30 Sep 2021 | London 1 (EC1–EC4) | £409 | £296 | £226 | £138 | S, R2 (CJC 2014 report, table of current GHR) |
| 1 Oct 2021 | London 1 | £512 | £348 | £270 | £186 | S, R1 |
| 1 Jan 2024 | London 1 | £546 | £371 | £288 | £198 | S, R1 |
| 1 Jan 2025 | London 1 | £566 | | | | S·snip, R3 |
| 1 Jan 2026 | London 1 | £579 | £393 | £305 | £210 | S·snip, R3 (as reported; "London" band) |

#### 2.2 Magic Circle market rates (Jim Diamond's annual survey)

| Year | Magic Circle partner £/hr | Other comparison | Tag |
| --- | --- | --- | --- |
| 2003 | £375–£450 | — | S·snip, R4 |
| 2005 | **£425–£525** | — | S·snip, R4 (Law Gazette table) |
| 2007 | £625–£700 (average £625, +67% in four years; tax/regulatory ≈£700) | US top firms' London partners £450–£500 | S·snip, R4 |
| 2011 | £600–£700 | City non-Magic-Circle partners £425–£600 | S·snip, R4 |
| 2015 | not found (≈£800–£1,000) | | A: interpolated between 2011 and 2022 |
| 2022 | £1,000–£1,500; NQs charged out at ≈£600 | US firms' London partners £950–£1,350; other top London firms up to £900 | S·snip, R4 |
| 2024–25 | top rates ≈£1,600 | | S·snip, R4 (Feb 2025) |

**Associates [A]:** about 45–55% of the partner rate. In 2005 that gives roughly £200–£300 for NQs to 3 PQE and £300–£400 for senior associates. Basis: the 2022 NQ rate of £600 against partners at £1,000–£1,500.

#### 2.3 London relative to New York
- **2005 [D]:** a Magic Circle partner at £425–£525 × $1.82 ≈ **$775–$955/hr**. This is at or slightly above top New York partner rates of the time (NY elite partners ≈$700–$900 [A]; the 2012 CEB TyMetrix NY average was $755.68 [S·snip, R5]). The game can treat London ≈ **1.0× NY in US$** in 2005.
- **2012:** the NY average partner rate was $755.68 [S·snip]. London Magic Circle (2011) £600–£700 × $1.60 ≈ $960–$1,120 [D] is above the NY *average*, which includes non-elite firms.
- **2022–24:** Magic Circle £1,000–£1,500 × $1.24 ≈ $1,240–$1,860 [D]. Elite NY partners were by then often $1,800–$2,500 [A]. London is ≈0.8–0.9× elite NY.
- **Suggested game ratio [A]:** London/NY ≈ 1.0 (2005–08), falling to ≈0.85 after 2016 (the weak pound and the rise of US elite rates).

---

#### 3. Trainee and NQ salaries (London, Magic Circle)

#### 3.1 Salary series

| Year (rises usually May, effective then or September) | 1st-year trainee | 2nd-year trainee | NQ | Tag / source |
| --- | --- | --- | --- | --- |
| 2004 | not found | not found | ≈£50k (Linklaters "smashes ceiling") | S·snip (The Lawyer 17 May 2004 headline); amount A |
| 2005 | ≈£29k [A] | ≈£32k [A] | ≈£50k | D: £55k in 2006 was "a 10% increase on 2005" (T1) → £50k |
| 2006 | Linklaters "at least £30,000" (year not stated) | ≈£33k [A] | **£55,000** (Norton Rose, Herbert Smith, Simmons; "top London firms") | S, T1; S·snip, T2 |
| 2007 | ≈£36k [A] | ≈£40k [A] | Linklaters £64,000 (from £61,500) | S·snip, T2 |
| 2008 | A&O £38,000 (from £37,000) | ≈£42k [A] | Linklaters £66,600 | S·snip, T2 |
| 2009–2012 | ≈£38–39k | ≈£42–44k | ≈£59–£65k (freezes; some firms cut NQ pay to ≈£59k in 2009 [A]) | A: no source found for the cuts |
| 2013 | £39,000 (Freshfields, Slaughters, A&O; Freshfields "unchanged for five years") | £44,000 | ≈£65k | S·snip, T2; NQ A |
| 2015 | ≈£42k | ≈£47k | Freshfields band £67,500–£77,500 (frozen for 2015–16) | S·snip, T2; trainees A |
| 2016 | ≈£43.5k | ≈£49k | Freshfields £85,000 (bonus folded into base, as reported); A&O £78,500 | S·snip (date uncertain) |
| 2017 | CC £44,800 | CC £50,500 | CC £87,300; A&O £81,000 (from £78,500) | S·snip, T3/T2 |
| 2018 | ≈£45–£47k (Freshfields top) | ≈£50–£52k | Links/A&O/Slaughters £83,000 | S·snip, T3 |
| 2019 | ≈£46.5–£48k | ≈£52–£54k | **£100,000** (Freshfields May 2019; CC from £91k, June; the others by July) | S·snip, T2/T3 |
| 2021 | ≈£50k | ≈£55k | CC/Links £107,500; A&O froze at £107,500 | S·snip, T3 |
| 2022 | ≈£50–£52k | ≈£55–£57k | **£125,000** (Freshfields and CC first, May 2022) | S·snip, T3 |
| 2024 | ≈£56k | ≈£61k | **£150,000** (A&O Shearman, CC, Freshfields, Links in May 2024; Slaughters in Sep 2024) | S·snip, T3 |
| 2025 | **£56,000** | **£61,000** (A&O Shearman, CC, Freshfields, Links) | £150,000 (Slaughters held) | S·snip, T3 |

#### 3.2 US firms in London (NQ)
- before 2016: Akin £100,000 [S·snip]
- mid-2016: Akin £127,000 [S·snip]
- 2018: Akin £143,000 [S·snip]
- 2021: Milbank $200k ≈ £143,500 [S·snip]
- late 2023: Milbank $225k ≈ £177,500–£183,000; Gibson Dunn and Quinn £180,000 [S·snip]
- 2024: Milbank £183,409; Akin, Kirkland and Latham £173,254; Gibson and Paul Weiss £180,000 [S·snip, T3]
- 2025: not confirmed

The "NQ wars" therefore ran from 2016 (US firms) and from 2019 (the Magic Circle).

#### 3.3 Training structure
- **Training contracts (pre-SQE route) [A, general knowledge, consistent with T-sources]:**
  - offered about two years ahead, after vacation schemes;
  - two years of four six-month "seats";
  - intakes start in September and March, so qualification falls each September and March;
  - Magic Circle firms took about 90–130 trainees a year each [A];
  - retention on qualification was typically 75–90% (the "war for talent pushes retention rates past 90%", Apr 2007 [S·snip, T2 search]).
- **SQE:** in force **1 September 2021** [S, U2]. Candidates need two years' full-time-equivalent **Qualifying Work Experience**, in up to four organisations, confirmed by a solicitor or COLP [S, U3]. LPC-route candidates may finish under transitional arrangements [S, U3]; the end date was not found.
- **QLTS** (for foreign lawyers): introduced **1 September 2010**, replacing the QLTT; last MCT July 2021; last OSCE April 2022 [S, U2].

---

#### 4. UK rivals at FY2005/06

**Exchange rate:** FY2005/06 runs May 2005 to April 2006, so $/£ ≈ 1.828 [D: 8/12 × 1.8204 + 4/12 × 1.8434, FX annual averages]. Revenue is The Lawyer UK100 2006 (global turnover) [S, L2]. Where L2 and Legal Week differ, L2 is used.

#### 4.1 Summary

| `rival_key` [A] | Firm (2005 name) | Revenue FY05/06 | ≈US$ [D] | Lawyers | Partners (equity) | PEP FY05/06 | Offices | Comp [A] | Personality [A] |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `clifford_chance` | Clifford Chance | £1,030.0m [S, L2] | $1,883m (Am Law: $1,875m [S, L10]) | 3,688 incl. 608 partners (Jul 2006) [S, WA] | ≈400 eq. [A from L3's 412 in 2008/09] | £814k [S·snip, P1] | 30 (London + 29) [S, WA] | modified lockstep | global_verein (closest: integrated global; "verein" is a weak fit) |
| `linklaters` | Linklaters | £935.3m [S] | $1,710m (Am Law $1,702m [S, L10]) | ≈2,000 [A: 2,202 in 2008/09, D from L3] | ≈410 eq. [A] | £1.06m [S·snip, P2] | 30 in 23 countries [S, WA] | modified lockstep | elite_lockstep |
| `freshfields` | Freshfields Bruckhaus Deringer | £882.0m [S] | $1,612m (Am Law $1,605.5m [S, L10]) | 2,463 incl. 515 partners and principals [S, WA, 2006] | ≈410 eq. [A] | £832k (from £700k) [S·snip, P3] | 28 [S, WA] | modified lockstep | elite_lockstep |
| `allen_overy` | Allen & Overy | £736.0m [S] | $1,345m (Am Law $1,340m [S, L10]) | ≈1,900 [A: 2,052 in 2008/09] | ≈360 eq. [A] | £788k (+20%) [S·snip, P4] | 25 [S, WA] | modified lockstep | elite_lockstep |
| `slaughter_may` | Slaughter and May | £321.0m [S] (does not publish; estimate) | $587m | ≈500 [A: ≈550 in 2008/09] | ≈125 (all equity) [A: 124 in 2008/09, L3] | not disclosed; ≈£1.3m [A: £1.54m est. in 2008/09 after −5%, L3; back-cast with revenue] | 4 (London, Paris, Brussels, Hong Kong) [A; 4 today, W] | **pure lockstep** | elite_lockstep |
| `herbert_smith` | Herbert Smith | £296.0m [S] | $541m | ≈950 [A: 1,038 in 2008/09] | ≈125 eq. [A] | £839k [S, WA (2006 page; year implied FY05/06)] | ≈14 [A] | lockstep | elite_lockstep (litigation-led) |
| `lovells` | Lovells | £396.0m [S] | $724m | ≈1,200, 250+ partners [S, WA 2006] | ≈230 eq. [A] | not found (FY04/05 £427k [S·snip, P8]); ≈£560k [A, between £427k and FY07/08 £661k (D from L3)] | 26 [S, WA] | lockstep | global_verein (weak; Euro-network) |
| `ashurst` | Ashurst | £214.0m [S] (+7%) | $391m | ≈700 [A] | ≈120 eq. [A] | £701k (from £567k) [S·snip, P5] | ≈12 [A] | lockstep | elite_lockstep |
| `norton_rose` | Norton Rose | £210.0m [S] | $384m | ≈850 [A] | ≈150 eq. [A] | ≈£445k [D: FY06/07 £512k "up 15%" (P7) ÷ 1.15] | ≈20 [A] | lockstep | global_verein (pre-2011 a weak fit; strong after the NRF mergers) |
| `simmons` | Simmons & Simmons | £227.0m [S] | $415m | ≈700 (2,000+ staff) [S staff, WA; lawyers A] | ≈125 eq. [A] | not found (≈£500k [A: FY07/08 £647k (D) back-cast]) | 21 (London + 20) [S, WA 2009] | lockstep (LLP from Nov 2010) | performance_machine (weak) / elite_lockstep |
| `cms_cmck` | CMS Cameron McKenna | £181.3m [S] | $331m | ≈700 [A] | 130+ partners [S, WA 2006] | not found (≈£480k [A]) | ≈10 own + CMS network [A] | modified lockstep | global_verein (CMS EEIG, from 1999 [S, W]) |
| `eversheds` | Eversheds | £323.0m [S] | $590m | ≈1,800 (3,870 staff FY04/05 [S, L9]) [A] | ≈150 eq. [A] | £390k (+27%) [S·snip, P6] | ≈20 [A] | merit-based | volume_mid_market / regional_champion |
| `dla_uk` (**flag**) | DLA Piper (UK/international LLP) | £366.4m [S, L2 UK100] | $670m | ≈2,000 [A: 2,327 intl. LLP 2008/09] | ≈160 eq. [A: 176 in 2008/09] | not found | — | merit-based | performance_machine. **The game already models `dla_piper` on a US basis; use these figures only if the international LLP is split out. DLA merged with Piper Rudnick and Gray Cary on 1 Jan 2005 [S, W "current organization dates to 2005"].** |
| `addleshaw_goddard` | Addleshaw Goddard | £161.2m [S] | $295m | ≈600 [S, WA 2006: "almost 600 lawyers"] | ≈110 eq. [A] | not found (≈£450k [A]) | 3 (Leeds, London, Manchester) [S, WA] | modified lockstep | regional_champion |
| `blp` | Berwin Leighton Paisner | £145.0m [S] | $265m | ≈650 [A] | ≈80 eq. [A] | not found (≈£500k [A]) | ≈4 [A] | merit-based | performance_machine |
| `sj_berwin` | SJ Berwin | £155.0m [S] | $283m | ≈500 [A] | ≈95 eq. [A] | not found (≈£650k [A: FY07/08 £801k (D)]) | ≈9 [A] | merit-based | performance_machine |
| `pinsent_masons` | Pinsent Masons | £172.0m [S] | $314m | ≈900 "legal team", 260+ partners [S, WA 2006] | ≈110 eq. [A] | not found (≈£420k [A]) | 11 (7 UK + Brussels, Dubai, HK, Shanghai) [S, WA] | modified lockstep / merit | regional_champion / volume_mid_market |
| `macfarlanes` | Macfarlanes | £90.0m [S] | $165m | ≈220 [A: 227 in 2008/09] | ≈50 eq. [A] | not found (≈£1.0m [A: FY07/08 £1.226m (D)]) | 1 (London) [S, WA 2012] | lockstep | elite_lockstep |
| `travers_smith` | Travers Smith | £68.1m [S] | $124m | ≈200 [A]; 250 fee-earners incl. 66 partners (2008) [S, WA] | ≈45 eq. [A] | not found (≈£650k [A: FY07/08 "tops £800k" (WA citation title)]) | 2 (London, Paris) [S, WA] | lockstep (LLP Jul 2008 [S, WA]) | elite_lockstep |

**FY2004/05 reference** (The Lawyer 100 2005 [S, L1]): CC £914m, Linklaters £805m, Freshfields £780m, A&O £666m, Lovells £366m, DLA £322m, Eversheds £303m, Slaughters £290m, Herbert Smith £265m, Norton Rose £210m, Ashurst £201m, Simmons £196m, CMCK £163m, Pinsent Masons £150m, AG £139m, SJB £122m, BLP £121m, Macfarlanes £74m, Travers £55m. Bloomberg's FY2005 London staff headcounts (all staff, not lawyers) were CC 6,700, Freshfields 5,245, Linklaters 4,770, A&O 4,766, DLA 4,851, Eversheds 3,870 [S, L9].

#### 4.2 Paths: revenue (£m) / PEP (£k)

- **FY07/08** is derived from the FY08/09 figures and their % changes in L3.
- **FY08/09** is from L3: revenue, PEP, lawyers (D: revenue ÷ RPL, excluding trainees and PSLs), and total/equity partners.
- **FY09/10** is from L5.
- **FY14/15** is from L6, with "partners/lawyers" as L6 prints them.
- **FY17/18** is from L7, with total/equity partners.
- **Latest:** see the notes column.

| Firm | FY06/07 rev [S, L2] | FY07/08 rev / PEP [D] | FY08/09 rev / PEP / lawyers / partners (eq.) [S, L3] | FY09/10 rev / PEP [S, L5] | FY14/15 rev / PEP / partners/lawyers [S, L6] | FY17/18 rev / PEP / partners (eq.) [S, L7] | Latest (FY24/25 unless noted) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Clifford Chance | 1,194 | 1,328 / 1,156 | 1,262 / 733 / 2,903 / 637 (412) | 1,197 / 933 | 1,350 / 1,117 / 569/2,992 | 1,623 / 1,600 / 557 (392) | £2.4bn / £2.11m; profit £944m [S·snip, N2]. FY22/23 £2.04bn / £2.0m; ≈3,680 lawyers; 34 offices [S, W] |
| Linklaters | 1,121 | 1,293 / 1,440 | 1,298 / 1,302 / 2,202 / 499 (422) | 1,183 / 1,214 | 1,270 / 1,368 / 450/2,601 | 1,523.5 / 1,538 / 460 (440) | £2.32bn (+11%) / £2.2m (+15%); profit £1.08bn [S, L12]; ≈3,100 lawyers incl. 560 partners (Jun 2023) [S, W] |
| Freshfields | 986 | 1,178 / 1,434 | 1,287 / 1,443 / 2,194 / 442 (415) | 1,141 / 1,406 | 1,245 / 1,370 / 424/2,322 | 1,403 / 1,743 / 394 (392) | £2.25bn (+6%, LLP accounts) [S·snip, N2]; PEP not found; 2,761 lawyers; 33 offices [S, W]; FY18/19 £1.472bn / £1.839m [S, W] |
| Allen & Overy → A&O Shearman | 887 | 1,016 / 1,122 | 1,091 / 1,000 / 2,052 / 486 (370) | 1,050 / 1,100 | 1,281 / 1,210 / 519/2,523 | 1,573.2 / 1,640 / 538 (389) | A&O Shearman ≈£2.9bn ($3.7bn) / ≈£2.0m; PBT £1.1bn [S·snip, N1]; ≈4,000 lawyers, 48+ offices [S, W] |
| Slaughter and May | 417 | 419 / 1,621 | 431.6 / 1,540 / 550 / 130 (124) (estimates) | 439.5 / 1,840 | 504.5 / 2,229 / 118/702 | 571 / 2,700 / 112 (106) (estimates) | FY23/24 est. £654m / est. £2.9m; ≈649 lawyers [S, W] |
| Herbert Smith → HSF → HSF Kramer | 334 | 422 / 1,036 | 444 / 845 / 1,038 / 238 (137) | 449.9 / 862 | HSF 815 / 801 / 454/2,294 | HSF 926.8 / 852 / 464 (325) | HSF £1.358bn (+4%) / £1.43m [S·snip, N2]; FY23/24 £1.306bn / £1.315m; 2,600 lawyers [S, W] |
| Lovells → Hogan Lovells | 425 | 479 / 661 | 531 / 586 / 1,500 / 352 (240) | 542 / 663 | HL 1,098 / 692 / 788/2,593 | HL 1,587 / 1,000 / 836 (556) | HL calendar 2024 $2.97bn / $3.07m; 2025 $3.285bn / $3.52m [S·snip, N2] |
| Ashurst | 275 | 323 / 1,040 | 301 / 673 / 844 / 230 (144) | 293 / 689 | 561 / 680 / 413/1,633 | 564 / 743 / 374 (239) | £1.034bn (+8%) / £1.39m [S, L12] |
| Norton Rose → NRF | 233 | 297 / 625 | 314 / 517 / 996 / 264 (172) | 307 / 486 | NRF 1,118 / 541 (L6's later revision; the earlier copy said 394) / 1,168/3,405 | NRF 1,526 / 670 / 1,212 (714) | not found (3,000+ lawyers [S, W]) |
| Simmons & Simmons | 250.4 | 289 / 647 | 291.3 / 520 / 769 / 232 (133) | 251 / 461 | 290.1 / 649 / 241/842 | 354.1 / 686 / 275 (160) | £615m (+7%) / £1.128m; 974 lawyers; 23 offices [S, W; S·snip] |
| CMS Cameron McKenna → CMS | 197.4 | 235 / 655 | 240 / 554 / 785 / 194 (122) | 214.4 / 453 | CMS EEIG 753.3 / 437 / 782/2,776 | CMS 1,133.8 / 574 / 1,047 (598) (global; Nabarro and Olswang from May 2017) | CMS ≈$2.07bn (year not stated) [S, W]; UK revenue FY2025 £598m [S, L11] |
| Eversheds → Eversheds Sutherland | 356 | 391 / 552 | 365.9 / 404 / 1,247 / 334 (145) | 355.2 / 517 | 380.7 / 642 / 332/1,364 | ES 805 / 845 / 677 (191) | FY23/24 $0.915bn (L8 list) [S]; 2,511 lawyers, 72 offices (2025) [S, W]; UK FY2025 £583m [S, L11] |
| DLA Piper (intl. LLP; **flag**) | 446 | 503 / 689 | 585 / 645 / 2,327 / 593 (176) (to 31 Dec) | 581 / 527 | global 1,626 / 903 / 1,236/3,981 | global 2,054 / 1,369 / 1,205 (404) | global $3.68bn / $2.8m (2022) [S, W] |
| Addleshaw Goddard | 176.7 | 195 / 586 | 173.1 / 405 / 598 / 178 (109) | 167.5 / 426 | 192.5 / 457 / 173/674 | 242.4 / 650 / 230 (105) | £551m / £1m ("2025") [S, W]; 2,000+ lawyers, 21 offices |
| Berwin Leighton Paisner → BCLP | 169.0 | 185 / 620 | 180 / 414 / 746 / 193 (86) | 191 / 455 | 246 / 661 / 202/706 | 288.3 / 643 / 197 (80) (legacy BLP) | BCLP $840m (2024) [S, W] |
| SJ Berwin → KWM Europe | 189.0 | 215 / 801 | 184 / 410 / 589 / 171 (97) | 171 / 447 | — (in KWM from Nov 2013) | — (collapsed Jan 2017) | — |
| Pinsent Masons | 192.4 | 213 / 486 | 215 / 310 / 939 / 280 (117) | 206 / 410 | 323.2 / 387 / 367/1,548 | 449.9 / 653 / 428 (178) | £680m [S, W]; PEP not found |
| Macfarlanes | 103.0 | 111 / 1,226 | 99 / 846 / 227 / 75 (52) | 92.4 / 710 | 159.6 / 1,555.5 / 80/344 | 201.6 / 1,744 / 86.6 (53) | PEP £3.1m (+8%), profit £206.5m [S, L12]; FY25/26 £389.5m / £3.1m [S, W] |
| Travers Smith | 78.5 | 81 / 754 (FY to 30 Jun) | 64.5 / 470 / 204 / 63 (46) | not found | 105.9 / 947 / 64/317 | 146.9 / 1,206 / 71 (47) | FY23/24 £215m / £1.3m; ≈370 lawyers [S, W] |

L4 (Wikipedia, 2010) gives Slaughter and May's 2009 turnover as £504m and PEP as £2.25m, against Legal Week's £431.6m and £1.54m. The firm does not publish, so treat its figures as ±20%.

**Lawyer counts in US$ terms.** FY2022 counts [S, L8]: A&O 2,821; CC 2,547; Links 2,684; Freshfields 2,062; HSF 2,299; Slaughters 594; Simmons 973; AG 1,197; Macfarlanes 404. FY2023/24 (L8 live): CC $2.81bn with 3,319 lawyers; Links $2.73bn with 3,075; A&O $2.69bn with 3,358; Freshfields $2.55bn with 2,038; HSF $1.594bn; Ashurst $1.173bn; ES $0.915bn; BCLP $0.840bn; Slaughters $0.805bn with 594; Pinsent $0.793bn; Simmons $0.701bn; AG $0.606bn.

#### 4.3 Dated events, 2005–2025

| Date | Event | Tag / source |
| --- | --- | --- |
| 1 Jan 2005 | DLA + Piper Rudnick + Gray Cary → DLA Piper (international and US partnerships, not financially integrated) | S, W (DLA_Piper: "current organization dates to 2005"); L5 note |
| 2004 (May) | Pinsents + Masons → Pinsent Masons (founding 2004 [A]; W lists the merger chain without a date) | A |
| 1 May 2003 | Addleshaw Booth + Theodore Goddard → Addleshaw Goddard (before the game start) | S, W |
| 2005–06 | A&O the first Magic Circle LLP (decided by Feb 2005); CC converts to UK LLP Dec 2006 (second) | S·snip, U8 |
| May 2008 | Freshfields, Macfarlanes and Hammonds convert to LLP; Travers Smith Jul 2008 | S·snip, U8; S, WA |
| Nov 2010 | Simmons & Simmons converts to LLP | S·snip, U8 |
| 15 Dec 2009 / **1 May 2010** | Lovells + Hogan & Hartson agree, then form **Hogan Lovells** | S, W |
| 2011 | Norton Rose + Ogilvy Renault (Canada) (1 Jun 2011 [A]) | A (date from general knowledge; not seen this session) |
| 2012 | Norton Rose + Macleod Dixon (Canada) (1 Jan 2012 [A]); Pinsent Masons + McGrigors (1 May 2012 [A]; "merged with McGrigors in 2012" [S, L6]) | A / S |
| 1 Mar 2012 | Ashurst combines its Asian business with Blake Dawson (renamed Ashurst Australia); full merger **Nov 2013** | S, W; S, L6 note |
| **1 Oct 2012** | Herbert Smith + Freehills → **Herbert Smith Freehills** | S, W |
| **Jun 2013** (2 Jun [A]) | Norton Rose + Fulbright & Jaworski → **Norton Rose Fulbright** (Chadbourne & Parke absorbed Jun 2017) | S (2013 and Jun 2017), W |
| **Nov 2013** (1 Nov [A]) | SJ Berwin joins King & Wood Mallesons (KWM Europe) | S (2013), W |
| May 2014 | CMS Cameron McKenna + Dundas & Wilson | S, L6 note |
| **Jan 2017** | KWM Europe (ex-SJ Berwin) enters administration and ceases operations | S, W |
| **Feb 2017** (1 Feb [A]) | Eversheds + Sutherland Asbill & Brennan → **Eversheds Sutherland** (2017) | S (2017), W |
| **May 2017** | CMS Cameron McKenna + Nabarro + Olswang → CMS (UK) | S, L7 note 4 |
| 2017 | Addleshaw Goddard + HBJ Gateley (Scotland) | S, W |
| **3 Apr 2018** | Berwin Leighton Paisner + Bryan Cave → **Bryan Cave Leighton Paisner** | S, L7 note 8 |
| 21 May 2023 / 13 Oct 2023 / **1 May 2024** | A&O + Shearman & Sterling announced, then approved by >99%, then completed → **A&O Shearman** | S, W |
| Nov 2024 / **1 Jun 2025** | HSF + Kramer Levin announced, then completed → **HSF Kramer** | S, W |
| Dec 2025 / 1 Jul 2026 | Hogan Lovells + Cadwalader → Hogan Lovells Cadwalader (outside the 2005–25 window) | S, W |

**US firms in London (context).** Office openings: Cravath 1973, Latham 1990, Kirkland 1994 [S·snip, Chambers Student and nonbillable guides]. Sullivan & Cromwell ≈1972, Skadden ≈1988 and Weil ≈1996 are [A]. By FY2025, Kirkland (£914m) and Latham (£811m) were the 3rd and 6th largest firms by UK revenue [S, L11]. Nearly 100 US firms had London offices by the late 2010s [S·snip]. Their NQ salaries led the market from 2016 (§3.2).

**Listed firms and ABSs**
- **Legal Services Act 2007:** ABSs began on **6 Oct 2011** (the CLC licensed the first, Premier Property Lawyers). The SRA took applications from **3 Jan 2012** and issued its first licences on **28 Mar 2012** (Co-operative Legal Services, John Welch & Stammers, Lawbridge) [S, U1; S·snip, U7].
- **Slater & Gordon** (ASX-listed since 2007): entered the UK in 2012 by acquisition (Russell Jones & Walker, 2012 [A on the firm name; "acquisition of several UK firms" S, W]). It bought Quindell's professional services division for £637m on 30 Mar 2015, then took a ≈A$1bn loss (Feb 2016). The UK arm was separated in its Dec 2017 recapitalisation [S, W].
- **Gateley:** the first UK law firm IPO, on AIM. Trading began **8 Jun 2015**; it raised £30m at a ≈£100m valuation [S·snip, U9].
- **Keystone Law:** announced its IPO in Nov 2017 (the third UK listed law firm) [S, W].
- **DWF:** floated on the LSE in **Mar 2019** at just under £370m. Inflexion agreed to buy it for £342m in Jul 2023 and took it private (2023) [S, W].

---

#### 5. GBP/USD annual average (US$ per £1; Federal Reserve, FRED AEXUSUK) [S, FX]

| Year | $/£ | Year | $/£ | Year | $/£ |
| --- | --- | --- | --- | --- | --- |
| 2004 | 1.8330 | 2012 | 1.5853 | 2020 | 1.2829 |
| 2005 | 1.8204 | 2013 | 1.5642 | 2021 | 1.3764 |
| 2006 | 1.8434 | 2014 | 1.6484 | 2022 | 1.2371 |
| 2007 | 2.0020 | 2015 | 1.5284 | 2023 | 1.2440 |
| 2008 | 1.8545 | 2016 | 1.3555 | 2024 | 1.2781 |
| 2009 | 1.5661 | 2017 | 1.2890 | 2025 | 1.3192 |
| 2010 | 1.5452 | 2018 | 1.3363 | | |
| 2011 | 1.6043 | 2019 | 1.2768 | | |

This is the Federal Reserve noon-rate series, not the Bank of England's; the two differ by no more than about 0.01. For an April year end, use 8/12 of year *n* plus 4/12 of year *n*+1. FY2005/06 gives 1.828; FY2008/09 gives 1.758 [D] (this overstates FY08/09, because sterling fell sharply after Oct 2008).

---

#### 6. UK rules

| Rule | Detail | Tag / source |
| --- | --- | --- |
| SRA established | **29 January 2007** (infobox). Formed in January 2007 as the Law Society's independent regulatory arm (the board was formerly the Law Society Regulation Board [A]). Later powers came from the Legal Services Act 2007 (Royal Assent 30 Oct 2007 [A]) | S, U1 |
| Regulation milestones | Outcomes-focused SRA Handbook **6 Oct 2011** [S for 2011, U1; day A]. Replaced by the **SRA Standards and Regulations on 25 Nov 2019** | S, U1 |
| Solicitors Indemnity Insurance | Compulsory open-market cover on minimum terms since **1 Sep 2000**, when the Solicitors Indemnity Fund stopped underwriting new risks. Minimum **£2m any one claim**; **£3m** for "relevant recognised bodies", i.e. LLPs and companies. Insurers must sign the SRA Qualifying Insurers Agreement. The Assigned Risks Pool was abolished from 1 Oct 2013 | S·snip, U4. The £3m LLP/company tier applies from at least the SRA's 2010s rules; its start date was not found (likely 2005, with LLPs [A]) |
| Client money | Solicitors' Accounts Rules 1998 (in force in 2005); then SRA Accounts Rules 2011. Replaced by the **SRA Accounts Rules 2019 (25 Nov 2019)**: cut from 52 rules to 13; added **third-party managed accounts** as an alternative to a client account; "client money" redefined | S·snip, U5 (2019); 1998/2011 names A |
| LLP status | Limited Liability Partnerships Act 2000, in force 6 Apr 2001 [A]. Major-firm conversions: A&O first (decided by Feb 2005); Clifford Chance Dec 2006 (previously a US-registered LLP); Linklaters "on ice" Mar 2006, converted later [A: 2007]; Freshfields and Macfarlanes May 2008; Travers Jul 2008; Simmons Nov 2010; Ince Mar 2011 ("one of the last top 50"). **Slaughter and May remains a general partnership** | S·snip, U8; S, W |
| Foreign lawyers | Registered Foreign Lawyers (RFLs) may be partners in solicitor firms (in force 2005 [A]). US attorneys requalify via the **QLTT** (to 2010), then the **QLTS** (1 Sep 2010 – 2021/22), then the **SQE** (from 1 Sep 2021). US-qualified lawyers had exemptions under QLTS and partial exemptions under SQE [A] | S, U2 |
| Practising certificate fee (individual, England & Wales) | 2005/06: not found (≈£1,000 including compensation-fund contribution [A]; a Solicitors Journal headline reports the PC fee "for the first time in history broken the £1,000 mark, rising to £1,180", date not seen). 2019/20: £278 [S·snip]; 2021/22: £266; 2022/23: £286; 2024/25: £307 + £90 compensation fund = £397; 2025/26: £396 total | S·snip, U6 |

---

#### 7. Six US cities relative to New York

#### 7.1 Size, rates, pay, rent and practices

| City | (a) Large-firm lawyers, 2025 (Am Law 200) [S, C4] | ≈ ratio to NY [D] | (b) Partner rate vs NY [S·snip, R5] | (c) 1st-year salary, 2005 → matching NY steps [S, C1/C2] | (d) CBD Class A asking rent, Q4 2005, $/sf/yr [S, C3] | Rent ratio to NY (Midtown $60.17) [D] | (e) Dominant practices [A] |
| --- | --- | --- | --- | --- | --- | --- | --- |
| New York | 27,400 (NLJ 500 Dec 2024: 29,352 [S·snip, C6]) | 1.00 | 2012 avg $755.68; 2021 median $955; 2023 $975 | $125,000 (2000–05); $145k (Apr 2006); $160k (2007) | $60.17 (Downtown $40.26) | 1.00 | M&A, capital markets, finance, litigation, restructuring |
| Washington, DC | 15,300 | 0.56 | 2012 $649.24 (0.86×); 2021 $872 (0.91×); 2023 $925 (0.95×); DC litigation the highest in 2023 | $125,000 (2005; $120k in 2002–04); $135k (2006); $145k (2007); **$160k (2008, matched)** | $46.08 | 0.77 | regulatory/government, antitrust, white collar, appellate, telecoms, IP |
| Chicago | 8,800 (NLJ 500: 10,281) | 0.32 | 2012 $585.47 (0.77×); 2014 avg $691; 2023 $765 (0.78×) | $125,000 (2005); $132.5k (2006); $145k (2007); **$160k (2008)** | $29.42 | 0.49 | corporate/PE, litigation, restructuring, futures/derivatives |
| Boston | 5,300 (NLJ 500: 6,103) | 0.19 | 2012 $598.69 (0.79×); 2021 avg $830 | $125k [A]; $135k (2006) [S, C2] | $41.36 (Q2 2005 Greater Boston $32.68 [S·snip]) | 0.69 | life sciences/biotech, investment funds, VC, IP, private equity |
| Los Angeles | 7,800 (NLJ 500: 8,458) | 0.28 | 2012 $620.34 (0.82×); 2014 avg $665; 2023 $795 (0.82×) | $125,000 (2001–05); $135k (2006); $145k (2007); **$160k (2008)** | $26.76 | 0.44 | entertainment/media, litigation, real estate, employment |
| SF Bay Area | 4,900 (San Francisco only; Palo Alto/Silicon Valley not found) | 0.18 (city) / ≈0.30 incl. Silicon Valley [A] | SF 2012 $651.33 (0.86×); 2021 $580 (0.61×, as reported); 2023 $608 | $125k (Silicon Valley "unchanged since April 2000") [S·snip]; $135k (2006) [S, C2] | SF $32.78; San Jose $28.23; Oakland $27.41 | 0.54 / 0.47 | tech/VC, emerging companies, IP/patent litigation, securities litigation |
| Houston | not found (Texas holds 7% of Am Law 200 lawyers [S, C4]) | ≈0.15 [A] | 2012 $549.25 (0.73×); 2021 growth <2% | $125k [A]; $135k (2006) [S, C2]; 2019: 61.5% of reporting offices at $190k [S·snip, C11] | $22.16 | 0.37 | energy (oil and gas, LNG, power), project finance, energy litigation, restructuring |

**Notes on the table**
- **Headcount ratios** are the only city data found, and they are for 2024–25. For 2005 the game can assume similar ratios, with DC ≈0.6 [A] (NY had "65% more NLJ 250 attorneys than DC", an undated Law.com infographic [S·snip], which gives DC ≈ 0.61×).
- **Largest single office per city:** in 2016, Paul Weiss NY 781, Covington DC 459, Kirkland Chicago 569, Lewis Brisbois LA 299, Ropes Boston 438, MoFo SF 228, V&E Houston 243; in 2025, Kirkland NY 969, Covington DC 627, Kirkland Chicago 756, Gibson LA 299, Ropes Boston 504 [S, C5].
- **Later salary steps** [S·snip, C11, and general knowledge]: NY moved to $180k in 2016, $190k in 2018 and $215k in 2022, with $225k at many firms by 2023–25. By 2025 the $225k scale was paid in Austin, Boston, Houston, NYC, San Francisco and Washington DC [S·snip, C11]. Chicago and LA large firms generally matched within weeks [A]. Big-firm medians: $180k in 2019 (701+ lawyers), the all-firm median $200k in 2023 and 2025, and $215k in firms of 700+ in 2025 [S·snip, C11].
- **2024 rents [S·snip, C12]:** Manhattan Class A average $82.74 (Q1 2024; Midtown South $103.42); Chicago CBD Class A $51.06; SF $61.91 (Dec 2023); DC Class A ≈$60 gross (date unclear). Boston, LA and Houston 2024 were not found.

#### 7.2 London versus New York, office cost
In CBRE's November 2006 survey of prime occupancy cost, **London West End was $212.03/sf/yr** (the most expensive in the world), **London "City" $144.78** and **Midtown Manhattan $62.07** (ranked 24th) [S·snip, C7]. City of London prime occupancy therefore cost ≈**2.3× Midtown** in 2006 [D: 144.78 ÷ 62.07]. Occupancy cost includes taxes and service charges, while the US figure is asking rent; on rent alone the ratio is ≈1.6–2.0× [A].

---

#### 8. US bar admission

| Jurisdiction | Admission on motion (current) | Fee (motion) | Pro hac vice (approx.) | Tag |
| --- | --- | --- | --- | --- |
| New York | Yes; 5 of the past 7 years in practice (reciprocity required [A]); plus a $375 biennial attorney registration | $400 | court-by-court (≈$0–$375 [A]); not found | S, C8/C9 |
| District of Columbia | Yes (D.C. App. R. 46). No reciprocity; routes: 3 of the 5 years before applying; a member in good standing of another bar for 5 years; or a transferred MBE score (133 [A]) | $595 + C&F (from 4/1/2024) | not found (≈$100 [A]) | S, C8/C9 |
| Illinois | Yes; 3 of the past 5 years (no reciprocity showing) | $1,500 total ($150 preliminary questionnaire) | ARDC per-case fee ≈$250 [A]; not found | S, C8/C9 |
| Massachusetts | Yes; 5 of the past 7 years | $1,015 + C&F | $355 (raised from $301 in 2018) | S, C8; S·snip, C10 |
| California | **No** admission on motion or reciprocity. Attorneys licensed elsewhere sit the bar exam (the "Attorneys' Examination" was the shorter variant; current details not seen) | — | court rule cap $50; the State Bar approved $500 per application (proposal; adoption not confirmed) | S, C8; S·snip, C10 |
| Texas | Yes; 5 of the past 7 years | $1,040 | proposed $200 per case (status unclear); S.D. Tex. federal fee exists | S, C8; S·snip, C10 |

- **Bar exam timing** [A, general knowledge]: the exam sits on the last Tuesday–Wednesday of **July** and of **February**. Results come out in about 3–4 months: NY by late Oct/Nov for July; California in mid-November; DC, Illinois, Massachusetts and Texas Oct–Nov. February results come out in April–May. Admission ceremonies follow 1–4 months later (NY needs character and fitness review and the 50-hour pro bono rule from 2015 [A]).
- **Federal courts:** the most common pro hac vice fee is $100 (30 districts) [S·snip, C10].
- **Rule history 2005–25:** not researched. DC already admitted without examination in 2005 [A]. Illinois and Massachusetts liberalised admission on motion in the 2010s [A].

---

### Gaps

1. **FY2005/06 PEP not found** for Slaughter and May (undisclosed), Lovells, Simmons, CMCK, AG, BLP, SJB, Pinsent Masons, Macfarlanes, Travers and DLA International. **FY2005/06 lawyer and equity-partner counts** are mostly [A], back-cast from FY2008/09. The Lawyer UK100 2006 and the Legal Week Top 50 2006 tables (paywalled) would fix both.
2. **Paths missing:**
   - FY2012 and FY2019/FY2021 per firm (only FY09/10, FY14/15 and FY17/18 are filled);
   - the FY2024/25 PEP for Freshfields, Pinsent, Eversheds, BCLP, Travers, NRF, CMS;
   - the Norton Rose Fulbright FY2024 revenue.
3. **Practice-area split of the London market:** only the FY2014/15 headline shares (litigation, corporate, finance) are sourced; everything else is [A].
4. **UK top-50 totals:** no single consistent series. Legal Week (2008/09, 2017/18) and The Lawyer (2004/05–2006/07, UK200 2009) are solid. 2009/10–2016/17 come from headlines only. 2019/20–2024/25 use mixed bases (Evelyn filed accounts, LB100, TheCityUK). FY2015/16 and FY2021/22 totals were not found.
5. **UK legal services market size for 2005** not found (TheCityUK's series starts in about 2014 in what was seen).
6. **London rates:** the 2005 City-band guideline hourly rate was not found, and neither were firm-specific Magic Circle partner rates for 2010, 2015 or 2020 (only the survey ranges for 2003, 2005, 2007, 2011, 2022 and 2025). Associate charge-out rates are [A] except the 2022 NQ rate of £600.
7. **Salaries:** the NQ series for 2009–2014 (including any 2009 cuts) and all Magic Circle trainee pay for 2005–2012 are [A] or thinly sourced. The 2016 Freshfields £85k date is uncertain.
8. **US cities:** no 2005 large-firm headcount by city; no Houston or Silicon Valley headcount; no 2005 partner-rate survey (the earliest by city is 2012); Boston and Houston 2005 starting salaries are [A]; no 2024 rents for Boston, LA or Houston; no London Class A rent for 2024.
9. **US admission:** pro hac vice fees for NY, DC, Illinois and Texas, the California Attorneys' Exam details, and rule changes over 2005–25 were not confirmed.
10. **UK rules:** the start date of the £3m minimum indemnity for LLPs and companies, the 2005–2018 practising-certificate fees, Linklaters' and Herbert Smith's LLP conversion dates, and the exact days of several merger completions (Ogilvy Renault, Macleod Dixon, Fulbright, KWM, Sutherland, McGrigors) are [A].
11. **Slater & Gordon's 2012 purchase of Russell Jones & Walker** is [A] on the firm name: the source seen says only "several UK firms in 2012".

---

## Part B — Notable lawyers dossier, part B: 18 London firms at January 2005

**Status:** research pass compiled 2026-11-23 for PT-M5 (`notables.yaml`; ADR PT-0013, spec §10.1). Research only: no code or data YAML was changed. Firm keys are the ones named in the brief (they are not yet in `firms.yaml`; check them against it before pasting).

## Rules applied (ADR PT-0013 and the 2026-11-19 review notes)

- **Public professional standing only:** name, role in January 2005, office, practice, standing, and dated professional moves 2005–2025 (laterals, elections as senior or managing partner, government or bench appointments, in-house or non-legal moves, consultancies, retirement from partnership).
- **Never recorded:** private life, family, health, age or birth date, death, politics, honours tied to politics, misconduct, discipline, lawsuits, scandals, workplace conduct or criticism. Where a source covered any of these (for example a cause of departure), it was left out. Anyone who stopped practising by 2025 has **"left practice (YYYY)"** with no cause, whatever the reason. Nobody mainly known for a controversy was picked.
- **Every row has an [S] source for the January-2005 role at that firm** (the first source listed for the row, and the `role S` URL in the YAML). Rows without one were dropped. Where the only source is dated just before or after January 2005, it is a press report of a role that spans January 2005 (for example an election in 2004 to a term starting 2005, or a re-election in 2006 for a role held since 2001).
- **Every row has a career-start year:** [S] where a source gives a qualification, trainee or joining year (a joining year is used as the career start when nothing earlier was found, and the basis says so), [D] where derived from a stated tenure ("retired in 2016 after 39 years"), otherwise [A] with the basis stated.
- **Tags:** **[S]** sourced this session (URL in the numbered list), **[D]** derived from sourced facts, **[A]** assumed (basis stated).
- **standing** (`elite | leading | strong`) is always [D], my judgement from leadership roles, practice-head roles and reputation shown in the sources; no Chambers UK or Legal 500 2005 band was found for anyone (archived editions were not reachable), so no band is recorded.
- **practice** uses `backend/data/practices.yaml` keys only. Competition, energy, tax and arbitration have no key, so the nearest is used and tagged [D] or [A] (competition and energy and tax: `corporate_ma`; arbitration: `commercial_litigation`). Many firm leaders' practices were not confirmed; they are `corporate_ma` [A].
- **level** is `equity_partner` for everyone (all were partners of lockstep or equity partnerships in 2005). **chair: true** marks the firm's senior partner or chairman in January 2005; where a firm had both, the senior partner or chairman has `chair: true` and the managing partner or CEO is noted in `role_2005`. Freshfields had joint senior partners; Salz has `chair: true` and Mettenheimer `false` (noted in his role).
- **Moves:** `chair_role` is used for every election to senior partner, managing partner, chair or CEO (including later ones and merged-firm roles). `to` is given only for a lateral to one of the brief's firm keys or the listed US firms. Laterals to the Bar or to firms outside those lists have no `to`. Non-legal executive roles are `in_house` (for example S&P, Shell) or `left_practice` when the person left law (for example Citi, Rothschild, Terra Firma). Months are [A] where the source gives only a year (noted in the row).
- Firm mergers (Hogan Lovells 2010, Norton Rose Fulbright 2013, HSF 2012, SJ Berwin into KWM 2013, BCLP 2018, CMS 2017, A&O Shearman 2024) are firm events, not moves.

**Count:** 78 people across 18 firms. Career starts: 24 [S], 11 [D], 43 [A]. The first eleven firms have 4–7 each (Slaughter and May, Ashurst and CMS have 4); the last seven have 2–4 (Eversheds and BLP have 2). See *Gaps*.

## Tables

### Clifford Chance (`clifford_chance`) — 6 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Stuart Popham | `clifford_chance__stuart_popham` | Senior partner (elected 2002, in office from 2003; re-elected 2006 to Dec 2010) [S] | London | `corporate_ma` [A: practice not confirmed this session] | equity_partner | leading | true | 1978 [S: admitted 1978 (Powerbase)] | 2011-04 left_practice: left CC Apr 2011 (joined Citi Jul 2011, non-legal role) [S] | left practice (2011) [S] | 1, 2, 3, 4 |
| Peter Cornell | `clifford_chance__peter_cornell` | Global managing partner (to Apr 2006) [S] | London | `corporate_ma` [A: nearest; later private equity role] | equity_partner | leading | false | 1975 [A: tenure from 1975 per MarketScreener profile cited in press search] | 2006-10 left_practice: left CC Oct 2006; Terra Firma from Oct 2007 [S] | left practice (2006) [S] | 5, 6, 7, 8 |
| David Childs | `clifford_chance__david_childs` | Chief operating officer (since 2003); global head of corporate until Mar 2005 [S] | London | `corporate_ma` [S: global corporate head] | equity_partner | leading | false | 1978 [A: no year found; COO by 2003 after a long CC career, assumed ~25 years qualified] | 2006-05 chair_role: Managing partner from 1 May 2006 (two terms) [S]; 2014-05 left_practice: retired as MP May 2014; FRC committee chair [S] | left practice (2014) [S] | 9, 10, 11 |
| Malcolm Sweeting | `clifford_chance__malcolm_sweeting` | Finance partner (partner since 1990); led London banking group [S] | London | `banking_finance` [S] | equity_partner | leading | false | 1982 [A: partner 1990 less ~8 years] | 2011-01 chair_role: Senior partner Jan 2011 (re-elected 2014) [S]; 2019-03 left_practice: left for a role outside the legal sector [S] | left practice (2019) [S] | 12, 13, 14 |
| Matthew Layton | `clifford_chance__matthew_layton` | Corporate partner (joined 1983, partner 1991) [S] | London | `corporate_ma` [S: M&A, private equity, corporate finance] | equity_partner | leading | false | 1983 [S: joined CC 1983 (WEF bio, City AM)] | 2014-05 chair_role: Global managing partner from 1 May 2014 (re-elected 2017) [S] |  | 15, 16, 17 |
| Audley Sheppard | `clifford_chance__audley_sheppard` | International arbitration partner (partner 1995-2023) [S] | London | `commercial_litigation` [D: nearest key for arbitration] | equity_partner | leading | false | 1986 [D: 38 years at CC to 2024 (Twenty Essex)] | 2023-05 of_counsel: consultant to CC [S]; 2024-06 lateral: to Twenty Essex (barristers' chambers) as arbitrator [S] |  | 18, 19 |

### Linklaters (`linklaters`) — 6 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Anthony Cann | `linklaters__anthony_cann` | Senior partner (Sep 2001 - Sep 2006) [S] | London | `corporate_ma` [S: public and private M&A] | equity_partner | leading | true | 1969 [D: 37 years with the firm at Sep 2006 retirement] | 2006-09 left_practice: retired at end of term [S] | left practice (2006) [S] | 20, 21 |
| Tony Angel | `linklaters__tony_angel` | Managing partner (elected 1998, second term 2003; head of tax from 1994) [S] | London | `corporate_ma` [A: tax is not a game key; nearest] | equity_partner | leading | false | 1978 [D: 30-year spell at the firm ending 2008; partner 1984] | 2008-04 in_house: left Linklaters Apr 2008; executive MD at Standard & Poor's (non-legal) [S]; 2011-11 lateral: DLA Piper global co-chairman [S] |  | 22, 23, 24 |
| David Cheyne | `linklaters__david_cheyne` | Global head of corporate (2000-2005) [S] | London | `corporate_ma` [S] | equity_partner | elite | false | 1972 [S: joined Linklaters 1972, partner 1980] | 2006-10 chair_role: Senior partner 1 Oct 2006 - 2011 [S]; 2011-10 of_counsel: consultant after term [S] |  | 25, 21, 26, 27 |
| Robert Elliott | `linklaters__robert_elliott` | Global head of restructuring and insolvency (from 1996); banking partner [S] | London | `restructuring` [S] | equity_partner | elite | false | 1976 [S: joined Wilde Sapte 1976; Linklaters 1990, partner 1991] | 2011-10 chair_role: Senior partner Oct 2011 - Sep 2016 [S]; 2016-10 of_counsel: consultant [S] |  | 28, 29, 30 |
| Simon Davies | `linklaters__simon_davies` | Managing partner, Asia (2003-2007) [S] | Hong Kong | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1985 [A: no year found; more than a decade in Asia before 2007, assumed] | 2008-01 chair_role: Firmwide managing partner from 1 Jan 2008 (second term 2012) [S]; 2016-01 in_house: Lloyds Banking Group chief people, legal and strategy officer [S] | left practice (2016) [S] | 31, 32, 33 |
| Charles Jacobs | `linklaters__charles_jacobs` | Corporate partner (joined 1990, partner 1999) [S] | London | `corporate_ma` [S: M&A and capital raisings] | equity_partner | leading | false | 1992 [S: admitted 1992 (Law Gazette)] | 2016-10 chair_role: Senior partner from 1 Oct 2016 [S] |  | 34, 35 |

### Allen & Overy (`allen_overy`) — 5 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Guy Beringer | `allen_overy__guy_beringer` | Senior partner (2000-2008; second term confirmed 2003) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1978 [S: joined A&O as a trainee 1978 (New Law Journal)] | 2008-04 left_practice: stepped down and retired end Apr 2008 [S] | left practice (2008) [S] | 36, 37, 38 |
| David Morley | `allen_overy__david_morley` | Managing partner (from 2003); former global head of banking (1998) [S] | London | `banking_finance` [S] | equity_partner | leading | false | 1982 [S: trainee 1980, qualified 1982, partner 1988] | 2008-05 chair_role: Senior partner 2008-2016 [S]; 2016-04 left_practice: retired end Apr 2016 [S] | left practice (2016) [S] | 39, 40, 41 |
| Wim Dejonghe | `allen_overy__wim_dejonghe` | Managing partner, Belgian offices; co-head global corporate (A&O partner from 2001) [S] | Brussels | `corporate_ma` [S] | equity_partner | leading | false | 1985 [A: partner at Loeff Claeys Verbeke from 1993; assumed qualified ~8 years earlier] | 2008-05 chair_role: Global managing partner May 2008 [S]; 2016-05 chair_role: Senior partner May 2016 (re-elected 2020) [S] |  | 42, 43 |
| Andrew Ballheimer | `allen_overy__andrew_ballheimer` | Corporate partner (associate 1987, partner 1994) [S] | London | `corporate_ma` [S] | equity_partner | leading | false | 1987 [S: joined as associate 1987] | 2016-05 chair_role: Global managing partner 2016-2020 [S]; 2020-04 left_practice: retired end Apr 2020 [S] | left practice (2020) [S] | 44, 45 |
| Richard Cranfield | `allen_overy__richard_cranfield` | Global head of corporate (from 2000) [S] | London | `corporate_ma` [S] | equity_partner | leading | false | 1978 [S: joined A&O from university 1978] | 2021-10 left_practice: retired as partner Oct 2021 (senior adviser to May 2022) [S] | left practice (2021) [S] | 46, 47 |

### Freshfields Bruckhaus Deringer (`freshfields`) — 7 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Anthony Salz | `freshfields__anthony_salz` | Joint senior partner (senior partner since 1996; joint with Mettenheimer from 1 May 2004) [S] | London | `corporate_ma` [A: corporate background; not confirmed] | equity_partner | elite | true | 1975 [S: joined Freshfields 1975] | 2006-05 left_practice: retired from the firm 2006; Rothschild executive vice-chairman (month A) [S] | left practice (2006) [S] | 48, 49, 50, 51 |
| Konstantin Mettenheimer | `freshfields__konstantin_mettenheimer` | Joint senior partner (from 1 May 2004); tax and corporate [S] | Frankfurt [A: Germany-based per law.com 2009; city assumed] | `corporate_ma` [S: tax and corporate] | equity_partner | leading | false | 1986 [S: with the firm since 1986 (joining year, used as career start)] | none recorded |  | 48, 52 |
| Peter Jeffcote | `freshfields__peter_jeffcote` | Managing partner (from Oct 2001; reappointed late 2005); former employment head [S] | London | `employment` [S] | equity_partner | leading | false | 1978 [A: no year found; employment head by 2001, assumed] | none recorded |  | 53, 54, 55 |
| Guy Morton | `freshfields__guy_morton` | Head of financial services regulatory practice (partner since 1986) [S] | London | `banking_finance` [D: financial services regulation; nearest] | equity_partner | leading | false | 1978 [A: partner 1986 less ~8 years] | 2006-05 chair_role: Joint senior partner (elected Dec 2005; month A) [S] |  | 56, 54 |
| Ian Terry | `freshfields__ian_terry` | Dispute resolution partner; former managing partner (1996-2001) [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1978 [D: left in 2016 after 38 years] | 2016-03 lateral: to the Bar (Chambers of Lord Grabiner) [S] |  | 53, 57, 58 |
| Edward Braham | `freshfields__edward_braham` | Corporate / M&A partner (trainee 1985, partner c.1995) [S] | London | `corporate_ma` [S] | equity_partner | leading | false | 1985 [S: joined as trainee 1985 (Legal Business)] | 2016-01 chair_role: Senior partner from 1 Jan 2016 [S] |  | 59, 60 |
| Jan Paulsson | `freshfields__jan_paulsson` | Head of international arbitration and public international law (1993-2012) [S] | Paris | `commercial_litigation` [D: nearest key for arbitration] | equity_partner | elite | false | 1975 [A: law degree c.1975 (Yale JD per Wikipedia; not re-read this session)] | 2014-01 lateral: Three Crowns partner 2014-2020 (left Freshfields 2012) [S] |  | 61, 62 |

### Slaughter and May (`slaughter_may`) — 4 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Tim Clark | `slaughter_may__tim_clark` | Senior partner (May 2001 - Apr 2008; extended Feb 2005) [S] | London | `corporate_ma` [S: corporate dealmaker] | equity_partner | leading | true | 1974 [S: practised at Slaughters from 1974] | 2008-04 left_practice: retired end Apr 2008 [S] | left practice (2008) [S] | 63, 64, 65, 66 |
| Chris Saul | `slaughter_may__chris_saul` | Head of corporate (from Apr 2004) [S] | London | `corporate_ma` [S] | equity_partner | elite | false | 1977 [D: retired Apr 2016 after 39 years] | 2008-05 chair_role: Senior partner from 1 May 2008 [S]; 2016-04 left_practice: retired 30 Apr 2016 [S] | left practice (2016) [S] | 67, 65, 68, 69 |
| Nigel Boardman | `slaughter_may__nigel_boardman` | M&A partner (partner 1982-2019) [S] | London | `corporate_ma` [S] | equity_partner | elite | false | 1973 [S: joined Slaughter and May 1973] | 2019-04 of_counsel: retired as partner; consultant [S]; 2022-05 left_practice: left the firm after consultancy [S] | left practice (2022) [S] | 70, 71 |
| Steve Cooke | `slaughter_may__steve_cooke` | Head of M&A (since 2001) [S] | London | `corporate_ma` [S] | equity_partner | elite | false | 1982 [S: joined as trainee 1982] | 2016-05 chair_role: Senior partner from 1 May 2016 (extended to 2024) [S] |  | 69, 72 |

### Herbert Smith (`herbert_smith`) — 5 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Richard Bond | `herbert_smith__richard_bond` | Senior partner (five-year term to 31 Mar 2005); former head of corporate [S] | London | `corporate_ma` [S: former corporate head] | equity_partner | leading | true | 1972 [A: no year found; senior partner c.2000, assumed ~30 years qualified by 2005] | 2005-04 left_practice: retired at end of term (month A) [S] | left practice (2005) [S] | 73, 74, 75 |
| David Gold | `herbert_smith__david_gold` | Head of litigation; senior partner-elect (elected Oct 2004, term from 1 Apr 2005) [S] | London | `commercial_litigation` [S] | equity_partner | elite | false | 1975 [A: no year found; head of litigation by 2004, assumed] | 2005-04 chair_role: Senior partner Apr 2005 - May 2010 [S]; 2011-01 left_practice: left to launch own consultancy (year D, month A) [D] | left practice (2011) [D] | 73, 76, 77, 78 |
| David Willis | `herbert_smith__david_willis` | Corporate partner [S] | London | `corporate_ma` [S] | equity_partner | leading | false | 1980 [A: no year found; senior corporate partner by 2005, assumed] | 2008-04 chair_role: Managing partner Apr 2008 (to 2013) [S] |  | 79, 80 |
| Jonathan Scott | `herbert_smith__jonathan_scott` | Head of EU and competition (1996-2007); partner since 1988 [S] | London | `corporate_ma` [D: competition has no key; nearest] | equity_partner | leading | false | 1980 [D: left Jan 2015 after 35 years] | 2010-05 chair_role: Senior partner May 2010 [S]; 2015-01 left_practice: retired as chair and partner [S] | left practice (2015) [S] | 81, 82, 83 |
| James Palmer | `herbert_smith__james_palmer` | Equity capital markets co-head (2005-2010); partner since 1994 [S] | London | `capital_markets` [S] | equity_partner | leading | false | 1986 [S: joined as trainee 1986] | 2015-05 chair_role: Senior partner 2015 (re-elected 2018; to Apr 2021) (month A) [S] |  | 84, 85 |

### Lovells (`lovells`) — 6 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| John Young | `lovells__john_young` | Senior partner (from 1 May 2004) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1979 [D: 33-year legal career to 2012] | 2010-05 chair_role: Co-chairman of Hogan Lovells on the 2010 merger [S]; 2012-04 left_practice: retired Apr 2012 [S] | left practice (2012) [S] | 86, 87, 88 |
| Lesley MacDonagh | `lovells__lesley_macdonagh` | Managing partner (1 May 1995 - Apr 2005) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1978 [S: joined Lovell White & King 1978 (joining year), partner 1981] | 2006-05 of_counsel: retired from partnership 2006; stayed to 2007 in a firm role (month A) [S] | left practice (2007) [S] | 86, 89, 90 |
| David Harris | `lovells__david_harris` | Head of finance stream; managing partner-elect (elected Nov 2004, from 1 May 2005) [S] | London | `capital_markets` [S: capital markets and structured finance] | equity_partner | leading | false | 1982 [A: no year found; finance stream head by 2004, assumed] | 2005-05 chair_role: Managing partner May 2005 [S]; 2010-05 chair_role: Co-CEO of Hogan Lovells 2010 - Jun 2014 [S] |  | 91, 92, 93 |
| Patrick Sherrington | `lovells__patrick_sherrington` | Head of dispute resolution [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1980 [A: no year found; practice-group head by 2005, assumed] | none recorded |  | 94, 92 |
| Nicholas Cheffings | `lovells__nicholas_cheffings` | Real estate disputes partner (Lovells partner from 1999) [S] | London | `real_estate` [S: real estate litigation] | equity_partner | leading | false | 1983 [S: qualified 1983 (Legal 500)] | 2012-05 chair_role: Sole chairman of Hogan Lovells (three-year term) [S] |  | 95, 96 |
| Lisa Mayhew | `lovells__lisa_mayhew` | Employment partner (joined Lovells as partner 2002) [S] | London | `employment` [S] | equity_partner | leading | false | 1990 [A: no year found; partner by 2002, assumed] | 2010-01 lateral to `berwin_leighton_paisner`: to BLP in 2010 from Jones Day (Lovells-to-Jones Day date not found; month A) [S]; 2015-05 chair_role: BLP managing partner 1 May 2015; BCLP co-chair 2018 [S] |  | 97, 98 |

### Ashurst (`ashurst`) — 4 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Geoffrey Green | `ashurst__geoffrey_green` | Senior partner (1998-2008; re-elected Nov 2003) [S] | London | `private_equity` [S: built PE practice as corporate head] | equity_partner | leading | true | 1979 [D: retired 2013 after 34 years] | 2013-04 left_practice: retired after the Blake Dawson integration (month A) [S]; 2015-04 government: FRC Financial Reporting Review Panel chair [S] | left practice (2013) [S] | 99, 100, 101 |
| Simon Bromwich | `ashurst__simon_bromwich` | Managing partner (2004-2012) [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1991 [A: partner 1999 (five years as partner by 2004) less ~8 years] | none recorded |  | 102, 103, 104 |
| Charlie Geffen | `ashurst__charlie_geffen` | Private equity head (corporate partner) [D] | London | `private_equity` [S] | equity_partner | elite | false | 1980 [A: no year found; PE head by 2008, assumed] | 2009-01 chair_role: Senior partner from end 2008 (to 2013) [S]; 2014-10 lateral to `gibson_dunn`: to Gibson Dunn London [S] |  | 105, 106 |
| Edward Sparrow | `ashurst__edward_sparrow` | Litigation partner (since 1981); management board member (from 2004) [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1975 [A: partner 1981 less ~6 years] | none recorded |  | 107, 108, 105 |

### Norton Rose (`norton_rose`) — 5 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Paul Giles | `norton_rose__paul_giles` | Chairman (Apr 2003 - Apr 2009); asset finance partner [S] | London | `banking_finance` [S: asset finance (aviation, shipping)] | equity_partner | leading | true | 1978 [A: no year found; Asia managing partner before 2003, assumed] | none recorded |  | 109, 110 |
| Peter Martyr | `norton_rose__peter_martyr` | Chief executive (from 2002 election; re-elected Nov 2005) [S] | London | `commercial_litigation` [S: shipping litigation] | equity_partner | leading | false | 1979 [D: trainee 1977; qualified about two years later; partner 1985] | none recorded |  | 111, 112 |
| Stephen Parish | `norton_rose__stephen_parish` | London head of banking (global banking head from Jan 2006) [S] | London | `banking_finance` [S] | equity_partner | leading | false | 1974 [S: joined Norton Rose 1974 (joining year)] | 2009-05 chair_role: Chairman 1 May 2009 (re-elected 2012, 2015; stepped down 2018) [S] |  | 113, 110, 114 |
| Jeffery Barratt | `norton_rose__jeffery_barratt` | Global head of banking (to Jan 2006) [S] | London | `banking_finance` [S] | equity_partner | leading | false | 1976 [S: joined Norton Rose Sep 1976] | 2014-12 left_practice: senior banking partner 2006-2014 (month A) [D] | left practice (2014) [D] | 113, 115 |
| Peter Rees | `norton_rose__peter_rees` | Litigation partner (partner 1987-2006); head of international strategy (board, 2004) [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1979 [A: partner 1987 less ~8 years] | 2006-01 lateral to `debevoise`: to Debevoise & Plimpton (month A) [S]; 2010-11 in_house: Shell legal director [S]; 2014-03 lateral: to the Bar (39 Essex Street) [S] |  | 116, 117, 118 |

### Simmons & Simmons (`simmons`) — 5 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Janet Gaymer | `simmons__janet_gaymer` | Senior partner (since 2001) [S] | London | `employment` [S] | equity_partner | elite | true | 1975 [D: 30 years in employment law by end 2005] | 2006-01 government: Commissioner for Public Appointments (Jan 2006 - Dec 2010) [S] | left practice (2006) [S] | 119, 120, 121 |
| David Dickinson | `simmons__david_dickinson` | Managing partner (1999 - May 2005); founding partner of the finance practice [S] | London | `banking_finance` [S] | equity_partner | leading | false | 1978 [A: no year found; MP from 1999, assumed] | 2006-04 chair_role: Senior partner Apr 2006 - Jul 2011 [S]; 2011-08 left_practice: retired from the firm [S] | left practice (2011) [S] | 122, 123, 124 |
| Mark Dawkins | `simmons__mark_dawkins` | Head of financial markets; managing partner-elect (chosen Nov 2004, from 1 May 2005) [S] | London | `commercial_litigation` [S: banking litigator] | equity_partner | leading | false | 1982 [A: no year found; practice head by 2004, assumed] | 2005-05 chair_role: Managing partner May 2005 - 2011 [S]; 2011-06 lateral: to Bingham McCutchen London [S] |  | 122, 124, 125 |
| Colin Passmore | `simmons__colin_passmore` | Litigation partner (joined 1986, partner 1990) [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1986 [S: joined the firm 1986] | 2011-08 chair_role: Senior partner Aug 2011 - Jul 2021 [S] |  | 124, 126 |
| Jeremy Hoyland | `simmons__jeremy_hoyland` | Finance partner (trainee 1989, partner 1997); head of financial institutions sector (2005) [S] | London | `banking_finance` [S] | equity_partner | leading | false | 1989 [S: joined as trainee 1989] | 2011-05 chair_role: Managing partner from 1 May 2011 (third term 2019) [S] |  | 127, 128 |

### CMS Cameron McKenna (`cms_cameron_mckenna`) — 4 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Richard Price | `cms_cameron_mckenna__richard_price` | Senior partner (from May 2002 to Apr 2011); corporate partner [S] | London | `corporate_ma` [S] | equity_partner | leading | true | 1976 [A: no year found; senior partner from 2002, assumed] | none recorded |  | 129, 130 |
| Dick Tyler | `cms_cameron_mckenna__dick_tyler` | Managing partner (2000 - Apr 2008) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1978 [A: no year found; MP from 2000, assumed] | 2008-09 chair_role: CMS (network) executive partner [S]; 2011-05 chair_role: Senior partner May 2011 - 2014 [S] |  | 131, 132, 130 |
| Duncan Weston | `cms_cameron_mckenna__duncan_weston` | Managing partner, Central and Eastern Europe (from 2001) [S] | Central and Eastern Europe [A: city not found] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1985 [A: no year found; CEE head from 2001, assumed] | 2008-05 chair_role: UK managing partner 1 May 2008 (second term 2011) [S] |  | 133, 134, 131 |
| Penelope Warne | `cms_cameron_mckenna__penelope_warne` | Energy partner (joined 1993 to set up the Aberdeen office) [S] | Aberdeen | `corporate_ma` [D: energy has no key; nearest] | equity_partner | leading | false | 1986 [A: trained at Slaughter and May (five years) before 1993; assumed] | 2014-05 chair_role: Senior partner May 2014 (second term 2020) [S] |  | 135, 136, 137 |

### Eversheds (`eversheds`) — 2 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Alan Jenkins | `eversheds__alan_jenkins` | Chairman (from 2004) and head of international [S] | London [A] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1978 [A: no year found; head of international by 2004, assumed] | 2011-04 left_practice: retired Apr 2011 [S] | left practice (2011) [S] | 138, 139, 140 |
| David Gray | `eversheds__david_gray` | Managing partner (from May 2003; second term from 2006) [S] | Leeds [A: former Leeds and Manchester managing partner] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1980 [A: no year found; regional MP by 2002, assumed] | 2009-05 chair_role: Chairman of Eversheds International (to 2013) (month A) [S] |  | 141, 142, 143 |

### Addleshaw Goddard (`addleshaw_goddard`) — 4 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Paul Lee | `addleshaw_goddard__paul_lee` | Senior partner and chairman of the board (senior partner since 1997) [S] | Manchester [A] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1970 [A: retired after 40 years (TheBusinessDesk), year not found; assumed] | none recorded |  | 144, 145, 146 |
| Mark Jones | `addleshaw_goddard__mark_jones` | Managing partner (continued after the 2003 merger; fourth term 2006) [S] | Leeds [A] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1980 [A: no year found; MP before 2003, assumed] | none recorded |  | 146, 147, 148 |
| Monica Burch | `addleshaw_goddard__monica_burch` | Litigation partner (Theodore Goddard partner 1999) [S] | London | `commercial_litigation` [S] | equity_partner | leading | false | 1988 [S: trainee at Theodore Goddard 1988] | 2010-05 chair_role: Chairman and senior partner May 2010 - 2016 [S]; 2016-05 of_counsel: consultant 2016/17 (month A) [S] | left practice (2017) [D] | 149, 150, 151 |
| Paul Devitt | `addleshaw_goddard__paul_devitt` | Corporate partner; corporate division managing partner (2005) [S] | Manchester [A] | `corporate_ma` [S] | equity_partner | leading | false | 1985 [A: no year found; corporate division head by 2005, assumed] | 2009-05 chair_role: Managing partner 1 May 2009 [S] |  | 152, 148 |

### Berwin Leighton Paisner (`berwin_leighton_paisner`) — 2 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Harold Paisner | `berwin_leighton_paisner__harold_paisner` | Senior partner (since the 2001 merger) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1970 [A: no year found; name partner, assumed] | none recorded |  | 153, 154 |
| Neville Eisenberg | `berwin_leighton_paisner__neville_eisenberg` | Managing partner (1999-2015) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1980 [A: no year found; MP from 1999, assumed] | 2015-05 chair_role: Senior partner 2015-2018 [S] |  | 155, 153, 156 |

### SJ Berwin (`sj_berwin`) — 4 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| David Harrel | `sj_berwin__david_harrel` | Senior partner (longstanding, to Dec 2005) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1970 [A: no year found; longstanding senior partner, assumed] | none recorded |  | 157 |
| Ralph Cohen | `sj_berwin__ralph_cohen` | Managing partner (since 2002); EU and competition lawyer [S] | London | `corporate_ma` [D: competition has no key; nearest] | equity_partner | leading | false | 1980 [A: no year found; MP from 2002, assumed] | none recorded |  | 157, 158 |
| Jonathan Blake | `sj_berwin__jonathan_blake` | Head of private equity / funds (founded the fund formation practice 1982) [S] | London | `private_equity` [S] | equity_partner | elite | false | 1977 [A: founded the practice in 1982; assumed qualified ~5 years earlier] | 2006-01 chair_role: Senior partner 2006-2012 [S]; 2020-01 lateral to `herbert_smith`: to Herbert Smith Freehills (from O'Melveny & Myers) [S] |  | 159, 160, 157 |
| Stephen Kon | `sj_berwin__stephen_kon` | Head of EU competition department (from 1982 to 2008) [S] | London | `corporate_ma` [D: competition has no key; nearest] | equity_partner | leading | false | 1975 [A: joined 1982 to head the competition team; assumed qualified earlier] | 2012-03 chair_role: Senior partner Mar 2012 [S] |  | 161, 162 |

### Pinsent Masons (`pinsent_masons`) — 3 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Julian Tonks | `pinsent_masons__julian_tonks` | Senior partner (since 1994; stood down mid-term 2005) [S] | Birmingham [A] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1970 [A: no year found; senior partner from 1994, assumed] | none recorded |  | 163, 164 |
| David Ryan | `pinsent_masons__david_ryan` | Managing partner (1998-2014) [S] | London [A] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1980 [A: no year found; MP from 1998, assumed] | none recorded |  | 165, 166 |
| Chris Mullen | `pinsent_masons__chris_mullen` | Partner; elected senior partner June/July 2005 [S] | Birmingham [A] | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1980 [A: no year found; assumed] | 2005-07 chair_role: Senior partner Jul 2005 - Sep 2014 [S] |  | 163, 167 |

### Macfarlanes (`macfarlanes`) — 3 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Robert Sutton | `macfarlanes__robert_sutton` | Senior partner (1999-2007/8) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1975 [A: no year found; senior partner from 1999, assumed] | none recorded |  | 168, 169 |
| Paul Phippen | `macfarlanes__paul_phippen` | Managing partner (since May 1999) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1978 [A: no year found; MP from 1999, assumed] | none recorded |  | 170, 169 |
| Charles Martin | `macfarlanes__charles_martin` | M&A and private equity partner [S] | London | `corporate_ma` [S] | equity_partner | elite | false | 1985 [S: qualified as a solicitor 1985 (Rothschild release)] | 2008-05 chair_role: Senior partner 2008-2020 (sources give 2007 or 2008; month A) [S]; 2020-05 left_practice: retired from partnership; Rothschild senior adviser Jan 2021 (month A) [S] | left practice (2020) [S] | 171, 172 |

### Travers Smith (`travers_smith`) — 3 people

| name | notable_key | role Jan 2005 [tag] | office | practice key | level | standing [D] | chair | career_start [tag] | moves 2005–2025 [tag] | left practice [tag] | sources |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Christopher Bell | `travers_smith__christopher_bell` | Senior partner (retiring 2006 after 35 years with the firm) [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | true | 1971 [D: 35 years with the firm at 2006] | 2006-07 left_practice: retired from the post Jul 2006 [S] | left practice (2006) [S] | 173 |
| Chris Carroll | `travers_smith__chris_carroll` | Managing partner (2001-2010); private equity and funds partner (partner from 1986) [S] | London | `private_equity` [S] | equity_partner | leading | false | 1978 [A: partner 1986 less ~8 years] | 2010-07 chair_role: Senior partner 1 Jul 2010 (Hale named successor 2013) [S] |  | 174, 175 |
| Alasdair Douglas | `travers_smith__alasdair_douglas` | Partner; former managing partner (late 1990s); elected senior partner from 1 Jul 2006 [S] | London | `corporate_ma` [A: practice not confirmed] | equity_partner | leading | false | 1975 [A: no year found; MP in the 1990s, assumed] | 2006-07 chair_role: Senior partner Jul 2006 - Jun 2010 [S]; 2010-06 left_practice: retired from the firm [S] | left practice (2010) [S] | 173, 174, 176 |

## Sources

1. https://www.law.com/international-edition/2006/10/03/cc-confirms-popham-for-second-tenure/
2. https://en.wikipedia.org/wiki/Stuart_Popham
3. https://powerbase.info/index.php/Stuart_Popham
4. https://law.com/international-edition/2011/03/29/former-cc-senior-partner-popham-joins-citi-as-emea-banking-vice-chair
5. https://www.law.com/international-edition/2005/01/19/cornell-all-set-to-make-waves/
6. https://www.law.com/international-edition/2005/12/18/cc-managing-partner-to-step-down/
7. https://www.law.com/legal-week/sites/legalweek/2006/10/11/former-head-cornell-leaves-clifford-chance/
8. https://law.com/international-edition/2007/10/01/peter-cornell-buys-in-to-terra-firma-role
9. https://www.law.com/legal-week/sites/legalweek/2005/03/16/cc-in-hunt-for-corporate-head-as-childs-steps-down/
10. https://www.law.com/legal-week/sites/legalweek/2006/03/02/childs-confirmed-as-ccs-new-chief/
11. https://law.com/international-edition/2013/12/19/childs-to-take-financial-watchdog-role-as-first-post-cc-appointment
12. https://www.cliffordchance.com/people_and_places/people/lawyers/gb/malcolm_sweeting.html
13. https://law.com/international-edition/2010/11/04/clifford-chance-votes-in-sweeting-as-firms-new-senior-partner
14. https://www.law.com/legal-week/2019/03/07/former-cc-senior-partner-to-depart-for-role-outside-legal-sector/
15. https://www.cliffordchance.com/news/news/2013/11/matthew_layton_electedascliffordchancemanagingpartner.html
16. https://weforum.org/stories/authors/matthew-layton
17. https://www.cityam.com/?p=497159
18. https://www.ibanet.org/conference/CONF2584/speaker-details/CONF2584_320008
19. https://twentyessex.com/people/audley-sheppard
20. https://www.law.com/legal-week/sites/legalweek/2001/06/20/cann-named-as-linklaters-senior-partner/
21. https://www.lawfuel.com/?p=9379
22. https://www.law.com/international-edition/2003/05/05/linklaters-turns-to-angel-for-2nd-term/
23. https://www.law.com/legal-week/sites/legalweek/2008/05/01/linklaters-legend-tony-angel-takes-a-bow-after-30-year-spell-at-firm/
24. https://law.com/international-edition/2011/10/26/former-linklaters-chief-tony-angel-set-to-join-dla-piper-in-top-role
25. https://law.com/international-edition/2005/04/06/cheynes-gang
26. https://www.law.com/legal-week/sites/legalweek/2006/06/21/cheyne-takes-links-senior-partner-crown/
27. https://law.com/international-edition/2011/09/26/linklaters-cheyne-takes-consultant-role-in-post-senior-partner-move
28. https://www.law.com/international-edition/2011/05/03/elliott-succeeds-cheyne-as-linklaters-senior-partner-as-final-vote-closes/
29. https://www.lawgazette.co.uk/features/interview-robert-elliott/5060603.article
30. https://www.legalbusiness.co.uk/law-firms/blogs/sticking-around-linklaters-elliott-to-stay-on-as-consultant-as-senior-partner-term-ends/
31. https://financeasia.com/article/new-managing-partner-for-linklaters/31328
32. https://en.wikipedia.org/wiki/Simon_Davies_(solicitor)
33. https://www.thelawyer.com/issues/15-october-2007/linklaters-new-chief-vows-to-take-on-the-us-2/
34. https://www.legalbusiness.co.uk/law-firms/blogs/a-big-man-for-a-big-job-frontrunner-jacobs-elected-as-linklaters-new-senior-partner/
35. https://www.lawgazette.co.uk/practice/jacobs-takes-helm-at-linklaters/5055445.article
36. https://www.law.com/international-edition/2003/09/03/beringer-wins-second-term-at-ao-helm/
37. https://www.newlawjournal.co.uk/content/guy-governor
38. https://law.com/international-edition/2008/03/06/ao-senior-partner-and-freshfields-crisp-secure-senior-positions-after-law
39. https://www.law.com/international-edition/2006/09/27/morley-in-talks-to-extend-term-at-ao-helm/
40. https://www.legalbusiness.co.uk/law-firms/blogs/allen-overy-gears-up-to-replace-its-c-suite-as-morley-to-retire-in-2016-2/
41. https://www.cityam.com/?p=953219
42. https://www.lawgazette.co.uk/practice/ao-elects-dejonghe-as-senior-partner/5053725.article
43. https://www.allenovery.com/de-de/global/people/Wim_Dejonghe
44. https://law.com/international-edition/2016/02/25/allen-overy-elects-ballheimer-as-managing-partner
45. https://law.com/international-edition/2019/12/02/ao-managing-partner-ballheimer-set-to-retire-as-gun-fired-on-elections
46. https://www.janushenderson.com/corporate/bio/richard-cranfield/
47. https://www.law.com/international-edition/2010/02/02/ao-selects-new-corporate-chiefs-creates-new-role-for-cranfield/
48. https://www.lawfuel.com/?p=1889
49. https://www.law.com/international-edition/2005/07/10/freshfields-chief-salz-to-retire/
50. https://en.wikipedia.org/wiki/Anthony_Salz
51. https://moneyweek.com/31033/anthony-salz-the-city-lawyer-everyone-wants-to-hire
52. https://law.com/international-edition/2009/04/24/freshfields-names-new-global-head-of-tax
53. https://law.com/international-edition/2001/09/26/jeffcote-to-take-freshfields-helm
54. https://www.law.com/international-edition/2006/01/05/freshfields-finalises-top-brass/
55. https://law.com/international-edition/2010/09/30/lawes-wins-freshfields-senior-partner-vote-burke-takes-recast-managing-partner-brief
56. https://www.thelawyer.com/issues/12-december-2005/de-brauw-commits-to-lockstep/
57. https://www.law.com/international-edition/2006/01/11/freshfields-appoints-terry-as-new-litigation-chief/
58. https://www.legalbusiness.co.uk/law-firms/blogs/freshfields-disputes-veteran-terry-heads-to-the-bar/
59. https://law.com/international-edition/2015/06/22/freshfields-elects-braham-as-senior-partner
60. https://legalbusiness.co.uk/analysis/the-last-champions-meet-the-leaders-intent-on-sealing-freshfields-place-in-the-global-elite/amp
61. https://www.tas-cas.org/uploads/tx_tascas/CV_Jan_Paulsson_Jan2021_01.pdf
62. https://en.wikipedia.org/wiki/Jan_Paulsson
63. https://www.law.com/international-edition/2005/02/16/slaughters-votes-to-extend-clarks-partnership-reign-for-two-years/
64. https://slaughterandmay.com/news/tim-clark-to-continue-as-senior-partner
65. https://www.slaughterandmay.com/news/slaughter-and-may-elects-new-senior-partner/
66. https://law.com/international-edition/2009/09/29/ex-slaughters-and-sjb-senior-partners-lauch-litigation-support-company
67. https://law.com/international-edition/2004/04/07/slaughters-names-saul-as-new-corporate-head
68. https://law.com/international-edition/2015/06/22/slaughters-senior-partner-chris-saul-to-retire-next-year
69. https://www.slaughterandmay.com/news/slaughter-and-may-elects-new-senior-partner-1/
70. https://www.gov.uk/government/people/nigel-boardman
71. https://law.com/international-edition/2022/06/01/nigel-boardman-leaves-slaughter-and-may-after-nearly-50-years
72. https://www.legalbusiness.co.uk/law-firms/blogs/tremendous-experience-city-ma-heavyweight-steve-cooke-elected-as-senior-partner-at-slaughter-and-may/
73. https://www.lawfuel.com/?p=3358
74. https://www.law.com/international-edition/2004/03/17/legal-week-comment-in-search-of-the-next-bond/
75. https://www.postonline.co.uk/node/1263862
76. https://www.law.com/legal-week/sites/legalweek/2004/10/21/herbert-smith-go-for-gold/
77. https://www.law.com/international-edition/2009/10/14/gold-rules-out-bid-for-second-term-as-herbert-smith-senior-partner/
78. https://law.com/international-edition/2010/11/19/herbert-smiths-gold-made-tory-life-peer-ahead-of-consultancy-launch
79. https://www.lawfuel.com/?p=4473
80. https://www.law.com/legal-week/sites/legalweek/2008/04/14/herbert-smith-appoints-willis-as-first-managing-partner-since-mid-1990s/
81. https://law.com/international-edition/2009/12/18/herbert-smith-votes-in-competition-specialist-as-new-senior-partner
82. https://www.hsfkramer.com/alumni/alumni-matters-2025/a-charmed-life-and-career
83. https://law.com/international-edition/2014/11/02/four-partners-in-the-race-as-hsf-senior-partner-jonathan-scott-prepares-to-stand-down-in-january
84. https://law.com/international-edition/2014/11/10/herbert-smith-freehills-votes-in-james-palmer-as-new-senior-partner
85. https://www.legalbusiness.co.uk/law-firms/news-review/herbert-smith-freehills-heavyweight-misses-out-on-management-post-after-elections/
86. https://www.lawfuel.com/?p=1909
87. https://law.com/international-edition/2012/05/17/young-and-restless-john-young-reflects-on-a-33-year-legal-career
88. https://www.law.com/legal-week/sites/legalweek/2007/11/12/unopposed-young-to-lead-lovells-until-2012/
89. https://www.womenslegallandmarks.com/?p=198
90. https://discovery.ucl.ac.uk/id/eprint/10044581/
91. https://www.law.com/legal-week/sites/legalweek/2004/11/21/lovells-confirms-finance-chief-as-new-mp/
92. https://law360.com/amp/articles/175696
93. https://law.com/international-edition/2013/12/11/hogan-lovells-lines-up-immelt-to-fill-sole-ceo-role
94. https://www.law.com/legal-week/sites/legalweek/2006/02/08/lovells-recruits-links-litigation-partner/
95. https://legal500.com/firms/2116-hogan-lovells-international-llp/334-london-england/lawyers/592497-nicholas-cheffings
96. https://law.com/international-edition/2012/02/08/hogan-lovells-confirms-real-estate-litigator-cheffings-as-sole-chairman
97. https://www.bclplaw.com/en-GB/people/lisa-mayhew.html
98. https://www.newlawjournal.co.uk/content/lisa-mayhew-blp
99. https://www.law.com/legal-week/sites/legalweek/2003/11/23/green-re-elected-as-ashursts-chief/
100. https://www.law.com/legal-week/sites/legalweek/2013/03/11/ashurst-appoints-new-asia-head-as-green-takes-australia-integration-role/
101. https://www.law.com/legal-week/sites/legalweek/2015/01/08/former-ashurst-senior-partner-takes-new-role-at-accounting-watchdog/
102. https://www.law.com/legal-week/sites/legalweek/2004/01/08/ashurst-names-new-managing-partner/
103. https://www.ashurst.com/people/simon-bromwich
104. https://law.com/international-edition/2012/02/01/ashurst-managing-partner-to-stand-down-ahead-of-schedule
105. https://law.com/international-edition/2008/09/11/geffen-and-sparrow-fight-for-ashurst-sp-role
106. https://law.com/international-edition/2014/10/01/ex-ashurst-chief-charlie-geffen-to-join-gibson-dunn-with-mark-sperotto
107. https://www.law.com/international-edition/2010/01/14/ashurst-litigation-partner-steps-down-from-top-level-management-board/
108. https://www.legalbusiness.co.uk/law-firms/blogs/challenges-ahead-ashurst-litigation-veteran-ed-sparrow-takes-on-top-clls-job/
109. https://www.thelawyer.com/issues/14-april-2003/giles-wins-race-to-become-chairman-of-norton-rose/
110. https://www.law.com/legal-week/sites/legalweek/2009/02/06/norton-rose-names-banking-chief-as-new-chairman/
111. https://www.law.com/international-edition/2005/11/16/norton-rose-re-elects-martyr-as-ceo/
112. https://www.thelawyer.com/martyr-to-focus-on-international-strategy-as-norton-rose-new-ceo/
113. https://www.law.com/legal-week/sites/legalweek/2006/01/25/parish-to-lead-norton-rose-banking-drive/
114. https://law.com/international-edition/2018/02/09/norton-rose-fulbright-names-first-female-chair-for-emea-as-parish-steps-down
115. https://nortonrosefulbright.com/en/about/our-firm/alumni-community/alumni-stories/jeff-barratt-and-norton-rose-fulbright-a-shared-history
116. https://www.law.com/legal-week/sites/legalweek/2004/11/24/rees-draws-line-under-norton-rose-international-expansion/
117. https://legalbusiness.co.uk/gcs/gc-powerlist-2013/energy/peter-rees-qc-royal-dutch-shell/amp
118. https://law.com/international-edition/2014/03/25/exclusive-former-shell-legal-boss-peter-rees-joins-39-essex-street
119. https://www.personneltoday.com/hr/employment-lawyer-named-as-new-commissioner-for-public-appointments
120. https://www.law.com/international-edition/2005/12/20/gaymer-to-take-top-public-appointments-role/
121. https://en.wikipedia.org/wiki/Janet_Gaymer
122. https://www.law.com/legal-week/sites/legalweek/2004/11/14/dawkins-chosen-as-next-simmons-managing-partner/
123. https://www.law.com/international-edition/2006/04/12/dickinson-beats-slater-to-take-simmons-top-spot-once-again/
124. https://law.com/international-edition/2011/04/28/simmons-votes-in-passmore-ahead-of-dawkins-as-new-senior-partner
125. https://law.com/international-edition/2011/06/27/ex-simmons-chief-dawkins-quits-for-bingham-after-senior-partner-defeat
126. https://www.simmons-simmons.com/people/ck0dzj2wzedwq0b94ukrnz95q/colin-passmore
127. https://law.com/international-edition/2010/12/10/simmons-votes-in-city-finance-chief-hoyland-as-new-managing-partner
128. https://www.newlawjournal.co.uk/content/simmons-simmons-jeremy-hoyland
129. https://www.law.com/international-edition/2002/03/26/camerons-names-price-as-senior-partner/
130. https://law.com/international-edition/2011/03/28/camerons-votes-in-former-mp-tyler-as-firms-new-senior-partner
131. https://cms.law/en/int/news-information/duncan-weston-takes-the-reins-at-cms-cameron-mckenna
132. https://www.law.com/international-edition/2008/05/07/weston-takes-reins-from-tyler-as-camerons-head/
133. https://ceelegalmatters.com/cms/15171-building-blocks-of-cee-duncan-weston-brings-cee-to-cms
134. https://www.thelawyer.com/issues/26-november-2007/womens-problems/
135. https://law.com/international-edition/2013/12/02/camerons-elects-penelope-warne-as-new-senior-partner
136. https://first100years.org.uk/?p=5562
137. https://cms.law/en/GBR/News-Information/Penelope-Warne-today-takes-up-the-role-of-Senior-Partner-at-law-firm-CMS
138. https://www.thelawyer.com/issues/9-february-2004/ryanair-flies-in-weil-to-aid-al-in-brussels-case/
139. https://www.law.com/legal-week/sites/legalweek/2007/03/26/eversheds-chair-jenkins-to-serve-second-term/
140. https://law.com/international-edition/2010/11/09/ex-eversheds-chair-set-to-retire-as-firm-appoints-new-client-chief
141. https://law.com/international-edition/2005/10/19/eversheds-moves-to-head-off-election-battle-as-gray-set-for-second-term
142. https://law.com/international-edition/2002/10/02/north-west-head-gray-triumphs-in-eversheds-election
143. https://www.law.com/legal-week/2013/05/02/eversheds-votes-in-ireland-chief-as-new-international-chairman/
144. https://www.law.com/international-edition/2002/05/01/lee-retains-addleshaws-top-role/
145. https://law.com/international-edition/2009/12/08/addleshaws-senior-partner-set-to-step-down-after-12-years-at-the-top
146. https://www.lawgazette.co.uk/news/addleshaw-goddard-born/39353.article
147. https://www.law.com/legal-week/sites/legalweek/2006/04/05/addleshaws-jones-re-elected-as-head-as-llp-switch-is-confirmed/
148. https://www.law.com/legal-week/sites/legalweek/2009/03/04/addleshaws-selects-new-mp-in-management-re-jig/
149. https://law.com/international-edition/2010/03/31/addleshaws-litigation-partner-burch-steps-into-new-chairman-role
150. https://first100years.org.uk/person/monica-burch-2/
151. https://www.shoosmiths.com/people/directory/monica-burch
152. https://www.unquote.com/uk/analysis/80219/addleshaw-goddard
153. https://www.legalbusiness.co.uk/law-firms/blogs/succeeding-paisner-eisenberg-to-become-senior-partner-at-blp-when-managing-partner-term-ends/
154. https://law.com/international-edition/2015/04/24/i-will-do-it-in-my-way-blps-neville-eisenberg-on-his-new-role
155. https://www.legalbusiness.co.uk/wp-content/uploads/2017/04/lbas05_management.pdf
156. https://www.solicitorsjournal.com/sjarticle/10-questions--neville-eisenberg-life-after-five-terms-as-managing-partner
157. https://www.law.com/international-edition/2005/12/12/sj-berwin-agrees-joint-ticket-leadership-as-blake-takes-senior-partner-role/
158. https://law.com/international-edition/2010/08/10/sjb-managing-partner-cohen-to-step-down-as-proskauer-talks-continue
159. https://www.privateequityinternational.com/sj-berwin-appoints-new-senior-partner/
160. https://www.hsfkramer.com/news/2020-01/father-of-private-equity-funds-jonathan-blake-joins-herbert-smith-freehills-as-head-of
161. https://globalcompetitionreview.com/article/kon-takes-sj-berwin-leadership-role
162. https://law.com/international-edition/2012/03/15/sj-berwin-hands-senior-partner-role-to-kon-after-contested-vote
163. https://www.law.com/legal-week/sites/legalweek/2005/06/29/pinsents-elects-mullen-as-new-senior-partner/
164. https://www.law.com/legal-week/sites/legalweek/2005/07/06/pinsents-turns-to-mullen-as-tonks-stands-down/
165. https://law.com/international-edition/2014/06/10/chris-mullen-faces-challenge-in-pinsent-masons-senior-partner-vote-with-managing-partner-election-to-follow
166. https://www.law.com/international-edition/2008/10/09/strategy-updated-as-pinsents-mp-ryan-appointed-for-another-term/
167. https://www.lawgazette.co.uk/practice/foley-ousts-nine-year-incumbent-at-pinsent-masons/5041961.article
168. https://www.thelawyer.com/issues/4-april-2005/macfarlanes-hikes-partnership-with-a-record-six-promotions-2/
169. https://en.wikipedia.com/wiki/Macfarlanes
170. https://it.marketscreener.com/insider/PAUL-PHIPPEN-A0BXXF
171. https://law.com/international-edition/2018/01/08/macfarlanes-names-next-senior-partner-as-charles-martin-confirms-plans-to-step-down
172. https://www.rothschildandco.com/en-fr/newsroom/press-releases/2021/01/charles-martin-joins-as-senior-adviser/
173. https://www.unquote.com/uk/news/75169/travers-smith-appoints-senior-partner
174. https://www.law.com/international-edition/2010/03/29/travers-names-carroll-as-new-senior-partner-as-firm-eyes-overseas-growth/
175. https://www.law.com/international-edition/2009/03/26/travers-mp-carroll-set-to-stand-down-after-third-term-at-the-helm/
176. https://law.com/international-edition/2011/06/15/ex-travers-senior-partner-named-clls-chair

## YAML (notables.yaml flow format)

```yaml
notables:
  # clifford_chance
  - { key: clifford_chance__stuart_popham, firm: clifford_chance, first_name: "Stuart", last_name: "Popham", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1978, left_practice: 2011, moves: [{ ym: [2011, 4], kind: left_practice }], role_2005: "Senior partner (elected 2002, in office from 2003; re-elected 2006 to Dec 2010)", src: "role S https://www.law.com/international-edition/2006/10/03/cc-confirms-popham-for-second-tenure/; start S Powerbase; left S law.com 2011" }
  - { key: clifford_chance__peter_cornell, firm: clifford_chance, first_name: "Peter", last_name: "Cornell", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1975, left_practice: 2006, moves: [{ ym: [2006, 10], kind: left_practice }], role_2005: "Global managing partner (to Apr 2006)", src: "role S https://www.law.com/international-edition/2005/01/19/cornell-all-set-to-make-waves/; start A MarketScreener tenure; left S Legal Week 2006" }
  - { key: clifford_chance__david_childs, firm: clifford_chance, first_name: "David", last_name: "Childs", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1978, left_practice: 2014, moves: [{ ym: [2006, 5], kind: chair_role }, { ym: [2014, 5], kind: left_practice }], role_2005: "Chief operating officer (since 2003); global head of corporate until Mar 2005", src: "role S https://www.law.com/legal-week/sites/legalweek/2005/03/16/cc-in-hunt-for-corporate-head-as-childs-steps-down/; start A no source; left S law.com 2013" }
  - { key: clifford_chance__malcolm_sweeting, firm: clifford_chance, first_name: "Malcolm", last_name: "Sweeting", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1982, left_practice: 2019, moves: [{ ym: [2011, 1], kind: chair_role }, { ym: [2019, 3], kind: left_practice }], role_2005: "Finance partner (partner since 1990); led London banking group", src: "role S https://www.cliffordchance.com/people_and_places/people/lawyers/gb/malcolm_sweeting.html; start A partner 1990 less 8; left S Legal Week 2019" }
  - { key: clifford_chance__matthew_layton, firm: clifford_chance, first_name: "Matthew", last_name: "Layton", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1983, moves: [{ ym: [2014, 5], kind: chair_role }], role_2005: "Corporate partner (joined 1983, partner 1991)", src: "role S https://weforum.org/stories/authors/matthew-layton; start S WEF bio" }
  - { key: clifford_chance__audley_sheppard, firm: clifford_chance, first_name: "Audley", last_name: "Sheppard", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1986, moves: [{ ym: [2023, 5], kind: of_counsel }, { ym: [2024, 6], kind: lateral }], role_2005: "International arbitration partner (partner 1995-2023)", src: "role S https://www.ibanet.org/conference/CONF2584/speaker-details/CONF2584_320008; start D Twenty Essex 38 years" }
  # linklaters
  - { key: linklaters__anthony_cann, firm: linklaters, first_name: "Anthony", last_name: "Cann", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1969, left_practice: 2006, moves: [{ ym: [2006, 9], kind: left_practice }], role_2005: "Senior partner (Sep 2001 - Sep 2006)", src: "role S https://www.lawfuel.com/?p=9379; start D 37 years at 2006; left S Linklaters release" }
  - { key: linklaters__tony_angel, firm: linklaters, first_name: "Tony", last_name: "Angel", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [{ ym: [2008, 4], kind: in_house }, { ym: [2011, 11], kind: lateral }], role_2005: "Managing partner (elected 1998, second term 2003; head of tax from 1994)", src: "role S https://www.law.com/international-edition/2003/05/05/linklaters-turns-to-angel-for-2nd-term/; start D 30 years to 2008" }
  - { key: linklaters__david_cheyne, firm: linklaters, first_name: "David", last_name: "Cheyne", practice: corporate_ma, level: equity_partner, standing: elite, chair: false, career_start: 1972, moves: [{ ym: [2006, 10], kind: chair_role }, { ym: [2011, 10], kind: of_counsel }], role_2005: "Global head of corporate (2000-2005)", src: "role S https://www.lawfuel.com/?p=9379; start S Linklaters release (joined 1972)" }
  - { key: linklaters__robert_elliott, firm: linklaters, first_name: "Robert", last_name: "Elliott", practice: restructuring, level: equity_partner, standing: elite, chair: false, career_start: 1976, moves: [{ ym: [2011, 10], kind: chair_role }, { ym: [2016, 10], kind: of_counsel }], role_2005: "Global head of restructuring and insolvency (from 1996); banking partner", src: "role S https://www.lawgazette.co.uk/features/interview-robert-elliott/5060603.article; start S Law Gazette interview" }
  - { key: linklaters__simon_davies, firm: linklaters, first_name: "Simon", last_name: "Davies", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1985, left_practice: 2016, moves: [{ ym: [2008, 1], kind: chair_role }, { ym: [2016, 1], kind: in_house }], role_2005: "Managing partner, Asia (2003-2007)", src: "role S https://financeasia.com/article/new-managing-partner-for-linklaters/31328; start A no source; left S Wikipedia" }
  - { key: linklaters__charles_jacobs, firm: linklaters, first_name: "Charles", last_name: "Jacobs", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1992, moves: [{ ym: [2016, 10], kind: chair_role }], role_2005: "Corporate partner (joined 1990, partner 1999)", src: "role S https://www.legalbusiness.co.uk/law-firms/blogs/a-big-man-for-a-big-job-frontrunner-jacobs-elected-as-linklaters-new-senior-partner/; start S Law Gazette" }
  # allen_overy
  - { key: allen_overy__guy_beringer, firm: allen_overy, first_name: "Guy", last_name: "Beringer", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1978, left_practice: 2008, moves: [{ ym: [2008, 4], kind: left_practice }], role_2005: "Senior partner (2000-2008; second term confirmed 2003)", src: "role S https://www.law.com/international-edition/2003/09/03/beringer-wins-second-term-at-ao-helm/; start S NLJ; left S law.com 2008" }
  - { key: allen_overy__david_morley, firm: allen_overy, first_name: "David", last_name: "Morley", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1982, left_practice: 2016, moves: [{ ym: [2008, 5], kind: chair_role }, { ym: [2016, 4], kind: left_practice }], role_2005: "Managing partner (from 2003); former global head of banking (1998)", src: "role S https://www.law.com/international-edition/2006/09/27/morley-in-talks-to-extend-term-at-ao-helm/; start S City AM profile; left S Legal Business" }
  - { key: allen_overy__wim_dejonghe, firm: allen_overy, first_name: "Wim", last_name: "Dejonghe", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1985, moves: [{ ym: [2008, 5], kind: chair_role }, { ym: [2016, 5], kind: chair_role }], role_2005: "Managing partner, Belgian offices; co-head global corporate (A&O partner from 2001)", src: "role S https://www.allenovery.com/de-de/global/people/Wim_Dejonghe; start A partner 1993 less 8" }
  - { key: allen_overy__andrew_ballheimer, firm: allen_overy, first_name: "Andrew", last_name: "Ballheimer", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1987, left_practice: 2020, moves: [{ ym: [2016, 5], kind: chair_role }, { ym: [2020, 4], kind: left_practice }], role_2005: "Corporate partner (associate 1987, partner 1994)", src: "role S https://law.com/international-edition/2016/02/25/allen-overy-elects-ballheimer-as-managing-partner; start S law.com 2016; left S law.com 2019" }
  - { key: allen_overy__richard_cranfield, firm: allen_overy, first_name: "Richard", last_name: "Cranfield", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1978, left_practice: 2021, moves: [{ ym: [2021, 10], kind: left_practice }], role_2005: "Global head of corporate (from 2000)", src: "role S https://www.janushenderson.com/corporate/bio/richard-cranfield/; start S Janus Henderson bio; left S same" }
  # freshfields
  - { key: freshfields__anthony_salz, firm: freshfields, first_name: "Anthony", last_name: "Salz", practice: corporate_ma, level: equity_partner, standing: elite, chair: true, career_start: 1975, left_practice: 2006, moves: [{ ym: [2006, 5], kind: left_practice }], role_2005: "Joint senior partner (senior partner since 1996; joint with Mettenheimer from 1 May 2004)", src: "role S https://www.lawfuel.com/?p=1889; start S MoneyWeek; left S law.com 2005 / Wikipedia" }
  - { key: freshfields__konstantin_mettenheimer, firm: freshfields, first_name: "Konstantin", last_name: "Mettenheimer", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1986, moves: [], role_2005: "Joint senior partner (from 1 May 2004); tax and corporate", src: "role S https://www.lawfuel.com/?p=1889; start S lawfuel (with firm since 1986)" }
  - { key: freshfields__peter_jeffcote, firm: freshfields, first_name: "Peter", last_name: "Jeffcote", practice: employment, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [], role_2005: "Managing partner (from Oct 2001; reappointed late 2005); former employment head", src: "role S https://www.law.com/international-edition/2006/01/05/freshfields-finalises-top-brass/; start A no source" }
  - { key: freshfields__guy_morton, firm: freshfields, first_name: "Guy", last_name: "Morton", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [{ ym: [2006, 5], kind: chair_role }], role_2005: "Head of financial services regulatory practice (partner since 1986)", src: "role S https://www.thelawyer.com/issues/12-december-2005/de-brauw-commits-to-lockstep/; start A partner 1986 less 8" }
  - { key: freshfields__ian_terry, firm: freshfields, first_name: "Ian", last_name: "Terry", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [{ ym: [2016, 3], kind: lateral }], role_2005: "Dispute resolution partner; former managing partner (1996-2001)", src: "role S https://www.law.com/international-edition/2006/01/11/freshfields-appoints-terry-as-new-litigation-chief/; start D Legal Business 38 years" }
  - { key: freshfields__edward_braham, firm: freshfields, first_name: "Edward", last_name: "Braham", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1985, moves: [{ ym: [2016, 1], kind: chair_role }], role_2005: "Corporate / M&A partner (trainee 1985, partner c.1995)", src: "role S https://legalbusiness.co.uk/analysis/the-last-champions-meet-the-leaders-intent-on-sealing-freshfields-place-in-the-global-elite/amp; start S Legal Business" }
  - { key: freshfields__jan_paulsson, firm: freshfields, first_name: "Jan", last_name: "Paulsson", practice: commercial_litigation, level: equity_partner, standing: elite, chair: false, career_start: 1975, moves: [{ ym: [2014, 1], kind: lateral }], role_2005: "Head of international arbitration and public international law (1993-2012)", src: "role S https://www.tas-cas.org/uploads/tx_tascas/CV_Jan_Paulsson_Jan2021_01.pdf; start A Wikipedia" }
  # slaughter_may
  - { key: slaughter_may__tim_clark, firm: slaughter_may, first_name: "Tim", last_name: "Clark", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1974, left_practice: 2008, moves: [{ ym: [2008, 4], kind: left_practice }], role_2005: "Senior partner (May 2001 - Apr 2008; extended Feb 2005)", src: "role S https://www.law.com/international-edition/2005/02/16/slaughters-votes-to-extend-clarks-partnership-reign-for-two-years/; start S law.com 2009; left S Slaughter and May" }
  - { key: slaughter_may__chris_saul, firm: slaughter_may, first_name: "Chris", last_name: "Saul", practice: corporate_ma, level: equity_partner, standing: elite, chair: false, career_start: 1977, left_practice: 2016, moves: [{ ym: [2008, 5], kind: chair_role }, { ym: [2016, 4], kind: left_practice }], role_2005: "Head of corporate (from Apr 2004)", src: "role S https://law.com/international-edition/2004/04/07/slaughters-names-saul-as-new-corporate-head; start D 39 years to 2016; left S Slaughter and May" }
  - { key: slaughter_may__nigel_boardman, firm: slaughter_may, first_name: "Nigel", last_name: "Boardman", practice: corporate_ma, level: equity_partner, standing: elite, chair: false, career_start: 1973, left_practice: 2022, moves: [{ ym: [2019, 4], kind: of_counsel }, { ym: [2022, 5], kind: left_practice }], role_2005: "M&A partner (partner 1982-2019)", src: "role S https://www.gov.uk/government/people/nigel-boardman; start S press (joined 1973); left S law.com 2022" }
  - { key: slaughter_may__steve_cooke, firm: slaughter_may, first_name: "Steve", last_name: "Cooke", practice: corporate_ma, level: equity_partner, standing: elite, chair: false, career_start: 1982, moves: [{ ym: [2016, 5], kind: chair_role }], role_2005: "Head of M&A (since 2001)", src: "role S https://www.slaughterandmay.com/news/slaughter-and-may-elects-new-senior-partner-1/; start S Legal Business" }
  # herbert_smith
  - { key: herbert_smith__richard_bond, firm: herbert_smith, first_name: "Richard", last_name: "Bond", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1972, left_practice: 2005, moves: [{ ym: [2005, 4], kind: left_practice }], role_2005: "Senior partner (five-year term to 31 Mar 2005); former head of corporate", src: "role S https://www.lawfuel.com/?p=3358; start A no source; left S Post (retirement)" }
  - { key: herbert_smith__david_gold, firm: herbert_smith, first_name: "David", last_name: "Gold", practice: commercial_litigation, level: equity_partner, standing: elite, chair: false, career_start: 1975, left_practice: 2011, moves: [{ ym: [2005, 4], kind: chair_role }, { ym: [2011, 1], kind: left_practice }], role_2005: "Head of litigation; senior partner-elect (elected Oct 2004, term from 1 Apr 2005)", src: "role S https://www.lawfuel.com/?p=3358; start A no source; left D law.com 2010" }
  - { key: herbert_smith__david_willis, firm: herbert_smith, first_name: "David", last_name: "Willis", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [{ ym: [2008, 4], kind: chair_role }], role_2005: "Corporate partner", src: "role S https://www.lawfuel.com/?p=4473; start A no source" }
  - { key: herbert_smith__jonathan_scott, firm: herbert_smith, first_name: "Jonathan", last_name: "Scott", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, left_practice: 2015, moves: [{ ym: [2010, 5], kind: chair_role }, { ym: [2015, 1], kind: left_practice }], role_2005: "Head of EU and competition (1996-2007); partner since 1988", src: "role S https://www.hsfkramer.com/alumni/alumni-matters-2025/a-charmed-life-and-career; start D HSF alumni 35 years; left S same" }
  - { key: herbert_smith__james_palmer, firm: herbert_smith, first_name: "James", last_name: "Palmer", practice: capital_markets, level: equity_partner, standing: leading, chair: false, career_start: 1986, moves: [{ ym: [2015, 5], kind: chair_role }], role_2005: "Equity capital markets co-head (2005-2010); partner since 1994", src: "role S https://www.legalbusiness.co.uk/law-firms/news-review/herbert-smith-freehills-heavyweight-misses-out-on-management-post-after-elections/; start S Legal Business" }
  # lovells
  - { key: lovells__john_young, firm: lovells, first_name: "John", last_name: "Young", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1979, left_practice: 2012, moves: [{ ym: [2010, 5], kind: chair_role }, { ym: [2012, 4], kind: left_practice }], role_2005: "Senior partner (from 1 May 2004)", src: "role S https://www.lawfuel.com/?p=1909; start D law.com 33 years; left S law.com 2012" }
  - { key: lovells__lesley_macdonagh, firm: lovells, first_name: "Lesley", last_name: "MacDonagh", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1978, left_practice: 2007, moves: [{ ym: [2006, 5], kind: of_counsel }], role_2005: "Managing partner (1 May 1995 - Apr 2005)", src: "role S https://www.womenslegallandmarks.com/?p=198; start S Women's Legal Landmarks; left S same" }
  - { key: lovells__david_harris, firm: lovells, first_name: "David", last_name: "Harris", practice: capital_markets, level: equity_partner, standing: leading, chair: false, career_start: 1982, moves: [{ ym: [2005, 5], kind: chair_role }, { ym: [2010, 5], kind: chair_role }], role_2005: "Head of finance stream; managing partner-elect (elected Nov 2004, from 1 May 2005)", src: "role S https://www.law.com/legal-week/sites/legalweek/2004/11/21/lovells-confirms-finance-chief-as-new-mp/; start A no source" }
  - { key: lovells__patrick_sherrington, firm: lovells, first_name: "Patrick", last_name: "Sherrington", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [], role_2005: "Head of dispute resolution", src: "role S https://www.law.com/legal-week/sites/legalweek/2006/02/08/lovells-recruits-links-litigation-partner/; start A no source; 2006 source for head role" }
  - { key: lovells__nicholas_cheffings, firm: lovells, first_name: "Nicholas", last_name: "Cheffings", practice: real_estate, level: equity_partner, standing: leading, chair: false, career_start: 1983, moves: [{ ym: [2012, 5], kind: chair_role }], role_2005: "Real estate disputes partner (Lovells partner from 1999)", src: "role S https://legal500.com/firms/2116-hogan-lovells-international-llp/334-london-england/lawyers/592497-nicholas-cheffings; start S Legal 500" }
  - { key: lovells__lisa_mayhew, firm: lovells, first_name: "Lisa", last_name: "Mayhew", practice: employment, level: equity_partner, standing: leading, chair: false, career_start: 1990, moves: [{ ym: [2010, 1], kind: lateral, to: berwin_leighton_paisner }, { ym: [2015, 5], kind: chair_role }], role_2005: "Employment partner (joined Lovells as partner 2002)", src: "role S https://www.bclplaw.com/en-GB/people/lisa-mayhew.html; start A no source" }
  # ashurst
  - { key: ashurst__geoffrey_green, firm: ashurst, first_name: "Geoffrey", last_name: "Green", practice: private_equity, level: equity_partner, standing: leading, chair: true, career_start: 1979, left_practice: 2013, moves: [{ ym: [2013, 4], kind: left_practice }, { ym: [2015, 4], kind: government }], role_2005: "Senior partner (1998-2008; re-elected Nov 2003)", src: "role S https://www.law.com/legal-week/sites/legalweek/2003/11/23/green-re-elected-as-ashursts-chief/; start D 34 years to 2013; left S Legal Week 2013" }
  - { key: ashurst__simon_bromwich, firm: ashurst, first_name: "Simon", last_name: "Bromwich", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1991, moves: [], role_2005: "Managing partner (2004-2012)", src: "role S https://www.ashurst.com/people/simon-bromwich; start A partner 1999 less 8" }
  - { key: ashurst__charlie_geffen, firm: ashurst, first_name: "Charlie", last_name: "Geffen", practice: private_equity, level: equity_partner, standing: elite, chair: false, career_start: 1980, moves: [{ ym: [2009, 1], kind: chair_role }, { ym: [2014, 10], kind: lateral, to: gibson_dunn }], role_2005: "Private equity head (corporate partner)", src: "role S https://law.com/international-edition/2008/09/11/geffen-and-sparrow-fight-for-ashurst-sp-role; role D law.com 2008 (PE head); start A no source" }
  - { key: ashurst__edward_sparrow, firm: ashurst, first_name: "Edward", last_name: "Sparrow", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1975, moves: [], role_2005: "Litigation partner (since 1981); management board member (from 2004)", src: "role S https://www.law.com/international-edition/2010/01/14/ashurst-litigation-partner-steps-down-from-top-level-management-board/; start A partner 1981 less 6" }
  # norton_rose
  - { key: norton_rose__paul_giles, firm: norton_rose, first_name: "Paul", last_name: "Giles", practice: banking_finance, level: equity_partner, standing: leading, chair: true, career_start: 1978, moves: [], role_2005: "Chairman (Apr 2003 - Apr 2009); asset finance partner", src: "role S https://www.thelawyer.com/issues/14-april-2003/giles-wins-race-to-become-chairman-of-norton-rose/; start A no source" }
  - { key: norton_rose__peter_martyr, firm: norton_rose, first_name: "Peter", last_name: "Martyr", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1979, moves: [], role_2005: "Chief executive (from 2002 election; re-elected Nov 2005)", src: "role S https://www.law.com/international-edition/2005/11/16/norton-rose-re-elects-martyr-as-ceo/; start D trainee 1977 + 2" }
  - { key: norton_rose__stephen_parish, firm: norton_rose, first_name: "Stephen", last_name: "Parish", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1974, moves: [{ ym: [2009, 5], kind: chair_role }], role_2005: "London head of banking (global banking head from Jan 2006)", src: "role S https://www.law.com/legal-week/sites/legalweek/2006/01/25/parish-to-lead-norton-rose-banking-drive/; start S law.com 2009" }
  - { key: norton_rose__jeffery_barratt, firm: norton_rose, first_name: "Jeffery", last_name: "Barratt", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1976, left_practice: 2014, moves: [{ ym: [2014, 12], kind: left_practice }], role_2005: "Global head of banking (to Jan 2006)", src: "role S https://www.law.com/legal-week/sites/legalweek/2006/01/25/parish-to-lead-norton-rose-banking-drive/; start S NRF alumni story; left D same" }
  - { key: norton_rose__peter_rees, firm: norton_rose, first_name: "Peter", last_name: "Rees", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1979, moves: [{ ym: [2006, 1], kind: lateral, to: debevoise }, { ym: [2010, 11], kind: in_house }, { ym: [2014, 3], kind: lateral }], role_2005: "Litigation partner (partner 1987-2006); head of international strategy (board, 2004)", src: "role S https://legalbusiness.co.uk/gcs/gc-powerlist-2013/energy/peter-rees-qc-royal-dutch-shell/amp; start A partner 1987 less 8" }
  # simmons
  - { key: simmons__janet_gaymer, firm: simmons, first_name: "Janet", last_name: "Gaymer", practice: employment, level: equity_partner, standing: elite, chair: true, career_start: 1975, left_practice: 2006, moves: [{ ym: [2006, 1], kind: government }], role_2005: "Senior partner (since 2001)", src: "role S https://www.personneltoday.com/hr/employment-lawyer-named-as-new-commissioner-for-public-appointments; start D Personnel Today 30 years; left S Wikipedia (government)" }
  - { key: simmons__david_dickinson, firm: simmons, first_name: "David", last_name: "Dickinson", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1978, left_practice: 2011, moves: [{ ym: [2006, 4], kind: chair_role }, { ym: [2011, 8], kind: left_practice }], role_2005: "Managing partner (1999 - May 2005); founding partner of the finance practice", src: "role S https://www.law.com/international-edition/2006/04/12/dickinson-beats-slater-to-take-simmons-top-spot-once-again/; start A no source; left S law.com 2011" }
  - { key: simmons__mark_dawkins, firm: simmons, first_name: "Mark", last_name: "Dawkins", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1982, moves: [{ ym: [2005, 5], kind: chair_role }, { ym: [2011, 6], kind: lateral }], role_2005: "Head of financial markets; managing partner-elect (chosen Nov 2004, from 1 May 2005)", src: "role S https://www.law.com/legal-week/sites/legalweek/2004/11/14/dawkins-chosen-as-next-simmons-managing-partner/; start A no source" }
  - { key: simmons__colin_passmore, firm: simmons, first_name: "Colin", last_name: "Passmore", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1986, moves: [{ ym: [2011, 8], kind: chair_role }], role_2005: "Litigation partner (joined 1986, partner 1990)", src: "role S https://www.simmons-simmons.com/people/ck0dzj2wzedwq0b94ukrnz95q/colin-passmore; start S Simmons bio" }
  - { key: simmons__jeremy_hoyland, firm: simmons, first_name: "Jeremy", last_name: "Hoyland", practice: banking_finance, level: equity_partner, standing: leading, chair: false, career_start: 1989, moves: [{ ym: [2011, 5], kind: chair_role }], role_2005: "Finance partner (trainee 1989, partner 1997); head of financial institutions sector (2005)", src: "role S https://www.newlawjournal.co.uk/content/simmons-simmons-jeremy-hoyland; start S NLJ" }
  # cms_cameron_mckenna
  - { key: cms_cameron_mckenna__richard_price, firm: cms_cameron_mckenna, first_name: "Richard", last_name: "Price", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1976, moves: [], role_2005: "Senior partner (from May 2002 to Apr 2011); corporate partner", src: "role S https://www.law.com/international-edition/2002/03/26/camerons-names-price-as-senior-partner/; start A no source" }
  - { key: cms_cameron_mckenna__dick_tyler, firm: cms_cameron_mckenna, first_name: "Dick", last_name: "Tyler", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [{ ym: [2008, 9], kind: chair_role }, { ym: [2011, 5], kind: chair_role }], role_2005: "Managing partner (2000 - Apr 2008)", src: "role S https://cms.law/en/int/news-information/duncan-weston-takes-the-reins-at-cms-cameron-mckenna; start A no source" }
  - { key: cms_cameron_mckenna__duncan_weston, firm: cms_cameron_mckenna, first_name: "Duncan", last_name: "Weston", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1985, moves: [{ ym: [2008, 5], kind: chair_role }], role_2005: "Managing partner, Central and Eastern Europe (from 2001)", src: "role S https://ceelegalmatters.com/cms/15171-building-blocks-of-cee-duncan-weston-brings-cee-to-cms; start A no source" }
  - { key: cms_cameron_mckenna__penelope_warne, firm: cms_cameron_mckenna, first_name: "Penelope", last_name: "Warne", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1986, moves: [{ ym: [2014, 5], kind: chair_role }], role_2005: "Energy partner (joined 1993 to set up the Aberdeen office)", src: "role S https://first100years.org.uk/?p=5562; start A five years at Slaughter and May before 1993" }
  # eversheds
  - { key: eversheds__alan_jenkins, firm: eversheds, first_name: "Alan", last_name: "Jenkins", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1978, left_practice: 2011, moves: [{ ym: [2011, 4], kind: left_practice }], role_2005: "Chairman (from 2004) and head of international", src: "role S https://www.thelawyer.com/issues/9-february-2004/ryanair-flies-in-weil-to-aid-al-in-brussels-case/; start A no source; left S law.com 2010" }
  - { key: eversheds__david_gray, firm: eversheds, first_name: "David", last_name: "Gray", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [{ ym: [2009, 5], kind: chair_role }], role_2005: "Managing partner (from May 2003; second term from 2006)", src: "role S https://law.com/international-edition/2005/10/19/eversheds-moves-to-head-off-election-battle-as-gray-set-for-second-term; start A no source" }
  # addleshaw_goddard
  - { key: addleshaw_goddard__paul_lee, firm: addleshaw_goddard, first_name: "Paul", last_name: "Lee", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1970, moves: [], role_2005: "Senior partner and chairman of the board (senior partner since 1997)", src: "role S https://www.law.com/international-edition/2002/05/01/lee-retains-addleshaws-top-role/; start A no source" }
  - { key: addleshaw_goddard__mark_jones, firm: addleshaw_goddard, first_name: "Mark", last_name: "Jones", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [], role_2005: "Managing partner (continued after the 2003 merger; fourth term 2006)", src: "role S https://www.lawgazette.co.uk/news/addleshaw-goddard-born/39353.article; start A no source" }
  - { key: addleshaw_goddard__monica_burch, firm: addleshaw_goddard, first_name: "Monica", last_name: "Burch", practice: commercial_litigation, level: equity_partner, standing: leading, chair: false, career_start: 1988, left_practice: 2017, moves: [{ ym: [2010, 5], kind: chair_role }, { ym: [2016, 5], kind: of_counsel }], role_2005: "Litigation partner (Theodore Goddard partner 1999)", src: "role S https://first100years.org.uk/person/monica-burch-2/; start S First 100 Years; left D Shoosmiths profile" }
  - { key: addleshaw_goddard__paul_devitt, firm: addleshaw_goddard, first_name: "Paul", last_name: "Devitt", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1985, moves: [{ ym: [2009, 5], kind: chair_role }], role_2005: "Corporate partner; corporate division managing partner (2005)", src: "role S https://www.unquote.com/uk/analysis/80219/addleshaw-goddard; start A no source" }
  # berwin_leighton_paisner
  - { key: berwin_leighton_paisner__harold_paisner, firm: berwin_leighton_paisner, first_name: "Harold", last_name: "Paisner", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1970, moves: [], role_2005: "Senior partner (since the 2001 merger)", src: "role S https://www.legalbusiness.co.uk/law-firms/blogs/succeeding-paisner-eisenberg-to-become-senior-partner-at-blp-when-managing-partner-term-ends/; start A no source" }
  - { key: berwin_leighton_paisner__neville_eisenberg, firm: berwin_leighton_paisner, first_name: "Neville", last_name: "Eisenberg", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [{ ym: [2015, 5], kind: chair_role }], role_2005: "Managing partner (1999-2015)", src: "role S https://www.legalbusiness.co.uk/wp-content/uploads/2017/04/lbas05_management.pdf; start A no source" }
  # sj_berwin
  - { key: sj_berwin__david_harrel, firm: sj_berwin, first_name: "David", last_name: "Harrel", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1970, moves: [], role_2005: "Senior partner (longstanding, to Dec 2005)", src: "role S https://www.law.com/international-edition/2005/12/12/sj-berwin-agrees-joint-ticket-leadership-as-blake-takes-senior-partner-role/; start A no source" }
  - { key: sj_berwin__ralph_cohen, firm: sj_berwin, first_name: "Ralph", last_name: "Cohen", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [], role_2005: "Managing partner (since 2002); EU and competition lawyer", src: "role S https://www.law.com/international-edition/2005/12/12/sj-berwin-agrees-joint-ticket-leadership-as-blake-takes-senior-partner-role/; start A no source" }
  - { key: sj_berwin__jonathan_blake, firm: sj_berwin, first_name: "Jonathan", last_name: "Blake", practice: private_equity, level: equity_partner, standing: elite, chair: false, career_start: 1977, moves: [{ ym: [2006, 1], kind: chair_role }, { ym: [2020, 1], kind: lateral, to: herbert_smith }], role_2005: "Head of private equity / funds (founded the fund formation practice 1982)", src: "role S https://www.hsfkramer.com/news/2020-01/father-of-private-equity-funds-jonathan-blake-joins-herbert-smith-freehills-as-head-of; start A practice founded 1982" }
  - { key: sj_berwin__stephen_kon, firm: sj_berwin, first_name: "Stephen", last_name: "Kon", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1975, moves: [{ ym: [2012, 3], kind: chair_role }], role_2005: "Head of EU competition department (from 1982 to 2008)", src: "role S https://globalcompetitionreview.com/article/kon-takes-sj-berwin-leadership-role; start A joined 1982 as department head" }
  # pinsent_masons
  - { key: pinsent_masons__julian_tonks, firm: pinsent_masons, first_name: "Julian", last_name: "Tonks", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1970, moves: [], role_2005: "Senior partner (since 1994; stood down mid-term 2005)", src: "role S https://www.law.com/legal-week/sites/legalweek/2005/06/29/pinsents-elects-mullen-as-new-senior-partner/; start A no source" }
  - { key: pinsent_masons__david_ryan, firm: pinsent_masons, first_name: "David", last_name: "Ryan", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [], role_2005: "Managing partner (1998-2014)", src: "role S https://law.com/international-edition/2014/06/10/chris-mullen-faces-challenge-in-pinsent-masons-senior-partner-vote-with-managing-partner-election-to-follow; start A no source" }
  - { key: pinsent_masons__chris_mullen, firm: pinsent_masons, first_name: "Chris", last_name: "Mullen", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1980, moves: [{ ym: [2005, 7], kind: chair_role }], role_2005: "Partner; elected senior partner June/July 2005", src: "role S https://www.law.com/legal-week/sites/legalweek/2005/06/29/pinsents-elects-mullen-as-new-senior-partner/; start A no source" }
  # macfarlanes
  - { key: macfarlanes__robert_sutton, firm: macfarlanes, first_name: "Robert", last_name: "Sutton", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1975, moves: [], role_2005: "Senior partner (1999-2007/8)", src: "role S https://www.thelawyer.com/issues/4-april-2005/macfarlanes-hikes-partnership-with-a-record-six-promotions-2/; start A no source" }
  - { key: macfarlanes__paul_phippen, firm: macfarlanes, first_name: "Paul", last_name: "Phippen", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [], role_2005: "Managing partner (since May 1999)", src: "role S https://it.marketscreener.com/insider/PAUL-PHIPPEN-A0BXXF; start A no source" }
  - { key: macfarlanes__charles_martin, firm: macfarlanes, first_name: "Charles", last_name: "Martin", practice: corporate_ma, level: equity_partner, standing: elite, chair: false, career_start: 1985, left_practice: 2020, moves: [{ ym: [2008, 5], kind: chair_role }, { ym: [2020, 5], kind: left_practice }], role_2005: "M&A and private equity partner", src: "role S https://www.rothschildandco.com/en-fr/newsroom/press-releases/2021/01/charles-martin-joins-as-senior-adviser/; start S Rothschild release; left S law.com 2018" }
  # travers_smith
  - { key: travers_smith__christopher_bell, firm: travers_smith, first_name: "Christopher", last_name: "Bell", practice: corporate_ma, level: equity_partner, standing: leading, chair: true, career_start: 1971, left_practice: 2006, moves: [{ ym: [2006, 7], kind: left_practice }], role_2005: "Senior partner (retiring 2006 after 35 years with the firm)", src: "role S https://www.unquote.com/uk/news/75169/travers-smith-appoints-senior-partner; start D 35 years to 2006; left S Unquote" }
  - { key: travers_smith__chris_carroll, firm: travers_smith, first_name: "Chris", last_name: "Carroll", practice: private_equity, level: equity_partner, standing: leading, chair: false, career_start: 1978, moves: [{ ym: [2010, 7], kind: chair_role }], role_2005: "Managing partner (2001-2010); private equity and funds partner (partner from 1986)", src: "role S https://www.law.com/international-edition/2010/03/29/travers-names-carroll-as-new-senior-partner-as-firm-eyes-overseas-growth/; start A partner 1986 less 8" }
  - { key: travers_smith__alasdair_douglas, firm: travers_smith, first_name: "Alasdair", last_name: "Douglas", practice: corporate_ma, level: equity_partner, standing: leading, chair: false, career_start: 1975, left_practice: 2010, moves: [{ ym: [2006, 7], kind: chair_role }, { ym: [2010, 6], kind: left_practice }], role_2005: "Partner; former managing partner (late 1990s); elected senior partner from 1 Jul 2006", src: "role S https://www.unquote.com/uk/news/75169/travers-smith-appoints-senior-partner; start A no source; left S law.com 2011" }
```

## Gaps

1. **Career starts are weak:** 43 of 78 rows are [A]. The worst are firm leaders whose bios were not found: Childs, Cornell (CC); Davies (Linklaters); Jeffcote, Morton (Freshfields); Bond, Gold, Willis (Herbert Smith); Harris, Sherrington, Mayhew (Lovells); Price, Tyler, Weston (CMS); every Eversheds, BLP, SJ Berwin, Pinsent Masons, Macfarlanes (except Martin) and most Addleshaw and Travers leaders. A follow-up pass through firm alumni pages, Who's Who-style professional entries or Law Society "Find a Solicitor" admission years should replace these.
2. **Practices not confirmed** for about 20 leaders (tagged `corporate_ma` [A]), including Popham, Cornell, Angel, Beringer, Salz, Young, MacDonagh, Tyler, Weston, Jenkins, Gray, Lee, Jones, Paisner, Eisenberg, Harrel, Tonks, Ryan, Mullen, Sutton, Phippen, Bell, Douglas.
3. **Short firms:** Slaughter and May 4, Ashurst 4, CMS 4, Eversheds 2, BLP 2, Pinsent Masons 3, Macfarlanes 3, Travers Smith 3. Candidates searched but dropped for want of an [S] 2005 role source: Philip Wood (A&O; the sources say he rejoined A&O in 2008, so his 2005 status is unclear), Richard Clark and Richard Swallow (Slaughter and May), Richard Fleck (Herbert Smith; Oct 2004 election loser, career start unknown), Robert Derry-Evans (CMS), John Heaps and Ian Gray (Eversheds), Richard Foley (Pinsent Masons; 2005 role not sourced), Andrew Lilley (Travers Smith), Alistair Asher (A&O).
4. **The brief's examples that did not check out:** David Childs was Clifford Chance's COO, not senior partner, in 2005 (Stuart Popham was senior partner, Peter Cornell managing partner). Ian Terry was not Freshfields' managing partner in 2005 (Peter Jeffcote was, from 2001). Wim Dejonghe was A&O's Belgian managing partner, not global managing partner (David Morley was). Chris Saul was Slaughter and May's head of corporate, not senior partner. At Herbert Smith, no "Richard Turnor" was found; the senior partner in January 2005 was Richard Bond (David Gold from 1 April 2005), and David Willis was a corporate partner (the firm had no managing partner then). At Lovells, Lesley MacDonagh (not David Harris) was managing partner in January 2005; Harris took over on 1 May 2005.
5. **Dates where sources disagree:** Popham's first term start (2002 or 2003); MacDonagh's end (Apr 2005 vs 2006: Harris's May 2005 start is used); Charles Martin's senior partnership start (May 2007 or 2008: 2008 used); Salz's departure month (2006, month [A]); Morton's start as joint senior partner (elected Dec 2005; May 2006 [A]); Gold's departure from Herbert Smith (2011 [D] from the late-2010 consultancy report).
6. **Leaders whose end of practice was not found** (engine retires them by age): Mettenheimer, Jeffcote, Sherrington, Price, Tyler, Weston, Giles, Martyr, Paisner, Eisenberg, Harrel, Cohen, Tonks, Ryan, Mullen, Sutton, Phippen, Carroll, Lee, Jones, Devitt, Gray, Willis, Harris, Bromwich, Sparrow. Julian Tonks stood down as senior partner mid-term in 2005; whether he left practice then was not established, so no end year is recorded.
7. **Lisa Mayhew** moved Lovells → Jones Day → BLP; the date she left Lovells was not found, so the YAML records only the 2010 lateral to `berwin_leighton_paisner` (the engine will move her straight from Lovells). Fix when the Jones Day date is found.
8. **Mergers before 2005** (Pinsent Masons, December 2004) are fine; Addleshaw Goddard's Monica Burch is recorded as a legacy Theodore Goddard partner at the merged firm.
9. **Not checked against `firms.yaml`:** the 18 firm keys and the US `to` keys (`gibson_dunn`, `debevoise`) should be confirmed before pasting.
