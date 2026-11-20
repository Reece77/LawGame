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
      ]) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
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
  | { kind: 'forum'; court: string };

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
