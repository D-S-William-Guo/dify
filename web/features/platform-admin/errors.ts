import type {
  GetPlatformAdminWorkspacesByWorkspaceIdError,
  GetPlatformAdminWorkspacesByWorkspaceIdMembersError,
  GetPlatformAdminWorkspacesError,
  PatchPlatformAdminWorkspacesByWorkspaceIdError,
  PatchPlatformAdminWorkspacesByWorkspaceIdMembersByMemberIdRoleError,
  PlatformAdminErrorResponse,
  PostPlatformAdminWorkspacesByWorkspaceIdMembersInvitationsError,
  UnauthorizedResponse,
} from '@dify/contracts/api/console/platform-admin/types.gen'

export type PlatformAdminOperationError =
  | GetPlatformAdminWorkspacesError
  | GetPlatformAdminWorkspacesByWorkspaceIdError
  | PatchPlatformAdminWorkspacesByWorkspaceIdError
  | GetPlatformAdminWorkspacesByWorkspaceIdMembersError
  | PostPlatformAdminWorkspacesByWorkspaceIdMembersInvitationsError
  | PatchPlatformAdminWorkspacesByWorkspaceIdMembersByMemberIdRoleError

const platformAdminErrorKindByStatus = {
  401: 'unauthorized',
  403: 'permissionDenied',
  404: 'notFound',
  409: 'conflict',
  503: 'serviceUnavailable',
} as const

export type PlatformAdminKnownErrorKind =
  (typeof platformAdminErrorKindByStatus)[keyof typeof platformAdminErrorKindByStatus]

const platformAdminErrorKeyByKind = {
  unauthorized: 'platformAdmin.errors.unauthorized',
  permissionDenied: 'platformAdmin.errors.permissionDenied',
  notFound: 'platformAdmin.errors.notFound',
  conflict: 'platformAdmin.errors.conflict',
  serviceUnavailable: 'platformAdmin.errors.serviceUnavailable',
} as const

export type PlatformAdminErrorKey =
  (typeof platformAdminErrorKeyByKind)[keyof typeof platformAdminErrorKeyByKind]

export type PlatformAdminErrorResult =
  | {
      kind: PlatformAdminKnownErrorKind
      key: PlatformAdminErrorKey
      status: number
    }
  | {
      kind: 'unknown'
      status?: number
    }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

export function isUnauthorizedResponse(value: unknown): value is UnauthorizedResponse {
  return (
    isRecord(value) &&
    typeof value.code === 'string' &&
    typeof value.message === 'string' &&
    !('status' in value)
  )
}

export function isPlatformAdminErrorResponse(value: unknown): value is PlatformAdminErrorResponse {
  return (
    isRecord(value) &&
    typeof value.code === 'string' &&
    typeof value.message === 'string' &&
    typeof value.status === 'number'
  )
}

export function isPlatformAdminOperationError(
  value: unknown,
): value is PlatformAdminOperationError {
  return isUnauthorizedResponse(value) || isPlatformAdminErrorResponse(value)
}

function isPlatformAdminErrorStatus(
  status: number,
): status is keyof typeof platformAdminErrorKindByStatus {
  return status in platformAdminErrorKindByStatus
}

export function mapPlatformAdminError(error: unknown): PlatformAdminErrorResult {
  const transportStatus = error instanceof Response ? error.status : undefined
  const domainStatus = isPlatformAdminErrorResponse(error) ? error.status : undefined
  const status = transportStatus ?? domainStatus

  if (status === undefined) return { kind: 'unknown' }

  if (!isPlatformAdminErrorStatus(status)) return { kind: 'unknown', status }

  const kind = platformAdminErrorKindByStatus[status]
  return { kind, key: platformAdminErrorKeyByKind[kind], status }
}
