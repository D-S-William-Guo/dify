'use client'

import type { PlatformAdminMemberResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import { Button } from '@langgenius/dify-ui/button'
import { useTranslation } from 'react-i18next'

type MemberTableProps = {
  members: PlatformAdminMemberResponse[]
  mutationSupported: boolean
  onChangeRole: (member: PlatformAdminMemberResponse) => void
}

export function MemberTable({ members, mutationSupported, onChangeRole }: MemberTableProps) {
  const { t } = useTranslation()

  return (
    <ul
      aria-label={t(($) => $['platformAdmin.members.title'], { ns: 'common' })}
      className="divide-y divide-divider-subtle rounded-xl border border-components-panel-border bg-components-panel-bg"
    >
      {members.map((member) => {
        const canChangeRole =
          mutationSupported &&
          member.mutation_supported &&
          member.role !== 'owner' &&
          member.role_source !== 'rbac_unavailable'
        const roleLabelKey = memberRoleLabelKey(member.role)

        return (
          <li key={member.id} className="flex min-w-0 items-center gap-4 px-4 py-3">
            <span className="flex min-w-0 grow flex-col">
              <span className="flex min-w-0 items-center gap-1.5">
                <span className="truncate system-sm-medium text-text-secondary">{member.name}</span>
                {member.role === 'owner' && (
                  <span className="shrink-0 system-xs-medium text-text-warning">
                    {t(($) => $['platformAdmin.ownerBadge'], { ns: 'common' })}
                  </span>
                )}
              </span>
              <span className="truncate system-xs-regular text-text-tertiary">{member.email}</span>
            </span>
            <span className="shrink-0 system-sm-regular text-text-secondary">
              {roleLabelKey ? t(($) => $[roleLabelKey], { ns: 'common' }) : null}
            </span>
            <Button
              type="button"
              size="small"
              variant="secondary"
              disabled={!canChangeRole}
              aria-label={`${t(($) => $['platformAdmin.changeRole.title'], { ns: 'common' })} ${member.name}`}
              onClick={() => onChangeRole(member)}
            >
              {t(($) => $['platformAdmin.changeRole.title'], { ns: 'common' })}
            </Button>
          </li>
        )
      })}
    </ul>
  )
}

function memberRoleLabelKey(role: PlatformAdminMemberResponse['role']) {
  switch (role) {
    case 'owner':
      return 'platformAdmin.roles.owner'
    case 'admin':
      return 'platformAdmin.roles.admin'
    case 'normal':
      return 'platformAdmin.roles.member'
    default:
      return undefined
  }
}
