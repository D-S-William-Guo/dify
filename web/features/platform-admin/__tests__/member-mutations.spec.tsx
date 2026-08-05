import type {
  PlatformAdminMemberListResponse,
  PlatformAdminMemberRoleUpdateResponse,
  PlatformAdminWorkspaceResponse,
} from '@dify/contracts/api/console/platform-admin/types.gen'
import type { ReactNode } from 'react'
import { toast } from '@langgenius/dify-ui/toast'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { Provider as JotaiProvider } from 'jotai'
import { queryClientAtom } from 'jotai-tanstack-query'
import { useHydrateAtoms } from 'jotai/react/utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WorkspaceDetailPage } from '../workspace-detail-page'

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
  workspace: { kind: 'success', data: undefined } as QueryMockState,
  members: { kind: 'success', data: undefined } as QueryMockState,
  renameFn: vi.fn(),
  inviteFn: vi.fn(),
  roleChangeFn: vi.fn(),
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
  const workspaceKey = (input: { params: { workspace_id: string } }) =>
    actual.consoleQuery.platformAdmin.workspaces.byWorkspaceId.get.queryKey({ input })
  const membersKey = (input: { params: { workspace_id: string } }) =>
    actual.consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.get.queryKey({ input })

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
              byWorkspaceId: {
                get: {
                  queryKey: workspaceKey,
                  queryOptions: (
                    options: { input?: { params: { workspace_id: string } } } = {},
                  ) => ({
                    ...options,
                    queryKey: workspaceKey(options.input!),
                    queryFn: createQueryFn(() => mockState.workspace),
                  }),
                },
                patch: {
                  mutationOptions: () => ({ mutationFn: mockState.renameFn, retry: false }),
                },
                members: {
                  get: {
                    queryKey: membersKey,
                    queryOptions: (
                      options: { input?: { params: { workspace_id: string } } } = {},
                    ) => ({
                      ...options,
                      queryKey: membersKey(options.input!),
                      queryFn: createQueryFn(() => mockState.members),
                    }),
                  },
                  invitations: {
                    post: {
                      mutationOptions: () => ({ mutationFn: mockState.inviteFn, retry: false }),
                    },
                  },
                  byMemberId: {
                    role: {
                      patch: {
                        mutationOptions: () => ({
                          mutationFn: mockState.roleChangeFn,
                          retry: false,
                        }),
                      },
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

function renderDetailPage() {
  const queryClient = createTestQueryClient()

  function Wrapper({ children }: { children: ReactNode }) {
    return (
      <JotaiProvider>
        <QueryClientProvider client={queryClient}>
          <QueryClientAtomHydrator queryClient={queryClient}>{children}</QueryClientAtomHydrator>
        </QueryClientProvider>
      </JotaiProvider>
    )
  }

  const result = render(
    <Wrapper>
      <WorkspaceDetailPage workspaceId="ws-1" />
    </Wrapper>,
  )

  return { ...result, queryClient }
}

const workspace: PlatformAdminWorkspaceResponse = {
  created_at: '2026-01-01T00:00:00Z',
  id: 'ws-1',
  member_count: 3,
  name: 'Alpha Workspace',
  owner: { email: 'owner1@example.com', id: 'user-1', name: 'Owner One' },
  plan: 'sandbox',
  status: 'normal',
  updated_at: '2026-01-01T00:00:00Z',
}

const memberList: PlatformAdminMemberListResponse = {
  mutation_supported: true,
  items: [
    {
      created_at: '2026-01-01T00:00:00Z',
      current: false,
      email: 'owner@example.com',
      id: 'm-1',
      last_active_at: null,
      last_login_at: null,
      mutation_supported: true,
      name: 'Owner One',
      role: 'owner',
      role_source: 'tenant_account_join',
      status: 'active',
    },
    {
      created_at: '2026-01-01T00:00:00Z',
      current: false,
      email: 'admin@example.com',
      id: 'm-2',
      last_active_at: null,
      last_login_at: null,
      mutation_supported: true,
      name: 'Admin Two',
      role: 'admin',
      role_source: 'tenant_account_join',
      status: 'active',
    },
  ],
}

const roleUpdateResponse: PlatformAdminMemberRoleUpdateResponse = {
  member_id: 'm-2',
  result: 'success',
  workspace_id: 'ws-1',
}

describe('platform-admin member mutations', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: true, mutation_supported: true },
    }
    mockState.workspace = { kind: 'success', data: workspace }
    mockState.members = { kind: 'success', data: memberList }
    mockState.renameFn.mockResolvedValue(workspace)
    mockState.inviteFn.mockResolvedValue({ workspace_id: 'ws-1', results: [] })
    mockState.roleChangeFn.mockResolvedValue(roleUpdateResponse)
    vi.spyOn(toast, 'success').mockReturnValue('toast-id')
    vi.spyOn(toast, 'error').mockReturnValue('toast-id')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('invites members with the default role and shows the per-email results', async () => {
    mockState.inviteFn.mockResolvedValue({
      workspace_id: 'ws-1',
      results: [
        { email: 'alice@example.com', action: 'invitation_queued', email_delivery: 'queued' },
      ],
    })
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.invite.title' }),
    )

    const dialog = await screen.findByRole('dialog', { name: 'common.platformAdmin.invite.title' })
    const recipientsInput = within(dialog).getByRole('textbox', {
      name: 'common.platformAdmin.invite.recipientsLabel',
    })
    await user.type(recipientsInput, 'alice@example.com')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.invite.send' }),
    )

    await waitFor(() => {
      expect(mockState.inviteFn).toHaveBeenCalledWith(
        {
          params: { workspace_id: 'ws-1' },
          body: {
            emails: ['alice@example.com'],
            role: 'admin',
            language: 'en-US',
          },
        },
        expect.any(Object),
      )
    })

    expect(
      await within(dialog).findByText('common.platformAdmin.invite.resultTitle'),
    ).toBeInTheDocument()
    expect(within(dialog).getByText('alice@example.com')).toBeInTheDocument()
    expect(
      within(dialog).getByText('common.platformAdmin.invite.status.pending'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByText('common.platformAdmin.invite.delivery.sent'),
    ).toBeInTheDocument()
  })

  it('invites with a selected member role', async () => {
    mockState.inviteFn.mockResolvedValue({
      workspace_id: 'ws-1',
      results: [
        { email: 'bob@example.com', action: 'membership_created', email_delivery: 'queued' },
      ],
    })
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.invite.title' }),
    )

    const dialog = await screen.findByRole('dialog', { name: 'common.platformAdmin.invite.title' })
    await user.type(
      within(dialog).getByRole('textbox', { name: 'common.platformAdmin.invite.recipientsLabel' }),
      'bob@example.com',
    )
    await user.click(
      within(dialog).getByRole('combobox', { name: 'common.platformAdmin.invite.roleLabel' }),
    )
    await user.click(
      await screen.findByRole('option', { name: 'common.platformAdmin.roles.member' }),
    )
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.invite.send' }),
    )

    await waitFor(() => {
      expect(mockState.inviteFn).toHaveBeenCalledWith(
        {
          params: { workspace_id: 'ws-1' },
          body: expect.objectContaining({ emails: ['bob@example.com'], role: 'normal' }),
        },
        expect.any(Object),
      )
    })
  })

  it('shows mixed delivery outcomes in the invitation results', async () => {
    mockState.inviteFn.mockResolvedValue({
      workspace_id: 'ws-1',
      results: [
        { email: 'ok@example.com', action: 'invitation_queued', email_delivery: 'queued' },
        { email: 'failed@example.com', action: 'membership_created', email_delivery: 'failed' },
      ],
    })
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.invite.title' }),
    )

    const dialog = await screen.findByRole('dialog', { name: 'common.platformAdmin.invite.title' })
    await user.type(
      within(dialog).getByRole('textbox', { name: 'common.platformAdmin.invite.recipientsLabel' }),
      'ok@example.com, failed@example.com',
    )
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.invite.send' }),
    )

    expect(await within(dialog).findByText('ok@example.com')).toBeInTheDocument()
    expect(within(dialog).getByText('failed@example.com')).toBeInTheDocument()
    expect(
      within(dialog).getByText('common.platformAdmin.invite.status.pending'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByText('common.platformAdmin.invite.status.activated'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByText('common.platformAdmin.invite.delivery.sent'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByText('common.platformAdmin.invite.delivery.failed'),
    ).toBeInTheDocument()
  })

  it('keeps the invite draft on a 503 and does not auto retry', async () => {
    mockState.inviteFn.mockRejectedValue(
      new Response(
        JSON.stringify({ code: 'rbac_mode_not_supported', message: 'Unavailable', status: 503 }),
        { status: 503 },
      ),
    )
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.invite.title' }),
    )

    const dialog = await screen.findByRole('dialog', { name: 'common.platformAdmin.invite.title' })
    const recipientsInput = within(dialog).getByRole('textbox', {
      name: 'common.platformAdmin.invite.recipientsLabel',
    })
    await user.type(recipientsInput, 'retry@example.com')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.invite.send' }),
    )

    expect(
      await within(dialog).findByText('common.platformAdmin.errors.serviceUnavailable'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByRole('textbox', { name: 'common.platformAdmin.invite.recipientsLabel' }),
    ).toHaveValue('retry@example.com')
    expect(mockState.inviteFn).toHaveBeenCalledTimes(1)
  })

  it('respects the owner guard and changes a non-owner member role', async () => {
    const user = userEvent.setup()
    renderDetailPage()

    await screen.findByText('admin@example.com')
    expect(
      screen.getByRole('button', { name: 'common.platformAdmin.changeRole.title Owner One' }),
    ).toBeDisabled()
    const changeRoleButton = screen.getByRole('button', {
      name: 'common.platformAdmin.changeRole.title Admin Two',
    })
    expect(changeRoleButton).toBeEnabled()

    await user.click(changeRoleButton)

    const dialog = await screen.findByRole('dialog', {
      name: 'common.platformAdmin.changeRole.title',
    })
    expect(
      within(dialog).getByText('common.platformAdmin.changeRole.confirmMessage'),
    ).toBeInTheDocument()
    await user.click(
      within(dialog).getByRole('combobox', { name: 'common.platformAdmin.members.roleLabel' }),
    )
    await user.click(
      await screen.findByRole('option', { name: 'common.platformAdmin.roles.member' }),
    )
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.changeRole.save' }),
    )

    await waitFor(() => {
      expect(mockState.roleChangeFn).toHaveBeenCalledWith(
        {
          params: { workspace_id: 'ws-1', member_id: 'm-2' },
          body: { role: 'normal' },
        },
        expect.any(Object),
      )
    })
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('common.platformAdmin.changeRole.success')
    })
  })

  it('disables role change for a member whose mutation is unsupported', async () => {
    mockState.members = {
      kind: 'success',
      data: {
        mutation_supported: true,
        items: [
          {
            created_at: '2026-01-01T00:00:00Z',
            current: false,
            email: 'locked@example.com',
            id: 'm-4',
            last_active_at: null,
            last_login_at: null,
            mutation_supported: false,
            name: 'Locked Member',
            role: 'admin',
            role_source: 'rbac_unavailable',
            status: 'active',
          },
        ],
      },
    }
    renderDetailPage()

    await screen.findByText('locked@example.com')
    expect(
      screen.getByRole('button', { name: 'common.platformAdmin.changeRole.title Locked Member' }),
    ).toBeDisabled()
  })

  it('keeps the role-change dialog open and preserves the selection on a 409', async () => {
    mockState.roleChangeFn.mockRejectedValue(
      new Response(JSON.stringify({ code: 'workspace_changed', message: 'Changed', status: 409 }), {
        status: 409,
      }),
    )
    const user = userEvent.setup()
    renderDetailPage()

    await screen.findByText('admin@example.com')
    await user.click(
      screen.getByRole('button', { name: 'common.platformAdmin.changeRole.title Admin Two' }),
    )

    const dialog = await screen.findByRole('dialog', {
      name: 'common.platformAdmin.changeRole.title',
    })
    await user.click(
      within(dialog).getByRole('combobox', { name: 'common.platformAdmin.members.roleLabel' }),
    )
    await user.click(
      await screen.findByRole('option', { name: 'common.platformAdmin.roles.member' }),
    )
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.changeRole.save' }),
    )

    expect(
      await within(dialog).findByText('common.platformAdmin.errors.conflict'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('dialog', { name: 'common.platformAdmin.changeRole.title' }),
    ).toBeInTheDocument()
  })
})
