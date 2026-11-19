// Org server state (PT-M2) over the generated client (ADR-0009). No game logic here: every
// rule is the engine's, and a refused action comes back as an ApiError with its message.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';
import { unwrap } from './api';

export type Org = Schemas['OrgOut'];
export type OrgUnit = Schemas['OrgUnitOut'];
export type OrgMember = Schemas['OrgMemberOut'];
export type Plan = Schemas['PlanOut'];
export type PlanBody = Schemas['PlanIn'];
export type PersonOrg = Schemas['PersonOrgOut'];

const path = (slug: string) => ({ params: { path: { slug } } });

export const useOrg = (slug: string) =>
  useQuery({
    queryKey: ['org', slug],
    queryFn: async () => unwrap(await api.GET('/api/saves/{slug}/org', path(slug))),
  });

export const usePersonOrg = (slug: string, personId: number) =>
  useQuery({
    queryKey: ['org', slug, 'person', personId],
    queryFn: async () =>
      unwrap(
        await api.GET('/api/saves/{slug}/org/people/{person_id}', {
          params: { path: { slug, person_id: personId } },
        }),
      ),
  });

/** The org actions; each returns the fresh org, which replaces the cached one. */
export type OrgCommand =
  | { kind: 'create_unit'; body: Schemas['CreateUnitIn'] }
  | { kind: 'dissolve_unit'; unitId: number }
  | { kind: 'set_leader'; unitId: number; personId: number | null }
  | { kind: 'move_person'; personId: number; unitId: number | null }
  | { kind: 'promote'; personId: number }
  | { kind: 'create_plan'; body: PlanBody }
  | { kind: 'close_plan'; planId: number };

async function send(slug: string, cmd: OrgCommand): Promise<Org> {
  switch (cmd.kind) {
    case 'create_unit':
      return unwrap(
        await api.POST('/api/saves/{slug}/org/units', { ...path(slug), body: cmd.body }),
      );
    case 'dissolve_unit':
      return unwrap(
        await api.DELETE('/api/saves/{slug}/org/units/{unit_id}', {
          params: { path: { slug, unit_id: cmd.unitId } },
        }),
      );
    case 'set_leader':
      return unwrap(
        await api.PUT('/api/saves/{slug}/org/units/{unit_id}/leader', {
          params: { path: { slug, unit_id: cmd.unitId } },
          body: { person_id: cmd.personId },
        }),
      );
    case 'move_person':
      return unwrap(
        await api.PUT('/api/saves/{slug}/org/people/{person_id}/unit', {
          params: { path: { slug, person_id: cmd.personId } },
          body: { unit_id: cmd.unitId },
        }),
      );
    case 'promote':
      return unwrap(
        await api.POST('/api/saves/{slug}/org/people/{person_id}/promote', {
          params: { path: { slug, person_id: cmd.personId } },
        }),
      );
    case 'create_plan':
      return unwrap(
        await api.POST('/api/saves/{slug}/org/plans', { ...path(slug), body: cmd.body }),
      );
    case 'close_plan':
      return unwrap(
        await api.DELETE('/api/saves/{slug}/org/plans/{plan_id}', {
          params: { path: { slug, plan_id: cmd.planId } },
        }),
      );
  }
}

export function useOrgAction(slug: string) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: (cmd: OrgCommand) => send(slug, cmd),
    onSuccess: (org) => {
      client.setQueryData(['org', slug], org);
      void client.invalidateQueries({ queryKey: ['org', slug, 'person'] });
      void client.invalidateQueries({ queryKey: ['people', slug] });
    },
  });
}

/** "strong" -> a badge colour for a supervising partner's label. */
export function supervisorColor(label: string): string {
  return label === 'strong' ? 'teal' : label === 'stretched' ? 'orange' : 'gray';
}
