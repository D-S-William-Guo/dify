import type { MarketplaceAssetPaginationResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { NuqsTestingAdapter } from 'nuqs/adapters/testing'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MySubmissionsPage } from '../my-submissions-page'

type QueryMockState = {
  kind: 'pending' | 'success' | 'error'
  data?: unknown
  error?: unknown
}

const mockState = vi.hoisted(() => ({
  submissions: { kind: 'success', data: undefined } as QueryMockState,
  submissionsFetches: 0,
  resubmitFn: vi.fn(),
}))

vi.mock('@/service/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/service/client')>()

  function createQueryFn(getMock: () => QueryMockState) {
    return () => {
      mockState.submissionsFetches += 1
      const mock = getMock()
      if (mock.kind === 'pending') return new Promise(() => {})
      if (mock.kind === 'error') return Promise.reject(mock.error)
      return Promise.resolve(mock.data)
    }
  }

  const submissionsKey = actual.consoleQuery.enterpriseMarketplace.submissions.get.key()

  return {
    ...actual,
    consoleQuery: new Proxy(actual.consoleQuery, {
      get(target, prop, receiver) {
        if (prop === 'enterpriseMarketplace') {
          return {
            submissions: {
              get: {
                queryKey: () => submissionsKey,
                key: () => submissionsKey,
                queryOptions: (options: { input?: unknown } = {}) => ({
                  ...options,
                  queryKey: submissionsKey,
                  queryFn: createQueryFn(() => mockState.submissions),
                }),
              },
            },
          }
        }
        if (prop === 'apps') {
          return {
            byAppId: {
              enterpriseMarketplace: {
                submissions: {
                  post: {
                    mutationOptions: () => ({ mutationFn: mockState.resubmitFn, retry: false }),
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

function renderSubmissionsPage(searchParams = '') {
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
      <MySubmissionsPage />
    </Wrapper>,
  )

  return { ...result, queryClient, onUrlUpdate }
}

const submissionsList: MarketplaceAssetPaginationResponse = {
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
      tags: ['support', 'chat'],
      title: 'Support Agent',
      updated_at: '2026-01-02T00:00:00Z',
    },
    {
      allow_show_workspace_name: true,
      asset_id: 'asset-2',
      category: 'Data Analysis',
      created_at: '2026-01-03T00:00:00Z',
      description: 'Summarizes spreadsheets.',
      publication_status: 'published',
      review_note: 'Looks good',
      reviewed_at: '2026-01-04T00:00:00Z',
      reviewer_account_id: 'admin-1',
      row_version: 5,
      scenario: 'Analysis',
      snapshot_error_code: null,
      snapshot_state: 'succeeded',
      source_app_id: 'src-app-2',
      source_tenant_id: 'tenant-a',
      status: 'approved',
      submitter_account_id: 'user-1',
      tags: ['data'],
      title: 'Data Summarizer',
      updated_at: '2026-01-04T00:00:00Z',
    },
  ],
  limit: 24,
  page: 1,
  total: 2,
}

describe('enterprise-marketplace my submissions', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.submissions = { kind: 'success', data: submissionsList }
    mockState.submissionsFetches = 0
    mockState.resubmitFn.mockResolvedValue(submissionsList.items[0])
  })

  it('shows a table skeleton while the submissions are pending', async () => {
    mockState.submissions = { kind: 'pending' }
    renderSubmissionsPage()

    expect(
      await screen.findByRole('status', {
        name: 'common.enterpriseMarketplace.submissions.loading',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'common.enterpriseMarketplace.submissions.resubmit' }),
    ).not.toBeInTheDocument()
  })

  it('renders the submission rows with status labels and resubmit actions', async () => {
    renderSubmissionsPage()

    expect(await screen.findByText('Support Agent')).toBeInTheDocument()
    expect(screen.getByText('Data Summarizer')).toBeInTheDocument()
    expect(screen.getByText('common.enterpriseMarketplace.status.pending')).toBeInTheDocument()
    expect(screen.getByText('common.enterpriseMarketplace.status.approved')).toBeInTheDocument()
    expect(screen.getByText('common.enterpriseMarketplace.status.unpublished')).toBeInTheDocument()
    expect(screen.getByText('common.enterpriseMarketplace.status.published')).toBeInTheDocument()
    expect(
      screen.getAllByRole('button', { name: 'common.enterpriseMarketplace.submissions.resubmit' }),
    ).toHaveLength(2)
  })

  it('shows the empty state with a call-to-action link when there are no submissions', async () => {
    mockState.submissions = {
      kind: 'success',
      data: { ...submissionsList, items: [], total: 0 },
    }
    renderSubmissionsPage()

    expect(
      await screen.findByText('common.enterpriseMarketplace.submissions.empty'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: 'common.enterpriseMarketplace.submissions.emptyCta' }),
    ).toHaveAttribute('href', '/apps')
  })

  it('renders no invented label for an unknown status value', async () => {
    mockState.submissions = {
      kind: 'success',
      data: {
        ...submissionsList,
        items: [
          {
            ...submissionsList.items[0]!,
            status: 'unknown-status',
            publication_status: 'unknown-publication',
          },
        ],
      },
    }
    renderSubmissionsPage()

    expect(await screen.findByText('Support Agent')).toBeInTheDocument()
    expect(
      screen.queryByText('common.enterpriseMarketplace.status.pending'),
    ).not.toBeInTheDocument()
  })

  it('opens the dedicated resubmit dialog only from the resubmit action', async () => {
    const user = userEvent.setup()
    renderSubmissionsPage()

    const resubmitButtons = await screen.findAllByRole('button', {
      name: 'common.enterpriseMarketplace.submissions.resubmit',
    })
    await user.click(resubmitButtons[0]!)

    expect(
      await screen.findByRole('dialog', {
        name: 'common.enterpriseMarketplace.resubmitDialog.title',
      }),
    ).toBeInTheDocument()
    expect(
      screen.queryByText('common.enterpriseMarketplace.submitDialog.title'),
    ).not.toBeInTheDocument()
  })

  it('sends the current row version with the resubmit payload', async () => {
    const user = userEvent.setup()
    renderSubmissionsPage()

    const resubmitButtons = await screen.findAllByRole('button', {
      name: 'common.enterpriseMarketplace.submissions.resubmit',
    })
    await user.click(resubmitButtons[0]!)

    const dialog = await screen.findByRole('dialog', {
      name: 'common.enterpriseMarketplace.resubmitDialog.title',
    })
    await user.click(
      within(dialog).getByRole('button', {
        name: 'common.enterpriseMarketplace.resubmitDialog.confirm',
      }),
    )

    await waitFor(() => {
      expect(mockState.resubmitFn).toHaveBeenCalledWith(
        {
          params: { app_id: 'src-app-1' },
          body: expect.objectContaining({
            title: 'Support Agent',
            category: 'Customer Service',
            tags: ['support', 'chat'],
            expected_row_version: 3,
          }),
        },
        expect.any(Object),
      )
    })
  })

  it('preserves the draft, refetches the current row, and does not auto-replay on a 409', async () => {
    mockState.resubmitFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'stale_asset_version', message: 'Changed', status: 409 }),
        { status: 409 },
      ),
    )
    const user = userEvent.setup()
    renderSubmissionsPage()

    const resubmitButtons = await screen.findAllByRole('button', {
      name: 'common.enterpriseMarketplace.submissions.resubmit',
    })
    await user.click(resubmitButtons[0]!)

    const dialog = await screen.findByRole('dialog', {
      name: 'common.enterpriseMarketplace.resubmitDialog.title',
    })
    const titleInput = within(dialog).getByRole('textbox', {
      name: 'common.enterpriseMarketplace.detail.title',
    })
    await user.clear(titleInput)
    await user.type(titleInput, 'My Edited Title')
    await user.click(
      within(dialog).getByRole('button', {
        name: 'common.enterpriseMarketplace.resubmitDialog.confirm',
      }),
    )

    await waitFor(() => {
      expect(mockState.resubmitFn).toHaveBeenCalledTimes(1)
    })

    expect(
      await screen.findByText('common.enterpriseMarketplace.resubmitDialog.conflict'),
    ).toBeInTheDocument()
    expect(
      screen.getByText('common.enterpriseMarketplace.resubmitDialog.conflictMessage'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.title' }),
    ).toHaveValue('My Edited Title')
    await waitFor(() => {
      expect(mockState.submissionsFetches).toBeGreaterThanOrEqual(2)
    })
    expect(mockState.resubmitFn).toHaveBeenCalledTimes(1)
  })
})
