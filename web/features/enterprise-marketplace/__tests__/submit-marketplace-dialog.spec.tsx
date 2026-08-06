import type { MarketplaceAssetResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { consoleQuery } from '@/service/client'
import { SubmitMarketplaceDialog } from '../submit-marketplace-dialog'

const mockState = vi.hoisted(() => ({
  submitFn: vi.fn(),
}))

vi.mock('@/service/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/service/client')>()
  const realOptions =
    actual.consoleQuery.apps.byAppId.enterpriseMarketplace.submissions.post.mutationOptions()

  return {
    ...actual,
    consoleQuery: new Proxy(actual.consoleQuery, {
      get(target, prop, receiver) {
        if (prop === 'apps') {
          return {
            byAppId: {
              enterpriseMarketplace: {
                submissions: {
                  post: {
                    mutationOptions: () => ({ ...realOptions, mutationFn: mockState.submitFn }),
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

const toastMocks = vi.hoisted(() => {
  const record = vi.fn()
  return {
    record,
    api: Object.assign(vi.fn(), {
      success: vi.fn((message: unknown) => record({ type: 'success', message })),
      error: vi.fn((message: unknown) => record({ type: 'error', message })),
    }),
  }
})

vi.mock('@langgenius/dify-ui/toast', () => ({
  toast: toastMocks.api,
}))

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

const submittedAsset: MarketplaceAssetResponse = {
  allow_show_workspace_name: true,
  asset_id: 'asset-1',
  category: 'Customer Service',
  created_at: '2026-01-01T00:00:00Z',
  description: 'A customer service assistant.',
  publication_status: 'unpublished',
  review_note: null,
  reviewed_at: null,
  reviewer_account_id: null,
  row_version: 1,
  scenario: 'Support',
  snapshot_error_code: null,
  snapshot_state: 'succeeded',
  source_app_id: 'app-1',
  source_tenant_id: 'tenant-a',
  status: 'pending',
  submitter_account_id: 'user-1',
  tags: ['support'],
  title: 'My App',
  updated_at: '2026-01-02T00:00:00Z',
}

function renderSubmitDialog(queryClient = createTestQueryClient()) {
  const onOpenChange = vi.fn()

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  const result = render(
    <Wrapper>
      <SubmitMarketplaceDialog appId="app-1" open onOpenChange={onOpenChange} />
    </Wrapper>,
  )

  return { ...result, queryClient, onOpenChange }
}

async function fillRequiredFields(title = 'My App', category = 'Customer Service') {
  const user = userEvent.setup()
  await user.type(
    screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.title' }),
    title,
  )
  await user.type(
    screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.category' }),
    category,
  )
  return user
}

describe('enterprise-marketplace first-submit dialog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.submitFn.mockResolvedValue(submittedAsset)
  })

  it('keeps the confirm button disabled until the required title and category are filled', async () => {
    renderSubmitDialog()

    const confirmButton = screen.getByRole('button', {
      name: 'common.enterpriseMarketplace.submitDialog.confirm',
    })
    expect(confirmButton).toBeDisabled()

    await userEvent.type(
      screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.title' }),
      'My App',
    )
    expect(confirmButton).toBeDisabled()

    await userEvent.type(
      screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.category' }),
      'Customer Service',
    )
    expect(confirmButton).toBeEnabled()
  })

  it('submits the first-submit payload without expected_row_version', async () => {
    renderSubmitDialog()
    const user = await fillRequiredFields()
    await user.type(
      screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.description' }),
      'A customer service assistant.',
    )
    await user.type(
      screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.scenario' }),
      'Support',
    )
    await user.type(
      screen.getByRole('textbox', { name: 'common.enterpriseMarketplace.detail.tags' }),
      'support, chat',
    )

    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.submitDialog.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.submitFn).toHaveBeenCalledWith(
        {
          params: { app_id: 'app-1' },
          body: expect.objectContaining({
            title: 'My App',
            category: 'Customer Service',
            description: 'A customer service assistant.',
            scenario: 'Support',
            tags: ['support', 'chat'],
          }),
        },
        expect.any(Object),
      )
    })

    const submitCall = mockState.submitFn.mock.calls[0]![0] as { body: Record<string, unknown> }
    expect(submitCall.body).not.toHaveProperty('expected_row_version')
  })

  it('invalidates the real submissions and admin asset query keys after a successful submit', async () => {
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
          gcTime: Infinity,
          staleTime: Infinity,
          queryFn: () => new Promise(() => {}),
        },
        mutations: { retry: false },
      },
    })
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
    const { onOpenChange } = renderSubmitDialog(queryClient)

    const user = await fillRequiredFields()
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.submitDialog.confirm' }),
    )

    await waitFor(() => {
      expect(queryClient.getQueryState(submissionsKey)?.isInvalidated).toBe(true)
    })
    expect(queryClient.getQueryState(adminAssetsKey)?.isInvalidated).toBe(true)
    expect(onOpenChange).toHaveBeenCalledWith(false)
    expect(toastMocks.record).toHaveBeenCalledWith({
      type: 'success',
      message: 'common.enterpriseMarketplace.submitDialog.success',
    })
  })

  it('does not fire a second submit while the first one is pending', async () => {
    let resolveSubmit: (value: MarketplaceAssetResponse) => void = () => {}
    mockState.submitFn.mockImplementation(
      () => new Promise<MarketplaceAssetResponse>((resolve) => (resolveSubmit = resolve)),
    )
    renderSubmitDialog()

    const user = await fillRequiredFields()
    const confirmButton = screen.getByRole('button', {
      name: 'common.enterpriseMarketplace.submitDialog.confirm',
    })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(mockState.submitFn).toHaveBeenCalledTimes(1)
    })
    expect(confirmButton).toHaveAttribute('aria-disabled', 'true')

    await user.click(confirmButton)
    expect(mockState.submitFn).toHaveBeenCalledTimes(1)

    resolveSubmit(submittedAsset)
    await waitFor(() => {
      expect(toastMocks.record).toHaveBeenCalledWith({
        type: 'success',
        message: 'common.enterpriseMarketplace.submitDialog.success',
      })
    })
  })

  it('keeps the dialog open and shows the mapped error when the submit fails', async () => {
    mockState.submitFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'stale_asset_version', message: 'Changed', status: 409 }),
        { status: 409 },
      ),
    )
    const { onOpenChange } = renderSubmitDialog()

    const user = await fillRequiredFields()
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.submitDialog.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.submitFn).toHaveBeenCalledTimes(1)
    })
    expect(
      await screen.findByText('common.enterpriseMarketplace.errors.conflict'),
    ).toBeInTheDocument()
    expect(onOpenChange).not.toHaveBeenCalled()
    expect(
      screen.getByRole('dialog', { name: 'common.enterpriseMarketplace.submitDialog.title' }),
    ).toBeInTheDocument()
  })

  it('keeps the dialog open without an invented message or auto-replay on an unknown error', async () => {
    mockState.submitFn.mockRejectedValue(new Response('bad request', { status: 400 }))
    const { onOpenChange } = renderSubmitDialog()

    const user = await fillRequiredFields()
    const confirmButton = screen.getByRole('button', {
      name: 'common.enterpriseMarketplace.submitDialog.confirm',
    })
    await user.click(confirmButton)

    await waitFor(() => {
      expect(mockState.submitFn).toHaveBeenCalledTimes(1)
    })
    expect(onOpenChange).not.toHaveBeenCalled()
    expect(
      screen.getByRole('dialog', { name: 'common.enterpriseMarketplace.submitDialog.title' }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()

    await user.click(confirmButton)
    expect(mockState.submitFn).toHaveBeenCalledTimes(2)
  })
})
