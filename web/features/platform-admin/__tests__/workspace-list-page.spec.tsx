import type { PlatformAdminWorkspacePaginationResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider as JotaiProvider } from 'jotai'
import { queryClientAtom } from 'jotai-tanstack-query'
import { useHydrateAtoms } from 'jotai/react/utils'
import { NuqsTestingAdapter } from 'nuqs/adapters/testing'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorkspaceListPage } from '../workspace-list-page'

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
  workspaces: { kind: 'success', data: undefined } as QueryMockState,
  workspacesInputs: [] as unknown[],
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

  const statusKey = actual.consoleQuery.account.platformAdminStatus.get.queryKey()
  const workspacesKey = actual.consoleQuery.platformAdmin.workspaces.get.key()

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
            workspaces: {
              get: {
                queryKey: () => workspacesKey,
                queryOptions: (options: { input?: unknown } = {}) => {
                  mockState.workspacesInputs.push(options.input)
                  return {
                    ...options,
                    queryKey: workspacesKey,
                    queryFn: createQueryFn(() => mockState.workspaces),
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

function renderListPage(searchParams = '') {
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
      <WorkspaceListPage />
    </Wrapper>,
  )

  return { ...result, queryClient, onUrlUpdate }
}

const workspaceList: PlatformAdminWorkspacePaginationResponse = {
  has_more: false,
  items: [
    {
      created_at: '2026-01-01T00:00:00Z',
      id: 'ws-1',
      member_count: 3,
      name: 'Alpha Workspace',
      owner: { email: 'owner1@example.com', id: 'user-1', name: 'Owner One' },
      plan: 'sandbox',
      status: 'normal',
      updated_at: '2026-01-01T00:00:00Z',
    },
    {
      created_at: '2026-01-02T00:00:00Z',
      id: 'ws-2',
      member_count: 1,
      name: 'Beta Workspace',
      owner: { email: 'owner2@example.com', id: 'user-2', name: 'Owner Two' },
      plan: 'professional',
      status: 'archive',
      updated_at: '2026-01-02T00:00:00Z',
    },
  ],
  limit: 50,
  page: 1,
  total: 51,
}

describe('platform-admin workspace list page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: true, mutation_supported: true },
    }
    mockState.workspaces = { kind: 'success', data: workspaceList }
    mockState.workspacesInputs.length = 0
  })

  it('keeps the page fail closed while the status query is pending', () => {
    mockState.status = { kind: 'pending' }
    renderListPage()

    expect(screen.getByText('common.platformAdmin.errors.loading')).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Alpha Workspace' })).not.toBeInTheDocument()
  })

  it('fails closed for a non-admin deep link without rendering protected data', async () => {
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: false, mutation_supported: true },
    }
    renderListPage()

    expect(
      await screen.findByText('common.platformAdmin.errors.permissionDenied'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Alpha Workspace' })).not.toBeInTheDocument()
  })

  it('renders the workspace rows with detail links and status labels', async () => {
    renderListPage()

    expect(await screen.findByRole('link', { name: 'Alpha Workspace' })).toHaveAttribute(
      'href',
      '/platform-admin/workspaces/ws-1',
    )
    expect(screen.getByRole('link', { name: 'Beta Workspace' })).toHaveAttribute(
      'href',
      '/platform-admin/workspaces/ws-2',
    )
    expect(screen.getByText('Owner One')).toBeInTheDocument()
    const list = screen.getByRole('list', { name: 'common.platformAdmin.workspaces.title' })
    expect(
      within(list).getByText('common.platformAdmin.workspaces.filterNormal'),
    ).toBeInTheDocument()
    expect(
      within(list).getByText('common.platformAdmin.workspaces.filterArchived'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('heading', { name: 'common.platformAdmin.workspaces.title' }),
    ).toBeInTheDocument()
  })

  it('issues the list query with the fixed page size and the URL-driven filters', async () => {
    renderListPage('?search=alpha&status=archive&page=2')

    await waitFor(() => {
      expect(mockState.workspacesInputs.some((input) => input !== undefined)).toBe(true)
    })

    const inputs = mockState.workspacesInputs.filter((item) => item !== undefined) as Array<{
      query: Record<string, unknown>
    }>
    const input = inputs[0]!
    expect(input.query.page).toBe(2)
    expect(input.query.limit).toBe(50)
    expect(input.query.keyword).toBe('alpha')
    expect(input.query.status).toBe('archive')
  })

  it('shows a loading skeleton while the workspace list is pending', async () => {
    mockState.workspaces = { kind: 'pending' }
    renderListPage()

    expect(
      await screen.findByRole('status', { name: 'common.platformAdmin.workspaces.loading' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Alpha Workspace' })).not.toBeInTheDocument()
  })

  it('shows the empty state when the search has no results', async () => {
    mockState.workspaces = {
      kind: 'success',
      data: { ...workspaceList, items: [], total: 0 },
    }
    renderListPage()

    expect(await screen.findByText('common.platformAdmin.workspaces.empty')).toBeInTheDocument()
  })

  it('maps a 403 list failure to the permission-denied state and retries', async () => {
    mockState.workspaces = {
      kind: 'error',
      error: new Response(JSON.stringify({ code: 'forbidden', message: 'No', status: 403 }), {
        status: 403,
      }),
    }
    const user = userEvent.setup()
    renderListPage()

    expect(
      await screen.findByText('common.platformAdmin.errors.permissionDenied'),
    ).toBeInTheDocument()

    mockState.workspaces = { kind: 'success', data: workspaceList }
    await user.click(screen.getByRole('button', { name: 'common.platformAdmin.workspaces.retry' }))

    expect(await screen.findByRole('link', { name: 'Alpha Workspace' })).toBeInTheDocument()
  })

  it('updates the page in the URL when paginating', async () => {
    const user = userEvent.setup()
    const { onUrlUpdate } = renderListPage()

    await user.click(await screen.findByRole('button', { name: 'Next page' }))

    await waitFor(() => {
      const lastUpdate = onUrlUpdate.mock.calls.at(-1)?.[0]
      expect(lastUpdate?.searchParams.get('page')).toBe('2')
    })
  })

  it('resets to the first page and commits the search keyword', async () => {
    const user = userEvent.setup()
    const { onUrlUpdate } = renderListPage('?page=3')

    const searchInput = await screen.findByRole('textbox', {
      name: 'common.platformAdmin.workspaces.searchPlaceholder',
    })
    await user.type(searchInput, 'alpha')
    await user.click(
      screen.getByRole('button', { name: 'common.platformAdmin.workspaces.searchButton' }),
    )

    await waitFor(() => {
      const lastUpdate = onUrlUpdate.mock.calls.at(-1)?.[0]
      expect(lastUpdate?.searchParams.get('search')).toBe('alpha')
      expect(lastUpdate?.searchParams.has('page')).toBe(false)
    })
  })

  it('writes the selected status filter to the URL and resets the page', async () => {
    const user = userEvent.setup()
    const { onUrlUpdate } = renderListPage('?page=3')

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.workspaces.filterNormal' }),
    )

    await waitFor(() => {
      const lastUpdate = onUrlUpdate.mock.calls.at(-1)?.[0]
      expect(lastUpdate?.searchParams.get('status')).toBe('normal')
      expect(lastUpdate?.searchParams.has('page')).toBe(false)
    })
  })
})
