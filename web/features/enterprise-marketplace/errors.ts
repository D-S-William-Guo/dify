import type { PostAppsByAppIdEnterpriseMarketplaceSubmissionsError } from '@dify/contracts/api/console/apps/types.gen'
import type {
  GetEnterpriseMarketplaceAssetsByAssetIdError,
  GetEnterpriseMarketplaceAssetsError,
  GetEnterpriseMarketplaceSubmissionsError,
  MarketplaceErrorResponse,
  PostEnterpriseMarketplaceAssetsByAssetIdCopiesError,
  UnauthorizedResponse,
} from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type {
  GetPlatformAdminEnterpriseMarketplaceAssetsError,
  PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdReviewsError,
  PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdUnlistError,
} from '@dify/contracts/api/console/platform-admin/types.gen'

export type MarketplaceOperationError =
  | GetEnterpriseMarketplaceAssetsError
  | GetEnterpriseMarketplaceAssetsByAssetIdError
  | GetEnterpriseMarketplaceSubmissionsError
  | PostEnterpriseMarketplaceAssetsByAssetIdCopiesError
  | GetPlatformAdminEnterpriseMarketplaceAssetsError
  | PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdReviewsError
  | PostPlatformAdminEnterpriseMarketplaceAssetsByAssetIdUnlistError
  | PostAppsByAppIdEnterpriseMarketplaceSubmissionsError

const marketplaceErrorKindByStatus = {
  401: 'unauthorized',
  403: 'permissionDenied',
  404: 'notFound',
  409: 'conflict',
  422: 'validation',
  503: 'serviceUnavailable',
} as const

export type MarketplaceKnownErrorKind =
  (typeof marketplaceErrorKindByStatus)[keyof typeof marketplaceErrorKindByStatus]

const marketplaceErrorKeyByKind = {
  unauthorized: 'enterpriseMarketplace.errors.unauthorized',
  permissionDenied: 'enterpriseMarketplace.errors.permissionDenied',
  notFound: 'enterpriseMarketplace.errors.notFound',
  conflict: 'enterpriseMarketplace.errors.conflict',
  validation: 'enterpriseMarketplace.errors.validation',
  serviceUnavailable: 'enterpriseMarketplace.errors.serviceUnavailable',
} as const

export type MarketplaceErrorKey =
  (typeof marketplaceErrorKeyByKind)[keyof typeof marketplaceErrorKeyByKind]

export type MarketplaceErrorResult =
  | {
      kind: MarketplaceKnownErrorKind
      key: MarketplaceErrorKey
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

export function isMarketplaceErrorResponse(value: unknown): value is MarketplaceErrorResponse {
  return (
    isRecord(value) &&
    typeof value.code === 'string' &&
    typeof value.message === 'string' &&
    typeof value.status === 'number'
  )
}

export function isMarketplaceOperationError(value: unknown): value is MarketplaceOperationError {
  return isUnauthorizedResponse(value) || isMarketplaceErrorResponse(value)
}

function isMarketplaceErrorStatus(
  status: number,
): status is keyof typeof marketplaceErrorKindByStatus {
  return status in marketplaceErrorKindByStatus
}

export function mapMarketplaceError(error: unknown): MarketplaceErrorResult {
  const transportStatus = error instanceof Response ? error.status : undefined
  const domainStatus = isMarketplaceErrorResponse(error) ? error.status : undefined
  const status = transportStatus ?? domainStatus

  if (status === undefined) return { kind: 'unknown' }

  if (!isMarketplaceErrorStatus(status)) return { kind: 'unknown', status }

  const kind = marketplaceErrorKindByStatus[status]
  return { kind, key: marketplaceErrorKeyByKind[kind], status }
}
