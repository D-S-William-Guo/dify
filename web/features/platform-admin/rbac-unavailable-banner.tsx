'use client'

import { useTranslation } from 'react-i18next'

export function RbacUnavailableBanner() {
  const { t } = useTranslation()

  return (
    <div
      role="status"
      className="flex items-start gap-1.5 rounded-lg bg-state-warning-hover p-2 text-text-warning"
    >
      <span aria-hidden="true" className="i-ri-error-warning-fill size-4 shrink-0" />
      <span className="min-w-0">
        <span className="block system-sm-medium text-text-primary">
          {t(($) => $['platformAdmin.rbacUnavailable.title'], { ns: 'common' })}
        </span>
        <span className="block body-xs-regular text-text-tertiary">
          {t(($) => $['platformAdmin.rbacUnavailable.message'], { ns: 'common' })}
        </span>
      </span>
    </div>
  )
}
