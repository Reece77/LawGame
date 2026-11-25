// PT-M15: the Risk screen's queries and actions (spec 11.3-11.6). Every number is the API's.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';
import { unwrap } from './api';

export type Risk = Schemas['RiskScreenOut'];
export type RiskClaim = Schemas['MalpracticeClaimOut'];
export type RiskCase = Schemas['CaseOut'];
export type RiskInquiry = Schemas['InquiryOut'];
export type RiskReconciliation = Schemas['ReconciliationOut'];
export type RiskAudit = Schemas['AuditOut'];
export type RiskArbitration = Schemas['ArbitrationOut'];

export const useRisk = (slug: string) =>
  useQuery({
    queryKey: ['risk', slug],
    queryFn: async (): Promise<Risk> =>
      unwrap(await api.GET('/api/saves/{slug}/risk', { params: { path: { slug } } })),
  });

function useRiskAction<B>(slug: string, send: (body: B) => Promise<Risk>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: send,
    onSuccess: (data) => {
      client.setQueryData(['risk', slug], data);
      for (const key of ['game', 'inbox', 'finance', 'guidance']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const useSetPolicyTerms = (slug: string) =>
  useRiskAction(
    slug,
    async (body: {
      insurer?: string | null;
      limit_cents?: number | null;
      deductible_cents?: number | null;
    }) =>
      unwrap(await api.POST('/api/saves/{slug}/risk/terms', { params: { path: { slug } }, body })),
  );

export const useSetSupervision = (slug: string) =>
  useRiskAction(slug, async (body: { supervision: 'standard' | 'lax' }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/risk/supervision', { params: { path: { slug } }, body }),
    ),
  );

export const useRespondClaim = (slug: string) =>
  useRiskAction(slug, async (a: { id: number; choice: string }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/risk/claims/{claim_id}/respond', {
        params: { path: { slug, claim_id: a.id } },
        body: { choice: a.choice },
      }),
    ),
  );

export const useRespondCase = (slug: string) =>
  useRiskAction(slug, async (a: { id: number; choice: string }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/risk/cases/{case_id}/respond', {
        params: { path: { slug, case_id: a.id } },
        body: { choice: a.choice },
      }),
    ),
  );

export const useRespondInquiry = (slug: string) =>
  useRiskAction(slug, async (a: { id: number; choice: string }) =>
    unwrap(
      await api.POST('/api/saves/{slug}/risk/inquiries/{inquiry_id}/respond', {
        params: { path: { slug, inquiry_id: a.id } },
        body: { choice: a.choice },
      }),
    ),
  );
