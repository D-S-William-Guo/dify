import type {
  Member,
  PlatformAdminWorkspaceCreateResponse,
  PlatformAdminWorkspaceListResponse,
} from '@/models/common'
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  createPlatformAdminWorkspace,
  deletePlatformAdminWorkspace,
  deleteMemberOrCancelInvitation,
  fetchMembers,
  fetchPlatformAdminWorkspaces,
  inviteMember,
  patchPlatformAdminWorkspace,
  updateMemberRole,
} from './common'

type PlatformAdminWorkspaceQueryParams = {
  keyword?: string
}

type CreateWorkspacePayload = {
  name: string
  owner_email?: string
  owner_name?: string
}

type InviteWorkspaceMembersPayload = {
  emails: string[]
  role: Exclude<Member['role'], 'owner'>
  language: string
}

type UpdateWorkspaceMemberRolePayload = {
  memberId: string
  role: Exclude<Member['role'], 'owner'>
}

const platformAdminWorkspaceListStaleTime = 30 * 1000
const platformAdminWorkspaceMemberListStaleTime = 15 * 1000

export const platformAdminKeys = {
  all: ['platform-admin'] as const,
  workspaces: () => [...platformAdminKeys.all, 'workspaces'] as const,
  workspaceList: (params: PlatformAdminWorkspaceQueryParams) => [...platformAdminKeys.workspaces(), params] as const,
  workspaceMembers: (workspaceId: string) => [...platformAdminKeys.all, 'workspace-members', workspaceId] as const,
}

const invalidatePlatformAdminWorkspaces = (queryClient: ReturnType<typeof useQueryClient>) => {
  return queryClient.invalidateQueries({
    queryKey: platformAdminKeys.workspaces(),
  })
}

const invalidatePlatformAdminWorkspaceMembers = (
  queryClient: ReturnType<typeof useQueryClient>,
  workspaceId: string,
) => {
  if (!workspaceId)
    return Promise.resolve()

  return queryClient.invalidateQueries({
    queryKey: platformAdminKeys.workspaceMembers(workspaceId),
    exact: true,
  })
}

export const usePlatformAdminWorkspaces = (
  params: PlatformAdminWorkspaceQueryParams,
  enabled: boolean,
) => {
  return useQuery<PlatformAdminWorkspaceListResponse>({
    queryKey: platformAdminKeys.workspaceList(params),
    queryFn: () => fetchPlatformAdminWorkspaces({
      url: '/platform-admin/workspaces',
      params: {
        page: 1,
        limit: 200,
        keyword: params.keyword,
      },
    }),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: platformAdminWorkspaceListStaleTime,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}

export const usePlatformAdminWorkspaceMembers = (
  workspaceId: string,
  enabled: boolean,
) => {
  return useQuery<{ accounts: Member[] | null }>({
    queryKey: platformAdminKeys.workspaceMembers(workspaceId),
    queryFn: () => fetchMembers({
      url: `/platform-admin/workspaces/${workspaceId}/members`,
      params: {},
    }),
    enabled,
    staleTime: platformAdminWorkspaceMemberListStaleTime,
    refetchOnWindowFocus: false,
    refetchOnReconnect: false,
  })
}

export const useCreatePlatformAdminWorkspace = () => {
  const queryClient = useQueryClient()

  return useMutation<PlatformAdminWorkspaceCreateResponse, Error, CreateWorkspacePayload>({
    mutationFn: body => createPlatformAdminWorkspace({
      url: '/platform-admin/workspaces',
      body,
    }),
    onSuccess: async () => {
      await invalidatePlatformAdminWorkspaces(queryClient)
    },
  })
}

export const useRenamePlatformAdminWorkspace = (workspaceId: string) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (name: string) => patchPlatformAdminWorkspace({
      url: `/platform-admin/workspaces/${workspaceId}`,
      body: { name },
    }),
    onSuccess: async () => {
      await invalidatePlatformAdminWorkspaces(queryClient)
    },
  })
}

export const useDeletePlatformAdminWorkspace = () => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (workspaceId: string) => deletePlatformAdminWorkspace({
      url: `/platform-admin/workspaces/${workspaceId}`,
    }),
    onSuccess: async () => {
      await invalidatePlatformAdminWorkspaces(queryClient)
    },
  })
}

export const useInvitePlatformAdminWorkspaceMembers = (workspaceId: string) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (body: InviteWorkspaceMembersPayload) => inviteMember({
      url: `/platform-admin/workspaces/${workspaceId}/members/invite`,
      body,
    }),
    onSuccess: async () => {
      await Promise.all([
        invalidatePlatformAdminWorkspaces(queryClient),
        invalidatePlatformAdminWorkspaceMembers(queryClient, workspaceId),
      ])
    },
  })
}

export const useUpdatePlatformAdminWorkspaceMemberRole = (workspaceId: string) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ memberId, role }: UpdateWorkspaceMemberRolePayload) => updateMemberRole({
      url: `/platform-admin/workspaces/${workspaceId}/members/${memberId}/role`,
      body: { role },
    }),
    onSuccess: async () => {
      await invalidatePlatformAdminWorkspaceMembers(queryClient, workspaceId)
    },
  })
}

export const useDeletePlatformAdminWorkspaceMember = (workspaceId: string) => {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (memberId: string) => deleteMemberOrCancelInvitation({
      url: `/platform-admin/workspaces/${workspaceId}/members/${memberId}`,
    }),
    onSuccess: async () => {
      await Promise.all([
        invalidatePlatformAdminWorkspaces(queryClient),
        invalidatePlatformAdminWorkspaceMembers(queryClient, workspaceId),
      ])
    },
  })
}
