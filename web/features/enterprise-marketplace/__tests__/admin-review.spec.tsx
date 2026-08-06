import type { MarketplaceAssetPaginationResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider as JotaiProvider } from 'jotai'
import { queryClientAtom } from 'jotai-tanstack-query'
import { useHydrateAtoms } from 'jotai/react/utils'
import { NuqsTestingAdapter } from 'nuqs/adapters/testing'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AdminReviewPage } from '../admin-review-page'

type QueryMockState = {
  kind: 'pending' | 'success' | 'error'
  data?: unknown
  error?: unknown
}

const mockState = vi.hoisted(() => ({
  status: {
    kind: 'success',
    data: { is_platform_admin: true, mutation_supported: true },
  } as QueryMockState,
  adminAssets: { kind: 'success', data: undefined } as QueryMockState,
  adminAssetsInputs: [] as unknown[],
  adminAssetsFetches: 0,
  reviewFn: vi.fn(),
  unlistFn: vi.fn(),
}))

vi.mock('@/service/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/service/client')>()

  function createQueryFn(getMock: () => QueryMockState, onFetch?: () => void) {
    return () => {
      onFetch?.()
      const mock = getMock()
      if (mock.kind === 'pending') return new Promise(() => {})
      if (mock.kind === 'error') return Promise.reject(mock.error)
      return Promise.resolve(mock.data)
    }
  }

  const statusKey = actual.consoleQuery.account.platformAdminStatus.get.queryKey()
  const adminAssetsKey = actual.consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.key()

  return {
    ...actual,
    consoleQuery: new Proxy(actual.consoleQuery, {
      get(target, prop, receiver) {
        if (prop === 'account') {
          return {
            platformAdminStatus: {
              get: {
                queryKey: () => statusKey,
                queryOptions: (options: object = {}) => ({
                  ...options,
                  queryKey: statusKey,
                  queryFn: createQueryFn(() => mockState.status),
                }),
              },
            },
          }
        }
        if (prop === 'platformAdmin') {
          return {
            enterpriseMarketplace: {
              assets: {
                get: {
                  queryKey: () => adminAssetsKey,
                  key: () => adminAssetsKey,
                  queryOptions: (options: { input?: unknown } = {}) => {
                    mockState.adminAssetsInputs.push(options.input)
                    return {
                      ...options,
                      queryKey: adminAssetsKey,
                      queryFn: createQueryFn(
                        () => mockState.adminAssets,
                        () => {
                          mockState.adminAssetsFetches += 1
                        },
                      ),
                    }
                  },
                },
                byAssetId: {
                  reviews: {
                    post: {
                      mutationOptions: () => ({ mutationFn: mockState.reviewFn, retry: false }),
                    },
                  },
                  unlist: {
                    post: {
                      mutationOptions: () => ({ mutationFn: mockState.unlistFn, retry: false }),
                    },
                  },
                },
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

function renderAdminReviewPage(searchParams = '') {
  const queryClient = createTestQueryClient()
  const onUrlUpdate = vi.fn()

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <JotaiProvider>
        <QueryClientProvider client={queryClient}>
          <QueryClientAtomHydrator queryClient={queryClient}>
            <NuqsTestingAdapter searchParams={searchParams} onUrlUpdate={onUrlUpdate}>
              {children}
            </NuqsTestingAdapter>
          </QueryClientAtomHydrator>
        </QueryClientProvider>
      </JotaiProvider>
    )
  }

  const result = render(
    <Wrapper>
      <AdminReviewPage />
    </Wrapper>,
  )

  return { ...result, queryClient, onUrlUpdate }
}

const adminAssetList: MarketplaceAssetPaginationResponse = {
  has_more: false,
  items: [
    {
      allow_show_workspace_name: true,
      asset_id: 'asset-1',
      category: 'Customer Service',
      created_at: '2026-01-01T00:00:00Z',
      description: 'A customer service assistant.',
      publication_status: 'unpublished',
      review_note: null,
      reviewed_at: null,
      reviewer_account_id: null,
      row_version: 3,
      scenario: 'Support',
      snapshot_error_code: null,
      snapshot_state: 'succeeded',
      source_app_id: 'src-app-1',
      source_tenant_id: 'tenant-a',
      status: 'pending',
      submitter_account_id: 'user-1',
      tags: ['support'],
      title: 'Support Agent',
      updated_at: '2026-01-02T00:00:00Z',
    },
  ],
  limit: 24,
  page: 1,
  total: 1,
}

const adminAsset = adminAssetList.items[0]!

async function openReviewDialog(
  user: ReturnType<typeof userEvent.setup>,
  action: 'approve' | 'reject',
) {
  const actionName =
    action === 'approve'
      ? 'common.enterpriseMarketplace.review.approve'
      : 'common.enterpriseMarketplace.review.reject'
  await user.click(await screen.findByRole('button', { name: actionName }))

  return screen.findByRole('dialog', { name: 'common.enterpriseMarketplace.review.title' })
}

describe('enterprise-marketplace admin review', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: true, mutation_supported: true },
    }
    mockState.adminAssets = { kind: 'success', data: adminAssetList }
    mockState.adminAssetsInputs.length = 0
    mockState.adminAssetsFetches = 0
    mockState.reviewFn.mockResolvedValue(adminAsset)
    mockState.unlistFn.mockResolvedValue(adminAsset)
  })

  it('keeps the page fail closed while the status query is pending', () => {
    mockState.status = { kind: 'pending' }
    renderAdminReviewPage()

    expect(screen.getByText('common.enterpriseMarketplace.browse.loading')).toBeInTheDocument()
    expect(screen.queryByText('Support Agent')).not.toBeInTheDocument()
  })

  it('fails closed for a non-admin deep link without rendering protected data', async () => {
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: false, mutation_supported: true },
    }
    renderAdminReviewPage()

    expect(
      await screen.findByText('common.enterpriseMarketplace.errors.permissionDenied'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Support Agent')).not.toBeInTheDocument()
  })

  it('renders the review queue rows with status labels and actions', async () => {
    renderAdminReviewPage()

    expect(await screen.findByText('Support Agent')).toBeInTheDocument()
    const list = screen.getByRole('list', { name: 'common.enterpriseMarketplace.review.title' })
    expect(
      within(list).getByText('common.enterpriseMarketplace.status.pending'),
    ).toBeInTheDocument()
    expect(
      within(list).getByText('common.enterpriseMarketplace.status.unpublished'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.review.approve' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.review.reject' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.unlist.title' }),
    ).toBeInTheDocument()
  })

  it('shows a loading skeleton while the admin list is pending', async () => {
    mockState.adminAssets = { kind: 'pending' }
    renderAdminReviewPage()

    expect(
      await screen.findByRole('status', { name: 'common.enterpriseMarketplace.browse.loading' }),
    ).toBeInTheDocument()
    expect(screen.queryByText('Support Agent')).not.toBeInTheDocument()
  })

  it('shows the empty state when the review queue has no assets', async () => {
    mockState.adminAssets = {
      kind: 'success',
      data: { ...adminAssetList, items: [], total: 0 },
    }
    renderAdminReviewPage()

    expect(await screen.findByText('common.enterpriseMarketplace.browse.empty')).toBeInTheDocument()
  })

  it('issues the admin list query with the URL-driven filter arrays', async () => {
    renderAdminReviewPage('?status=pending&publication_status=published&snapshot_state=error')

    await waitFor(() => {
      expect(mockState.adminAssetsInputs.some((input) => input !== undefined)).toBe(true)
    })

    const inputs = mockState.adminAssetsInputs.filter((item) => item !== undefined) as Array<{
      query: Record<string, unknown>
    }>
    const input = inputs[0]!
    expect(input.query.page).toBe(1)
    expect(input.query.limit).toBe(24)
    expect(input.query.status).toEqual(['pending'])
    expect(input.query.publication_status).toEqual(['published'])
    expect(input.query.snapshot_state).toEqual(['error'])
  })

  it('writes a toggled status filter to the URL', async () => {
    const user = userEvent.setup()
    const { onUrlUpdate } = renderAdminReviewPage()

    await user.click(
      await screen.findByRole('checkbox', { name: 'common.enterpriseMarketplace.status.pending' }),
    )

    await waitFor(() => {
      const lastUpdate = onUrlUpdate.mock.calls.at(-1)?.[0]
      expect(lastUpdate?.searchParams.get('status')).toBe('pending')
    })
  })

  it('sends the current row version when approving', async () => {
    const user = userEvent.setup()
    renderAdminReviewPage()

    const dialog = await openReviewDialog(user, 'approve')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.review.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.reviewFn).toHaveBeenCalledWith(
        {
          params: { asset_id: 'asset-1' },
          body: {
            decision: 'approved',
            review_note: null,
            expected_row_version: 3,
          },
        },
        expect.any(Object),
      )
    })
  })

  it('sends the current row version when rejecting', async () => {
    const user = userEvent.setup()
    renderAdminReviewPage()

    const dialog = await openReviewDialog(user, 'reject')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.review.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.reviewFn).toHaveBeenCalledWith(
        {
          params: { asset_id: 'asset-1' },
          body: {
            decision: 'rejected',
            review_note: null,
            expected_row_version: 3,
          },
        },
        expect.any(Object),
      )
    })
  })

  it('sends the current row version when unlisting', async () => {
    const user = userEvent.setup()
    renderAdminReviewPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.enterpriseMarketplace.unlist.title' }),
    )

    const dialog = await screen.findByRole('dialog', {
      name: 'common.enterpriseMarketplace.unlist.title',
    })
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.unlist.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.unlistFn).toHaveBeenCalledWith(
        {
          params: { asset_id: 'asset-1' },
          body: {
            review_note: null,
            expected_row_version: 3,
          },
        },
        expect.any(Object),
      )
    })
  })

  it('keeps the review dialog open, refetches, and does not auto-replay on a 409', async () => {
    mockState.reviewFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'stale_asset_version', message: 'Changed', status: 409 }),
        { status: 409 },
      ),
    )
    const user = userEvent.setup()
    renderAdminReviewPage()

    const dialog = await openReviewDialog(user, 'approve')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.review.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.reviewFn).toHaveBeenCalledTimes(1)
    })

    expect(
      await screen.findByText('common.enterpriseMarketplace.review.error.conflict'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('dialog', { name: 'common.enterpriseMarketplace.review.title' }),
    ).toBeInTheDocument()
    await waitFor(() => {
      expect(mockState.adminAssetsFetches).toBeGreaterThanOrEqual(2)
    })
    expect(mockState.reviewFn).toHaveBeenCalledTimes(1)
  })

  it('shows the validation error on a review 422', async () => {
    mockState.reviewFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'snapshot_contains_secret', message: 'Invalid', status: 422 }),
        { status: 422 },
      ),
    )
    const user = userEvent.setup()
    renderAdminReviewPage()

    const dialog = await openReviewDialog(user, 'approve')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.review.confirm' }),
    )

    expect(
      await screen.findByText('common.enterpriseMarketplace.review.error.validation'),
    ).toBeInTheDocument()
  })

  it('shows the service-unavailable error on a review 503', async () => {
    mockState.reviewFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'rbac_mode_not_supported', message: 'Down', status: 503 }),
        { status: 503 },
      ),
    )
    const user = userEvent.setup()
    renderAdminReviewPage()

    const dialog = await openReviewDialog(user, 'reject')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.review.confirm' }),
    )

    expect(
      await screen.findByText('common.enterpriseMarketplace.review.error.serviceUnavailable'),
    ).toBeInTheDocument()
  })
})
