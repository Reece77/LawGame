// Automation server state (PT-M9) over the generated client (ADR-0009): areas, owners,
// limits, proposals, the digest and "Run by". Ported from TST's src/hooks/automation.ts
// @ 80a38079; changed: Partner Track's endpoints (no companies, no plan preview). No game
// logic here: every rule is the engine's, and a refused action comes back as an ApiError.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';
import { unwrap } from './api';

export type Automation = Schemas['AutomationOut'];
export type Area = Schemas['AreaRowOut'];
export type Proposal = Schemas['ProposalOut'];
export type OwnerRecord = Schemas['OwnerRecordOut'];
export type Digest = Schemas['DigestOut'];
export type RunBy = Schemas['RunByOut'];

const path = (slug: string) => ({ params: { path: { slug } } });

export const useAutomation = (slug: string) =>
  useQuery({
    queryKey: ['automation', slug],
    queryFn: async () => unwrap(await api.GET('/api/saves/{slug}/automation', path(slug))),
  });

export const useDigest = (slug: string, turn: number | null) =>
  useQuery({
    queryKey: ['automation-digest', slug, turn],
    enabled: turn !== null,
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/automation/digest/{turn}', {
          params: { path: { slug, turn: turn ?? 0 } },
        }),
      ),
  });

export const useRunBy = (slug: string, area: string, slot = 0) =>
  useQuery({
    queryKey: ['run-by', slug, area, slot],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/automation/run-by/{area}', {
          params: { path: { slug, area }, query: { slot } },
        }),
      ),
  });

export type AutomationCommand =
  | {
      kind: 'give';
      area: string;
      slot: number;
      personId: number;
      limitCents?: number | null;
      monthlyCents?: number | null;
    }
  | { kind: 'take_over'; area: string; slot: number }
  | {
      kind: 'settings';
      area: string;
      slot: number;
      limitCents?: number | null;
      monthlyCents?: number | null;
      priority?: number | null;
      answerEvents?: boolean | null;
      guardrails?: { key: string; value: number }[] | null;
    }
  | { kind: 'answer'; proposalId: number; approve: boolean };

async function send(slug: string, cmd: AutomationCommand): Promise<Automation> {
  switch (cmd.kind) {
    case 'give':
      return unwrap(
        await api.POST('/api/saves/{slug}/automation/give', {
          ...path(slug),
          body: {
            area: cmd.area,
            slot: cmd.slot,
            person_id: cmd.personId,
            limit_cents: cmd.limitCents ?? null,
            monthly_cents: cmd.monthlyCents ?? null,
          },
        }),
      );
    case 'take_over':
      return unwrap(
        await api.POST('/api/saves/{slug}/automation/take-over', {
          ...path(slug),
          body: { area: cmd.area, slot: cmd.slot },
        }),
      );
    case 'settings':
      return unwrap(
        await api.POST('/api/saves/{slug}/automation/settings', {
          ...path(slug),
          body: {
            area: cmd.area,
            slot: cmd.slot,
            limit_cents: cmd.limitCents ?? null,
            monthly_cents: cmd.monthlyCents ?? null,
            priority: cmd.priority ?? null,
            answer_events: cmd.answerEvents ?? null,
            guardrails: cmd.guardrails ?? null,
          },
        }),
      );
    case 'answer':
      return unwrap(
        await api.POST('/api/saves/{slug}/automation/proposals/{proposal_id}/answer', {
          params: { path: { slug, proposal_id: cmd.proposalId } },
          body: { approve: cmd.approve },
        }),
      );
  }
}

/** The automation actions; each returns the fresh view, which replaces the cached one. */
export function useAutomationAction(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cmd: AutomationCommand) => send(slug, cmd),
    onSuccess: (view) => {
      qc.setQueryData(['automation', slug], view);
      void qc.invalidateQueries({ queryKey: ['run-by', slug] });
      void qc.invalidateQueries({ queryKey: ['inbox', slug] });
      void qc.invalidateQueries({ queryKey: ['leadership', slug] });
      void qc.invalidateQueries({ queryKey: ['game', slug] });
    },
  });
}
