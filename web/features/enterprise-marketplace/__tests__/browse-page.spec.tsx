import type { MarketplaceSnapshotPaginationResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NuqsTestingAdapter } from 'nuqs/adapters/testing'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketplaceBrowsePage } from '../browse-page'

type QueryMockState = {
  kind: 'pending' | 'success' | 'error'
  data?: unknown
  error?: unknown
}

const mockState = vi.hoisted(() => ({
  assets: { kind: 'success', data: undefined } as QueryMockState,
  assetsInputs: [] as unknown[],
}))

vi.mock('@/service/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/service/client')>()

  function createQueryFn(getMock: () => QueryMockState) {
    return () => {
      const mock = getMock()
      if (mock.kind === 'pending') return new Promise(() => {})
      if (mock.kind === 'error') return Promise.reject(mock.error)
      return Promise.resolve(mock.data)
    }
  }

  const assetsKey = actual.consoleQuery.enterpriseMarketplace.assets.get.key()

  return {
    ...actual,
    consoleQuery: new Proxy(actual.consoleQuery, {
      get(target, prop, receiver) {
        if (prop === 'enterpriseMarketplace') {
          return {
            assets: {
              get: {
                queryKey: () => assetsKey,
                queryOptions: (options: { input?: unknown } = {}) => {
                  mockState.assetsInputs.push(options.input)
                  return {
                    ...options,
                    queryKey: assetsKey,
                    queryFn: createQueryFn(() => mockState.assets),
                  }
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

function renderBrowsePage(searchParams = '') {
  const queryClient = createTestQueryClient()
  const onUrlUpdate = vi.fn()

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <NuqsTestingAdapter searchParams={searchParams} onUrlUpdate={onUrlUpdate}>
          {children}
        </NuqsTestingAdapter>
      </QueryClientProvider>
    )
  }

  const result = render(
    <Wrapper>
      <MarketplaceBrowsePage />
    </Wrapper>,
  )

  return { ...result, queryClient, onUrlUpdate }
}

const snapshotList: MarketplaceSnapshotPaginationResponse = {
  has_more: false,
  items: [
    {
      allow_show_workspace_name: true,
      app_description: null,
      app_icon: null,
      app_icon_background: null,
      app_icon_type: null,
      app_mode: 'chat',
      app_name: null,
      asset_id: 'asset-1',
      category: 'Customer Service',
      content_sha256: null,
      created_at: '2026-01-01T00:00:00Z',
      dependencies: null,
      description: 'A customer service assistant.',
      dsl_version: null,
      frozen_at: null,
      publication_status: 'published',
      row_version: 3,
      scenario: 'Support',
      snapshot_id: 'snap-1',
      snapshot_state: 'succeeded',
      snapshot_version: 2,
      source_tenant_name: 'Tenant A',
      status: 'approved',
      tags: ['support', 'chat'],
      title: 'Support Agent',
      updated_at: '2026-01-02T00:00:00Z',
    },
    {
      allow_show_workspace_name: true,
      app_description: null,
      app_icon: null,
      app_icon_background: null,
      app_icon_type: null,
      app_mode: 'workflow',
      app_name: null,
      asset_id: 'asset-2',
      category: 'Data Analysis',
      content_sha256: null,
      created_at: '2026-01-03T00:00:00Z',
      dependencies: null,
      description: 'Summarizes spreadsheets.',
      dsl_version: null,
      frozen_at: null,
      publication_status: 'published',
      row_version: 1,
      scenario: 'Analysis',
      snapshot_id: 'snap-2',
      snapshot_state: 'succeeded',
      snapshot_version: 1,
      source_tenant_name: 'Tenant B',
      status: 'approved',
      tags: ['data'],
      title: 'Data Summarizer',
      updated_at: '2026-01-03T00:00:00Z',
    },
  ],
  limit: 24,
  page: 1,
  total: 50,
}

describe('enterprise-marketplace browse page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.assets = { kind: 'success', data: snapshotList }
    mockState.assetsInputs.length = 0
  })

  it('renders the asset cards with detail links, titles, and descriptions', async () => {
    renderBrowsePage()

    expect(await screen.findByRole('link', { name: 'Support Agent' })).toHaveAttribute(
      'href',
      '/enterprise-marketplace/asset-1',
    )
    expect(screen.getByRole('link', { name: 'Data Summarizer' })).toHaveAttribute(
      'href',
      '/enterprise-marketplace/asset-2',
    )
    expect(screen.getByText('A customer service assistant.')).toBeInTheDocument()
    expect(screen.getByText('Customer Service')).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'common.enterpriseMarketplace.browse.title' }),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'common.enterpriseMarketplace.submissions.title' }),
    ).toHaveAttribute('href', '/enterprise-marketplace/submissions')
  })

  it('issues the list query with the fixed page size and the URL-driven filters', async () => {
    renderBrowsePage('?page=2&search=alpha&category=chat&sort=title_asc')

    await waitFor(() => {
      expect(mockState.assetsInputs.some((input) => input !== undefined)).toBe(true)
    })

    const inputs = mockState.assetsInputs.filter((item) => item !== undefined) as Array<{
      query: Record<string, unknown>
    }>
    const input = inputs[0]!
    expect(input.query.page).toBe(2)
    expect(input.query.limit).toBe(24)
    expect(input.query.keyword).toBe('alpha')
    expect(input.query.category).toBe('chat')
    expect(input.query.sort).toBe('title_asc')
  })

  it('shows a loading skeleton while the list is pending', async () => {
    mockState.assets = { kind: 'pending' }
    renderBrowsePage()

    expect(
      await screen.findByRole('status', { name: 'common.enterpriseMarketplace.browse.loading' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Support Agent' })).not.toBeInTheDocument()
  })

  it('shows the empty state when there are no results', async () => {
    mockState.assets = {
      kind: 'success',
      data: { ...snapshotList, items: [], total: 0 },
    }
    renderBrowsePage()

    expect(await screen.findByText('common.enterpriseMarketplace.browse.empty')).toBeInTheDocument()
  })

  it('maps a 400 list failure to the inline error state and retries', async () => {
    mockState.assets = {
      kind: 'error',
      error: new Response(
        JSON.stringify({ code: 'invalid_request', message: 'Bad', status: 400 }),
        {
          status: 400,
        },
      ),
    }
    const user = userEvent.setup()
    renderBrowsePage()

    expect(await screen.findByText('common.enterpriseMarketplace.browse.error')).toBeInTheDocument()

    mockState.assets = { kind: 'success', data: snapshotList }
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.browse.retry' }),
    )

    expect(await screen.findByRole('link', { name: 'Support Agent' })).toBeInTheDocument()
  })

  it('maps a 503 list failure to the service-unavailable error and retries', async () => {
    mockState.assets = {
      kind: 'error',
      error: new Response(
        JSON.stringify({ code: 'service_unavailable', message: 'Down', status: 503 }),
        { status: 503 },
      ),
    }
    const user = userEvent.setup()
    renderBrowsePage()

    expect(
      await screen.findByText('common.enterpriseMarketplace.errors.serviceUnavailable'),
    ).toBeInTheDocument()

    mockState.assets = { kind: 'success', data: snapshotList }
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.browse.retry' }),
    )

    expect(await screen.findByRole('link', { name: 'Support Agent' })).toBeInTheDocument()
  })

  it('updates the page in the URL when paginating', async () => {
    const user = userEvent.setup()
    const { onUrlUpdate } = renderBrowsePage()

    await user.click(await screen.findByRole('button', { name: 'Next page' }))

    await waitFor(() => {
      const lastUpdate = onUrlUpdate.mock.calls.at(-1)?.[0]
      expect(lastUpdate?.searchParams.get('page')).toBe('2')
    })
  })

  it('resets to the first page and commits the search keyword', async () => {
    const user = userEvent.setup()
    const { onUrlUpdate } = renderBrowsePage('?page=3')

    const searchInput = await screen.findByRole('textbox', {
      name: 'common.enterpriseMarketplace.browse.searchPlaceholder',
    })
    await user.type(searchInput, 'alpha')
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.browse.searchButton' }),
    )

    await waitFor(() => {
      const lastUpdate = onUrlUpdate.mock.calls.at(-1)?.[0]
      expect(lastUpdate?.searchParams.get('search')).toBe('alpha')
      expect(lastUpdate?.searchParams.has('page')).toBe(false)
    })
  })

  it('renders a card for a snapshot with unknown display values without crashing', async () => {
    mockState.assets = {
      kind: 'success',
      data: {
        ...snapshotList,
        items: [
          {
            ...snapshotList.items[0]!,
            app_icon: null,
            app_name: null,
            publication_status: 'unknown-publication',
            status: 'unknown-status',
          },
        ],
      },
    }
    renderBrowsePage()

    expect(await screen.findByRole('link', { name: 'Support Agent' })).toHaveAttribute(
      'href',
      '/enterprise-marketplace/asset-1',
    )
    expect(screen.getByText('Customer Service')).toBeInTheDocument()
  })
})
