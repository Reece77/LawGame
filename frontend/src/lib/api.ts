// Server-state hooks over the generated client (ADR-0009). No game logic here.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';

export type Game = Schemas['GameOut'];
export type SaveSummary = Schemas['SaveOut'];
export type Meta = Schemas['MetaOut'];
export type NewGameBody = Schemas['NewGameIn'];

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
    onSuccess: (game) => client.setQueryData(['game', slug], game),
  });
}
