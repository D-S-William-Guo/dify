import type {
  PlatformAdminMemberListResponse,
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
    {
      created_at: '2026-01-01T00:00:00Z',
      current: false,
      email: 'member@example.com',
      id: 'm-3',
      last_active_at: null,
      last_login_at: null,
      mutation_supported: true,
      name: 'Member Three',
      role: 'normal',
      role_source: 'tenant_account_join',
      status: 'active',
    },
  ],
}

describe('platform-admin workspace detail page', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: true, mutation_supported: true },
    }
    mockState.workspace = { kind: 'success', data: workspace }
    mockState.members = { kind: 'success', data: memberList }
    mockState.renameFn.mockResolvedValue({ ...workspace, name: 'Renamed' })
    mockState.inviteFn.mockResolvedValue({ workspace_id: 'ws-1', results: [] })
    mockState.roleChangeFn.mockResolvedValue({
      member_id: 'm-2',
      result: 'success',
      workspace_id: 'ws-1',
    })
    vi.spyOn(toast, 'success').mockReturnValue('toast-id')
    vi.spyOn(toast, 'error').mockReturnValue('toast-id')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the workspace name and the member rows with roles', async () => {
    renderDetailPage()

    expect(
      await screen.findByRole('heading', { name: 'common.platformAdmin.workspaceDetail.title' }),
    ).toBeInTheDocument()
    expect(screen.getByText('Alpha Workspace')).toBeInTheDocument()
    expect(screen.getByText('common.platformAdmin.members.title')).toBeInTheDocument()
    expect(screen.getByText('owner@example.com')).toBeInTheDocument()
    expect(screen.getByText('admin@example.com')).toBeInTheDocument()
    expect(screen.getByText('common.platformAdmin.roles.owner')).toBeInTheDocument()
    expect(screen.getByText('common.platformAdmin.roles.admin')).toBeInTheDocument()
  })

  it('shows the not-found state when the workspace does not exist', async () => {
    mockState.workspace = {
      kind: 'error',
      error: new Response(JSON.stringify({ code: 'workspace_not_found', message: 'Missing' }), {
        status: 404,
      }),
    }
    renderDetailPage()

    expect(await screen.findByText('common.platformAdmin.errors.notFound')).toBeInTheDocument()
    expect(screen.queryByText('Alpha Workspace')).not.toBeInTheDocument()
  })

  it('shows a members loading indicator while members are pending', async () => {
    mockState.members = { kind: 'pending' }
    renderDetailPage()

    expect(
      await screen.findByRole('status', { name: 'common.platformAdmin.members.loading' }),
    ).toBeInTheDocument()
  })

  it('shows a retryable member error without triggering a side effect', async () => {
    mockState.members = {
      kind: 'error',
      error: new Response(
        JSON.stringify({ code: 'rbac_mode_not_supported', message: 'Unavailable', status: 503 }),
        { status: 503 },
      ),
    }
    const user = userEvent.setup()
    renderDetailPage()

    expect(
      await screen.findByText('common.platformAdmin.errors.serviceUnavailable'),
    ).toBeInTheDocument()

    mockState.members = { kind: 'success', data: memberList }
    await user.click(screen.getByRole('button', { name: 'common.platformAdmin.members.retry' }))

    expect(await screen.findByText('owner@example.com')).toBeInTheDocument()
  })

  it('shows the RBAC banner and disables mutation controls when mutation support is off', async () => {
    mockState.members = {
      kind: 'success',
      data: { ...memberList, mutation_supported: false },
    }
    renderDetailPage()

    expect(
      await screen.findByText('common.platformAdmin.rbacUnavailable.title'),
    ).toBeInTheDocument()
    expect(screen.getByText('common.platformAdmin.rbacUnavailable.message')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'common.platformAdmin.renameWorkspace.title' }),
    ).toBeDisabled()
    expect(screen.getByRole('button', { name: 'common.platformAdmin.invite.title' })).toBeDisabled()
    const roleChangeButtons = screen.getAllByRole('button', {
      name: /^common\.platformAdmin\.changeRole\.title /,
    })
    expect(roleChangeButtons.length).toBeGreaterThan(0)
    roleChangeButtons.forEach((button) => expect(button).toBeDisabled())
  })

  it('fails closed for a non-admin deep link', async () => {
    mockState.status = {
      kind: 'success',
      data: { is_platform_admin: false, mutation_supported: true },
    }
    renderDetailPage()

    expect(
      await screen.findByText('common.platformAdmin.errors.permissionDenied'),
    ).toBeInTheDocument()
    expect(screen.queryByText('Alpha Workspace')).not.toBeInTheDocument()
  })

  it('renames the workspace from the rename dialog', async () => {
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.renameWorkspace.title' }),
    )

    const dialog = await screen.findByRole('dialog', {
      name: 'common.platformAdmin.renameWorkspace.title',
    })
    const nameInput = within(dialog).getByRole('textbox', {
      name: 'common.platformAdmin.renameWorkspace.nameLabel',
    })
    expect(nameInput).toHaveValue('Alpha Workspace')

    await user.clear(nameInput)
    await user.type(nameInput, 'Renamed Workspace')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.renameWorkspace.save' }),
    )

    await waitFor(() => {
      expect(mockState.renameFn).toHaveBeenCalledWith(
        {
          params: { workspace_id: 'ws-1' },
          body: { name: 'Renamed Workspace' },
        },
        expect.any(Object),
      )
    })
    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('common.platformAdmin.renameWorkspace.success')
    })
    await waitFor(() => {
      expect(
        screen.queryByRole('dialog', { name: 'common.platformAdmin.renameWorkspace.title' }),
      ).not.toBeInTheDocument()
    })
  })

  it('keeps the rename draft and shows the conflict message on a 409', async () => {
    mockState.renameFn.mockRejectedValue(
      new Response(JSON.stringify({ code: 'workspace_changed', message: 'Changed', status: 409 }), {
        status: 409,
      }),
    )
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.renameWorkspace.title' }),
    )

    const dialog = await screen.findByRole('dialog', {
      name: 'common.platformAdmin.renameWorkspace.title',
    })
    const nameInput = within(dialog).getByRole('textbox', {
      name: 'common.platformAdmin.renameWorkspace.nameLabel',
    })
    await user.clear(nameInput)
    await user.type(nameInput, 'Draft Name')
    await user.click(
      within(dialog).getByRole('button', { name: 'common.platformAdmin.renameWorkspace.save' }),
    )

    expect(
      await within(dialog).findByText('common.platformAdmin.renameWorkspace.conflict'),
    ).toBeInTheDocument()
    expect(
      within(dialog).getByRole('textbox', {
        name: 'common.platformAdmin.renameWorkspace.nameLabel',
      }),
    ).toHaveValue('Draft Name')
  })

  it('disables duplicate rename submits while the mutation is pending', async () => {
    mockState.renameFn.mockImplementation(() => new Promise(() => {}))
    const user = userEvent.setup()
    renderDetailPage()

    await user.click(
      await screen.findByRole('button', { name: 'common.platformAdmin.renameWorkspace.title' }),
    )

    const dialog = await screen.findByRole('dialog', {
      name: 'common.platformAdmin.renameWorkspace.title',
    })
    const nameInput = within(dialog).getByRole('textbox', {
      name: 'common.platformAdmin.renameWorkspace.nameLabel',
    })
    const saveButton = within(dialog).getByRole('button', {
      name: 'common.platformAdmin.renameWorkspace.save',
    })
    await user.clear(nameInput)
    await user.type(nameInput, 'New Name')
    await user.click(saveButton)

    await waitFor(() => expect(mockState.renameFn).toHaveBeenCalledTimes(1))
    await waitFor(() => expect(saveButton).toHaveAttribute('aria-disabled', 'true'))
    await user.click(saveButton)
    expect(mockState.renameFn).toHaveBeenCalledTimes(1)
  })
})
