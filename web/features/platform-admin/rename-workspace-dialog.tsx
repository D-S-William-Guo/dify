'use client'

import type { PlatformAdminWorkspaceResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import type { FormEvent } from 'react'
import { Button } from '@langgenius/dify-ui/button'
import { Dialog, DialogCloseButton, DialogContent, DialogTitle } from '@langgenius/dify-ui/dialog'
import { Field, FieldControl, FieldError, FieldLabel } from '@langgenius/dify-ui/field'
import { toast } from '@langgenius/dify-ui/toast'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { mapPlatformAdminError } from './errors'

type RenameWorkspaceDialogProps = {
  workspace: PlatformAdminWorkspaceResponse
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function RenameWorkspaceDialog({
  workspace,
  open,
  onOpenChange,
}: RenameWorkspaceDialogProps) {
  const { t } = useTranslation()
  const [name, setName] = useState(workspace.name)
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation(
    consoleQuery.platformAdmin.workspaces.byWorkspaceId.patch.mutationOptions(),
  )

  const normalizedName = name.trim()
  const hasError = normalizedName.length === 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending || hasError) return

    setSubmissionError(null)
    mutate(
      {
        params: { workspace_id: workspace.id },
        body: { name: normalizedName },
      },
      {
        onSuccess: () => {
          toast.success(t(($) => $['platformAdmin.renameWorkspace.success'], { ns: 'common' }))
          onOpenChange(false)
        },
        onError: (error) => {
          const mapped = mapPlatformAdminError(error)
          if (mapped.kind === 'conflict') {
            setSubmissionError(
              t(($) => $['platformAdmin.renameWorkspace.conflict'], { ns: 'common' }),
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
          <DialogTitle className="text-xl font-semibold text-text-primary">
            {t(($) => $['platformAdmin.renameWorkspace.title'], { ns: 'common' })}
          </DialogTitle>

          <Field name="name" invalid={hasError}>
            <FieldLabel>
              {t(($) => $['platformAdmin.renameWorkspace.nameLabel'], { ns: 'common' })}
            </FieldLabel>
            <FieldControl
              value={name}
              placeholder={t(($) => $['platformAdmin.renameWorkspace.namePlaceholder'], {
                ns: 'common',
              })}
              onChange={(event) => setName(event.target.value)}
            />
            <FieldError match="valueMissing">
              {t(($) => $['platformAdmin.renameWorkspace.nameRequired'], { ns: 'common' })}
            </FieldError>
          </Field>

          {submissionError && (
            <p role="alert" className="body-xs-regular text-text-destructive">
              {submissionError}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              {t(($) => $['platformAdmin.renameWorkspace.cancel'], { ns: 'common' })}
            </Button>
            <Button
              type="submit"
              variant="primary"
              loading={isPending}
              disabled={isPending || hasError}
            >
              {t(($) => $['platformAdmin.renameWorkspace.save'], { ns: 'common' })}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
