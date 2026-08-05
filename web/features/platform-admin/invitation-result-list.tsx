'use client'

import type { PlatformAdminMemberInviteResultResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import { useTranslation } from 'react-i18next'

type InviteActionLabelKey =
  | 'platformAdmin.invite.status.activated'
  | 'platformAdmin.invite.status.pending'

const INVITE_ACTION_LABEL_KEY: Record<
  PlatformAdminMemberInviteResultResponse['action'],
  InviteActionLabelKey
> = {
  account_created: 'platformAdmin.invite.status.activated',
  already_member: 'platformAdmin.invite.status.activated',
  invitation_queued: 'platformAdmin.invite.status.pending',
  invitation_resent: 'platformAdmin.invite.status.pending',
  membership_created: 'platformAdmin.invite.status.activated',
}

type InviteDeliveryLabelKey =
  | 'platformAdmin.invite.delivery.failed'
  | 'platformAdmin.invite.delivery.sent'

const INVITE_DELIVERY_LABEL_KEY: Record<
  PlatformAdminMemberInviteResultResponse['email_delivery'],
  InviteDeliveryLabelKey
> = {
  failed: 'platformAdmin.invite.delivery.failed',
  not_applicable: 'platformAdmin.invite.delivery.sent',
  queued: 'platformAdmin.invite.delivery.sent',
}

export function InvitationResultList({
  results,
}: {
  results: PlatformAdminMemberInviteResultResponse[]
}) {
  const { t } = useTranslation()

  return (
    <div className="grid gap-2">
      <h3 className="system-sm-medium text-text-primary">
        {t(($) => $['platformAdmin.invite.resultTitle'], { ns: 'common' })}
      </h3>
      <ul className="grid gap-1">
        {results.map((result) => (
          <li
            key={result.email}
            className="flex items-center justify-between gap-2 border-b border-divider-subtle py-1.5 last:border-b-0"
          >
            <span className="min-w-0 truncate system-sm-regular text-text-secondary">
              {result.email}
            </span>
            <span className="shrink-0 system-xs-regular text-text-tertiary">
              {t(($) => $[INVITE_ACTION_LABEL_KEY[result.action]], { ns: 'common' })}
            </span>
            <span className="shrink-0 system-xs-regular text-text-tertiary">
              {t(($) => $[INVITE_DELIVERY_LABEL_KEY[result.email_delivery]], { ns: 'common' })}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
