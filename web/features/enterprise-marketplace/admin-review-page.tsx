'use client'

import type { MarketplaceAssetResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import { Button } from '@langgenius/dify-ui/button'
import { Checkbox } from '@langgenius/dify-ui/checkbox'
import { Input } from '@langgenius/dify-ui/input'
import { Pagination } from '@langgenius/dify-ui/pagination'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useAtomValue } from 'jotai'
import { parseAsArrayOf, parseAsString, useQueryState } from 'nuqs'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { RbacUnavailableBanner } from '@/features/platform-admin/rbac-unavailable-banner'
import {
  isPlatformAdminAtom,
  platformAdminMutationSupportedAtom,
  platformAdminStatusErrorAtom,
  platformAdminStatusPendingAtom,
} from '@/features/platform-admin/state'
import { consoleQuery } from '@/service/client'
import { mapMarketplaceError } from './errors'
import {
  MARKETPLACE_PAGE_SIZE,
  marketplaceCategoryQueryState,
  marketplacePageQueryState,
  marketplaceSearchQueryState,
  marketplaceSortQueryState,
} from './marketplace-filters'
import { ReviewDialog } from './review-dialog'
import { SubmissionStatus } from './submission-status'
import { UnlistDialog } from './unlist-dialog'

const adminStatusQueryState = parseAsArrayOf(parseAsString).withDefault([])
const adminPublicationStatusQueryState = parseAsArrayOf(parseAsString).withDefault([])
const adminSnapshotStateQueryState = parseAsArrayOf(parseAsString).withDefault([])

const reviewStatusFilterOptions = [
  { value: 'pending', labelKey: 'enterpriseMarketplace.status.pending' },
  { value: 'approved', labelKey: 'enterpriseMarketplace.status.approved' },
  { value: 'rejected', labelKey: 'enterpriseMarketplace.status.rejected' },
] as const

const publicationStatusFilterOptions = [
  { value: 'published', labelKey: 'enterpriseMarketplace.status.published' },
  { value: 'unpublished', labelKey: 'enterpriseMarketplace.status.unpublished' },
  { value: 'unlisted', labelKey: 'enterpriseMarketplace.status.unlisted' },
] as const

function adminAssetsQueryRetry(failureCount: number, error: unknown) {
  if (error instanceof Response) return false

  return failureCount < 2
}

function resolveAdminListErrorMessage(error: unknown) {
  const mapped = mapMarketplaceError(error)

  return mapped.kind === 'unknown' ? 'enterpriseMarketplace.browse.error' : mapped.key
}

type ReviewTarget = {
  asset: MarketplaceAssetResponse
  decision: 'approved' | 'rejected'
}

export function AdminReviewPage() {
  const statusPending = useAtomValue(platformAdminStatusPendingAtom)
  const statusError = useAtomValue(platformAdminStatusErrorAtom)
  const isPlatformAdmin = useAtomValue(isPlatformAdminAtom)

  if (statusPending) return <AdminGateState kind="loading" />

  if (statusError || !isPlatformAdmin) return <AdminGateState kind="denied" />

  return <AdminReviewContent />
}

function AdminGateState({ kind }: { kind: 'loading' | 'denied' }) {
  const { t } = useTranslation()
  const message =
    kind === 'loading'
      ? t(($) => $['enterpriseMarketplace.browse.loading'], { ns: 'common' })
      : t(($) => $['enterpriseMarketplace.errors.permissionDenied'], { ns: 'common' })

  return (
    <div className="flex h-full min-h-0 flex-col items-center justify-center gap-3 bg-background-body">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
    </div>
  )
}

function AdminReviewContent() {
  const { t } = useTranslation()
  const mutationSupported = useAtomValue(platformAdminMutationSupportedAtom)
  const [page, setPage] = useQueryState('page', marketplacePageQueryState)
  const [search, setSearch] = useQueryState('search', marketplaceSearchQueryState)
  const [category, setCategory] = useQueryState('category', marketplaceCategoryQueryState)
  const [sort] = useQueryState('sort', marketplaceSortQueryState)
  const [status, setStatus] = useQueryState('status', adminStatusQueryState)
  const [publicationStatus, setPublicationStatus] = useQueryState(
    'publication_status',
    adminPublicationStatusQueryState,
  )
  const [snapshotState, setSnapshotState] = useQueryState(
    'snapshot_state',
    adminSnapshotStateQueryState,
  )
  const [reviewTarget, setReviewTarget] = useState<ReviewTarget | null>(null)
  const [unlistTarget, setUnlistTarget] = useState<MarketplaceAssetResponse | null>(null)

  const query = useQuery(
    consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.queryOptions({
      input: {
        query: {
          page,
          limit: MARKETPLACE_PAGE_SIZE,
          ...(search ? { keyword: search } : {}),
          ...(category ? { category } : {}),
          sort,
          ...(status.length > 0 ? { status } : {}),
          ...(publicationStatus.length > 0 ? { publication_status: publicationStatus } : {}),
          ...(snapshotState.length > 0 ? { snapshot_state: snapshotState } : {}),
        },
      },
      retry: adminAssetsQueryRetry,
      placeholderData: keepPreviousData,
    }),
  )

  const errorMessageKey = query.error ? resolveAdminListErrorMessage(query.error) : null
  const totalPages = query.data
    ? Math.max(1, Math.ceil(query.data.total / MARKETPLACE_PAGE_SIZE))
    : 1

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <div className="sticky top-0 z-10 flex flex-col gap-[14px] bg-background-body px-8 pt-4 pb-2">
        <div className="flex h-6 min-w-0 items-center">
          <h1 className="system-md-semibold text-text-primary">
            {t(($) => $['enterpriseMarketplace.review.title'], { ns: 'common' })}
          </h1>
        </div>
        <AdminReviewFilters
          search={search}
          onSearch={(nextSearch) => void setSearch(nextSearch)}
          category={category}
          categories={Array.from(
            new Set((query.data?.items ?? []).map((item) => item.category).filter(Boolean)),
          )}
          onCategory={(nextCategory) => void setCategory(nextCategory)}
          status={status}
          onStatus={(nextStatus) => void setStatus(nextStatus)}
          publicationStatus={publicationStatus}
          onPublicationStatus={(nextPublicationStatus) =>
            void setPublicationStatus(nextPublicationStatus)
          }
          snapshotState={snapshotState}
          onSnapshotState={(nextSnapshotState) => void setSnapshotState(nextSnapshotState)}
          onResetPage={() => void setPage(1)}
        />
      </div>
      {!mutationSupported && (
        <div className="px-8 pb-2">
          <RbacUnavailableBanner />
        </div>
      )}
      <div className="min-h-0 grow px-8 pb-8">
        {query.isPending ? (
          <AdminReviewSkeleton />
        ) : query.isError ? (
          <AdminReviewError
            message={t(($) => $[errorMessageKey ?? 'enterpriseMarketplace.browse.error'], {
              ns: 'common',
            })}
            onRetry={() => void query.refetch()}
          />
        ) : query.data.items.length === 0 ? (
          <AdminReviewEmpty />
        ) : (
          <div className="flex flex-col gap-4">
            <ul
              aria-label={t(($) => $['enterpriseMarketplace.review.title'], { ns: 'common' })}
              className="divide-y divide-divider-subtle rounded-xl border border-components-panel-border bg-components-panel-bg"
            >
              {query.data.items.map((asset) => (
                <li key={asset.asset_id} className="flex min-w-0 items-center gap-4 px-4 py-3">
                  <span className="min-w-0 grow truncate system-sm-medium text-text-primary">
                    {asset.title}
                  </span>
                  <span className="shrink-0 truncate system-xs-regular text-text-tertiary">
                    {asset.category}
                  </span>
                  <SubmissionStatus asset={asset} />
                  <div className="flex shrink-0 items-center gap-2">
                    <Button
                      type="button"
                      size="small"
                      variant="secondary"
                      disabled={!mutationSupported}
                      onClick={() => setReviewTarget({ asset, decision: 'approved' })}
                    >
                      {t(($) => $['enterpriseMarketplace.review.approve'], { ns: 'common' })}
                    </Button>
                    <Button
                      type="button"
                      size="small"
                      variant="secondary"
                      disabled={!mutationSupported}
                      onClick={() => setReviewTarget({ asset, decision: 'rejected' })}
                    >
                      {t(($) => $['enterpriseMarketplace.review.reject'], { ns: 'common' })}
                    </Button>
                    <Button
                      type="button"
                      size="small"
                      variant="secondary"
                      disabled={!mutationSupported}
                      onClick={() => setUnlistTarget(asset)}
                    >
                      {t(($) => $['enterpriseMarketplace.unlist.title'], { ns: 'common' })}
                    </Button>
                  </div>
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

      {reviewTarget && (
        <ReviewDialog
          key={`${reviewTarget.asset.asset_id}-${reviewTarget.decision}`}
          asset={reviewTarget.asset}
          decision={reviewTarget.decision}
          open
          onOpenChange={(open) => {
            if (!open) setReviewTarget(null)
          }}
        />
      )}
      {unlistTarget && (
        <UnlistDialog
          key={unlistTarget.asset_id}
          asset={unlistTarget}
          open
          onOpenChange={(open) => {
            if (!open) setUnlistTarget(null)
          }}
        />
      )}
    </div>
  )
}

type AdminReviewFiltersProps = {
  search: string
  onSearch: (search: string | null) => void
  category: string
  categories: string[]
  onCategory: (category: string | null) => void
  status: string[]
  onStatus: (status: string[] | null) => void
  publicationStatus: string[]
  onPublicationStatus: (publicationStatus: string[] | null) => void
  snapshotState: string[]
  onSnapshotState: (snapshotState: string[] | null) => void
  onResetPage: () => void
}

function AdminReviewFilters({
  search,
  onSearch,
  category,
  categories,
  onCategory,
  status,
  onStatus,
  publicationStatus,
  onPublicationStatus,
  snapshotState,
  onSnapshotState,
  onResetPage,
}: AdminReviewFiltersProps) {
  const { t } = useTranslation()
  const [searchDraft, setSearchDraft] = useState(search)

  function commitSearch() {
    const keyword = searchDraft.trim()
    onResetPage()
    onSearch(keyword || null)
  }

  function toggleStatusValue(value: string) {
    onResetPage()
    const next = status.includes(value)
      ? status.filter((item) => item !== value)
      : [...status, value]
    onStatus(next.length > 0 ? next : null)
  }

  function togglePublicationStatusValue(value: string) {
    onResetPage()
    const next = publicationStatus.includes(value)
      ? publicationStatus.filter((item) => item !== value)
      : [...publicationStatus, value]
    onPublicationStatus(next.length > 0 ? next : null)
  }

  function toggleSnapshotStateValue(value: string) {
    onResetPage()
    const next = snapshotState.includes(value)
      ? snapshotState.filter((item) => item !== value)
      : [...snapshotState, value]
    onSnapshotState(next.length > 0 ? next : null)
  }

  function selectCategory(value: string) {
    onResetPage()
    onCategory(value === '' ? null : value)
  }

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <form
        role="search"
        className="flex min-w-0 items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          commitSearch()
        }}
      >
        <Input
          aria-label={t(($) => $['enterpriseMarketplace.browse.searchPlaceholder'], {
            ns: 'common',
          })}
          className="h-8 w-60"
          placeholder={t(($) => $['enterpriseMarketplace.browse.searchPlaceholder'], {
            ns: 'common',
          })}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
        />
        <Button type="submit" size="small">
          {t(($) => $['enterpriseMarketplace.browse.searchButton'], { ns: 'common' })}
        </Button>
      </form>
      <label className="flex items-center gap-1.5 system-xs-regular text-text-secondary">
        <select
          aria-label={t(($) => $['enterpriseMarketplace.browse.categoryAll'], { ns: 'common' })}
          className="border-components-input-border h-8 rounded-lg border bg-components-input-bg-normal px-2 text-components-input-text-filled outline-hidden focus-visible:ring-2 focus-visible:ring-state-accent-solid"
          value={category}
          onChange={(event) => selectCategory(event.target.value)}
        >
          <option value="">
            {t(($) => $['enterpriseMarketplace.browse.categoryAll'], { ns: 'common' })}
          </option>
          {categories.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>
      </label>
      {reviewStatusFilterOptions.map((item) => (
        <label
          key={item.value}
          className="flex items-center gap-1.5 system-xs-regular text-text-secondary"
        >
          <Checkbox
            checked={status.includes(item.value)}
            onCheckedChange={() => toggleStatusValue(item.value)}
          />
          {t(($) => $[item.labelKey], { ns: 'common' })}
        </label>
      ))}
      {publicationStatusFilterOptions.map((item) => (
        <label
          key={item.value}
          className="flex items-center gap-1.5 system-xs-regular text-text-secondary"
        >
          <Checkbox
            checked={publicationStatus.includes(item.value)}
            onCheckedChange={() => togglePublicationStatusValue(item.value)}
          />
          {t(($) => $[item.labelKey], { ns: 'common' })}
        </label>
      ))}
      <label className="flex items-center gap-1.5 system-xs-regular text-text-secondary">
        <Checkbox
          checked={snapshotState.includes('error')}
          onCheckedChange={() => toggleSnapshotStateValue('error')}
        />
        {t(($) => $['enterpriseMarketplace.status.snapshotError'], { ns: 'common' })}
      </label>
    </div>
  )
}

function AdminReviewSkeleton() {
  const { t } = useTranslation()

  return (
    <div
      role="status"
      aria-label={t(($) => $['enterpriseMarketplace.browse.loading'], { ns: 'common' })}
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

function AdminReviewError({ message, onRetry }: { message: string; onRetry: () => void }) {
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

function AdminReviewEmpty() {
  const { t } = useTranslation()

  return (
    <p className="py-16 text-center system-sm-regular text-text-tertiary">
      {t(($) => $['enterpriseMarketplace.browse.empty'], { ns: 'common' })}
    </p>
  )
}
