'use client'

import { Button } from '@langgenius/dify-ui/button'
import { Pagination } from '@langgenius/dify-ui/pagination'
import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useAtomValue } from 'jotai'
import { useQueryState } from 'nuqs'
import { useTranslation } from 'react-i18next'
import { StudioListHeader } from '@/app/components/apps/studio-list-header'
import { consoleQuery } from '@/service/client'
import { mapPlatformAdminError } from './errors'
import {
  isPlatformAdminAtom,
  platformAdminStatusErrorAtom,
  platformAdminStatusPendingAtom,
} from './state'
import {
  WORKSPACE_PAGE_SIZE,
  WorkspaceFilters,
  workspacePageQueryState,
  workspaceSearchQueryState,
  workspaceStatusQueryState,
} from './workspace-filters'
import { WorkspaceTable } from './workspace-table'

function workspaceListQueryRetry(failureCount: number, error: unknown) {
  if (error instanceof Response) return false

  return failureCount < 2
}

function resolveListErrorMessage(error: unknown) {
  const mapped = mapPlatformAdminError(error)

  return mapped.kind === 'unknown' ? 'platformAdmin.workspaces.error' : mapped.key
}

export function WorkspaceListPage() {
  const statusPending = useAtomValue(platformAdminStatusPendingAtom)
  const statusError = useAtomValue(platformAdminStatusErrorAtom)
  const isPlatformAdmin = useAtomValue(isPlatformAdminAtom)

  if (statusPending) return <PageGateState kind="loading" />

  if (statusError || !isPlatformAdmin) return <PageGateState kind="denied" />

  return <WorkspaceListContent />
}

function PageGateState({ kind }: { kind: 'loading' | 'denied' }) {
  const { t } = useTranslation()
  const message =
    kind === 'loading'
      ? t(($) => $['platformAdmin.errors.loading'], { ns: 'common' })
      : t(($) => $['platformAdmin.errors.permissionDenied'], { ns: 'common' })

  return (
    <div className="flex h-full min-h-0 flex-col items-center justify-center gap-3 bg-background-body">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
    </div>
  )
}

function WorkspaceListContent() {
  const { t } = useTranslation()
  const [page, setPage] = useQueryState('page', workspacePageQueryState)
  const [search] = useQueryState('search', workspaceSearchQueryState)
  const [status] = useQueryState('status', workspaceStatusQueryState)

  const query = useQuery(
    consoleQuery.platformAdmin.workspaces.get.queryOptions({
      input: {
        query: {
          page,
          limit: WORKSPACE_PAGE_SIZE,
          ...(search ? { keyword: search } : {}),
          ...(status !== 'all' ? { status } : {}),
        },
      },
      retry: workspaceListQueryRetry,
      placeholderData: keepPreviousData,
    }),
  )

  const errorMessageKey = query.error ? resolveListErrorMessage(query.error) : null
  const totalPages = query.data ? Math.max(1, Math.ceil(query.data.total / WORKSPACE_PAGE_SIZE)) : 1

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <StudioListHeader
        title={
          <h1 className="system-md-semibold text-text-primary">
            {t(($) => $['platformAdmin.workspaces.title'], { ns: 'common' })}
          </h1>
        }
      >
        <WorkspaceFilters />
      </StudioListHeader>
      <div className="min-h-0 grow px-8 pb-8">
        {query.isPending ? (
          <WorkspaceListSkeleton />
        ) : query.isError ? (
          <WorkspaceListError
            message={t(($) => $[errorMessageKey ?? 'platformAdmin.workspaces.error'], {
              ns: 'common',
            })}
            onRetry={() => void query.refetch()}
          />
        ) : query.data.items.length === 0 ? (
          <WorkspaceListEmpty />
        ) : (
          <div className="flex flex-col gap-4">
            <WorkspaceTable items={query.data.items} />
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

function WorkspaceListSkeleton() {
  const { t } = useTranslation()

  return (
    <div
      role="status"
      aria-label={t(($) => $['platformAdmin.workspaces.loading'], { ns: 'common' })}
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

function WorkspaceListError({ message, onRetry }: { message: string; onRetry: () => void }) {
  const { t } = useTranslation()

  return (
    <div className="flex flex-col items-center gap-3 py-16">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
      <Button type="button" size="small" variant="secondary" onClick={onRetry}>
        {t(($) => $['platformAdmin.workspaces.retry'], { ns: 'common' })}
      </Button>
    </div>
  )
}

function WorkspaceListEmpty() {
  const { t } = useTranslation()

  return (
    <p className="py-16 text-center system-sm-regular text-text-tertiary">
      {t(($) => $['platformAdmin.workspaces.empty'], { ns: 'common' })}
    </p>
  )
}
