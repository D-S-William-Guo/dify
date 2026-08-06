'use client'

import type { MarketplaceCopyResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import { Button } from '@langgenius/dify-ui/button'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@langgenius/dify-ui/dialog'
import { useTranslation } from 'react-i18next'
import { useRouter } from '@/next/navigation'

type CopyResultDialogProps = {
  result: MarketplaceCopyResponse
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function CopyResultDialog({ result, open, onOpenChange }: CopyResultDialogProps) {
  const { t } = useTranslation()
  const router = useRouter()

  function navigateToApp() {
    onOpenChange(false)
    router.push(`/app/${result.app_id}/overview`)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent backdropProps={{ forceRender: true }}>
        <DialogCloseButton />

        <div className="grid gap-4 pt-5">
          <div className="grid gap-1 pr-8">
            <DialogTitle className="text-xl font-semibold text-text-primary">
              {t(($) => $['enterpriseMarketplace.copy.confirmTitle'], { ns: 'common' })}
            </DialogTitle>
            <DialogDescription className="text-sm text-text-tertiary">
              {t(($) => $['enterpriseMarketplace.copy.success'], { ns: 'common' })}
            </DialogDescription>
          </div>

          {result.warnings.length > 0 && (
            <div className="bg-state-warning-bg rounded-lg border border-components-panel-border p-3">
              <p className="system-sm-semibold text-text-warning">
                {t(($) => $['enterpriseMarketplace.copy.warningsTitle'], { ns: 'common' })}
              </p>
              <ul className="mt-1 list-disc space-y-1 pl-4">
                {result.warnings.map((warning) => (
                  <li key={warning} className="system-xs-regular text-text-warning">
                    {warning}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              {t(($) => $['enterpriseMarketplace.copy.cancel'], { ns: 'common' })}
            </Button>
            <Button type="button" variant="primary" onClick={navigateToApp}>
              {t(($) => $['enterpriseMarketplace.copy.navigateToApp'], { ns: 'common' })}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
