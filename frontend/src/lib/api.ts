// Server-state hooks over the generated client (ADR-0009). No game logic here.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
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

function unwrap<T>(result: { data?: T; error?: unknown }): T {
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
      for (const key of ['people', 'recruitment', 'inbox', 'payroll']) {
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
