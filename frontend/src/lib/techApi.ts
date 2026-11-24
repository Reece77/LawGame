// PT-M14: the Technology screen's queries and actions (spec 13). Every number is the API's.
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, type Schemas } from '../api/client';
import { unwrap } from './api';

export type Tech = Schemas['TechOut'];
export type TechEra = Schemas['EraOut'];
export type TechTask = Schemas['TaskOut'];
export type TechProduct = Schemas['ProductOut'];
export type TechKind = Schemas['KindOut'];

export const useTech = (slug: string) =>
  useQuery({
    queryKey: ['tech', slug],
    queryFn: async (): Promise<Tech> =>
      unwrap(await api.GET('/api/saves/{slug}/tech', { params: { path: { slug } } })),
  });

function useTechAction<B>(slug: string, send: (body: B) => Promise<Tech>) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: send,
    onSuccess: (data) => {
      client.setQueryData(['tech', slug], data);
      for (const key of ['game', 'inbox', 'finance', 'practices', 'matter']) {
        void client.invalidateQueries({ queryKey: [key, slug] });
      }
    },
  });
}

export const useInvestInEra = (slug: string) =>
  useTechAction(slug, async (body: { era: string; subscription_bp: number }) =>
    unwrap(await api.POST('/api/saves/{slug}/tech/invest', { params: { path: { slug } }, body })),
  );

export const useRolloutEra = (slug: string) =>
  useTechAction(slug, async (body: { era: string }) =>
    unwrap(await api.POST('/api/saves/{slug}/tech/rollout', { params: { path: { slug } }, body })),
  );

export const useSetTraining = (slug: string) =>
  useTechAction(slug, async (body: { hours: number }) =>
    unwrap(await api.POST('/api/saves/{slug}/tech/training', { params: { path: { slug } }, body })),
  );

export const useLaunchProduct = (slug: string) =>
  useTechAction(slug, async (body: { practice: string; kind_key: string; price_bp: number }) =>
    unwrap(await api.POST('/api/saves/{slug}/tech/products', { params: { path: { slug } }, body })),
  );

export const useRetireProduct = (slug: string) =>
  useTechAction(slug, async (productId: number) =>
    unwrap(
      await api.POST('/api/saves/{slug}/tech/products/{product_id}/retire', {
        params: { path: { slug, product_id: productId } },
      }),
    ),
  );
