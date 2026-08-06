'use client'

import { Button } from '@langgenius/dify-ui/button'
import { Pagination } from '@langgenius/dify-ui/pagination'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useQueryState } from 'nuqs'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { consoleQuery } from '@/service/client'
import { mapMarketplaceError } from './errors'
import {
  MARKETPLACE_PAGE_SIZE,
  marketplaceCategoryQueryState,
  marketplacePageQueryState,
  marketplaceSearchQueryState,
  marketplaceSortQueryState,
} from './marketplace-filters'
import { ResubmitAction } from './resubmit-action'
import { SubmissionStatus } from './submission-status'

function submissionsQueryRetry(failureCount: number, error: unknown) {
  if (error instanceof Response) return false

  return failureCount < 2
}

function resolveSubmissionsErrorMessage(error: unknown) {
  const mapped = mapMarketplaceError(error)

  return mapped.kind === 'unknown' ? 'enterpriseMarketplace.submissions.error' : mapped.key
}

export function MySubmissionsPage() {
  const { t } = useTranslation()
  const [page, setPage] = useQueryState('page', marketplacePageQueryState)
  const [search] = useQueryState('search', marketplaceSearchQueryState)
  const [category] = useQueryState('category', marketplaceCategoryQueryState)
  const [sort] = useQueryState('sort', marketplaceSortQueryState)

  const query = useQuery(
    consoleQuery.enterpriseMarketplace.submissions.get.queryOptions({
      input: {
        query: {
          page,
          limit: MARKETPLACE_PAGE_SIZE,
          ...(search ? { keyword: search } : {}),
          ...(category ? { category } : {}),
          sort,
        },
      },
      retry: submissionsQueryRetry,
      placeholderData: keepPreviousData,
    }),
  )

  const errorMessageKey = query.error ? resolveSubmissionsErrorMessage(query.error) : null
  const totalPages = query.data
    ? Math.max(1, Math.ceil(query.data.total / MARKETPLACE_PAGE_SIZE))
    : 1

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <div className="sticky top-0 z-10 flex flex-col gap-[14px] bg-background-body px-8 pt-4 pb-2">
        <div className="flex h-6 min-w-0 items-center">
          <h1 className="system-md-semibold text-text-primary">
            {t(($) => $['enterpriseMarketplace.submissions.title'], { ns: 'common' })}
          </h1>
        </div>
      </div>
      <div className="min-h-0 grow px-8 pb-8">
        {query.isPending ? (
          <SubmissionsTableSkeleton />
        ) : query.isError ? (
          <SubmissionsError
            message={t(($) => $[errorMessageKey ?? 'enterpriseMarketplace.submissions.error'], {
              ns: 'common',
            })}
            onRetry={() => void query.refetch()}
          />
        ) : query.data.items.length === 0 ? (
          <SubmissionsEmpty />
        ) : (
          <div className="flex flex-col gap-4">
            <ul
              aria-label={t(($) => $['enterpriseMarketplace.submissions.title'], { ns: 'common' })}
              className="divide-y divide-divider-subtle rounded-xl border border-components-panel-border bg-components-panel-bg"
            >
              {query.data.items.map((asset) => (
                <li key={asset.asset_id} className="flex min-w-0 items-center gap-4 px-4 py-3">
                  <span className="min-w-0 grow truncate system-sm-medium text-text-primary">
                    {asset.title}
                  </span>
                  <SubmissionStatus asset={asset} />
                  <ResubmitAction asset={asset} />
                </li>
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

function SubmissionsTableSkeleton() {
  const { t } = useTranslation()

  return (
    <div
      role="status"
      aria-label={t(($) => $['enterpriseMarketplace.submissions.loading'], { ns: 'common' })}
      className="flex flex-col gap-2 rounded-xl border border-components-panel-border bg-components-panel-bg p-4"
    >
      {[0, 1, 2, 3].map((index) => (
        <div
          key={index}
          className="h-10 animate-pulse rounded-lg bg-state-base-hover motion-reduce:animate-none"
        />
      ))}
    </div>
  )
}

function SubmissionsError({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center gap-3 py-16">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
      <Button type="button" size="small" variant="secondary" onClick={onRetry}>
        {t(($) => $['enterpriseMarketplace.submissions.retry'], { ns: 'common' })}
      </Button>
    </div>
  )
}

function SubmissionsEmpty() {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center gap-3 py-16">
      <p className="system-sm-regular text-text-tertiary">
        {t(($) => $['enterpriseMarketplace.submissions.empty'], { ns: 'common' })}
      </p>
      <Link
        href="/apps"
        className="rounded-sm system-sm-medium text-text-accent outline-hidden hover:text-text-accent-secondary focus-visible:ring-2 focus-visible:ring-state-accent-solid"
      >
        {t(($) => $['enterpriseMarketplace.submissions.emptyCta'], { ns: 'common' })}
      </Link>
    </div>
  )
}
