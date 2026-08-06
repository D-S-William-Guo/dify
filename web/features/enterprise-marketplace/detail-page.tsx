'use client'

import { Button } from '@langgenius/dify-ui/button'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { CopyAssetAction } from './copy-asset-action'
import { mapMarketplaceError } from './errors'

function detailQueryRetry(failureCount: number, error: unknown) {
  if (error instanceof Response) return false

  return failureCount < 2
}

export function MarketplaceDetailPage({ assetId }: { assetId: string }) {
  const { t } = useTranslation()
  const query = useQuery(
    consoleQuery.enterpriseMarketplace.assets.byAssetId.get.queryOptions({
      input: { params: { asset_id: assetId } },
      retry: detailQueryRetry,
    }),
  )

  if (query.isPending) return <DetailSkeleton />

  if (query.isError) {
    const mapped = mapMarketplaceError(query.error)

    if (mapped.kind === 'notFound') {
      return (
        <DetailMessage
          message={t(($) => $['enterpriseMarketplace.detail.notFound'], { ns: 'common' })}
        />
      )
    }

    return (
      <DetailMessage
        message={t(($) => $['enterpriseMarketplace.detail.error'], { ns: 'common' })}
        onRetry={() => void query.refetch()}
      />
    )
  }

  const asset = query.data

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <div className="px-8 pt-4 pb-2">
        <h1 className="system-md-semibold text-text-primary">
          {t(($) => $['enterpriseMarketplace.detail.title'], { ns: 'common' })}
        </h1>
        <h2 className="mt-1 truncate system-xl-semibold text-text-primary">{asset.title}</h2>
      </div>
      <div className="min-h-0 grow px-8 pb-8">
        <dl className="grid gap-3 rounded-xl border border-components-panel-border bg-components-panel-bg p-4">
          <DetailField
            label={t(($) => $['enterpriseMarketplace.detail.description'], { ns: 'common' })}
          >
            {asset.description}
          </DetailField>
          <DetailField
            label={t(($) => $['enterpriseMarketplace.detail.category'], { ns: 'common' })}
          >
            {asset.category}
          </DetailField>
          <DetailField
            label={t(($) => $['enterpriseMarketplace.detail.scenario'], { ns: 'common' })}
          >
            {asset.scenario}
          </DetailField>
          <DetailField label={t(($) => $['enterpriseMarketplace.detail.tags'], { ns: 'common' })}>
            {asset.tags.length > 0 ? asset.tags.join(', ') : ''}
          </DetailField>
        </dl>
        <div className="mt-4">
          <CopyAssetAction assetId={assetId} />
        </div>
      </div>
    </div>
  )
}

function DetailField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="system-xs-medium text-text-tertiary">{label}</dt>
      <dd className="mt-1 system-sm-regular whitespace-pre-wrap text-text-primary">{children}</dd>
    </div>
  )
}

function DetailSkeleton() {
  const { t } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <div className="px-8 pt-4 pb-2">
        <div className="h-4 w-32 animate-pulse rounded bg-state-base-hover motion-reduce:animate-none" />
      </div>
      <div
        role="status"
        aria-label={t(($) => $['enterpriseMarketplace.detail.title'], { ns: 'common' })}
        className="min-h-0 grow px-8 pb-8"
      >
        <div className="flex h-64 animate-pulse flex-col gap-3 rounded-xl border border-components-panel-border bg-components-panel-bg p-4 motion-reduce:animate-none">
          <div className="h-4 w-2/3 rounded bg-state-base-hover" />
          <div className="h-4 w-1/2 rounded bg-state-base-hover" />
          <div className="h-4 w-3/4 rounded bg-state-base-hover" />
        </div>
      </div>
    </div>
  )
}

function DetailMessage({ message, onRetry }: { message: string; onRetry?: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="flex h-full min-h-0 flex-col items-center justify-center gap-3 bg-background-body">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
      {onRetry && (
        <Button type="button" size="small" variant="secondary" onClick={onRetry}>
          {t(($) => $['enterpriseMarketplace.detail.retry'], { ns: 'common' })}
        </Button>
      )}
    </div>
  )
}
