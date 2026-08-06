import type {
  MarketplaceCopyResponse,
  MarketplaceSnapshotDetailResponse,
} from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type { ReactNode } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { MarketplaceDetailPage } from '../detail-page'

type QueryMockState = {
  kind: 'pending' | 'success' | 'error'
  data?: unknown
  error?: unknown
}

const routerPushMock = vi.hoisted(() => vi.fn())

const mockState = vi.hoisted(() => ({
  detail: { kind: 'success', data: undefined } as QueryMockState,
  copyFn: vi.fn(),
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

  const detailKey = (input: { params: { asset_id: string } }) =>
    actual.consoleQuery.enterpriseMarketplace.assets.byAssetId.get.queryKey({ input })

  return {
    ...actual,
    consoleQuery: new Proxy(actual.consoleQuery, {
      get(target, prop, receiver) {
        if (prop === 'enterpriseMarketplace') {
          return {
            assets: {
              byAssetId: {
                get: {
                  queryKey: detailKey,
                  queryOptions: (options: { input?: { params: { asset_id: string } } } = {}) => ({
                    ...options,
                    queryKey: detailKey(options.input!),
                    queryFn: createQueryFn(() => mockState.detail),
                  }),
                },
                copies: {
                  post: {
                    mutationOptions: () => ({ mutationFn: mockState.copyFn, retry: false }),
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

vi.mock('@/next/navigation', () => ({
  useRouter: () => ({
    push: routerPushMock,
  }),
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

function renderDetailPage() {
  const queryClient = createTestQueryClient()

  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  }

  const result = render(
    <Wrapper>
      <MarketplaceDetailPage assetId="asset-1" />
    </Wrapper>,
  )

  return { ...result, queryClient }
}

const snapshotDetail: MarketplaceSnapshotDetailResponse = {
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
}

const copyResponse: MarketplaceCopyResponse = {
  app_id: 'new-app-1',
  content_sha256: 'abc123',
  import_status: 'completed',
  snapshot_version: 2,
  warnings: ['Plugin dependency skipped.'],
}

async function openCopyConfirmDialog(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    await screen.findByRole('button', { name: 'common.enterpriseMarketplace.detail.copy' }),
  )
  return screen.findByRole('dialog', { name: 'common.enterpriseMarketplace.copy.confirmTitle' })
}

describe('enterprise-marketplace detail and copy', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.detail = { kind: 'success', data: snapshotDetail }
    mockState.copyFn.mockResolvedValue(copyResponse)
  })

  it('renders the immutable snapshot fields', async () => {
    renderDetailPage()

    expect(
      await screen.findByRole('heading', { name: 'common.enterpriseMarketplace.detail.title' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Support Agent')).toBeInTheDocument()
    expect(screen.getByText('A customer service assistant.')).toBeInTheDocument()
    expect(screen.getByText('Customer Service')).toBeInTheDocument()
    expect(screen.getByText('Support')).toBeInTheDocument()
    expect(screen.getByText('support, chat')).toBeInTheDocument()
  })

  it('shows the not-found state for a 404 without a retry action', async () => {
    mockState.detail = {
      kind: 'error',
      error: new Response(JSON.stringify({ code: 'not_found', message: 'No', status: 404 }), {
        status: 404,
      }),
    }
    renderDetailPage()

    expect(
      await screen.findByText('common.enterpriseMarketplace.detail.notFound'),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('button', { name: 'common.enterpriseMarketplace.detail.retry' }),
    ).not.toBeInTheDocument()
  })

  it('shows a retryable error for a transient detail failure', async () => {
    mockState.detail = {
      kind: 'error',
      error: new Response(
        JSON.stringify({ code: 'service_unavailable', message: 'Down', status: 503 }),
        { status: 503 },
      ),
    }
    const user = userEvent.setup()
    renderDetailPage()

    expect(await screen.findByText('common.enterpriseMarketplace.detail.error')).toBeInTheDocument()

    mockState.detail = { kind: 'success', data: snapshotDetail }
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.detail.retry' }),
    )

    expect(await screen.findByText('Support Agent')).toBeInTheDocument()
  })

  it('copies the asset and navigates to the new app overview with warnings visible', async () => {
    const user = userEvent.setup()
    renderDetailPage()

    const dialog = await openCopyConfirmDialog(user)
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.copy.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.copyFn).toHaveBeenCalledWith(
        { params: { asset_id: 'asset-1' }, body: {} },
        expect.any(Object),
      )
    })

    expect(
      await screen.findByText('common.enterpriseMarketplace.copy.warningsTitle'),
    ).toBeInTheDocument()
    expect(screen.getByText('Plugin dependency skipped.')).toBeInTheDocument()
    await user.click(
      screen.getByRole('button', { name: 'common.enterpriseMarketplace.copy.navigateToApp' }),
    )
    expect(routerPushMock).toHaveBeenCalledWith('/app/new-app-1/overview')
  })

  it('does not trigger a second copy while the first is pending', async () => {
    let resolveCopy: ((value: MarketplaceCopyResponse) => void) | undefined
    mockState.copyFn.mockImplementation(
      () =>
        new Promise<MarketplaceCopyResponse>((resolve) => {
          resolveCopy = resolve
        }),
    )
    const user = userEvent.setup()
    renderDetailPage()

    const dialog = await openCopyConfirmDialog(user)
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.copy.confirm' }),
    )

    await waitFor(() => {
      expect(mockState.copyFn).toHaveBeenCalledTimes(1)
    })

    const processingButton = within(dialog).getByRole('button', {
      name: 'common.enterpriseMarketplace.copy.processing',
    })
    expect(processingButton).toHaveAttribute('aria-disabled', 'true')
    await user.click(processingButton)

    expect(mockState.copyFn).toHaveBeenCalledTimes(1)

    await act(async () => {
      resolveCopy?.(copyResponse)
    })
    expect(
      await screen.findByText('common.enterpriseMarketplace.copy.warningsTitle'),
    ).toBeInTheDocument()
  })

  it('keeps the confirm dialog open and shows the conflict error on a copy 409', async () => {
    mockState.copyFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'stale_asset_version', message: 'Changed', status: 409 }),
        { status: 409 },
      ),
    )
    const user = userEvent.setup()
    renderDetailPage()

    const dialog = await openCopyConfirmDialog(user)
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.copy.confirm' }),
    )

    expect(
      await screen.findByText('common.enterpriseMarketplace.copy.error.conflict'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('dialog', { name: 'common.enterpriseMarketplace.copy.confirmTitle' }),
    ).toBeInTheDocument()
    expect(mockState.copyFn).toHaveBeenCalledTimes(1)
  })

  it('shows the validation error on a copy 422', async () => {
    mockState.copyFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'snapshot_contains_secret', message: 'Invalid', status: 422 }),
        { status: 422 },
      ),
    )
    const user = userEvent.setup()
    renderDetailPage()

    const dialog = await openCopyConfirmDialog(user)
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.copy.confirm' }),
    )

    expect(
      await screen.findByText('common.enterpriseMarketplace.copy.error.validation'),
    ).toBeInTheDocument()
  })

  it('shows the service-unavailable error on a copy 503', async () => {
    mockState.copyFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'rbac_mode_not_supported', message: 'Down', status: 503 }),
        { status: 503 },
      ),
    )
    const user = userEvent.setup()
    renderDetailPage()

    const dialog = await openCopyConfirmDialog(user)
    await user.click(
      within(dialog).getByRole('button', { name: 'common.enterpriseMarketplace.copy.confirm' }),
    )

    expect(
      await screen.findByText('common.enterpriseMarketplace.copy.error.serviceUnavailable'),
    ).toBeInTheDocument()
  })
})
