'use client'

import type { MarketplaceAssetResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import { useTranslation } from 'react-i18next'

const statusLabelKeyByValue = {
  pending: 'enterpriseMarketplace.status.pending',
  approved: 'enterpriseMarketplace.status.approved',
  rejected: 'enterpriseMarketplace.status.rejected',
} as const

const publicationStatusLabelKeyByValue = {
  published: 'enterpriseMarketplace.status.published',
  unpublished: 'enterpriseMarketplace.status.unpublished',
  unlisted: 'enterpriseMarketplace.status.unlisted',
} as const

function submissionStatusLabelKey(status: string) {
  return status in statusLabelKeyByValue
    ? statusLabelKeyByValue[status as keyof typeof statusLabelKeyByValue]
    : undefined
}

function publicationStatusLabelKey(publicationStatus: string) {
  return publicationStatus in publicationStatusLabelKeyByValue
    ? publicationStatusLabelKeyByValue[
        publicationStatus as keyof typeof publicationStatusLabelKeyByValue
      ]
    : undefined
}

function snapshotStateLabelKey(snapshotState: string) {
  return snapshotState === 'error' ? 'enterpriseMarketplace.status.snapshotError' : undefined
}

export function SubmissionStatus({ asset }: { asset: MarketplaceAssetResponse }) {
  const { t } = useTranslation()
  const statusKey = submissionStatusLabelKey(asset.status)
  const publicationKey = publicationStatusLabelKey(asset.publication_status)
  const snapshotKey = snapshotStateLabelKey(asset.snapshot_state)

  return (
    <span className="flex flex-wrap items-center gap-2 system-xs-regular text-text-tertiary">
      {statusKey && <span>{t(($) => $[statusKey], { ns: 'common' })}</span>}
      {publicationKey && <span>{t(($) => $[publicationKey], { ns: 'common' })}</span>}
      {snapshotKey && <span>{t(($) => $[snapshotKey], { ns: 'common' })}</span>}
    </span>
  )
}
