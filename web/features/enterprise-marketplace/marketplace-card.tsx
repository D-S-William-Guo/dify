'use client'

import type { MarketplaceSnapshotResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'

export function MarketplaceCard({ asset }: { asset: MarketplaceSnapshotResponse }) {
  const { t } = useTranslation()
  const detailHref = `/enterprise-marketplace/${asset.asset_id}`

  return (
    <li className="col-span-1 flex flex-col overflow-hidden rounded-xl border-[0.5px] border-components-panel-border bg-components-panel-on-panel-item-bg p-4 shadow-xs shadow-shadow-shadow-3">
      <div className="flex min-w-0 items-center justify-between gap-3">
        <Link
          href={detailHref}
          className="min-w-0 truncate rounded-sm system-md-semibold text-text-primary outline-hidden hover:text-text-accent focus-visible:ring-2 focus-visible:ring-state-accent-solid"
        >
          {asset.title}
        </Link>
        <span className="shrink-0 system-xs-regular text-text-tertiary">{asset.category}</span>
      </div>
      <p className="mt-2 line-clamp-2 min-h-8 flex-1 system-xs-regular text-text-tertiary">
        {asset.description}
      </p>
      <div className="mt-3 flex items-center justify-between gap-2">
        <span className="flex min-w-0 flex-wrap items-center gap-1">
          {asset.tags.slice(0, 3).map((tag) => (
            <span
              key={tag}
              className="truncate rounded-sm bg-state-base-hover px-1.5 py-0.5 system-2xs-medium text-text-tertiary"
            >
              {tag}
            </span>
          ))}
        </span>
        <Link
          href={detailHref}
          className="shrink-0 rounded-sm system-xs-medium text-text-accent outline-hidden hover:text-text-accent-secondary focus-visible:ring-2 focus-visible:ring-state-accent-solid"
        >
          {t(($) => $['enterpriseMarketplace.card.viewDetail'], { ns: 'common' })}
        </Link>
      </div>
    </li>
  )
}
