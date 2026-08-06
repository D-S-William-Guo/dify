'use client'

import type { MarketplaceAssetResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import type { FormEvent } from 'react'
import { Button } from '@langgenius/dify-ui/button'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@langgenius/dify-ui/dialog'
import { Field, FieldControl, FieldLabel } from '@langgenius/dify-ui/field'
import { toast } from '@langgenius/dify-ui/toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { mapMarketplaceError } from './errors'

type ReviewDialogProps = {
  asset: MarketplaceAssetResponse
  decision: 'approved' | 'rejected'
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ReviewDialog({ asset, decision, open, onOpenChange }: ReviewDialogProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [note, setNote] = useState('')
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation(
    consoleQuery.platformAdmin.enterpriseMarketplace.assets.byAssetId.reviews.post.mutationOptions(),
  )

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending) return

    setSubmissionError(null)
    mutate(
      {
        params: { asset_id: asset.asset_id },
        body: {
          decision,
          review_note: note.trim() || null,
          expected_row_version: asset.row_version,
        },
      },
      {
        onSuccess: () => {
          toast.success(t(($) => $['enterpriseMarketplace.review.success'], { ns: 'common' }))
          onOpenChange(false)
        },
        onError: (error) => {
          const mapped = mapMarketplaceError(error)
          if (mapped.kind === 'conflict') {
            setSubmissionError(
              t(($) => $['enterpriseMarketplace.review.error.conflict'], { ns: 'common' }),
            )
            void queryClient.invalidateQueries({
              queryKey: consoleQuery.platformAdmin.enterpriseMarketplace.assets.get.key(),
            })
            return
          }
          if (mapped.kind === 'validation') {
            setSubmissionError(
              t(($) => $['enterpriseMarketplace.review.error.validation'], { ns: 'common' }),
            )
            return
          }
          if (mapped.kind === 'serviceUnavailable') {
            setSubmissionError(
              t(($) => $['enterpriseMarketplace.review.error.serviceUnavailable'], {
                ns: 'common',
              }),
            )
            return
          }
          setSubmissionError(
            mapped.kind === 'unknown' ? null : t(($) => $[mapped.key], { ns: 'common' }),
          )
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent backdropProps={{ forceRender: true }}>
        <DialogCloseButton />

        <form onSubmit={handleSubmit} className="grid gap-4 pt-5">
          <div className="grid gap-1 pr-8">
            <DialogTitle className="text-xl font-semibold text-text-primary">
              {t(($) => $['enterpriseMarketplace.review.title'], { ns: 'common' })}
            </DialogTitle>
            <DialogDescription className="text-sm text-text-tertiary">
              {t(
                ($) =>
                  $[
                    decision === 'approved'
                      ? 'enterpriseMarketplace.review.approve'
                      : 'enterpriseMarketplace.review.reject'
                  ],
                { ns: 'common' },
              )}
            </DialogDescription>
          </div>

          <p className="truncate system-sm-medium text-text-secondary">{asset.title}</p>

          <Field name="review_note">
            <FieldLabel>
              {t(($) => $['enterpriseMarketplace.review.reviewNoteLabel'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl
              value={note}
              placeholder={t(($) => $['enterpriseMarketplace.review.reviewNotePlaceholder'], {
                ns: 'common',
              })}
              onChange={(event) => setNote(event.target.value)}
            />
          </Field>

          {submissionError && (
            <p role="alert" className="body-xs-regular text-text-destructive">
              {submissionError}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              {t(($) => $['enterpriseMarketplace.review.cancel'], { ns: 'common' })}
            </Button>
            <Button type="submit" variant="primary" loading={isPending} disabled={isPending}>
              {t(($) => $['enterpriseMarketplace.review.confirm'], { ns: 'common' })}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
