import type { MarketplaceSnapshotDetailResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type {
  MarketplaceAssetResponse,
  PlatformAdminMemberInviteResponse,
  PlatformAdminMemberRoleUpdateResponse,
  PlatformAdminWorkspacePaginationResponse,
  PlatformAdminWorkspaceResponse,
} from '@dify/contracts/api/console/platform-admin/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { Provider as JotaiProvider, useAtomValue } from 'jotai'
import { queryClientAtom } from 'jotai-tanstack-query'
import { useHydrateAtoms } from 'jotai/react/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { consoleQuery } from '@/service/client'
import { mapPlatformAdminError } from '../errors'
import {
  isPlatformAdminAtom,
  platformAdminMutationSupportedAtom,
  platformAdminStatusErrorAtom,
  platformAdminStatusPendingAtom,
} from '../state'

const mockStatusQuery = vi.hoisted(() => ({
  kind: 'pending' as 'success' | 'pending' | 'error',
  data: undefined as unknown,
  error: undefined as unknown,
}))

vi.mock('@/service/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/service/client')>()
  const realStatusQueryOptions =
    actual.consoleQuery.account.platformAdminStatus.get.queryOptions() as {
      retry?: (failureCount: number, error: unknown) => boolean
    }
  const statusQueryKey = actual.consoleQuery.account.platformAdminStatus.get.queryKey()

  return {
    ...actual,
    consoleQuery: new Proxy(actual.consoleQuery, {
      get(target, prop, receiver) {
        if (prop === 'account') {
          return {
            platformAdminStatus: {
              get: {
                queryKey: () => statusQueryKey,
                queryOptions: (options?: object) => ({
                  queryKey: statusQueryKey,
                  retry: realStatusQueryOptions.retry,
                  queryFn: () => {
                    if (mockStatusQuery.kind === 'pending') return new Promise(() => {})
                    if (mockStatusQuery.kind === 'error')
                      return Promise.reject(mockStatusQuery.error)
                    return Promise.resolve(mockStatusQuery.data)
                  },
                  ...options,
                }),
              },
            },
          }
        }

        return Reflect.get(target, prop, receiver)
      },
    }),
  }
})

function QueryClientAtomHydrator({
  children,
  queryClient,
}: {
  children: ReactNode
  queryClient: QueryClient
}) {
  useHydrateAtoms(new Map([[queryClientAtom, queryClient]]))

  return children
}

function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: Infinity,
        queryFn: () => new Promise(() => {}),
      },
      mutations: { retry: false },
    },
  })
}

function createStatusWrapper(queryClient: QueryClient) {
  return function StatusWrapper({ children }: { children: ReactNode }) {
    return (
      <JotaiProvider>
        <QueryClientProvider client={queryClient}>
          <QueryClientAtomHydrator queryClient={queryClient}>{children}</QueryClientAtomHydrator>
        </QueryClientProvider>
      </JotaiProvider>
    )
  }
}

function usePlatformAdminStatus() {
  return {
    pending: useAtomValue(platformAdminStatusPendingAtom),
    error: useAtomValue(platformAdminStatusErrorAtom),
    isPlatformAdmin: useAtomValue(isPlatformAdminAtom),
    mutationSupported: useAtomValue(platformAdminMutationSupportedAtom),
  }
}

describe('platform-admin status state', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStatusQuery.kind = 'pending'
    mockStatusQuery.data = undefined
    mockStatusQuery.error = undefined
  })

  it('keeps the admin identity fail closed while the status query is pending', () => {
    const queryClient = createTestQueryClient()
    mockStatusQuery.kind = 'pending'

    const { result } = renderHook(() => usePlatformAdminStatus(), {
      wrapper: createStatusWrapper(queryClient),
    })

    expect(result.current.pending).toBe(true)
    expect(result.current.error).toBe(false)
    expect(result.current.isPlatformAdmin).toBe(false)
    expect(result.current.mutationSupported).toBe(false)
  })

  it('keeps the admin identity fail closed when the status query errors with 401', async () => {
    const queryClient = createTestQueryClient()
    mockStatusQuery.kind = 'error'
    mockStatusQuery.error = new Response(
      JSON.stringify({ code: 'unauthorized', message: 'Not allowed' }),
      { status: 401 },
    )

    const { result } = renderHook(() => usePlatformAdminStatus(), {
      wrapper: createStatusWrapper(queryClient),
    })

    await waitFor(() => expect(result.current.error).toBe(true))
    expect(result.current.pending).toBe(false)
    expect(result.current.isPlatformAdmin).toBe(false)
  })

  it('keeps the admin identity fail closed when the status reports false', async () => {
    const queryClient = createTestQueryClient()
    mockStatusQuery.kind = 'success'
    mockStatusQuery.data = { is_platform_admin: false, mutation_supported: true }

    const { result } = renderHook(() => usePlatformAdminStatus(), {
      wrapper: createStatusWrapper(queryClient),
    })

    await waitFor(() => expect(result.current.pending).toBe(false))
    expect(result.current.isPlatformAdmin).toBe(false)
    expect(result.current.mutationSupported).toBe(true)
  })

  it('exposes the admin identity when the status reports true', async () => {
    const queryClient = createTestQueryClient()
    mockStatusQuery.kind = 'success'
    mockStatusQuery.data = { is_platform_admin: true, mutation_supported: true }

    const { result } = renderHook(() => usePlatformAdminStatus(), {
      wrapper: createStatusWrapper(queryClient),
    })

    await waitFor(() => expect(result.current.isPlatformAdmin).toBe(true))
    expect(result.current.pending).toBe(false)
    expect(result.current.error).toBe(false)
    expect(result.current.mutationSupported).toBe(true)
  })

  it('preserves a true admin identity when mutation support is disabled', async () => {
    const queryClient = createTestQueryClient()
    mockStatusQuery.kind = 'success'
    mockStatusQuery.data = { is_platform_admin: true, mutation_supported: false }

    const { result } = renderHook(() => usePlatformAdminStatus(), {
      wrapper: createStatusWrapper(queryClient),
    })

    await waitFor(() => expect(result.current.isPlatformAdmin).toBe(true))
    expect(result.current.mutationSupported).toBe(false)
  })
})

describe('platformAdminStatus query retry', () => {
  const getStatusQueryOptions = () =>
    consoleQuery.account.platformAdminStatus.get.queryOptions() as unknown as {
      queryKey: readonly unknown[]
      retry: (failureCount: number, error: unknown) => boolean
      queryFn: () => unknown
    }

  it('does not retry a 401 response', async () => {
    const options = getStatusQueryOptions()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retryDelay: 0 } } })
    const queryFn = vi.fn().mockRejectedValue(
      new Response(JSON.stringify({ code: 'unauthorized', message: 'Not allowed' }), {
        status: 401,
      }),
    )

    await expect(queryClient.fetchQuery({ ...options, queryFn })).rejects.toBeInstanceOf(Response)
    expect(queryFn).toHaveBeenCalledTimes(1)
  })

  it('retries a transient failure at most twice', async () => {
    const options = getStatusQueryOptions()
    const queryClient = new QueryClient({ defaultOptions: { queries: { retryDelay: 0 } } })
    const queryFn = vi.fn().mockRejectedValue(new Error('network unavailable'))

    await expect(queryClient.fetchQuery({ ...options, queryFn })).rejects.toBeInstanceOf(Error)
    expect(queryFn).toHaveBeenCalledTimes(3)
  })
})

describe('mapPlatformAdminError', () => {
  it('maps a 401 transport response to the unauthorized key', () => {
    const error = new Response(JSON.stringify({ code: 'unauthorized', message: 'Not allowed' }), {
      status: 401,
    })

    expect(mapPlatformAdminError(error)).toEqual({
      kind: 'unauthorized',
      key: 'platformAdmin.errors.unauthorized',
      status: 401,
    })
  })

  it('maps a 403 transport response to the permission denied key', () => {
    const error = new Response(
      JSON.stringify({ code: 'forbidden', message: 'No permission', status: 403 }),
      { status: 403 },
    )

    expect(mapPlatformAdminError(error)).toEqual({
      kind: 'permissionDenied',
      key: 'platformAdmin.errors.permissionDenied',
      status: 403,
    })
  })

  it('maps a 404 transport response to the not found key', () => {
    const error = new Response(
      JSON.stringify({ code: 'not_found', message: 'Missing', status: 404 }),
      { status: 404 },
    )

    expect(mapPlatformAdminError(error)).toEqual({
      kind: 'notFound',
      key: 'platformAdmin.errors.notFound',
      status: 404,
    })
  })

  it('maps a 409 transport response to the conflict key', () => {
    const error = new Response(
      JSON.stringify({ code: 'conflict', message: 'Changed', status: 409 }),
      { status: 409 },
    )

    expect(mapPlatformAdminError(error)).toEqual({
      kind: 'conflict',
      key: 'platformAdmin.errors.conflict',
      status: 409,
    })
  })

  it('maps a 503 transport response to the service unavailable key', () => {
    const error = new Response(
      JSON.stringify({ code: 'rbac_mode_not_supported', message: 'Unavailable', status: 503 }),
      { status: 503 },
    )

    expect(mapPlatformAdminError(error)).toEqual({
      kind: 'serviceUnavailable',
      key: 'platformAdmin.errors.serviceUnavailable',
      status: 503,
    })
  })

  it('treats a reachable 400 response as the safe unknown fallback', () => {
    const error = new Response(
      JSON.stringify({ code: 'invalid_request', message: 'Bad request', status: 400 }),
      { status: 400 },
    )

    expect(mapPlatformAdminError(error)).toEqual({ kind: 'unknown', status: 400 })
  })

  it('falls back to unknown for errors without a transport or domain status', () => {
    expect(mapPlatformAdminError(new Error('boom'))).toEqual({ kind: 'unknown' })
  })

  it('does not cast an unknown domain body code into a valid domain kind', () => {
    expect(mapPlatformAdminError({ code: 'stale_asset_version', message: 'Changed' })).toEqual({
      kind: 'unknown',
    })
  })

  it('classifies a domain error body by its status field', () => {
    const body = { code: 'rbac_mode_not_supported', message: 'Unavailable', status: 503 }

    expect(mapPlatformAdminError(body)).toEqual({
      kind: 'serviceUnavailable',
      key: 'platformAdmin.errors.serviceUnavailable',
      status: 503,
    })
  })
})

const workspacePagination: PlatformAdminWorkspacePaginationResponse = {
  has_more: false,
  items: [],
  limit: 50,
  page: 1,
  total: 0,
}

const workspace: PlatformAdminWorkspaceResponse = {
  created_at: '2026-01-01T00:00:00Z',
  id: 'ws-1',
  member_count: 1,
  name: 'Before',
  owner: { email: 'owner@example.com', id: 'user-1', name: 'Owner' },
  plan: 'sandbox',
  status: 'normal',
  updated_at: '2026-01-01T00:00:00Z',
}

const asset: MarketplaceAssetResponse = {
  allow_show_workspace_name: false,
  asset_id: 'asset-1',
  category: 'chat',
  created_at: '2026-01-01T00:00:00Z',
  description: 'Description',
  publication_status: 'published',
  review_note: null,
  reviewed_at: null,
  reviewer_account_id: null,
  row_version: 2,
  scenario: 'chat',
  snapshot_error_code: null,
  snapshot_state: 'ready',
  source_app_id: 'app-1',
  source_tenant_id: 'tenant-1',
  status: 'approved',
  submitter_account_id: 'user-1',
  tags: [],
  title: 'My App',
  updated_at: '2026-01-01T00:00:00Z',
}

const snapshotDetail: MarketplaceSnapshotDetailResponse = {
  allow_show_workspace_name: false,
  app_description: null,
  app_icon: null,
  app_icon_background: null,
  app_icon_type: null,
  app_mode: null,
  app_name: null,
  asset_id: 'asset-1',
  category: 'chat',
  content_sha256: 'abc',
  created_at: '2026-01-01T00:00:00Z',
  dependencies: null,
  description: 'Description',
  dsl_version: null,
  frozen_at: null,
  publication_status: 'published',
  row_version: 2,
  scenario: 'chat',
  snapshot_id: 'snapshot-1',
  snapshot_state: 'ready',
  snapshot_version: 1,
  source_tenant_name: null,
  status: 'approved',
  tags: [],
  title: 'My App',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('shared mutation invalidation defaults', () => {
  it('invalidates workspace lists and the exact workspace detail after a rename', async () => {
    const queryClient = createTestQueryClient()
    const listKey = consoleQuery.platformAdmin.workspaces.get.key()
    const detailKey = consoleQuery.platformAdmin.workspaces.byWorkspaceId.get.queryKey({
      input: { params: { workspace_id: 'ws-1' } },
    })
    queryClient.setQueryData(listKey, workspacePagination)
    queryClient.setQueryData(detailKey, workspace)

    const options = consoleQuery.platformAdmin.workspaces.byWorkspaceId.patch.mutationOptions()
    const variables = { params: { workspace_id: 'ws-1' }, body: { name: 'Renamed' } }
    await options.onSuccess?.({ ...workspace, name: 'Renamed' }, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(true)
  })

  it('invalidates members, workspace detail, and lists after an invitation', async () => {
    const queryClient = createTestQueryClient()
    const membersKey = consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.get.queryKey({
      input: { params: { workspace_id: 'ws-1' } },
    })
    const detailKey = consoleQuery.platformAdmin.workspaces.byWorkspaceId.get.queryKey({
      input: { params: { workspace_id: 'ws-1' } },
    })
    const listKey = consoleQuery.platformAdmin.workspaces.get.key()
    queryClient.setQueryData(membersKey, { items: [], mutation_supported: true })
    queryClient.setQueryData(detailKey, workspace)
    queryClient.setQueryData(listKey, workspacePagination)

    const invitationsPost =
      consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.invitations.post
    const options = invitationsPost.mutationOptions()
    const inviteResponse: PlatformAdminMemberInviteResponse = {
      results: [],
      workspace_id: 'ws-1',
    }
    const variables = {
      params: { workspace_id: 'ws-1' },
      body: { emails: ['member@example.com'], role: 'admin' as const },
    }
    await options.onSuccess?.(inviteResponse, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(membersKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(listKey)?.isInvalidated).toBe(true)
  })

  it('invalidates members after a member role update', async () => {
    const queryClient = createTestQueryClient()
    const membersKey = consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.get.queryKey({
      input: { params: { workspace_id: 'ws-1' } },
    })
    queryClient.setQueryData(membersKey, { items: [], mutation_supported: true })

    const options =
      consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.byMemberId.role.patch.mutationOptions()
    const roleUpdateResponse: PlatformAdminMemberRoleUpdateResponse = {
      member_id: 'member-1',
      result: 'success',
      workspace_id: 'ws-1',
    }
    const variables = {
      params: { workspace_id: 'ws-1', member_id: 'member-1' },
      body: { role: 'admin' as const },
    }
    await options.onSuccess?.(roleUpdateResponse, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(membersKey)?.isInvalidated).toBe(true)
  })

  it('invalidates own submissions and admin assets after a submit or resubmit', async () => {
    const queryClient = createTestQueryClient()
    const submissionsKey = consoleQuery.enterpriseMarketplace.submissions.get.key()
    const adminAssetsKey = consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.key()
    queryClient.setQueryData(submissionsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })
    queryClient.setQueryData(adminAssetsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })

    const options =
      consoleQuery.apps.byAppId.enterpriseMarketplace.submissions.post.mutationOptions()
    const variables = {
      params: { app_id: 'app-1' },
      body: { category: 'chat', title: 'My App' },
    }
    await options.onSuccess?.(asset, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(submissionsKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(adminAssetsKey)?.isInvalidated).toBe(true)
  })

  it('invalidates official app lists after a copy succeeds', async () => {
    const queryClient = createTestQueryClient()
    const appsListKey = consoleQuery.apps.get.key()
    queryClient.setQueryData(appsListKey, {
      data: [],
      has_more: false,
      limit: 24,
      page: 1,
      total: 0,
    })

    const options =
      consoleQuery.enterpriseMarketplace.assets.byAssetId.copies.post.mutationOptions()
    const variables = { params: { asset_id: 'asset-1' }, body: {} }
    const copyResponse = {
      app_id: 'app-2',
      content_sha256: 'abc',
      import_status: 'success',
      snapshot_version: 1,
      warnings: [],
    }
    await options.onSuccess?.(copyResponse, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(appsListKey)?.isInvalidated).toBe(true)
  })

  it('invalidates admin, public, submissions, and exact detail after a review', async () => {
    const queryClient = createTestQueryClient()
    const adminAssetsKey = consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.key()
    const publicAssetsKey = consoleQuery.enterpriseMarketplace.assets.get.key()
    const submissionsKey = consoleQuery.enterpriseMarketplace.submissions.get.key()
    const detailKey = consoleQuery.enterpriseMarketplace.assets.byAssetId.get.queryKey({
      input: { params: { asset_id: 'asset-1' } },
    })
    queryClient.setQueryData(adminAssetsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })
    queryClient.setQueryData(publicAssetsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })
    queryClient.setQueryData(submissionsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })
    queryClient.setQueryData(detailKey, snapshotDetail)

    const options =
      consoleQuery.platformAdmin.enterpriseMarketplace.assets.byAssetId.reviews.post.mutationOptions()
    const variables = {
      params: { asset_id: 'asset-1' },
      body: { decision: 'approved' as const, expected_row_version: 1 },
    }
    await options.onSuccess?.(asset, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(adminAssetsKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(publicAssetsKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(submissionsKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(true)
  })

  it('invalidates admin assets, public assets, and the exact detail after an unlist', async () => {
    const queryClient = createTestQueryClient()
    const adminAssetsKey = consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.key()
    const publicAssetsKey = consoleQuery.enterpriseMarketplace.assets.get.key()
    const detailKey = consoleQuery.enterpriseMarketplace.assets.byAssetId.get.queryKey({
      input: { params: { asset_id: 'asset-1' } },
    })
    queryClient.setQueryData(adminAssetsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })
    queryClient.setQueryData(publicAssetsKey, {
      has_more: false,
      items: [],
      limit: 50,
      page: 1,
      total: 0,
    })
    queryClient.setQueryData(detailKey, snapshotDetail)

    const options =
      consoleQuery.platformAdmin.enterpriseMarketplace.assets.byAssetId.unlist.post.mutationOptions()
    const variables = { params: { asset_id: 'asset-1' }, body: { expected_row_version: 1 } }
    await options.onSuccess?.(asset, variables, undefined, {
      client: queryClient,
      meta: undefined,
      mutationKey: options.mutationKey,
    })

    expect(queryClient.getQueryState(adminAssetsKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(publicAssetsKey)?.isInvalidated).toBe(true)
    expect(queryClient.getQueryState(detailKey)?.isInvalidated).toBe(true)
  })
})
