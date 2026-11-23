// Server-state hooks over the generated client (ADR-0009). No game logic here.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import { api, type Schemas } from '../api/client';

export type Game = Schemas['GameOut'];
export type SaveSummary = Schemas['SaveOut'];
export type Meta = Schemas['MetaOut'];
export type NewGameBody = Schemas['NewGameIn'];
export type PersonRow = Schemas['PersonRowOut'];
export type PersonProfile = Schemas['PersonOut'];

export class ApiError extends Error {
  code: string;

  constructor(code: string, message: string) {
    super(message);
    this.code = code;
  }
}

export function unwrap<T>(result: { data?: T; error?: unknown }): T {
  if (result.error !== undefined || result.data === undefined) {
    const body = (result.error ?? {}) as { code?: string; message?: string };
    throw new ApiError(body.code ?? 'error', body.message ?? 'The request failed');
  }
  return result.data;
}

export const useMeta = () =>
  useQuery({ queryKey: ['meta'], queryFn: async () => unwrap(await api.GET('/api/meta')) });

export const useSaves = () =>
  useQuery({ queryKey: ['saves'], queryFn: async () => unwrap(await api.GET('/api/saves')) });

export const useGame = (slug: string) =>
  useQuery({
    queryKey: ['game', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/game', { params: { path: { slug } } })),
  });

// Refetched after every Continue (the advance mutation invalidates ['people', slug]).
export const usePeople = (slug: string) =>
  useQuery({
    queryKey: ['people', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/people', { params: { path: { slug } } })),
  });

export const usePerson = (slug: string, personId: number) =>
  useQuery({
    queryKey: ['people', slug, personId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/people/{person_id}', {
          params: { path: { slug, person_id: personId } },
        }),
      ),
  });

export function useNewGame() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: NewGameBody) => unwrap(await api.POST('/api/saves', { body })),
    onSuccess: () => client.invalidateQueries({ queryKey: ['saves'] }),
  });
}

export function useAdvance(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.POST('/api/saves/{slug}/advance', { params: { path: { slug } } })),
    onSuccess: (game) => {
      client.setQueryData(['game', slug], game);
      for (const key of [
        'people',
        'recruitment',
        'inbox',
        'payroll',
        'org',
        'finance',
        'matters',
        'clients',
        'practices',
        'explain',
        'events',
        'texts',
        'partnership',
        'policies',
        'history',
        'guidance',
        'founder', // PT-M17
        'family',
        'rankings', // PT-M16
        'press',
      ]) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

// --- PT-M7a: Holiday and continue-until -------------------------------------------------------

export type HolidayBody = Schemas['HolidayIn'];
export type HolidayResult = Schemas['HolidayOut'];

export function useHoliday(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: HolidayBody) =>
      unwrap(await api.POST('/api/saves/{slug}/holiday', { params: { path: { slug } }, body })),
    onSuccess: () => {
      void client.invalidateQueries({ predicate: (q) => q.queryKey.includes(slug) });
    },
  });
}

// --- PT-M7a: firm policies (pro bono credit, the yearly rate rise) -------------------------

export type FirmPolicies = Schemas['FirmPoliciesOut'];

export const useFirmPolicies = (slug: string) =>
  useQuery({
    queryKey: ['policies', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/policies', { params: { path: { slug } } })),
  });

export type PolicyAction =
  | { kind: 'pro_bono'; hours: number }
  | { kind: 'rates'; riseBp: number | null }
  | { kind: 'hours'; hours: number | null };

async function putPolicy(slug: string, a: PolicyAction) {
  const params = { path: { slug } };
  switch (a.kind) {
    case 'pro_bono':
      return unwrap(
        await api.PUT('/api/saves/{slug}/policies/pro-bono', { params, body: { hours: a.hours } }),
      );
    case 'rates':
      return unwrap(
        await api.PUT('/api/saves/{slug}/policies/rates', { params, body: { rise_bp: a.riseBp } }),
      );
    case 'hours': // PT-M7b: the firm's billable target
      return unwrap(
        await api.PUT('/api/saves/{slug}/policies/hours', { params, body: { hours: a.hours } }),
      );
  }
}

export function usePolicyAction(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (a: PolicyAction) => putPolicy(slug, a),
    onSuccess: (policies) => {
      client.setQueryData(['policies', slug], policies);
      void client.invalidateQueries({ queryKey: ['game', slug] });
    },
  });
}

// --- PT-M1b: recruitment, inbox, payroll ------------------------------------------------------

export type Recruitment = Schemas['RecruitmentOut'];
export type Candidate = Schemas['CandidateOut'];
export type OpenSearchBody = Schemas['OpenSearchIn'];
export type PayPolicyBody = Schemas['PayPolicyIn'];
export type InboxItem = Schemas['InboxItemOut'];
export type Payroll = Schemas['PayrollOut'];

export const useRecruitment = (slug: string) =>
  useQuery({
    queryKey: ['recruitment', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/recruitment', { params: { path: { slug } } })),
  });

export const useInbox = (slug: string) =>
  useQuery({
    queryKey: ['inbox', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/inbox', { params: { path: { slug } } })),
  });

export const usePayroll = (slug: string) =>
  useQuery({
    queryKey: ['payroll', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/payroll', { params: { path: { slug } } })),
  });

export const useOfferPreview = (slug: string, candidateId: number | null, salaryCents: number) =>
  useQuery({
    queryKey: ['offer-preview', slug, candidateId, salaryCents],
    enabled: candidateId !== null && salaryCents > 0,
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/recruitment/candidates/{candidate_id}/offer-preview', {
          params: {
            path: { slug, candidate_id: candidateId ?? 0 },
            query: { salary_cents: salaryCents },
          },
        }),
      ),
  });

/** A recruitment action: the server applies it at once and returns the new view. */
export type RecruitmentAction =
  | { kind: 'open'; body: OpenSearchBody }
  | { kind: 'close' | 'scout'; searchId: number }
  | { kind: 'interview' | 'reference'; candidateId: number }
  | { kind: 'offer'; candidateId: number; salaryCents: number }
  | { kind: 'withdraw'; offerId: number }
  | { kind: 'pay'; body: PayPolicyBody };

async function runRecruitment(slug: string, a: RecruitmentAction): Promise<Recruitment> {
  const path = { slug };
  switch (a.kind) {
    case 'open':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/searches', {
          params: { path },
          body: a.body,
        }),
      );
    case 'close':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/searches/{search_id}/close', {
          params: { path: { slug, search_id: a.searchId } },
        }),
      );
    case 'scout':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/searches/{search_id}/scout', {
          params: { path: { slug, search_id: a.searchId } },
        }),
      );
    case 'interview':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/candidates/{candidate_id}/interview', {
          params: { path: { slug, candidate_id: a.candidateId } },
        }),
      );
    case 'reference':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/candidates/{candidate_id}/reference', {
          params: { path: { slug, candidate_id: a.candidateId } },
        }),
      );
    case 'offer':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/offers', {
          params: { path },
          body: { candidate_id: a.candidateId, salary_cents: a.salaryCents },
        }),
      );
    case 'withdraw':
      return unwrap(
        await api.POST('/api/saves/{slug}/recruitment/offers/{offer_id}/withdraw', {
          params: { path: { slug, offer_id: a.offerId } },
        }),
      );
    case 'pay':
      return unwrap(
        await api.PUT('/api/saves/{slug}/recruitment/pay-policy', {
          params: { path },
          body: a.body,
        }),
      );
  }
}

export function useRecruitmentAction(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: RecruitmentAction) => runRecruitment(slug, a),
    onSuccess: (view) => {
      client.setQueryData(['recruitment', slug], view);
      void client.invalidateQueries({ queryKey: ['payroll', slug] });
      void client.invalidateQueries({ queryKey: ['inbox', slug] });
      void client.invalidateQueries({ queryKey: ['game', slug] });
    },
  });
}

export function useMarkInboxRead(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async () =>
      unwrap(await api.POST('/api/saves/{slug}/inbox/read', { params: { path: { slug } } })),
    onSuccess: (items) => client.setQueryData(['inbox', slug], items),
  });
}

// --- PT-M3b: finance (KPIs, statements, ageing, bills and disputes, matter money) -------------

export type Finance = Schemas['FinanceOut'];
export type Bill = Schemas['BillOut'];
export type MatterMoney = Schemas['MatterMoneyOut'];
export type DisputeChoice = Schemas['DisputeIn']['choice'];

export const useFinance = (slug: string) =>
  useQuery({
    queryKey: ['finance', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/finance', { params: { path: { slug } } })),
  });

export const useBills = (slug: string) =>
  useQuery({
    queryKey: ['finance', slug, 'bills'],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/finance/bills', { params: { path: { slug } } })),
  });

/** Every bill the firm holds (open, and closed since last month), for a matter's page. */
export const useRecentBills = (slug: string) =>
  useQuery({
    queryKey: ['finance', slug, 'bills', 'recent'],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/finance/bills', {
          params: { path: { slug }, query: { status: 'recent' } },
        }),
      ),
  });

/** Each matter's money (PT-M3b) by matter id, for the Matters screens. */
export function useMatterMoneyById(slug: string): Map<number, MatterMoney> {
  const data = useMatterMoney(slug).data;
  return useMemo(() => new Map((data ?? []).map((m) => [m.matter_id, m])), [data]);
}

export const useMatterMoney = (slug: string) =>
  useQuery({
    queryKey: ['finance', slug, 'matters'],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/finance/matters', { params: { path: { slug } } })),
  });

export function useRespondDispute(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (a: { billId: number; choice: DisputeChoice }) =>
      unwrap(
        await api.POST('/api/saves/{slug}/finance/bills/{bill_id}/dispute', {
          params: { path: { slug, bill_id: a.billId } },
          body: { choice: a.choice },
        }),
      ),
    onSuccess: (bills) => {
      client.setQueryData(['finance', slug, 'bills'], bills);
      void client.invalidateQueries({ queryKey: ['finance', slug] });
    },
  });
}

export function useWriteDown(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (a: { matterId: number; bp: number }) =>
      unwrap(
        await api.POST('/api/saves/{slug}/finance/write-down', {
          params: { path: { slug } },
          body: { matter_id: a.matterId, bp: a.bp },
        }),
      ),
    onSuccess: (rows) => client.setQueryData(['finance', slug, 'matters'], rows),
  });
}

// --- PT-M3c: matters, clients and practices screens ---------------------------------------

export type MatterRow = Schemas['MatterRowOut'];
export type MatterDetail = Schemas['MatterOut'];
export type StaffingBoard = Schemas['StaffingBoardOut'];
export type BoardPerson = Schemas['BoardPersonOut'];
export type ClientRow = Schemas['ClientRowOut'];
export type ClientDetail = Schemas['ClientOut'];
export type PracticeScreenRow = Schemas['PracticeScreenOut'];
export type ExplainData = Schemas['ExplainOut'];
export type ExplainMetric = ExplainData['metric'];
export type MatterStatusFilter = 'open' | 'conflicted' | 'closed' | 'declined' | 'all';

export const useMatters = (slug: string, status: MatterStatusFilter = 'open') =>
  useQuery({
    queryKey: ['matters', slug, 'list', status],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/matters', {
          params: { path: { slug }, query: { status } },
        }),
      ),
  });

export const useMatter = (slug: string, matterId: number) =>
  useQuery({
    queryKey: ['matters', slug, matterId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/matters/{matter_id}', {
          params: { path: { slug, matter_id: matterId } },
        }),
      ),
  });

export const useStaffingBoard = (slug: string, matterId: number) =>
  useQuery({
    queryKey: ['matters', slug, matterId, 'board'],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/matters/{matter_id}/board', {
          params: { path: { slug, matter_id: matterId } },
        }),
      ),
  });

/** A matter action: the engine applies it at once and returns the fresh matter. */
export type MatterAction =
  | { kind: 'assign'; personId: number; hours: number }
  | { kind: 'hours'; personId: number; hours: number }
  | { kind: 'remove'; personId: number }
  | { kind: 'lead'; personId: number }
  | { kind: 'default' }
  | { kind: 'waiver'; advance: boolean }
  | { kind: 'settlement'; accept: boolean }
  | { kind: 'forum'; court: string }
  | { kind: 'assess' };

async function runMatter(slug: string, id: number, a: MatterAction): Promise<MatterDetail> {
  const path = { slug, matter_id: id };
  switch (a.kind) {
    case 'assign':
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/team', {
          params: { path },
          body: { person_id: a.personId, hours: a.hours },
        }),
      );
    case 'hours':
      return unwrap(
        await api.PUT('/api/saves/{slug}/matters/{matter_id}/team/{person_id}', {
          params: { path: { ...path, person_id: a.personId } },
          body: { hours: a.hours },
        }),
      );
    case 'remove':
      return unwrap(
        await api.DELETE('/api/saves/{slug}/matters/{matter_id}/team/{person_id}', {
          params: { path: { ...path, person_id: a.personId } },
        }),
      );
    case 'lead':
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/lead', {
          params: { path },
          body: { person_id: a.personId },
        }),
      );
    case 'default':
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/default-staffing', {
          params: { path },
        }),
      );
    case 'waiver':
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/waiver', {
          params: { path },
          body: { advance: a.advance },
        }),
      );
    case 'settlement':
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/settlement', {
          params: { path },
          body: { accept: a.accept },
        }),
      );
    case 'forum':
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/forum', {
          params: { path },
          body: { court: a.court },
        }),
      );
    case 'assess': // PT-M7a: early case assessment
      return unwrap(
        await api.POST('/api/saves/{slug}/matters/{matter_id}/assessment', { params: { path } }),
      );
  }
}

export function useMatterAction(slug: string, matterId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: MatterAction) => runMatter(slug, matterId, a),
    onSuccess: (matter) => {
      client.setQueryData(['matters', slug, matterId], matter);
      for (const key of [
        'matters',
        'clients',
        'practices',
        'explain',
        'game',
        'inbox',
        'finance',
      ]) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const useClients = (slug: string) =>
  useQuery({
    queryKey: ['clients', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/clients', { params: { path: { slug } } })),
  });

export const useClient = (slug: string, clientId: number) =>
  useQuery({
    queryKey: ['clients', slug, clientId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/clients/{client_id}', {
          params: { path: { slug, client_id: clientId } },
        }),
      ),
  });

export function useIntroduce(slug: string, clientId: number) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: { colleague_id: number; practice: string }) =>
      unwrap(
        await api.POST('/api/saves/{slug}/clients/{client_id}/introduce', {
          params: { path: { slug, client_id: clientId } },
          body,
        }),
      ),
    onSuccess: (view) => {
      client.setQueryData(['clients', slug, clientId], view);
      for (const key of ['clients', 'game', 'inbox']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const usePracticesScreen = (slug: string) =>
  useQuery({
    queryKey: ['practices', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/practices/screen', { params: { path: { slug } } })),
  });

export const useExplain = (
  slug: string,
  metric: ExplainMetric,
  entity: string | null,
  enabled: boolean,
) =>
  useQuery({
    queryKey: ['explain', slug, metric, entity],
    enabled,
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/explain/{metric}', {
          params: { path: { slug, metric }, query: entity === null ? {} : { entity } },
        }),
      ),
  });

export const usePracticeMarket = (slug: string) =>
  useQuery({
    queryKey: ['practices', slug, 'market'],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/practices', { params: { path: { slug } } })),
  });

/** Practice key -> label, for display (from the practices endpoint). */
export function usePracticeLabels(slug: string): (key: string) => string {
  const data = usePracticeMarket(slug).data;
  return useMemo(() => {
    const labels = new Map((data ?? []).map((p) => [p.key, p.label]));
    return (key: string) => labels.get(key) ?? key;
  }, [data]);
}

// --- PT-M6: events, read-only texts, the LLM settings and meter ------------------------------

export type GameEvent = Schemas['EventOut'];
export type TextItem = Schemas['TextOut'];
export type LlmSettings = Schemas['LLMSettingsOut'];
export type LlmSettingsBody = Schemas['LLMSettingsIn'];
export type LlmMeter = Schemas['MeterOut'];

export const useEvents = (slug: string) =>
  useQuery({
    queryKey: ['events', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/events', { params: { path: { slug } } })),
  });

export const useEvent = (slug: string, eventId: number | null) =>
  useQuery({
    queryKey: ['events', slug, eventId],
    enabled: eventId !== null,
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/events/{event_id}', {
          params: { path: { slug, event_id: eventId ?? 0 } },
        }),
      ),
  });

export function useChooseEvent(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ eventId, choice }: { eventId: number; choice: string }) =>
      unwrap(
        await api.POST('/api/saves/{slug}/events/{event_id}/choose', {
          params: { path: { slug, event_id: eventId } },
          body: { choice },
        }),
      ),
    onSuccess: () => {
      for (const key of [
        'events',
        'game',
        'people',
        'inbox',
        'payroll',
        'recruitment',
        'org',
        'finance',
      ]) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const useTexts = (slug: string, kind: TextItem['kind']) =>
  useQuery({
    queryKey: ['texts', slug, kind],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/texts', { params: { path: { slug }, query: { kind } } }),
      ),
  });

export const useLlmSettings = () =>
  useQuery({
    queryKey: ['llm-settings'],
    queryFn: async () => unwrap(await api.GET('/api/llm/settings')),
  });

export const useLlmMeter = () =>
  useQuery({
    queryKey: ['llm-meter'],
    queryFn: async () => unwrap(await api.GET('/api/llm/meter')),
  });

export function useSetLlmSettings() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: LlmSettingsBody) =>
      unwrap(await api.PUT('/api/llm/settings', { body })),
    onSuccess: (settings) => {
      client.setQueryData(['llm-settings'], settings);
      void client.invalidateQueries({ queryKey: ['llm-meter'] });
    },
  });
}

// --- PT-M5: the market (rival firms, RFPs, approaches) ---------------------------------------

export type MarketView = Schemas['MarketOut'];
export type RivalRow = Schemas['RivalRowOut'];
export type RivalDetail = Schemas['RivalOut'];
export type Rfp = Schemas['RfpOut'];
export type RivalApproach = Schemas['RivalApproachOut'];
export type MarketNews = Schemas['NewsOut'];
export type KeyPerson = Schemas['KeyPersonOut'];

export const useMarket = (slug: string) =>
  useQuery({
    queryKey: ['market', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/market', { params: { path: { slug } } })),
  });

export const useRival = (slug: string, firmId: number) =>
  useQuery({
    queryKey: ['market', slug, 'rival', firmId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/rivals/{firm_id}', {
          params: { path: { slug, firm_id: firmId } },
        }),
      ),
  });

function useMarketMutation<T>(slug: string, run: (body: T) => Promise<MarketView>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: run,
    onSuccess: (view) => {
      client.setQueryData(['market', slug], view);
      for (const key of ['market', 'game', 'inbox', 'recruitment', 'people']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const usePitchRfp = (slug: string) =>
  useMarketMutation(slug, async (body: { rfp_id: number; team: number[]; claims: string[] }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/rfps/{rfp_id}/pitch', {
        params: { path: { slug, rfp_id: body.rfp_id } },
        body: { team: body.team, claims: body.claims },
      }),
    ),
  );

export const useApproachRival = (slug: string) =>
  useMarketMutation(slug, async (body: { firm_id: number; practice: string | null }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/rivals/{firm_id}/approach', {
        params: { path: { slug, firm_id: body.firm_id } },
        body: { practice: body.practice },
      }),
    ),
  );

export const useApproachFreeAgents = (slug: string) =>
  useMarketMutation(slug, async () =>
    unwrap(
      await api.POST('/api/saves/{slug}/market/free-agents/approach', {
        params: { path: { slug } },
      }),
    ),
  );

export const useCounterApproach = (slug: string) =>
  useMarketMutation(slug, async (approachId: number) =>
    unwrap(
      await api.POST('/api/saves/{slug}/approaches/{approach_id}/counter', {
        params: { path: { slug, approach_id: approachId } },
      }),
    ),
  );
// --- PT-M4: the partnership ------------------------------------------------------------------

export type Partnership = Schemas['PartnershipOut'];
export type PartnerRow = Schemas['PartnerOut'];
export type VoteRow = Schemas['VoteOut'];
export type CandidateRow = Schemas['PartnerCandidateOut'];
export type ApproachRow = Schemas['ApproachOut'];
export type LateralRow = Schemas['LateralOut'];
export type Track = Schemas['ProposeIn']['track'];

export const usePartnership = (slug: string) =>
  useQuery({
    queryKey: ['partnership', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/partnership', { params: { path: { slug } } })),
  });

// Every partnership action returns the whole screen's data (ADR-0014: one action each).
export type PartnershipAction =
  | { kind: 'terms'; term: string; value: string | number | boolean }
  | { kind: 'capital_call'; amount_cents: number }
  | { kind: 'propose'; person_id: number; track: Track; sponsor_id?: number | null }
  | { kind: 'lobby'; person_id: number }
  | { kind: 'draws'; suspended: boolean }
  | { kind: 'comp_round'; person_id: number; gate_steps: number; adjust_bp: number }
  | { kind: 'lateral_search'; practice: string }
  | { kind: 'diligence'; person_id: number }
  | {
      kind: 'lateral_offer';
      person_id: number;
      comp_cents: number;
      guarantee_years: number;
      equity: boolean;
    }
  | { kind: 'counter'; approach_id: number; comp_cents: number; guarantee_years: number }
  | { kind: 'repay'; amount_cents: number }
  | { kind: 'withdraw'; vote_id: number }
  | { kind: 'election'; choice: 'stay' | 'hand_over'; successor_id?: number | null };

async function runPartnershipAction(slug: string, a: PartnershipAction): Promise<Partnership> {
  const path = { slug };
  switch (a.kind) {
    case 'terms':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/terms', {
          params: { path },
          body: { term: a.term, value: a.value },
        }),
      );
    case 'capital_call':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/capital-call', {
          params: { path },
          body: { amount_cents: a.amount_cents },
        }),
      );
    case 'propose':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/propose', {
          params: { path },
          body: { person_id: a.person_id, track: a.track, sponsor_id: a.sponsor_id ?? null },
        }),
      );
    case 'lobby':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/lobby', {
          params: { path },
          body: { person_id: a.person_id },
        }),
      );
    case 'draws':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/draws', {
          params: { path },
          body: { suspended: a.suspended },
        }),
      );
    case 'comp_round':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/comp-round', {
          params: { path },
          body: { person_id: a.person_id, gate_steps: a.gate_steps, adjust_bp: a.adjust_bp },
        }),
      );
    case 'lateral_search':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/laterals/search', {
          params: { path },
          body: { practice: a.practice },
        }),
      );
    case 'diligence':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/laterals/{person_id}/diligence', {
          params: { path: { slug, person_id: a.person_id } },
        }),
      );
    case 'lateral_offer':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/laterals/{person_id}/offer', {
          params: { path: { slug, person_id: a.person_id } },
          body: { comp_cents: a.comp_cents, guarantee_years: a.guarantee_years, equity: a.equity },
        }),
      );
    case 'counter':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/approaches/{approach_id}/counter', {
          params: { path: { slug, approach_id: a.approach_id } },
          body: { comp_cents: a.comp_cents, guarantee_years: a.guarantee_years },
        }),
      );
    case 'repay':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/revolver/repay', {
          params: { path },
          body: { amount_cents: a.amount_cents },
        }),
      );
    case 'withdraw':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/votes/{vote_id}/withdraw', {
          params: { path: { slug, vote_id: a.vote_id } },
        }),
      );
    case 'election':
      return unwrap(
        await api.POST('/api/saves/{slug}/partnership/election', {
          params: { path },
          body: { choice: a.choice, successor_id: a.successor_id ?? null },
        }),
      );
  }
}

export function usePartnershipAction(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: PartnershipAction) => runPartnershipAction(slug, a),
    onSuccess: (data) => {
      client.setQueryData(['partnership', slug], data);
      void client.invalidateQueries({ queryKey: ['game', slug] });
      void client.invalidateQueries({ queryKey: ['finance', slug] });
    },
  });
}

// --- PT-M7: History and the Overview's guidance --------------------------------------------

export type HistoryData = Schemas['HistoryOut'];
export type Guidance = Schemas['GuidanceOut'];

export const useHistory = (slug: string) =>
  useQuery({
    queryKey: ['history', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/history', { params: { path: { slug } } })),
  });

export const useGuidance = (slug: string) =>
  useQuery({
    queryKey: ['guidance', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/guidance', { params: { path: { slug } } })),
  });

// PT-M7: a practice save (pt-2008); a 409 means it was made before and simply opens
export function usePracticeSave() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (key: string) =>
      unwrap(await api.POST('/api/practice/{key}', { params: { path: { key } } })),
    onSettled: () => {
      void client.invalidateQueries({ queryKey: ['saves'] });
    },
  });
}

// --- PT-M17: the Founder and Family screens and the succession flow -------------------------

export type Founder = Schemas['FounderOut'];
export type SuccessorCandidate = Schemas['SuccessorCandidateOut'];
export type Family = Schemas['FamilyOut'];
export type FamilyMember = Schemas['MemberOut'];

export const useFounder = (slug: string) =>
  useQuery({
    queryKey: ['founder', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/founder', { params: { path: { slug } } })),
  });

export const useFamily = (slug: string) =>
  useQuery({
    queryKey: ['family', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/family', { params: { path: { slug } } })),
  });

// Every founder action returns the Founder screen's data (ADR-0014: one action each).
export type FounderAction =
  | { kind: 'foundation'; cause: string; name?: string }
  | { kind: 'gift'; amount_cents: number }
  | { kind: 'invest'; amount_cents: number }
  | { kind: 'family_office'; mandate: string; amount_cents: number }
  | { kind: 'committee'; on: boolean }
  | { kind: 'spend'; monthly_cents: number }
  | { kind: 'stand' }
  | { kind: 'plan'; person_id: number | null }
  | { kind: 'name'; person_id: number }
  | { kind: 'retirement_age'; age: number }
  | { kind: 'annuities'; share_bp: number; years: number };

async function runFounderAction(slug: string, a: FounderAction): Promise<Founder> {
  const params = { path: { slug } };
  switch (a.kind) {
    case 'foundation':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/foundation', {
          params,
          body: { cause: a.cause, name: a.name ?? '' },
        }),
      );
    case 'gift':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/foundation/gift', {
          params,
          body: { amount_cents: a.amount_cents },
        }),
      );
    case 'invest':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/invest', {
          params,
          body: { amount_cents: a.amount_cents },
        }),
      );
    case 'family_office':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/family-office', {
          params,
          body: { mandate: a.mandate, amount_cents: a.amount_cents },
        }),
      );
    case 'committee':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/bar/committee', { params, body: { on: a.on } }),
      );
    case 'spend':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/bar/spend', {
          params,
          body: { monthly_cents: a.monthly_cents },
        }),
      );
    case 'stand':
      return unwrap(await api.POST('/api/saves/{slug}/founder/bar/stand', { params }));
    case 'plan':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/succession/plan', {
          params,
          body: { person_id: a.person_id },
        }),
      );
    case 'name':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/succession/name', {
          params,
          body: { person_id: a.person_id },
        }),
      );
    case 'retirement_age':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/retirement-age', {
          params,
          body: { age: a.age },
        }),
      );
    case 'annuities':
      return unwrap(
        await api.POST('/api/saves/{slug}/founder/annuities', {
          params,
          body: { share_bp: a.share_bp, years: a.years },
        }),
      );
  }
}

export function useFounderAction(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: FounderAction) => runFounderAction(slug, a),
    onSuccess: (data) => {
      client.setQueryData(['founder', slug], data);
      void client.invalidateQueries({ queryKey: ['game', slug] });
      void client.invalidateQueries({ queryKey: ['partnership', slug] });
    },
  });
}

export type FamilyAction =
  | { kind: 'time'; energy: number }
  | { kind: 'education'; child_id: number; stage: 'school' | 'law_school'; tier: string }
  | { kind: 'join'; child_id: number }
  | { kind: 'mentor'; child_id: number; on: boolean }
  | { kind: 'gift'; child_id: number; amount_cents: number }
  | { kind: 'trust'; amount_cents: number };

async function runFamilyAction(slug: string, a: FamilyAction): Promise<Family> {
  const params = { path: { slug } };
  switch (a.kind) {
    case 'time':
      return unwrap(
        await api.POST('/api/saves/{slug}/family/time', { params, body: { energy: a.energy } }),
      );
    case 'education':
      return unwrap(
        await api.POST('/api/saves/{slug}/family/education', {
          params,
          body: { child_id: a.child_id, stage: a.stage, tier: a.tier },
        }),
      );
    case 'join':
      return unwrap(
        await api.POST('/api/saves/{slug}/family/join', {
          params,
          body: { child_id: a.child_id },
        }),
      );
    case 'mentor':
      return unwrap(
        await api.POST('/api/saves/{slug}/family/mentor', {
          params,
          body: { child_id: a.child_id, on: a.on },
        }),
      );
    case 'gift':
      return unwrap(
        await api.POST('/api/saves/{slug}/family/gift', {
          params,
          body: { child_id: a.child_id, amount_cents: a.amount_cents },
        }),
      );
    case 'trust':
      return unwrap(
        await api.POST('/api/saves/{slug}/family/trust', {
          params,
          body: { amount_cents: a.amount_cents },
        }),
      );
  }
}

export function useFamilyAction(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (a: FamilyAction) => runFamilyAction(slug, a),
    onSuccess: (data) => {
      client.setQueryData(['family', slug], data);
      void client.invalidateQueries({ queryKey: ['founder', slug] });
      void client.invalidateQueries({ queryKey: ['game', slug] });
      void client.invalidateQueries({ queryKey: ['people', slug] });
    },
  });
}

// --- PT-M16: reputation, press and rankings -------------------------------------------------

export type Rankings = Schemas['RankingsOut'];
export type TableRow = Schemas['TableRowOut'];
export type League = Schemas['LeagueOut'];
export type LeagueRow = Schemas['LeagueRowOut'];
export type PracticeBands = Schemas['PracticeBandsOut'];
export type BandFirm = Schemas['BandFirmOut'];
export type PersonBand = Schemas['PersonBandOut'];
export type PlacesRow = Schemas['PlacesRowOut'];
export type PlayerPlace = Schemas['PlayerPlaceOut'];
export type Submission = Schemas['SubmissionOut'];
export type SubmissionMatter = Schemas['SubmissionMatterOut'];
export type SubmissionReferee = Schemas['SubmissionRefereeOut'];
export type Press = Schemas['PressOut'];
export type PressMoment = Schemas['MomentOut'];
export type PressClaim = Schemas['ClaimOut'];
export type PressStatement = Schemas['ptk__api__standing__StatementOut'];
export type PressFeud = Schemas['FeudOut'];
export type PressCause = Schemas['ptk__api__standing__CauseOut'];
export type AnswerPressBody = Schemas['ptk__api__standing__AnswerIn'];

export const useRankings = (slug: string) =>
  useQuery({
    queryKey: ['rankings', slug],
    queryFn: async () =>
      unwrap(await api.GET('/api/saves/{slug}/rankings', { params: { path: { slug } } })),
  });

export const usePress = (slug: string) =>
  useQuery({
    queryKey: ['press', slug],
    // openapi-fetch widens claim_months' [lo, hi] tuple to number[]; the schema's type is exact.
    queryFn: async (): Promise<Press> =>
      unwrap(await api.GET('/api/saves/{slug}/press', { params: { path: { slug } } })) as Press,
  });

export function useMakeSubmission(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async (body: { matter_ids: number[]; referee_ids: number[] }) =>
      unwrap(
        await api.POST('/api/saves/{slug}/rankings/submission', {
          params: { path: { slug } },
          body,
        }),
      ),
    onSuccess: (data) => {
      client.setQueryData(['rankings', slug], data);
      for (const key of ['game', 'inbox', 'clients', 'founder']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export function useAnswerPress(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({
      momentId,
      body,
    }: {
      momentId: number;
      body: AnswerPressBody;
    }): Promise<Press> =>
      unwrap(
        await api.POST('/api/saves/{slug}/press/{moment_id}/answer', {
          params: { path: { slug, moment_id: momentId } },
          body,
        }),
      ) as Press,
    onSuccess: (data) => {
      client.setQueryData(['press', slug], data);
      for (const key of ['game', 'inbox', 'founder', 'practices']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}
