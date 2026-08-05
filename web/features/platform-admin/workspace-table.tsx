'use client'

import type { PlatformAdminWorkspaceResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'

export function WorkspaceTable({ items }: { items: PlatformAdminWorkspaceResponse[] }) {
  const { t } = useTranslation()

  return (
    <ul
      aria-label={t(($) => $['platformAdmin.workspaces.title'], { ns: 'common' })}
      className="divide-y divide-divider-subtle rounded-xl border border-components-panel-border bg-components-panel-bg"
    >
      {items.map((item) => (
        <li key={item.id} className="flex min-w-0 items-center gap-4 px-4 py-3">
          <Link
            href={`/platform-admin/workspaces/${item.id}`}
            className="min-w-0 shrink-0 truncate rounded-sm system-sm-medium text-text-accent outline-hidden hover:text-text-accent-secondary focus-visible:ring-2 focus-visible:ring-state-accent-solid"
          >
            {item.name}
          </Link>
          <span className="flex min-w-0 grow items-center gap-4 truncate system-xs-regular text-text-tertiary">
            <span className="truncate">{item.owner.name}</span>
            <span className="shrink-0 tabular-nums">{item.member_count}</span>
            <span className="shrink-0 truncate">{item.plan}</span>
          </span>
          <span className="shrink-0 system-xs-regular text-text-tertiary">
            {t(($) => $[workspaceStatusLabelKey(item.status)], { ns: 'common' })}
          </span>
        </li>
      ))}
    </ul>
  )
}

function workspaceStatusLabelKey(status: PlatformAdminWorkspaceResponse['status']) {
  return status === 'archive'
    ? 'platformAdmin.workspaces.filterArchived'
    : 'platformAdmin.workspaces.filterNormal'
}
