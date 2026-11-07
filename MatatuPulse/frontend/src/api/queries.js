import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import * as api from './client'

const POLL = 15000

export const useRoutes = (search) =>
  useQuery({
    queryKey: ['routes', search || ''],
    queryFn: () => api.getRoutes(search),
    placeholderData: keepPreviousData,
    refetchInterval: POLL,
  })

export const useRoute = (id) =>
  useQuery({
    queryKey: ['route', String(id)],
    queryFn: () => api.getRoute(id),
    refetchInterval: POLL,
    enabled: !!id,
  })

export const useSignal = () =>
  useQuery({ queryKey: ['signal'], queryFn: api.getSignal, refetchInterval: POLL })

function patchEvent(route, eventId, fn) {
  if (!route) return route
  const next = { ...route, events: route.events.map((e) => (e.id === eventId ? fn(e) : e)) }
  if (route.banner?.event?.id === eventId) next.banner = { ...route.banner, event: fn(route.banner.event) }
  return next
}

/** Votes update the card immediately, then refetch. */
export function useVote(routeId) {
  const qc = useQueryClient()
  const key = ['route', String(routeId)]
  return useMutation({
    mutationFn: ({ event, kind }) => api.vote(event.id, kind),
    onMutate: async ({ event, kind }) => {
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData(key)
      qc.setQueryData(key, (route) =>
        patchEvent(route, event.id, (e) => {
          const addsReporter = kind === 'still' && e.my_vote !== 'still' && !e.i_reported
          const losesReporter = kind === 'cleared' && e.my_vote === 'still'
          const confirmations = e.confirmations + (addsReporter ? 1 : 0) - (losesReporter ? 1 : 0)
          return {
            ...e,
            my_vote: kind,
            confirmations,
            needed: Math.max(0, 3 - confirmations),
            status: e.status === 'pending' && confirmations >= 3 ? 'verified' : e.status,
          }
        }),
      )
      return { prev }
    },
    onError: (_err, _vars, ctx) => ctx?.prev && qc.setQueryData(key, ctx.prev),
    onSuccess: (event) => qc.setQueryData(key, (route) => patchEvent(route, event.id, () => event)),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: key })
      qc.invalidateQueries({ queryKey: ['routes'] })
    },
  })
}

/** Reports drop the returned event straight into the route's card list, then refetch. */
export function useCreateReport(routeId) {
  const qc = useQueryClient()
  const key = ['route', String(routeId)]
  return useMutation({
    mutationFn: api.createReport,
    onSuccess: (res) =>
      qc.setQueryData(key, (route) => {
        if (!route) return route
        const exists = route.events.some((e) => e.id === res.event.id)
        const events = exists
          ? route.events.map((e) => (e.id === res.event.id ? res.event : e))
          : [res.event, ...route.events]
        return { ...route, events }
      }),
    onSettled: () => {
      qc.invalidateQueries({ queryKey: key })
      qc.invalidateQueries({ queryKey: ['routes'] })
      qc.invalidateQueries({ queryKey: ['signal'] })
    },
  })
}

export function useSubscribe(routeId) {
  const qc = useQueryClient()
  const key = ['route', String(routeId)]
  return useMutation({
    mutationFn: () => api.toggleSubscribe(routeId),
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: key })
      const prev = qc.getQueryData(key)
      qc.setQueryData(key, (r) => (r ? { ...r, subscribed: !r.subscribed } : r))
      return { prev }
    },
    onError: (_e, _v, ctx) => ctx?.prev && qc.setQueryData(key, ctx.prev),
    onSuccess: (res) => qc.setQueryData(key, (r) => (r ? { ...r, subscribed: res.subscribed } : r)),
  })
}
