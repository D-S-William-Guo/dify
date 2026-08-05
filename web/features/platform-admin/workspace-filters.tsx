/* oxlint-disable react/only-export-components -- the nuqs query-state parsers are shared constants consumed by the workspace list page and the filters surface. */
'use client'

import { Button } from '@langgenius/dify-ui/button'
import { Input } from '@langgenius/dify-ui/input'
import { SegmentedControl, SegmentedControlItem } from '@langgenius/dify-ui/segmented-control'
import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryState } from 'nuqs'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export const WORKSPACE_PAGE_SIZE = 50

export const WORKSPACE_STATUS_VALUES = ['all', 'normal', 'archive'] as const
export type WorkspaceStatusFilter = (typeof WORKSPACE_STATUS_VALUES)[number]

export const workspacePageQueryState = parseAsInteger.withDefault(1)
export const workspaceSearchQueryState = parseAsString.withDefault('')
export const workspaceStatusQueryState = parseAsStringEnum<WorkspaceStatusFilter>([
  ...WORKSPACE_STATUS_VALUES,
]).withDefault('all')

export function WorkspaceFilters() {
  const { t } = useTranslation()
  const [search, setSearch] = useQueryState('search', workspaceSearchQueryState)
  const [status, setStatus] = useQueryState('status', workspaceStatusQueryState)
  const [_page, setPage] = useQueryState('page', workspacePageQueryState)
  const [searchDraft, setSearchDraft] = useState(search)

  function commitSearch() {
    const keyword = searchDraft.trim()

    void setPage(1)
    void setSearch(keyword || null)
  }

  function commitStatus(nextStatus: WorkspaceStatusFilter) {
    void setPage(1)
    void setStatus(nextStatus === 'all' ? null : nextStatus)
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
          aria-label={t(($) => $['platformAdmin.workspaces.searchPlaceholder'], { ns: 'common' })}
          className="h-8 w-60"
          placeholder={t(($) => $['platformAdmin.workspaces.searchPlaceholder'], { ns: 'common' })}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
        />
        <Button type="submit" size="small">
          {t(($) => $['platformAdmin.workspaces.searchButton'], { ns: 'common' })}
        </Button>
      </form>
      <SegmentedControl
        value={[status]}
        onValueChange={(value) => {
          const nextStatus = value[0]
          if (nextStatus) commitStatus(nextStatus)
        }}
      >
        <SegmentedControlItem value="all">
          {t(($) => $['platformAdmin.workspaces.filterAll'], { ns: 'common' })}
        </SegmentedControlItem>
        <SegmentedControlItem value="normal">
          {t(($) => $['platformAdmin.workspaces.filterNormal'], { ns: 'common' })}
        </SegmentedControlItem>
        <SegmentedControlItem value="archive">
          {t(($) => $['platformAdmin.workspaces.filterArchived'], { ns: 'common' })}
        </SegmentedControlItem>
      </SegmentedControl>
    </div>
  )
}
