// Leadership server state (PT-M8) over the generated client (ADR-0009): seats, holders,
// authority and pitches. No game logic here: every rule is the engine's, and a refused
// action comes back as an ApiError with its message.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';
import { unwrap } from './api';
import { formatMoney } from './format';

export type Leadership = Schemas['LeadershipOut'];
export type Seat = Schemas['SeatOut'];
export type SeatSlot = Schemas['SeatSlotOut'];
export type SeatPitch = Schemas['SeatPitchOut'];

const path = (slug: string) => ({ params: { path: { slug } } });

export const useLeadership = (slug: string) =>
  useQuery({
    queryKey: ['leadership', slug],
    queryFn: async () => unwrap(await api.GET('/api/saves/{slug}/leadership', path(slug))),
  });

export type LeadershipCommand =
  | { kind: 'appoint'; seat: string; slot: number; personId: number | null }
  | {
      kind: 'authority';
      seat: string;
      slot: number;
      enabled: boolean;
      guardrails: { key: string; value: number }[];
    }
  | { kind: 'exco_term'; elected: boolean }
  | { kind: 'answer'; pitchId: number; answer: 'approve' | 'modify' | 'decline'; value?: number };

async function send(slug: string, cmd: LeadershipCommand): Promise<Leadership> {
  switch (cmd.kind) {
    case 'appoint':
      return unwrap(
        await api.POST('/api/saves/{slug}/leadership/appoint', {
          ...path(slug),
          body: { seat: cmd.seat, slot: cmd.slot, person_id: cmd.personId },
        }),
      );
    case 'authority':
      return unwrap(
        await api.POST('/api/saves/{slug}/leadership/authority', {
          ...path(slug),
          body: {
            seat: cmd.seat,
            slot: cmd.slot,
            enabled: cmd.enabled,
            guardrails: cmd.guardrails,
          },
        }),
      );
    case 'exco_term':
      return unwrap(
        await api.POST('/api/saves/{slug}/leadership/exco-term', {
          ...path(slug),
          body: { elected: cmd.elected },
        }),
      );
    case 'answer':
      return unwrap(
        await api.POST('/api/saves/{slug}/leadership/pitches/{pitch_id}/answer', {
          params: { path: { slug, pitch_id: cmd.pitchId } },
          body: { answer: cmd.answer, value: cmd.value ?? null },
        }),
      );
  }
}

/** The leadership actions; each returns the fresh view, which replaces the cached one. */
export function useLeadershipAction(slug: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cmd: LeadershipCommand) => send(slug, cmd),
    onSuccess: (view) => {
      qc.setQueryData(['leadership', slug], view);
      void qc.invalidateQueries({ queryKey: ['org', slug] });
      void qc.invalidateQueries({ queryKey: ['inbox', slug] });
      void qc.invalidateQueries({ queryKey: ['game', slug] });
    },
  });
}

/** A pitch's case in its unit (the engine sends the unit; formatting only). */
export function formatCase(unit: SeatPitch['case_unit'], value: number): string {
  switch (unit) {
    case 'cents':
      return formatMoney(value);
    case 'bp':
      return `${value >= 0 ? '+' : ''}${(value / 100).toFixed(1)}%`;
    case 'morale':
      return `${(value / 10).toFixed(0)} morale`;
    case 'people':
      return `${value} ${value === 1 ? 'person' : 'people'}`;
  }
}
