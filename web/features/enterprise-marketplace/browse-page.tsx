'use client'

import { Button } from '@langgenius/dify-ui/button'
import { Pagination } from '@langgenius/dify-ui/pagination'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useQueryState } from 'nuqs'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { mapMarketplaceError } from './errors'
import { MarketplaceCard } from './marketplace-card'
import {
  MARKETPLACE_PAGE_SIZE,
  marketplaceCategoryQueryState,
  MarketplaceFilters,
  marketplacePageQueryState,
  marketplaceSearchQueryState,
  marketplaceSortQueryState,
} from './marketplace-filters'

function marketplaceListQueryRetry(failureCount: number, error: unknown) {
  if (error instanceof Response) return false

  return failureCount < 2
}

function resolveListErrorMessage(error: unknown) {
  const mapped = mapMarketplaceError(error)

  return mapped.kind === 'unknown' ? 'enterpriseMarketplace.browse.error' : mapped.key
}

export function MarketplaceBrowsePage() {
  const { t } = useTranslation()
  const [page, setPage] = useQueryState('page', marketplacePageQueryState)
  const [search] = useQueryState('search', marketplaceSearchQueryState)
  const [category] = useQueryState('category', marketplaceCategoryQueryState)
  const [sort] = useQueryState('sort', marketplaceSortQueryState)

  const query = useQuery(
    consoleQuery.enterpriseMarketplace.assets.get.queryOptions({
      input: {
        query: {
          page,
          limit: MARKETPLACE_PAGE_SIZE,
          ...(search ? { keyword: search } : {}),
          ...(category ? { category } : {}),
          sort,
        },
      },
      retry: marketplaceListQueryRetry,
      placeholderData: keepPreviousData,
    }),
  )

  const categories = Array.from(
    new Set((query.data?.items ?? []).map((item) => item.category).filter(Boolean)),
  )
  const errorMessageKey = query.error ? resolveListErrorMessage(query.error) : null
  const totalPages = query.data
    ? Math.max(1, Math.ceil(query.data.total / MARKETPLACE_PAGE_SIZE))
    : 1

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <div className="sticky top-0 z-10 flex flex-col gap-[14px] bg-background-body px-8 pt-4 pb-2">
        <div className="flex h-6 min-w-0 items-center">
          <h1 className="system-md-semibold text-text-primary">
            {t(($) => $['enterpriseMarketplace.browse.title'], { ns: 'common' })}
          </h1>
        </div>
        <MarketplaceFilters categories={categories} />
      </div>
      <div className="min-h-0 grow px-8 pb-8">
        {query.isPending ? (
          <MarketplaceGridSkeleton />
        ) : query.isError ? (
          <MarketplaceListError
            message={t(($) => $[errorMessageKey ?? 'enterpriseMarketplace.browse.error'], {
              ns: 'common',
            })}
            onRetry={() => void query.refetch()}
          />
        ) : query.data.items.length === 0 ? (
          <MarketplaceListEmpty />
        ) : (
          <div className="flex flex-col gap-4">
            <ul
              aria-label={t(($) => $['enterpriseMarketplace.browse.title'], { ns: 'common' })}
              className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3"
            >
              {query.data.items.map((asset) => (
                <MarketplaceCard key={asset.asset_id} asset={asset} />
              ))}
            </ul>
            <Pagination
              page={page}
              totalPages={totalPages}
              onPageChange={(nextPage) => void setPage(nextPage)}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function MarketplaceGridSkeleton() {
  const { t } = useTranslation()

  return (
    <div
      role="status"
      aria-label={t(($) => $['enterpriseMarketplace.browse.loading'], { ns: 'common' })}
      className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3"
    >
      {[0, 1, 2].map((index) => (
        <div
          key={index}
          className="h-32 animate-pulse rounded-xl border border-components-panel-border bg-components-panel-bg p-4 motion-reduce:animate-none"
        />
      ))}
    </div>
  )
}

function MarketplaceListError({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center gap-3 py-16">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
      <Button type="button" size="small" variant="secondary" onClick={onRetry}>
        {t(($) => $['enterpriseMarketplace.browse.retry'], { ns: 'common' })}
      </Button>
    </div>
  )
}

function MarketplaceListEmpty() {
  const { t } = useTranslation()

  return (
    <p className="py-16 text-center system-sm-regular text-text-tertiary">
      {t(($) => $['enterpriseMarketplace.browse.empty'], { ns: 'common' })}
    </p>
  )
}
