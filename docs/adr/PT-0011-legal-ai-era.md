# ADR PT-0011: Legal technology and AI act on tasks, not on products

- Status: **Accepted** (Reece, 2026-11-17)
- Date: 2026-11-17
- Pattern from: TST §21 (eras) and §27.3 (first-mover window)

## Context

A law firm does not sell technology; technology changes how many hours a task takes. That attacks the hourly model, the pyramid and junior training at once.

## Decision

1. **Every matter's work is a task mix** (by practice and matter kind): `review` (documents, discovery), `diligence`, `research`, `drafting`, `negotiation`, `advocacy`, `advice`, `management`. Each task has a default level mix (who does it) and an **AI exposure** 0–1.
2. **Legal-tech eras** (`legal_eras.yaml`), dated to 2025 then seeded windows: e-discovery platforms (2005–), offshore review and legal process outsourcing (2008–), court-accepted technology-assisted review (2012), contract-analysis tools (2016–), generative AI (December 2022 onward; firm-wide tools from 2023), agentic tools (2025–, seeded thereafter).
3. **A firm's efficiency on a task** = 1 − exposure × era strength × the firm's **adoption** (0–1: investment, training, partner buy-in, knowledge assets). Hours needed = base hours × efficiency, by task.
4. **Client expectations** follow the market's average adoption with a lag: clients' willingness to pay for exposed tasks (realisation on hourly bills for those tasks) falls as the market adopts. A firm that adopts but bills hourly loses revenue on exposed tasks; a firm that prices fixed fees captures the saving as margin; a firm that never adopts loses realisation and RFPs.
5. **Training.** Hours that AI removes are often juniors' learning hours (ADR PT-0006 §4). A firm can buy back learning with training programmes (non-billable hours, cost) or accept slower associate growth.
6. **AI investment** is an action (capex and subscriptions to 6100; seeded vendor quality); the CIO or Chief Knowledge Officer area owns it under automation.

## Consequences

- From 2023 the game's central strategic question becomes pricing and the shape of the firm (pyramid to diamond), which is the profession's real question.
