'use client'

import type { MarketplaceAssetResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import { Button } from '@langgenius/dify-ui/button'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ResubmitMarketplaceDialog } from './resubmit-marketplace-dialog'

type ResubmitActionProps = {
  asset: MarketplaceAssetResponse
}

export function ResubmitAction({ asset }: ResubmitActionProps) {
  const { t } = useTranslation()
  const [open, setOpen] = useState(false)

  return (
    <>
      <Button
        type="button"
        size="small"
        variant="secondary"
        disabled={!asset.source_app_id}
        onClick={() => setOpen(true)}
      >
        {t(($) => $['enterpriseMarketplace.submissions.resubmit'], { ns: 'common' })}
      </Button>
      <ResubmitMarketplaceDialog
        key={String(open)}
        asset={asset}
        open={open}
        onOpenChange={setOpen}
      />
    </>
  )
}
