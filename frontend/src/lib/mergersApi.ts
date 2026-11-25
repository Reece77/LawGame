// PT-M13: the Mergers screen's queries and actions (spec 8.8). Every number is the API's.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';
import { unwrap } from './api';

export type Mergers = Schemas['MergersOut'];
export type MergerTarget = Schemas['MergerTargetOut'];
export type MergerDeal = Schemas['MergerDealOut'];
export type MergerIntegration = Schemas['MergerIntegrationOut'];
export type MergerTermsIn = Schemas['MergerTermsIn'];

export const useMergers = (slug: string) =>
  useQuery({
    queryKey: ['mergers', slug],
    queryFn: async (): Promise<Mergers> =>
      unwrap(await api.GET('/api/saves/{slug}/mergers', { params: { path: { slug } } })),
  });

function useMergersAction<B>(slug: string, send: (body: B) => Promise<Mergers>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: send,
    onSuccess: (data) => {
      client.setQueryData(['mergers', slug], data);
      for (const key of ['game', 'inbox', 'finance', 'partnership']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const useApproachFirm = (slug: string) =>
  useMergersAction(slug, async (body: { rival_key: string; form: 'merger' | 'verein' }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/mergers/approach', { params: { path: { slug } }, body }),
    ),
  );

export const useAnswerApproach = (slug: string) =>
  useMergersAction(slug, async (b: { deal_id: number; accept: boolean }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/mergers/{deal_id}/answer', {
        params: { path: { slug, deal_id: b.deal_id } },
        body: { accept: b.accept },
      }),
    ),
  );

export const useCommissionDiligence = (slug: string) =>
  useMergersAction(slug, async (dealId: number) =>
    unwrap(
      await api.POST('/api/saves/{slug}/mergers/{deal_id}/diligence', {
        params: { path: { slug, deal_id: dealId } },
      }),
    ),
  );

export const usePutTerms = (slug: string) =>
  useMergersAction(slug, async (b: { deal_id: number; terms: MergerTermsIn }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/mergers/{deal_id}/terms', {
        params: { path: { slug, deal_id: b.deal_id } },
        body: b.terms,
      }),
    ),
  );

export const useWalkAway = (slug: string) =>
  useMergersAction(slug, async (dealId: number) =>
    unwrap(
      await api.POST('/api/saves/{slug}/mergers/{deal_id}/walk-away', {
        params: { path: { slug, deal_id: dealId } },
      }),
    ),
  );
