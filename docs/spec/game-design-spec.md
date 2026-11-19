# Partner Track: Game Design and Technical Specification v0.1

**Status: DRAFT for Reece's review (2026-11-17).** Product manager and game designer's specification for a single-player, turn-based law firm management game built on Tech Startup Tycoon's engine. Technical decisions are in `docs/adr/` (PT-0001 to PT-0013); where this spec and an ADR differ on a technical matter, the ADR wins. Numbers below are **defaults** for `balance.yaml`; historical figures marked *(dossier)* are placeholders until the research dossiers (`docs/research/`) confirm them, the same practice as TST's v5 outline.

TST section references (for example "TST §32.1") point to `docs/formulas.md` in `Reece77/Tech_Executive_Tycoon`.

## Contents

1. Vision and pillars
2. The player: the founding partner
3. Player journey and firm stages
4. Core loop and time model
5. People
6. Practice areas
7. Clients and matters
8. The firm's economics
9. Leadership, seats and automation
10. Rivals and the legal market
11. Regulation and ethics
12. Reputation, press and rankings
13. Legal technology and AI
14. History and eras
15. Events and the LLM
16. Interface
17. Balance and tuning
18. Scope by release
19. Ideas for expanding the design
20. Open questions

---

## 1. Vision and pillars

**Partner Track** is Football Manager for a law firm. The player founds a small firm in January 2005 and, over a 30-year campaign to December 2034, tries to grow it into a global partnership, through the 2008 crash, the pandemic, the 2021 deal boom and the arrival of generative AI. The squad is lawyers; the fixtures are matters; the league tables are the Am Law 100, the directories and the deal tables; the dressing room is the partnership, which can vote the player out.

**Pillars** (TST's five, plus two of its own):

1. **People are the game.** Every lawyer is a person with skills, practice familiarity, personality, hidden potential and a breaking point. Hours, strain and learning are the squad management.
2. **The partnership is the boss.** No board, no shareholders: the player's own rainmakers decide the firm's fate by confidence and votes (ADR PT-0007).
3. **Every number reconciles.** Hours become WIP, bills, cash and PEP through a double-entry ledger (TST ADR-0003, PT-0003, PT-0005).
4. **Deterministic and seeded** (TST ADR-0002).
5. **Nothing is lost:** transactional turns, backups, history (TST ADR-0004).
6. **Real world, real scale.** Real firms at their 2005 sizes, real cycles to 2025, then the player's own future (PT-0008).
7. **Play at any depth.** Every area can be automated under people the player appoints, with money limits and one-offs that always need approval (TST §40), so the player can run one bet-the-company trial personally while a COO runs the rest.

**Not in scope:** courtroom simulation in real time, legal doctrine, document drafting mini-games, graphics beyond dense tables, charts and portraits-as-initials.

## 2. The player: the founding partner

### 2.1 Who they are

The player is the **founding partner**, a person with TST's full attribute model (§5.1), a background and a book of business. At founding they are also the **managing partner** (MP). They create the founding partner in the New Game screen:

| Background (`backgrounds.yaml`) | Starting skills lean | Book of business (2005) | Practice familiarity at 15+ |
| --- | --- | --- | --- |
| BigLaw M&A partner | negotiation, drafting, client care | $2.0M–$3.5M portable | corporate and M&A, private equity |
| Trial lawyer | advocacy, legal reasoning, writing | $1.0M–$2.5M | commercial litigation, white collar |
| Patent litigator with a science degree | legal reasoning, technical (IP) | $1.0M–$2.0M | IP |
| Regional generalist | client care, business development | $0.5M–$1.0M | corporate, real estate, employment |
| Government lawyer (DOJ, SEC, regulator) | legal reasoning, regulatory | $0.2M (reputation instead) | regulatory, white collar |

Age 34–52; bar admissions in the home jurisdiction (and others by background). Personality is chosen within limits (TST §5) or drawn at random.

### 2.2 Time: the founder still bills

The founding partner's monthly **energy** (TST §6, default 100) is time. One energy = two hours. Each month the player splits it between:

- **Billable work** on matters (they are a timekeeper, at the top rate);
- **Business development** (client meetings, pitches, speaking, writing) that raises relationships and origination;
- **Management** actions (hiring, reorganising, votes, comp, approving proposals).

Early, the founder's own hours are most of the firm's revenue; by stage 3 a founder who still bills 1,800 hours is starving the firm of leadership; by stage 4 the MP usually bills under 500. The New Game screen offers the classic choices: a **working MP** or a **full-time MP** (from stage 3; energy rises to 120 when billing is zero, because no client deadlines compete).

### 2.3 The founder's life (TST §32, §37: CHANGED lightly)

- **Stress and burnout** are TST §32.1's, now the founder's case of the strain model every lawyer has (§5.6, ADR PT-0006).
- **The personal account** (TST §32.2): the founder's draws, true-up, salary-equivalent, capital loan, personal investments and family office. Tax at `personal.tax_rate` on the founder's profit share (partners are taxed personally).
- **Persona** (TST §32.4): Visionary, Ruthless, Beloved, Reckless, raised by firm choices: Ruthless by de-equitisations, hostile laterals and layoffs; Beloved by pro bono, raises, fairness in comp; Visionary by early AI adoption, new practices, regions; Reckless by guarantees, leverage on the revolver, broken public claims.
- **Influence** (TST §32.5) becomes **bar politics and public life**: the bar association, the bench, government service (see §19 ideas).
- **The foundation** (TST §32.3) as is, with an access-to-justice cause added.

### 2.4 Family (TST §45: CHANGED)

TST §45.1–§45.3 and §45.6 port unchanged (partner, children, education, estate tax). A child who qualifies as a lawyer may join as an associate and rise on merit; the partnership notices nepotism (TST §45.4's staff reactions, applied to partner confidence as well).

### 2.5 Succession

- **Mandatory retirement**: the partnership agreement sets an age (default 65, a common BigLaw rule; the agreement can be changed by vote). From 60, the partnership expects a succession plan (confidence term).
- **How it happens:** by choice; at mandatory retirement; after losing an MP election (ADR PT-0007 §3); on health grounds (TST §45.5).
- **The choice:** the player names a **successor among the equity partners** (any partner, including a child who made partner); the partnership must elect them (a vote; a weak candidate can lose to a rival nominee). **The player then plays the successor** as the new MP (TST §45.5's "play the heir"), and the old founder becomes **senior partner** (an adviser with opinions, TST §45.5) until retirement, then a **retired partner** with an annuity if the agreement grants one (account 2600).
- **Name on the door.** If the firm still bears the founder's name, legacy counts it (§19).

## 3. Player journey and firm stages

| Stage | Name | Typical size | Unlocks |
| --- | --- | --- | --- |
| 0 | Founding | 1–3 lawyers, 1–2 staff | Matters, clients, hiring, the founders' agreement |
| 1 | Boutique | 4–20 lawyers | Practice groups (at 10), the first associate class, a second office in the home city region |
| 2 | Established | 21–100 | Income partners, a comp committee, the first business-services chiefs (CFO, COO), RFPs and panels, the partnership vote in full, laterals with guarantees |
| 3 | National | 101–400 | The executive committee, practice group leaders as seats, offices in other cities, automation, a pricing function, the MP term and elections |
| 4 | International | 401–1,500, or offices on two continents | Foreign offices under local rules, mergers, a verein or integrated structure, a CHRO and CKO |
| 5 | Global | 1,500+ lawyers on three continents, or Global 100 revenue | ABS entities where allowed, the conglomerate-style "firm and its affiliates" view |

Stage changes are checked in phase 10 (TST §42 unlocks): progressive screens, a guided first year, What next.

**Win and loss.** A standard campaign ends in December 2034 with the **firm score** (TST §30.1 adapted: revenue, PEP, rankings, reputation, longevity), the founder's **legacy** (TST §32.6), and the Hall of Fame. Game over: the firm dissolves, or the player leaves without a successor (ADR PT-0007 §4).

## 4. Core loop and time model

ADR PT-0002: monthly turns from January 2005, 360 turns, a firm-year calendar. ADR-0012's signature and ADR-0014's immediate actions are inherited.

### 4.1 Turn pipeline (TST's 12 slots, new bodies)

| Phase | TST name | Partner Track |
| --- | --- | --- |
| 1 | apply player decisions | offers and laterals resolve; votes held this month count; staffing changes take effect |
| 2 | rival decisions | the firm's delegates and automated areas act (ADR-0015); rival firms decide (§10) |
| 3 | R&D progress | knowledge and AI adoption progress (§13) |
| 4 | production and capacity | **intake**: clients instruct, RFPs award, conflicts are checked; **staffing**: hours are allocated to named matters, then flow work |
| 5 | sales, revenue, churn | **work and billing**: hours post to WIP; matter progress and outcomes; bills issue on each matter's cycle; collections; write-downs; client satisfaction |
| 6 | payroll and operating costs | salaries, bonuses (December), rent, insurance, technology, lateral and recruiting fees |
| 7 | financing | revolver interest and covenants; partner draws; capital in and out; December true-up; insolvency |
| 8 | people updates | strain and burnout, morale, growth and familiarity, reveals, relationships, resignations, lateral moves and poaching, retirements |
| 9 | market and macro update | legal demand indices, rate inflation, salary-scale moves, rankings (yearly) |
| 10 | stage checks | stages; partner confidence; petitions and elections; unlocks |
| 11 | snapshot and month-end report | KPIs; the monthly digest |
| 12 | event director | events for next month; campus and lateral candidate pools |

### 4.2 What the player does in a month

1. Reads the inbox and the digest (critical items block Continue: TST §23.1).
2. Staffs and watches named matters (who, how many hours, budget against actual).
3. Develops business: pitches, RFPs, client visits, cross-selling introductions.
4. Manages people: hiring, reviews, raises, promotions, comp, keeping rainmakers happy.
5. Manages the firm: rates, offices, investment in technology, the partnership agreement, votes.
6. Presses Continue, or Holiday until something needs them (TST §17.1).

## 5. People

### 5.1 Attribute model

Attributes are 1–20 floats shown as integers (TST §0), current ability CA and potential PA 10–200 (TST §1), revealed as ranges per observer (TST ADR-0007).

**Skills** (`skills.yaml`; TST's leadership group kept, the rest new):

| Group | Skills |
| --- | --- |
| Legal craft | legal reasoning, research, writing (drafting), advocacy (oral and trial), negotiation, deal structuring, procedure (court and filing practice), technical (science and engineering, for IP and regulatory), numeracy (tax, finance, restructuring) |
| Client | business development, client care, commercial awareness, languages (count plus a list) |
| Working | supervision, project management, stamina, technology (legal tech and AI fluency; rises from 2016 in new generations) |
| Leadership (TST) | leadership, mentoring, strategy, communication, judgment of talent, recruiting |
| Business services | finance, operations, marketing, human resources, IT, pricing, knowledge management |

**Practice familiarity** 1–20 for every practice area (§6), Football Manager's position grid (ADR PT-0006 §2). Effective skill on a matter = skill × `fam_factor(f)` = `0.70 + 0.30 × min(1, (f − 1) / 14)`.

**Personality** (TST `personality.yaml`, as is): ambition, loyalty, professionalism, temperament, adaptability, risk appetite, ego, integrity, sociability. **Hidden:** consistency, burnout risk, big moments, poachability, plus **portability** for partners (share of their book that follows them; ADR PT-0006 §5).

**Behaviour tags** (TST §2.7, extended): mentor, culture carrier, credit taker, toxic high performer, politician, perfectionist, quiet genius (as is); new: **rainmaker** (origination ×1.5), **grinder** (strain load ×0.7, BD ×0.7), **client whisperer** (relationship gains ×1.4), **cowboy** (cuts corners: speed +, error and malpractice risk ×2), **rule-bender** (billing padding risk; hidden until a dispute or audit), **lifer** (loyalty floor 14), **free agent** (moves every 3–5 years).

**Roles** (`roles.yaml`): lawyer roles by practice (a lawyer's role is their home practice; primaries and secondaries per practice, for example corporate: deal structuring, negotiation, writing; secondaries commercial awareness, project management, client care); paralegal (research, procedure, project management); legal technologist; business services (finance, HR, IT, marketing, BD, pricing, KM, operations, facilities, records and conflicts, risk and compliance).

### 5.2 Levels and the career ladder (ADR PT-0006 §1)

| Level | Years qualified | CA mean (sd) | Capacity hours / year | Billable target (default) |
| --- | --- | --- | --- | --- |
| Paralegal | — | 70 (12) | 1,950 | 1,500 |
| Trainee (UK) | 0 | 65 (10) | 1,950 | 1,200 |
| Associate, years 1–3 | 1–3 | 80 → 100 (12) | 2,300 | 1,900–2,000 |
| Associate, years 4–6 | 4–6 | 105 → 120 (12) | 2,300 | 2,000 |
| Associate, years 7–8 | 7–8 | 125 (12) | 2,300 | 2,000 |
| Counsel | 9+ | 130 (12) | 2,100 | 1,700 |
| Income partner | 8+ | 135 (12) | 2,200 | 1,800 |
| Equity partner | 10+ | 150 (15) | 2,200 | 1,700 + BD |

Associates advance one class year each September. Generation (TST §2) adds **law school tier** (T14-equivalent, national, regional; Oxbridge, Russell Group, other in the UK), which shifts CA and PA means and salary expectations, and the hiring channel (campus, lateral, referral).

### 5.3 How people change

- **Growth** (TST §3) with the learning factor `learn(h)` = share of the person's hours that were substantive work at or slightly above their level, ÷ the level's reference share (default 0.6), clamped 0.5–1.4 (ADR PT-0006 §4). Mentoring and the manager term (TST §13.5) apply through supervising partners.
- **Familiarity** += `fam.per_100h` (0.4) per 100 hours worked in an area, with diminishing returns above 15; −0.05 a month without work in it (floor at the level reached minus 3).
- **Morale** (TST §9) with new terms: **hours** (`W_hours = −10 × max(0, hours/target − 1.1)` and `−5` below 0.6, as idle associates fear for their jobs), **pay against the market scale** (the class-year scale replaces the band mid for associates), **bonus fairness** (December), **partnership prospects** (for years 6–8: a revealed sponsor and a realistic business case raise it), **interesting work** (matching interests and named-matter exposure), **origination credit fairness** (partners), and TST's manager, team, relationships and remote terms as they are.
- **Resignation** (TST §10) as is, with the job-hopper tag, the unvested-retention term replaced by **bonus timing** (associates leave after bonuses in January; partners after the true-up in April), and **lateral market heat** (the macro index of lateral moves).

### 5.4 Pay

- **Associates:** a **salary scale** by class year. A market-leading firm can raise the scale (a rival or the player); others match, lag or ignore it. History *(dossier)*: first-year salary of $125,000 in 2005 at top New York firms; $145,000 from 2006; $160,000 from 2007; $180,000 from 2016; $190,000 from 2018; $202,500 then $215,000 in 2021–22; $225,000 from 2024. Below-scale pay is allowed (regional firms run 50–80% of the scale) with morale and hiring costs. **Year-end bonuses** by class year in November–December follow the market (special bonuses in 2021).
- **Counsel and income partners:** salaries, with a discretionary bonus.
- **Equity partners:** a share of profit by the comp system (§8.5). No salary.
- **Business services:** TST's role bands, by city.

### 5.5 Up or out, and the partnership vote

- **Track.** An associate is eligible at `partner_track.years` (default 8; elite lockstep firms 9–10). Each year from year 6 the associate has a **sponsor** (a partner who champions them; chosen by the player or emerging from relationships) and a visible **business case**: book potential (relationship and BD skill), practice need (demand against capacity in the group), skills, and reviews.
- **December vote.** The player proposes candidates for **equity** or **income** partnership (or "not this year"). Each equity partner votes with utility `U = a × candidate quality (their displayed ranges) + b × practice need − c × dilution of their PEP (new points ÷ total) + d × relationship with candidate and sponsor + noise` (stream `vote`). Passing needs the agreement's threshold (default a simple majority of votes cast; two thirds for equity at lockstep firms). The player sees a predicted range and may lobby (energy, promised points, a seat).
- **Not made up:** the associate is told to move on (up or out: leaves within 12 months unless made **counsel**). Many leave for clients' in-house teams: they become **alumni** (§7.3), a source of future work.
- **De-equitisation** (December): moving an equity partner to income partner or out. A one-off with a vote; it raises Ruthless and lowers other partners' confidence by their fear (their own PEP contribution against the median), but improves PEP.

### 5.6 Strain and burnout (ADR PT-0006 §3)

`strain += 60 × max(0, hours/capacity − comfort) × (0.5 + burnout_risk / 20)`, with `comfort` = `1.0 + 0.01 × (stamina − 10)`; −8 a month when under comfort; −25 for a two-week holiday month; −40 for a sabbatical. **Burnout** at 80 (capacity × 0.7, error chance × 2, resignation × 2 for 6 months) until under 40. An associate at 2,600 hours a year (1.13 × 2,300) with stamina 10 and burnout risk 10 adds `60 × 0.13` = 7.8 a month: from 20, burnout in about 8 months. At 2,200 hours a year: never.

### 5.7 Hiring

- **Campus** (US): summer programme in May–July, offers in August, the class starts in September of the next year. Channel quality by school tier; offer acceptance by TST §7's logistic with the firm's **prestige** (§12) and the scale against market. UK: trainees two years ahead, qualification each September.
- **Lateral associates:** recruiter searches (TST §7: 20–25% fee), job posts, referrals; interviews required (TST ADR-0016).
- **Lateral partners:** a partner's **book** (displayed as a range, from their origination at their current firm; true portability hidden), comp demand (a multiple of their book), and often a **guarantee** (fixed comp for 1–3 years; account 2700). Due diligence (energy and cost) narrows the book's range and checks conflicts (ADR PT-0009). Lateral success is notoriously uneven: the portability draw happens when they move (stream `lateral`), and their book arrives over 12–24 months.
- **Group lifts:** a partner and their team (associates, paralegals) moving together; and team lifts from a failing rival (Dewey 2012) as events.
- **Delegated hiring** (TST §13.10) as is, with recruiting managers and practice leaders as delegates.

## 6. Practice areas

Practice areas are the game's categories (TST §11's segments, re-cast). Each has data in `practices.yaml`:

| Practice | Demand driver (index) | Cycle | Partner rate 2005 (NY, top firm) *(dossier)* | Leverage norm (associates per partner) | Margin norm | AI exposure (2030) |
| --- | --- | --- | --- | --- | --- | --- |
| Corporate and M&A | M&A volume | pro-cyclical, strong | $750 | 4.0 | 40% | medium (diligence, drafting) |
| Private equity and funds | PE deal and fundraising volume | pro-cyclical, strong; booms 2006–07, 2021 | $800 | 4.5 | 45% | medium |
| Capital markets | IPO and issuance volume | pro-cyclical, volatile | $750 | 3.5 | 42% | medium |
| Banking and finance | leveraged lending volume | pro-cyclical | $700 | 3.5 | 38% | medium |
| Restructuring and insolvency | default rate, distressed debt | **counter-cyclical** (2009, 2020, 2023) | $850 | 3.0 | 45% | low |
| Commercial litigation | litigation index | steady, slightly counter-cyclical | $700 | 3.0 | 35% | high (review, research) |
| White collar and investigations | enforcement intensity | policy-driven | $800 | 3.0 | 40% | high (review) |
| International arbitration | cross-border disputes | steady, rising | $700 | 2.5 | 35% | medium |
| IP (patent litigation, prosecution, transactional) | patent filings, tech M&A | steady; litigation waves | $650 | 2.5 | 35% | high (prosecution, review) |
| Employment and labour | employment level, regulation | counter-cyclical (layoffs) | $550 | 2.0 | 30% | medium |
| Tax | deal volume, tax reform events (2017) | mixed | $800 | 2.5 | 45% | medium |
| Real estate | property transactions | pro-cyclical (crashes 2008) | $550 | 2.5 | 30% | medium |
| Regulatory: antitrust and competition | merger reviews, enforcement | follows M&A, with policy | $800 | 3.0 | 42% | low |
| Regulatory: financial services | regulation intensity (2010 Dodd-Frank surge) | policy-driven | $750 | 2.5 | 40% | medium |
| Regulatory: healthcare and life sciences | healthcare deals and enforcement | steady, rising | $650 | 2.5 | 35% | medium |
| Energy, projects and infrastructure | project finance, energy transition | long cycles | $650 | 3.0 | 35% | medium |
| Technology, privacy and data | tech activity; privacy laws (GDPR 2018) | rising | $600 | 2.5 | 35% | medium |
| Private client, trusts and estates | wealth index | steady | $600 | 1.5 | 30% | medium |
| Insurance and reinsurance | catastrophe and claims cycles | steady | $550 | 2.5 | 30% | medium |
| Mass torts and class actions (plaintiff) | contingency; settlements | lumpy | contingency | 1.5 | volatile | medium |

Each practice also has: a **matter kind mix** (deals, cases, advisory, filings), a **task mix** per kind (ADR PT-0011), **billing model mix** (§7.7), standard **realisation** (85–95%) and **collection** (93–98%) norms, a **seasonality** (deal closings peak in December), a **conflict density** (how often its matters are adverse to large companies: litigation high, private client low) and **cross-sell affinities** (M&A with antitrust, tax, employment, finance).

**Demand.** For each region `r` and practice `p`, monthly demand in standard-value dollars:

```latex
D_{r,p}(t) = D^0_{r,p} \times G_{r,p}(t) \times \big(1 + \beta_p \,(I_p(t) - 1)\big) \times \varepsilon
```

where `G` is long-run growth (to 2025 from data, then seeded), `I_p` the driver index (1.0 = 2005 average), `β_p` the practice's sensitivity (M&A 1.4; restructuring −1.2; litigation −0.2), and `ε ~ LogNormal(0, σ_p)` monthly noise (stream `demand`). Demand is allocated to clients (§7.1), whose wallets are then split among firms.

## 7. Clients and matters

### 7.1 Clients

A **client** is an entity with: a sector, a size, a home region, a **legal wallet** by practice (its annual spend, drawn from its sector and size and moving with demand), a **panel** (the firms it uses, refreshed by RFP), a **general counsel** (a person, §7.3), a **price sensitivity**, a **loyalty**, and **outside counsel guidelines** (staffing limits, rate caps, e-billing rules that drive write-downs).

- **Real clients** for the top 300 (Fortune 500 and FTSE 100 names in 2005, personal use) with wallets sized from public estimates *(dossier)*; **generated clients** for the rest (`client_gen`). Clients are born, grow, merge (their M&A is the firm's M&A work), and fail (the 2008 crash takes some; their bankruptcy is the restructurers' work and unpaid bills are the firm's loss).
- **Private equity sponsors** are clients whose portfolio companies are also clients (a sponsor's relationship spreads to its companies).
- **Individuals** (private client, plaintiffs) are pooled as flow demand by region.

**Wallet share.** A client splits each practice's wallet among the panel firms by an appeal model (TST §11.6's logit pattern):

```latex
A_{f} = w_{rel}\,R_{c,f} + w_{rep}\,Rep_{f,p,r} + w_{price}\,\big(1 - \tfrac{rate_f}{rate_{ref}}\big) + w_{cap}\,Cap_{f,p} - w_{conf}\,Conflict_{c,f},\qquad s_f = \frac{e^{A_f}}{\sum_{g \in panel} e^{A_g}}
```

with the relationship `R` (0–100, below), reputation in the practice and region (§12), price, available capacity (strained firms lose work), and conflicts. Weights vary by client size (large clients weigh reputation; mid-market weighs price).

### 7.2 Relationships, origination and cross-selling

- **Relationship** `R_{c,f}` 0–100 per (client, firm), moved monthly by: outcomes on its matters (±), service (responsiveness from team strain and capacity), billing (disputes −, write-offs on budget overruns −), the relationship partner's client care and BD time (+), cross-practice breadth (+), alumni at the client (+), conflicts refused or waivers asked (−), and drift toward 40.
- **Relationship partner.** Each client has one; **origination credit** for its work goes to them (and splits by the agreement's rule for introductions). Their personal relationship with the GC is a TST §16.7 relationship between people. When they leave, the client follows with probability from their portability, the firm's breadth with the client, and the institutional relationship (§8.7).
- **Cross-selling.** A partner can **introduce** a colleague from another practice (energy; a small relationship cost if the introduced team underperforms); success raises the client's practice count, which raises loyalty: clients using 4+ practices rarely leave.
- **Panels and RFPs.** Large clients run panel reviews every 3 years, and RFPs for big matters. The firm answers with a pitch (team, price, AI and efficiency claims, diversity of team, references), written in the LLM's voice from engine facts; awards follow the appeal model plus pitch quality from the pitch team's skills (stream `rfp`).

### 7.3 People on the client side

- **General counsel and in-house lawyers** are generated people with personalities. They change jobs: a GC who moves takes their preferred firms to the new client (relationships carry, partially).
- **Alumni.** Lawyers who leave the firm for in-house roles become alumni: their relationship with the firm starts from their morale when they left. Up-or-out, handled well, becomes a business development engine; handled badly, a source of hostile GCs.

### 7.4 Matter intake and conflicts

Each month (phase 4), clients instruct work: flow demand for their panel firms, and **named matters** (ADR PT-0004) with a kind, a size (expected standard-value fees, LogNormal by practice and client size), a duration, parties, a deadline profile and a risk level. Intake runs the **conflicts check** (ADR PT-0009): a conflicted matter is declined automatically unless a waiver exists; the player may seek one (critical, for key clients).

### 7.5 Named matters as projects

| Field | Notes |
| --- | --- |
| Client, practice, kind | deal (M&A, financing, IPO), case (litigation, arbitration, investigation), advisory, filing (prosecution), restructuring |
| Lead partner, team | named people with roles (lead, senior associate, juniors, paralegals) and planned hours a month |
| Budget | hours and fees by phase (if the client asked for one: most large clients from 2010) |
| Phases | e.g. litigation: pleadings → discovery → motions → trial → appeal; M&A: diligence → negotiation → signing → regulatory → closing |
| Progress | per phase, from team output: `o = Σ_people hours × effective skill on the phase's task × (1 − strain penalty) × supervision factor` |
| Billing model | hourly, blended, capped, fixed, success fee, contingency, retainer (§7.7) |
| Outcome | per kind (§7.6) |
| Risk | error chance (malpractice), conflict, publicity |

**Staffing rules:** a partner supervises at most `span(leadership)` matters well (TST §13.2's span formula on matters); under-staffed matters slip (deadlines missed are critical events), over-staffed ones overrun budgets and draw write-downs (clients refuse to pay for "too many juniors on calls", per outside counsel guidelines).

### 7.6 Outcomes

- **Litigation and arbitration:** at the trial (or settlement point), `p_win = σ(k (Q_us − Q_them) + m)` where `Q` is the team's weighted craft (advocacy and legal reasoning lead; writing and procedure support), the lead's **big moments** hidden trait in trial, familiarity, and preparation (hours delivered against need); `m` is the case's **merits** (hidden, drawn at intake, revealed as a range by early case assessment); `Q_them` is **opposing counsel**: a named rival firm's team when the other side is represented by a real rival (PT-0008), else a pool. Settlements are offered by the other side as events during the case, valued from both sides' expectations; the client's risk appetite and the player's advice decide.
- **Deals:** `p_close` from the market (regulatory risk, financing conditions), the counterparty, and the team's negotiation and structuring; deals can **collapse** (2008) or be blocked (antitrust) through no fault of the firm. Quality of the result (terms won) moves the relationship.
- **Advisory and filings:** quality only; error chance.
- **Errors:** each matter-month, `p_error = base_p × (2 − effective skill/10) × strain multiplier × cowboy tag × supervision shortfall`. Errors are mostly caught (a cost in write-off hours); some escape (a missed deadline, a bad clause), surfacing later as **malpractice claims** (§11.3).

Outcomes are **public** for public matters (trials, listed deals) and feed **reputation** and the **league tables** (§12).

### 7.6a Courts and judges

- **Courts** in v1: the federal district courts for the home market and a few national forums (S.D.N.Y., E.D.N.Y., D. Del., N.D. Cal., E.D. Tex., W.D. Tex.), the Delaware Court of Chancery, New York's Commercial Division, and AAA and ICC arbitration as forums; v2 adds the English High Court and Commercial Court. Each court has a docket pace, a trial rate and local rules (pro hac vice, AI disclosure orders from 2023).
- **Judges** are people with **procedural** attributes only (ADR PT-0013): docket speed, appetite for trial, discovery strictness, settlement pressure, summary-judgment appetite, sanctions strictness. A case is assigned a judge at random within its court (stream `matter`). The judge changes a case's **duration, cost and path** (how often it settles, how long discovery runs, how severe sanctions are for an AI-hallucinated filing) and the value of preparation and procedure skill; the judge never favours a side. **Forum choice** is a real decision where the rules allow it (a patent plaintiff in the 2010s choosing a fast docket).
- **Real judges** by name in the modelled trial courts (ADR PT-0013), with traits from published docket statistics and orders, appointed and retiring as history did to 2025; generated judges afterwards and elsewhere. Appellate courts are institutions with reversal rates and timing.
- Lawyers and judges have **relationships** of a limited kind: familiarity with a judge's courtroom (hours appeared before them) improves procedure-skill effects there; a sanctioned lawyer starts behind with that judge.

### 7.7 Billing models

| Model | Revenue | Risk | When |
| --- | --- | --- | --- |
| Hourly (standard rates, discounts by client) | hours × rate × realisation | client pushback, write-downs on overruns | default |
| Blended hourly | hours × one blended rate | leverage shifts margin to the firm | mid-market |
| Capped fees | min(hourly, cap) | overruns are the firm's loss | from 2010 more common |
| Fixed fee (by phase or matter) | the price, recognised by progress | efficiency is the firm's gain or loss | rising from 2010; dominant for AI-exposed work after 2025 if the player leads |
| Success fee | base + bonus on outcome | outcome variance | deals and disputes |
| Contingency | share of recovery (25–40%) | the firm funds the case; years of WIP with no bill | plaintiff litigation; litigation funders (from about 2010) can share |
| Retainer | monthly fee for advisory | under-use is margin, over-use is loss | private client, employment, regulatory |

**Bills** issue monthly (or at phase ends). **Billing write-downs** at the partner's choice (to keep the client) or by guideline rejections; **collection** follows the client's days-to-pay (stressed clients pay late; bankrupt ones never). **Billing disputes** are events (the GC's personality; padding by a rule-bender partner discovered; e-billing audits); fee arbitration where the bar provides it.

### 7.8 Pro bono

Pro bono matters are named or flow matters with no fees. They raise associates' morale and learning (real responsibility early), recruiting appeal, reputation (rankings of pro bono), and the founder's Beloved trait; they cost capacity. The firm sets a credit policy (pro bono hours counting toward targets, default 50).

## 8. The firm's economics

### 8.1 The core identity

The game teaches (and the Explain panel decomposes, TST advisor) the identity every managing partner knows:

```latex
PEP = \frac{\text{Profit}}{\text{Equity partners}} = \underbrace{\frac{\text{Revenue}}{\text{Lawyers}}}_{\text{RPL}} \times \underbrace{\frac{\text{Profit}}{\text{Revenue}}}_{\text{margin}} \times \underbrace{\frac{\text{Lawyers}}{\text{Equity partners}}}_{\text{leverage}}
```

and RPL = hours per lawyer × average rate × realisation × collection. Each term is a slider the player moves indirectly: utilisation, rates, staffing, pricing, the number of equity partners.

**Worked example (a 2010 mid-size firm).** 120 lawyers, 30 equity partners; average 1,750 billed hours per lawyer at a standard $420 blended rate; realisation 88%, collection 96%: revenue = 120 × 1,750 × $420 × 0.88 × 0.96 = **$74.5M**, RPL $621k. Costs $45.0M (salaries $27M, rent $6M, other $12M): profit $29.5M, margin 39.6%, leverage 4.0, **PEP = $983k**.

### 8.2 KPIs (all derived; PT-0005)

Revenue, RPL, PEP, profit margin, leverage, **utilisation** (billed ÷ capacity), **realisation** (billed ÷ standard), **collection** (collected ÷ billed), **lockup days** (WIP + receivables over daily fees), revenue by practice, office and client concentration (top client share; top-10 share), associate attrition, partner attrition, lateral success rate, matters won and closed, malpractice claims, reputation by practice and region.

### 8.3 Costs

TST §8's payroll pattern: salaries by level and scale, benefits (`bp` of salary), bonuses in December, rent per lawyer by city (offices are leases with terms, TST §19's offices), malpractice insurance (by revenue, practice risk mix and claims history), technology and AI (per head and platform), recruiting and lateral fees, marketing and BD (events, sponsorships, hospitality), knowledge subscriptions, and general admin.

### 8.4 Capital, draws, debt (ADR PT-0003)

- **Capital:** each equity partner's capital at `capital.share_of_comp_bp` of target comp; required at admission (cash or a partner bank loan in their personal book). **Capital calls** (a vote) raise it; **returned** over 3 years after a partner leaves.
- **Draws** monthly, **true-up** after year end; the firm may hold back a reserve (`profit.retain_bp`, default 0; prudent firms 5–10%).
- **Debt:** a **revolver** sized by a multiple of receivables and WIP, with covenants (leverage, minimum partner capital, maximum partner departures as a share of revenue). **Private placements** (term debt; Dewey borrowed this way in 2010) for expansion. Covenant breach → the bank's event chain (TST §20.3's lender event pattern).
- **Retired-partner annuities** (an agreement term): a liability that grows with each retirement (Dewey's trap).

### 8.5 Compensation systems

Chosen in the founders' agreement and changeable by vote (two thirds):

| System | Rule | Effects |
| --- | --- | --- |
| **Pure lockstep** | points by seniority: 10 at admission rising by 2.5 a year to a plateau of 25 at year 7; profit per point | collegiality: cross-selling ×1.3, lateral appeal for stars ×0.7, star poachability ×1.3 (stars are underpaid), morale stable |
| **Modified lockstep** (default) | lockstep with gates (a partner can be held at a step or moved up 1–2 steps) and a super-point bonus pool (10%) | middle ground; comp committee time each December |
| **Eat what you kill** | formula: `comp = 0.50 × origination + 0.35 × working credit + 0.15 × management credit`, normalised to profit | rainmakers stay and laterals come; cross-selling ×0.6 (hoarding), credit disputes (events), juniors' morale ×0.9 |
| **Black box / committee discretion** | comp committee sets shares with an origination weight (0.4) and a contribution score | flexible; trust in the committee (the CHRO and MP) matters; secrecy breeds disputes |
| **Two-tier** (equity plus income partners) | combinable with any of the above | leverage up, PEP up; income partners' morale and lateral flight risk |

Each equity partner's **satisfaction** compares their share with (a) their own sense of contribution (true contribution plus ego), and (b) their **market value** (what a rival would pay for their book and skills). The gap drives confidence (ADR PT-0007) and flight (§8.7).

### 8.6 The partnership agreement

A document the player maintains, voted on: the comp system; partner classes; capital rules; voting thresholds (admission, merger, dissolution); MP term and powers; mandatory retirement age; annuities; non-compete and notice periods (US ethics rules bar most non-competes for lawyers; garden leave of 3–6 months is common in the UK); expulsion; the treatment of departing partners' capital. Each term changes behaviour (for example, a 6-month notice period slows group departures but raises lateral recruits' demands).

### 8.7 Partner flight and the exodus spiral

Monthly, for each equity partner (stream `poach`; TST §15.6's approach machinery):

```latex
p_{leave} = b \times \Big(1 + 2\,\max\big(0, \tfrac{V_{mkt} - comp}{comp}\big)\Big) \times \tfrac{21 - loyalty}{10} \times \Big(1 + c\,\tfrac{departed_{12m}}{group}\Big) \times \Big(1 + \tfrac{\max(0,\,50 - conf)}{25}\Big)
```

with base `b` 25 bp, market value `V_mkt` = book × the lateral market's multiple (macro), the **contagion** term `c` = 3 for departures from the same practice group in the last 12 months, and confidence `conf`. Rivals' approaches (§10) turn the probability into concrete offers the player can try to counter (counter-offer: points, a seat, a guarantee).

**The spiral.** When a partner leaves, their **portable** clients leave with them over 3–12 months; their capital is returned over 3 years; the revolver's covenants tighten; remaining partners' PEP falls; their `V_mkt − comp` gap widens; contagion rises. A firm with high debt, guarantees and annuities can fall into a self-reinforcing collapse. **Target:** recoverable by a skilled player who sees it early (warnings from the CFO and in the digest) but fatal if ignored (spec §17).

### 8.8 Offices, regions and mergers

- **Offices** (TST §19, CHANGED): leases in cities, local hiring pools, local rates and salaries, local demand reach (a client's work in a region favours firms with an office there), a local **office managing partner**. Foreign offices need **local rules** (bar rules: foreign lawyers' rights, partnership with local lawyers, joint ventures where required).
- **Opening a city** by organic start (one partner and a team), a **lateral group** (a team lift), or a **local merger**.
- **Mergers between firms** (TST §28, CHANGED): due diligence (books, partner quality, conflicts, annuities, leases), **terms** (the points ratio: each firm's partners' share of the merged profit pool; name; MP and governance; comp system harmonisation; rate harmonisation), **votes in both firms** (two thirds), **conflicts clearance** (every client of both firms), and **integration**: TST §28.5's culture clash and flight (partners whose PEP falls or whose practice is subordinated leave), client conflicts lost, rate harmonisation (low-rate clients balk). A **verein** (TST §31's group, CHANGED: member firms keep their own books and profit pools under one brand; shared costs by formula) lets a firm grow globally without pooling profit; an **integrated merger** pools everything. Combination targets include real rivals (any firm can be approached) and the player can be approached (accepting a merger in which the player's firm is absorbed ends the campaign as an exit, scored).

## 9. Leadership, seats and automation

### 9.1 Seats (TST §18.3, §24, CHANGED)

| Seat | Who | Seat score weights | Effect (`e = clamp((s − 10)/8, −0.5, 1)`, vacant from its stage = −0.5) | Authority (when given, TST §24.1) |
| --- | --- | --- | --- | --- |
| **Managing partner** | the player, or the CEO-like professional MP after succession | leadership 0.3, strategy 0.3, communication 0.2, business development 0.2 | partner confidence +0.5 e a month; vote predictions narrower | (the player) |
| **Executive committee** (3–9 partners) | elected or appointed partners | strategy 0.4, leadership 0.3, communication 0.3 | confidence of their constituencies; decision quality of firm-wide proposals | approves one-offs below a level the MP delegates |
| **Practice group leader** (one per practice group) | an equity partner | supervision 0.3, leadership 0.3, business development 0.2, judgment of talent 0.2 | group's utilisation management, staffing quality, associate morale | staffs flow work and named matters within the group; opens hiring plans; proposes laterals and promotions |
| **Office managing partner** | an equity partner in the office | leadership 0.3, client care 0.2, operations 0.2, communication 0.3 | office morale, local BD, local hiring pool | office hiring, local events, lease proposals |
| **General counsel (firm's own)** | a partner or counsel | legal reasoning 0.3, integrity (true) 0.3, communication 0.2, procedure 0.2 | malpractice and disciplinary outcomes; conflicts-check quality | conflicts clearance, waivers, claims handling |
| **CFO** | business services | finance 0.45, strategy 0.2, negotiation 0.2, communication 0.15 | collection +5% e; revolver terms; budget accuracy | billing and collections drives, cash and revolver, budgets; capital calls are one-offs |
| **COO** | business services | operations 0.35, leadership 0.25, strategy 0.2, communication 0.2 | support coverage (TST §18.4), office costs | support staffing, offices, procurement |
| **CMO / CBDO** | business services | marketing 0.45, communication 0.2, strategy 0.2, leadership 0.15 | RFP and pitch quality; reputation gains | pitches, events, panel reviews, directory submissions |
| **CHRO** | business services | human resources 0.4, judgment of talent 0.2, communication 0.2, leadership 0.2 | associate morale and attrition; campus quality | campus programme, associate reviews, salary-scale response within guardrails |
| **Pricing director** (stage 3) | business services | pricing 0.45, numeracy 0.25, negotiation 0.15, communication 0.15 | realisation +3% e; fixed-fee accuracy | rate cards within a band; fixed-fee quotes; budget reviews |
| **Chief knowledge officer / CIO** (stage 4) | business services or partner | knowledge management 0.35, technology 0.35, strategy 0.3 | AI adoption speed; training effectiveness | AI and tech investment within a budget; training programmes |

### 9.2 The partnership and the executive committee

ADR PT-0007. The executive committee is elected (or appointed by the MP in small firms), with members as seats. Its average confidence is the board-confidence analogue; quarterly partners' meetings replace board meetings (a summary item, TST §14.6's warnings). Proposals that need a vote of the whole partnership are listed in §8.6.

### 9.3 Pitches and reports (TST §27, CHANGED)

Seat holders with authority pitch big moves each quarter (TST §27.1's chance by ambition, quality by seat score): a lateral partner hire with a book (PGL), an office in a city (OMP or COO), a fixed-fee product for a matter type (pricing), an AI platform (CKO), a panel review push on target clients (CMO), a merger candidate (MP's executive committee member). Each pitch carries a low and high case, Approve/Modify/Decline, and a follow-through record. Reports with a voice (TST §27.2) quarterly.

### 9.4 Automation everywhere (TST §40, CHANGED)

| Area | Owner seat | Lead roles | What the owner does each month |
| --- | --- | --- | --- |
| Staffing (per practice group) | PGL | senior counsel, practice manager | allocates flow work and staffs named matters to targets (utilisation band, strain cap, learning share) |
| Intake and conflicts | GC | conflicts manager | runs checks; declines conflicted work; requests waivers below the limit |
| Billing and collections | CFO | billing manager | issues bills on cycle; chases receivables; proposes write-downs within a band |
| Pricing and rates | Pricing director | pricing analyst | January rate cards within ±band; fixed-fee quotes; discounts within limits |
| Business development and pitches | CMO | BD manager | panel reviews, RFP responses (team, price within band), events |
| Associate hiring and campus | CHRO | recruiting manager | campus targets, lateral associate plans, salary-scale response (match, lag) within guardrails |
| Associate development | CHRO / PGL | professional development manager | reviews, training, rotation for familiarity, sponsor assignments |
| Lateral partners | MP's delegate (exec committee member) | — | screening and approaches; **every hire with a guarantee is a one-off** |
| Offices and support | COO | operations manager | support coverage, lease proposals (one-offs above limit) |
| Knowledge and AI | CKO | legal technologist | adoption within budget; training |
| Risk and claims | GC | risk manager | claims handling, insurance renewal |
| Pro bono | a pro bono partner | pro bono counsel | keeps pro bono hours at the policy level |
| Routine events | the area's owner; else COO | — | TST §40.5 |

**One-offs** (always proposals; TST §40.2): partnership admissions and de-equitisations; guarantees; mergers and combinations; opening or closing an office; a capital call; changes to the partnership agreement; any AI platform above the limit; any lease above the limit; a salary-scale change above the market; litigation funding agreements; settling a malpractice claim above the deductible; taking on a matter adverse to a key client with a waiver; ABS formation. **Money limits**, **decision quality** (`clamp(0.55 + 0.03 s, 0.6, 0.98)`), **workload in energy**, the **monthly digest** and the **Automation screen** are TST §40 as built.

## 10. Rivals and the legal market

### 10.1 Rival firms (PT-0008)

About 60 real firms at their 2005 figures *(dossier)*, each with 5–10 **real notable lawyers** by name (its chair or MP and its best-known partners; ADR PT-0013) and generated people for the rest, a further 120 generated regional and mid-market firms, and spin-off boutiques founded during play (TST §15.4's startups: a partner group leaves a big firm to found a boutique; most stay small, some become the next Quinn Emanuel). Examples of personalities:

| Personality | Behaviour | Examples (2005) |
| --- | --- | --- |
| `elite_lockstep` | highest rates; small, selective; few laterals; never merges | Wachtell Lipton, Cravath, Sullivan & Cromwell, Davis Polk, Simpson Thacher, the Magic Circle (Slaughter and May the purest) |
| `performance_machine` | tiered partnership; aggressive laterals and PE focus; grows fast | Kirkland & Ellis, Latham & Watkins |
| `global_verein` | merges for footprint; many offices; moderate PEP | Baker & McKenzie, DLA Piper, later Dentons |
| `litigation_boutique` | trial-only; contingency possible; high PEP | Quinn Emanuel, Williams & Connolly, Boies Schiller |
| `tech_coast` | start-up and VC work; fixed fees early | Wilson Sonsini, Cooley, Fenwick |
| `regional_champion` | dominates a region; grows by local mergers | Reed Smith and K&L Gates from Pittsburgh (both became global, a path the player can follow), Jones Day from Cleveland |
| `volume_mid_market` | lower rates, high utilisation, cost leader | employment and insurance defence firms |
| `big_four_legal` | ABS entrants where rules allow; integrated with tax and consulting | KPMG Law, Deloitte Legal, PwC Legal, EY Law (UK and, later, Arizona) |
| `alsp` | alternative legal services: contract lawyers, review, managed services | Axiom, legal process outsourcers |

**Scale check:** in fiscal 2009 the top five by revenue were Baker & McKenzie ($2.11B), Skadden ($2.10B), Latham & Watkins ($1.82B), Jones Day ($1.52B) and Kirkland & Ellis ($1.43B); Am Law 100 average PEP was about $1.26M. These anchor the 2009 checkpoint of the history pin; the 2005 starting values come from the dossier.

### 10.2 Rival decisions (TST §15.3's utility AI, new actions)

One or two actions a month per rival, scored `U = need × weight(personality) + N(0, 0.1)`: raise rates, cut rates (for a client or a practice), hire a lateral partner (from any firm, including the player's), lift a team, open an office, bid on an RFP, merge (approach a firm), de-equitise, raise the salary scale, adopt AI (from its era), launch a fixed-fee offer, cut costs (layoffs in 2009), spin off a boutique (by its partners' departures, not a decision).

### 10.3 History's dated events (to 2025, PT-0008 §2) *(dossier)*

Mergers (Dewey Ballantine and LeBoeuf Lamb 2007; Hogan & Hartson and Lovells 2010; SNR Denton, Salans and FMC to form Dentons 2013, Dacheng 2015; Allen & Overy and Shearman & Sterling 2024; Herbert Smith Freehills and Kramer Levin 2025, among others), collapses (Heller Ehrman 2008; Howrey 2011; Dewey & LeBoeuf 2012; Bingham McCutchen absorbed 2014), splits and listings (Slater & Gordon 2007; Gateley 2015; others in the UK), and market-wide salary steps (§5.4). Each happens on its date unless the player changed its conditions; afterwards, rivals play freely.

### 10.4 The legal market's news

TST §41's World news, CHANGED: lateral moves, mergers, rate rises, league tables, rankings, big verdicts, collapses; rival firm pages (revenue, lawyers, PEP band, practices, offices, personality label, stance toward the player: competing for clients, poaching, merger interest).

## 11. Regulation and ethics

### 11.1 Bar rules by jurisdiction (PT-0010)

`bar_rules.yaml` per jurisdiction and date: admission rules (and reciprocity), foreign lawyers' rights, ownership and fee-sharing, advertising and solicitation, referral fees, lateral screening, non-competes for lawyers, trust accounting, mandatory insurance (England and Wales requires professional indemnity cover; most US states do not), continuing education, and the disciplinary process. A lawyer may only lead matters in jurisdictions where they are admitted (pro hac vice for litigation elsewhere at a cost).

### 11.2 Conflicts (PT-0009)

Engine rule; see the ADR. The GC's area owns checks; skipped or weak checks risk hidden conflicts.

### 11.3 Malpractice and insurance

- **Claims** arise from escaped errors (§7.6) and, in litigation, from losing clients with a grievance (a share of lost cases with high stakes). Each claim has a hidden merit and size; it is a TST §48-style case with visible stages (notice, investigation, defence, settlement or trial), costs, and an insurer.
- **Insurance**: a policy with a limit, a deductible and a premium that resets each renewal by claims history, revenue and practice mix (ALAS-like mutuals and commercial insurers). Uninsured excess falls on the partnership (and in a general partnership, on partners personally: an agreement term).
- **Reputation:** a public claim lowers reputation in that practice.

### 11.4 Discipline

- **Disciplinary cases** against individual lawyers (TST §48's investigation machinery for the bar regulator): billing fraud (a rule-bender's padding discovered), conflicts violations, trust-account misuse, misleading the court, sexual harassment or bullying at work (as workplace-conduct cases, handled by HR and the GC, kept to their professional consequences), and failures of supervision. Outcomes: dismissal, reprimand, fines, suspension (capacity lost), disbarment (the person leaves). The firm faces regulator inquiries where its systems failed (UK: the SRA can sanction firms).
- **Integrity** (hidden personality) drives the chance; supervision and the GC's checks reduce it.
- **Client money**: a trust-account shortfall is always critical and a disciplinary matter (PT-0003 §7).

### 11.5 Ownership rules and ABS (PT-0010)

DC's limited non-lawyer partnership (1991); England and Wales ABS licensing under the Legal Services Act 2007 (from 2011–12); Australian listed practices (2007); Utah's sandbox (August 2020); Arizona's abolition of Rule 5.4 with ABS licensing from 1 January 2021 *(dossier verifies each date and scope)*. An ABS entity lets the firm take outside equity, list (UK) or build a legal services arm with non-lawyer owners; it is a v2–v3 strategy.

### 11.6 Billing disputes and client audits

Events from guideline breaches, overruns and suspicious entries; fee arbitration; the client's e-billing audit (reductions by rule); public disputes harm reputation.

## 12. Reputation, press and rankings

### 12.1 Reputation

Per (firm, practice, region), 0–100, public, like TST's brand: moved by outcomes on public matters, league-table positions, lateral stars joining (+) and leaving (−), directory bands (+), malpractice claims and scandals (−), and drift toward the firm's long-run mean. **Prestige** (firm-wide) is the revenue-weighted average plus PEP rank, and drives campus and lateral appeal.

### 12.2 The legal press (TST §29, CHANGED)

Press moments: an Am Law ranking day, a big verdict, a lateral splash, a merger, layoffs, a collapse nearby, salary-scale moves, an AI announcement. Bold, measured or deflect; **public claims** (TST §29.2's promises) such as "we will double our London office by 2012", "no layoffs this year", "we will match the scale", checked by the engine at their deadlines. Credibility as TST §29.3. Rival MPs are characters with statements and feuds (TST §29.4).

### 12.3 Rankings and tables

- **Revenue and PEP tables** (the Am Law 100 and 200, the UK top 50, the Global 200) each spring from the prior year: public, the player's firm included once large enough.
- **League tables** (deal counts and values by practice and region) quarterly.
- **Directory rankings** (Chambers-style bands 1–6 per practice and region, and named individuals' bands), each October from a **submission** (March–April: the CMO's area or the player picks matters to showcase and referees to name; a weak submission loses bands), reputation, key matters, and individual stars. Bands raise appeal (§7.1) and associate recruiting.
- **Best places to work** (associate surveys): morale, hours, pay, training; affects campus appeal.

## 13. Legal technology and AI

ADR PT-0011. Task mixes, era strength, adoption, client expectations and training.

| Era (`legal_eras.yaml`) | Window | Exposed tasks | Notes |
| --- | --- | --- | --- |
| E-discovery platforms | from 2005 | review | firms buy or outsource |
| Offshore review and outsourcing | from 2008 | review, diligence | cost cut; associates idle; a client demand after 2009 |
| Technology-assisted review accepted by courts | 2012 *(dossier)* | review | review hours fall 30–50% for adopters |
| Contract analysis tools | from 2016 | diligence, drafting | |
| Generative AI | from December 2022 (firm-wide tools from 2023) | research, drafting, diligence, review | the great shock: era strength rises to 0.5 by 2026, then seeded |
| Agentic tools | from 2025, seeded windows after | management, negotiation (partly), advice (partly) | strength seeded 0.6–0.8 by 2032 |

**Adoption** (0–1) rises with investment (cost per lawyer and platform), training hours, the CKO's score, and **partner buy-in** (an average of partners' adaptability and technology skill; a vote-like threshold for firm-wide rollout). **Efficiency** = 1 − exposure × strength × adoption per task.

**The firm's choices** after 2023: keep hourly (revenue falls on exposed tasks, realisation drops as clients refuse to pay for "AI-able" hours); move to fixed fees (capture margin, but price risk); reshape the pyramid (hire fewer juniors, more legal technologists and senior associates: the diamond); invest in training to keep the partner pipeline; build **products** (fixed-price, AI-backed offerings for routine work, from stage 3). Clients, rivals and ALSPs move too; the Big Four's legal arms gain where ABS rules allow.

## 14. History and eras

| Year | What the game models *(dossier verifies)* |
| --- | --- |
| 2005–2007 | boom: M&A and PE records; lateral wars; rate rises 6–8% a year; salary scale to $160k |
| 2007 | Dewey & LeBoeuf merger; Slater & Gordon lists in Australia; UK Legal Services Act |
| 2008 | crisis: Lehman (September); deals collapse; Heller Ehrman dissolves; layoffs and deferred start dates; restructuring booms |
| 2009 | demand trough for transactional work; rates frozen; clients demand discounts and alternative fees; associate classes deferred |
| 2010 | Dodd-Frank (regulatory surge); the Hogan Lovells merger; ABS rules drafted in England |
| 2011–2012 | Howrey (2011) and Dewey & LeBoeuf (May 2012) collapse; first English ABS licences; court-accepted TAR |
| 2013–2015 | Dentons formed (2013) and joins Dacheng (2015); the first UK law firm listing (2015) |
| 2016–2019 | salary scale to $180k–$190k; Brexit referendum (2016); GDPR (2018); the US tax reform (2017); tech M&A |
| 2020 | pandemic: courts close, remote work, a brief demand shock then a surge; Utah sandbox; Arizona's ABS order |
| 2021 | the deal boom: record M&A and SPACs; special bonuses; salary scale above $200k; Arizona ABS live |
| 2022–2023 | rate shock and deal slowdown; generative AI (late 2022) and firm-wide tools (2023); restructuring rises |
| 2024–2025 | mega-mergers across the Atlantic; agentic tools; policy shocks for large firms in the US *(how far to model: question 17)* |
| 2026–2034 | seeded: cycles with the same statistics as 2005–2025, AI era strength rising, regulation of AI use by courts and bars (seeded windows) |

Macro indices (TST §20.1's layer, CHANGED): base rate, credit spread, **M&A volume**, **PE activity**, **IPO volume**, **default rate**, **litigation index**, **enforcement intensity**, employment, real-estate transactions, **lateral market heat**, **rate inflation** for legal services; each historical to 2025, then seeded AR(1) with regime switches for recessions (TST §20's downturns).

## 15. Events and the LLM

TST ADR-0005 and §16 as built: the director chooses slots, categories and caps; the LLM writes words and chooses among allowed effects; templates cover every category offline; $10 a month budget.

**Categories** (new templates): client (a GC's demand, a panel review, a fee dispute, a big instruction, a client's crisis), matter (a deadline slip, a smoking-gun document, a settlement offer, a deal on the brink, a judge's ruling), people (a star associate's counter-offer, a burnout, a sponsor's departure, an associate's mistake, a partner's conduct complaint, kept to its professional consequences), partnership (a credit dispute, a cabal against the MP, a partner wanting to retire early, a lateral group courting), market (salary-scale moves, a rival's collapse, a rival's merger, a client's bankruptcy), regulatory (a bar complaint, an audit, a trust-account query), press (§12.2), technology (an AI hallucination in a filing: a court sanction; a client's AI mandate).

**Critical events** block Continue (TST §23.1): trial verdicts on key matters, a partner group's resignation letter, a covenant breach, a trust-account shortfall, a malpractice claim above the limit, an MP no-confidence petition, a merger vote.

**Real people** (ADR PT-0013) are never the subject of misconduct, scandal, private-life or health events, and prompts about them are limited to business and procedural matters.

**LLM text kinds** added: matter briefings, pitch letters, partner memos (comp letters in the MP's voice), the year-end letter to partners, rival MP statements, the digest's opening.

## 16. Interface

TST's shell as is: dark, dense, keyboard-first, TanStack tables with saved views, Explain on every number, the command palette, the inbox with tabs and the digest, Holiday.

| Screen | Content |
| --- | --- |
| **Overview** | revenue, PEP, utilisation, realisation, lockup, cash and revolver, confidence whip count, What next |
| **Inbox** | as TST; digest view |
| **People** | the squad: name, level, practice, familiarity grid, hours (YTD against target), utilisation, strain, morale, ratings as ranges, partnership prospects |
| **Person** | profile with skills as ranges, familiarity grid, hours history, matters, relationships, comp, sponsor, career |
| **Recruitment** | campus season, lateral associates, lateral partners (book ranges, conflicts check, guarantee), searches |
| **Matters** | named matters: client, practice, lead, phase, budget against actual, hours, WIP, billed, realisation, risk; a matter page with staffing board (drag people onto a matter; hours per month), phase timeline, bills, events |
| **Clients** | client list: wallet estimate, our share, relationship, relationship partner, practices used, panel status, top matters, GC; client page with relationships, history and cross-sell map |
| **Practices** | per practice: demand trend, our revenue and share, capacity and utilisation, leverage, rates against market, reputation and bands |
| **Business development** | RFPs and panel reviews, pitches, cross-sell introductions, events, directory submissions |
| **Finance** | P&L (accrual and cash views), balance sheet, cash flow, WIP and receivables ageing, lockup, practice and office P&L, capital accounts, draws, revolver and covenants |
| **Partnership** | equity and income partners: points, comp, contribution (origination, working, hours), market value band, confidence; the agreement; votes (open, upcoming, history); comp season (December) |
| **Org** | practice groups, offices, the executive committee, seats |
| **Automation** | TST §40.8 |
| **Offices** | cities, leases, headcount, local market, office P&L |
| **Market** | rival firms, rankings, league tables, legal news, macro strip |
| **Rival firm** | as TST's rival page, with its notable lawyers |
| **Courts** | courts, judges (procedural traits), our record before each judge, forum choices |
| **Risk and ethics** | conflicts log, waivers, claims, insurance, disciplinary cases, trust accounts |
| **Technology** | eras, adoption by task, investment, training, pricing models |
| **Founder** | the founding partner's life: stress, persona, personal account, family, legacy |
| **History**, **Hall of Fame**, **Settings**, **Saves**, **Guide** | as TST |

## 17. Balance and tuning

See `docs/balance-targets.md` for v1's targets and strategies; TST's runner and printed-target discipline (`known_misses`, nightly and weekly suites) are adopted unchanged. Headline targets: do-nothing fails; no strategy wins more than 60% of seeds; associate attrition 15–25% a year; realisation and collection within real bands; the 2008 crisis hurts transactional firms and helps restructuring; the exodus spiral is survivable when seen early; rival history pinned within ±15% to 2025.

## 18. Scope by release

| Release | Contents |
| --- | --- |
| **v1: playable core (2005–2015 in one country)** | US, one home city; people, hiring (campus, laterals), org and practice groups; 10 practice areas; clients and matters (two tiers, conflicts, billing models hourly, capped, fixed, contingency); partnership economics (lockstep, modified, EWYK), capital, draws, revolver; up-or-out and the December vote; MP confidence and elections; 40 real rivals and generated firms with utility AI and poaching; events and LLM; macro history 2005–2015; balance runner; Holiday; History |
| **v2: depth** | seats, authority, pitches, automation everywhere and the digest; all 20 practices; offices in US cities and London; bar admissions; history to 2025 then seeded to 2034; mergers and the verein; legal tech and AI eras; malpractice, insurance, discipline, trust accounts; rankings, directories and press; the founding partner's life, family and succession |
| **v3: the world** | Asia, Europe and the Gulf with local rules; ABS entities, outside capital and listing where allowed; Big Four and ALSPs as rivals; litigation funding; a 2010 scenario pack; dynasty mode (a second 30 years) |

## 19. Ideas for expanding the design

1. **The alumni engine.** Make the firm's alumni network a first-class asset: an Alumni screen, alumni events, a tracker of where former associates are GCs. Up-or-out done well becomes the best BD channel in the game. Cheap to build on §7.3.
2. **Trial weeks.** Revive TST's deferred weekly sub-turns for jury trials of key matters: four weekly decisions (witness order, cross-examination strategy, settlement windows, a juror problem), with the lead partner's hidden big-moments trait at last mattering visibly.
3. **The revolving door.** Partners leave for government (DOJ, SEC, the White House Counsel's office, the bench) and return years later with clout in regulatory and white-collar work; the founder may end the game appointed a judge (an alternative retirement with a large legacy bonus).
4. **Directory season as a mini-game.** The March submission as a short drafting choice: which five matters, which referees (each referee is a client relationship spent), with a visible band result in October.
5. **Litigation finance.** From about 2010, funders (Burford-style) as counterparties who fund contingency cases for a share, or monetise a firm's portfolio; a new capital source outside ABS rules.
6. **Secondments.** Lend associates to key clients for 6 months: lost billable hours, large relationship and alumni gains, a poaching risk.
7. **Client crises.** A key client hit by a scandal sends a burst of investigations work, then a GC change that reopens the panel.
8. **Name on the door.** A naming decision at mergers (whose name survives) that matters to partners' egos and the founder's legacy.
9. **Partners' personal finances.** Lifestyle creep and capital loans make some partners dependent on high draws, so a PEP dip makes them flight risks sooner; visible as a range on the Partnership screen.
10. **Associate unionisation or walkout events** in the 2030s (seeded), a modern twist on morale.
11. **A London start** (v2) with SRA rules, trainees and NQs, lockstep culture and the ABS route: a second campaign with a different texture.
12. **Cross-game link (later):** a shared world seed where Tech Startup Tycoon's companies are Partner Track's clients. Out of scope for both v1s, but `sim-core`'s design should not preclude it.

## 20. Open questions

See `docs/questions.md` for the questions with proposed defaults.
