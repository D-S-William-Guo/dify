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
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { CopyResultDialog } from './copy-result-dialog'
import { mapMarketplaceError } from './errors'

type CopyAssetActionProps = {
  assetId: string
}

const copyErrorKeyByKind = {
  unauthorized: 'enterpriseMarketplace.errors.unauthorized',
  permissionDenied: 'enterpriseMarketplace.copy.error.permissionDenied',
  notFound: 'enterpriseMarketplace.copy.error.notFound',
  conflict: 'enterpriseMarketplace.copy.error.conflict',
  validation: 'enterpriseMarketplace.copy.error.validation',
  serviceUnavailable: 'enterpriseMarketplace.copy.error.serviceUnavailable',
} as const

export function CopyAssetAction({ assetId }: CopyAssetActionProps) {
  const { t } = useTranslation()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [result, setResult] = useState<MarketplaceCopyResponse | null>(null)
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation(
    consoleQuery.enterpriseMarketplace.assets.byAssetId.copies.post.mutationOptions(),
  )

  function startCopy() {
    if (isPending) return

    setSubmissionError(null)
    mutate(
      { params: { asset_id: assetId }, body: {} },
      {
        onSuccess: (data) => {
          setConfirmOpen(false)
          setResult(data)
        },
        onError: (error) => {
          const mapped = mapMarketplaceError(error)
          if (mapped.kind === 'unknown') {
            setSubmissionError(null)
            return
          }
          const key = copyErrorKeyByKind[mapped.kind] ?? mapped.key
          setSubmissionError(t(($) => $[key], { ns: 'common' }))
        },
      },
    )
  }

  return (
    <>
      <Button type="button" size="small" onClick={() => setConfirmOpen(true)}>
        {t(($) => $['enterpriseMarketplace.detail.copy'], { ns: 'common' })}
      </Button>

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent backdropProps={{ forceRender: true }}>
          <DialogCloseButton />

          <div className="grid gap-4 pt-5">
            <div className="grid gap-1 pr-8">
              <DialogTitle className="text-xl font-semibold text-text-primary">
                {t(($) => $['enterpriseMarketplace.copy.confirmTitle'], { ns: 'common' })}
              </DialogTitle>
              <DialogDescription className="text-sm text-text-tertiary">
                {t(($) => $['enterpriseMarketplace.copy.confirmMessage'], { ns: 'common' })}
              </DialogDescription>
            </div>

            {submissionError && (
              <p role="alert" className="body-xs-regular text-text-destructive">
                {submissionError}
              </p>
            )}

            <div className="flex justify-end gap-2">
              <Button type="button" variant="secondary" onClick={() => setConfirmOpen(false)}>
                {t(($) => $['enterpriseMarketplace.copy.cancel'], { ns: 'common' })}
              </Button>
              <Button
                type="button"
                variant="primary"
                loading={isPending}
                disabled={isPending}
                onClick={startCopy}
              >
                {isPending
                  ? t(($) => $['enterpriseMarketplace.copy.processing'], { ns: 'common' })
                  : t(($) => $['enterpriseMarketplace.copy.confirm'], { ns: 'common' })}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {result && (
        <CopyResultDialog
          result={result}
          open
          onOpenChange={(open) => {
            if (!open) setResult(null)
          }}
        />
      )}
    </>
  )
}
