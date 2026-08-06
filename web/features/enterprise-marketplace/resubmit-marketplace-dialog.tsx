'use client'

import type { MarketplaceAssetResponse } from '@dify/contracts/api/console/enterprise-marketplace/types.gen'
import type { FormEvent } from 'react'
import { Button } from '@langgenius/dify-ui/button'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@langgenius/dify-ui/dialog'
import { Field, FieldControl, FieldError, FieldLabel } from '@langgenius/dify-ui/field'
import { toast } from '@langgenius/dify-ui/toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { mapMarketplaceError } from './errors'

type ResubmitMarketplaceDialogProps = {
  asset: MarketplaceAssetResponse
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ResubmitMarketplaceDialog({
  asset,
  open,
  onOpenChange,
}: ResubmitMarketplaceDialogProps) {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [title, setTitle] = useState(asset.title)
  const [category, setCategory] = useState(asset.category)
  const [description, setDescription] = useState(asset.description)
  const [scenario, setScenario] = useState(asset.scenario)
  const [tags, setTags] = useState(asset.tags.join(', '))
  const [conflict, setConflict] = useState(false)
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation(
    consoleQuery.apps.byAppId.enterpriseMarketplace.submissions.post.mutationOptions(),
  )

  const normalizedTitle = title.trim()
  const normalizedCategory = category.trim()
  const hasError = normalizedTitle.length === 0 || normalizedCategory.length === 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending || hasError) return

    const sourceAppId = asset.source_app_id
    if (!sourceAppId) return

    setConflict(false)
    setSubmissionError(null)
    mutate(
      {
        params: { app_id: sourceAppId },
        body: {
          title: normalizedTitle,
          category: normalizedCategory,
          description: description.trim() || undefined,
          scenario: scenario.trim() || undefined,
          tags: tags
            .split(',')
            .map((tag) => tag.trim())
            .filter(Boolean),
          expected_row_version: asset.row_version,
        },
      },
      {
        onSuccess: () => {
          toast.success(
            t(($) => $['enterpriseMarketplace.resubmitDialog.success'], { ns: 'common' }),
          )
          onOpenChange(false)
        },
        onError: (error) => {
          const mapped = mapMarketplaceError(error)
          if (mapped.kind === 'conflict') {
            setConflict(true)
            setSubmissionError(null)
            void queryClient.invalidateQueries({
              queryKey: consoleQuery.enterpriseMarketplace.submissions.get.key(),
            })
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
              {t(($) => $['enterpriseMarketplace.resubmitDialog.title'], { ns: 'common' })}
            </DialogTitle>
            <DialogDescription className="text-sm text-text-tertiary">
              {t(($) => $['enterpriseMarketplace.resubmitDialog.description'], { ns: 'common' })}
            </DialogDescription>
          </div>

          {conflict && (
            <div
              role="alert"
              className="bg-state-warning-bg rounded-lg border border-components-panel-border p-3"
            >
              <p className="system-sm-semibold text-text-warning">
                {t(($) => $['enterpriseMarketplace.resubmitDialog.conflict'], { ns: 'common' })}
              </p>
              <p className="mt-1 system-xs-regular text-text-warning">
                {t(($) => $['enterpriseMarketplace.resubmitDialog.conflictMessage'], {
                  ns: 'common',
                })}
              </p>
            </div>
          )}

          {submissionError && (
            <p role="alert" className="body-xs-regular text-text-destructive">
              {submissionError}
            </p>
          )}

          <Field name="title">
            <FieldLabel>
              {t(($) => $['enterpriseMarketplace.detail.title'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl
              required
              value={title}
              onChange={(event) => setTitle(event.target.value)}
            />
            <FieldError match="valueMissing">
              {t(($) => $['enterpriseMarketplace.detail.title'], { ns: 'common' })}
            </FieldError>
          </Field>

          <Field name="category">
            <FieldLabel>
              {t(($) => $['enterpriseMarketplace.detail.category'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl
              required
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            />
            <FieldError match="valueMissing">
              {t(($) => $['enterpriseMarketplace.detail.category'], { ns: 'common' })}
            </FieldError>
          </Field>

          <Field name="description">
            <FieldLabel>
              {t(($) => $['enterpriseMarketplace.detail.description'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl
              value={description}
              onChange={(event) => setDescription(event.target.value)}
            />
          </Field>

          <Field name="scenario">
            <FieldLabel>
              {t(($) => $['enterpriseMarketplace.detail.scenario'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl value={scenario} onChange={(event) => setScenario(event.target.value)} />
          </Field>

          <Field name="tags">
            <FieldLabel>
              {t(($) => $['enterpriseMarketplace.detail.tags'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl value={tags} onChange={(event) => setTags(event.target.value)} />
          </Field>

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              {t(($) => $['enterpriseMarketplace.resubmitDialog.cancel'], { ns: 'common' })}
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={isPending}
              disabled={isPending || hasError}
            >
              {t(($) => $['enterpriseMarketplace.resubmitDialog.confirm'], { ns: 'common' })}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
