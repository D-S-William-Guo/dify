'use client'

import type { PlatformAdminMemberInviteResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectItemText,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from '@langgenius/dify-ui/select'
import { toast } from '@langgenius/dify-ui/toast'
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocale } from '@/context/i18n'
import { consoleQuery } from '@/service/client'
import { mapPlatformAdminError } from './errors'
import { InvitationResultList } from './invitation-result-list'

const INVITE_ROLE_OPTIONS = [
  { value: 'admin', labelKey: 'platformAdmin.roles.admin' },
  { value: 'normal', labelKey: 'platformAdmin.roles.member' },
] as const

type InviteRoleValue = (typeof INVITE_ROLE_OPTIONS)[number]['value']

type InviteMembersDialogProps = {
  workspaceId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function InviteMembersDialog({ workspaceId, open, onOpenChange }: InviteMembersDialogProps) {
  const { t } = useTranslation()
  const locale = useLocale()
  const [recipients, setRecipients] = useState('')
  const [role, setRole] = useState<InviteRoleValue>('admin')
  const [results, setResults] = useState<PlatformAdminMemberInviteResponse | null>(null)
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation(
    consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.invitations.post.mutationOptions(),
  )

  const emails = parseEmails(recipients)
  const canSubmit = emails.length > 0

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending || !canSubmit) return

    setSubmissionError(null)
    mutate(
      {
        params: { workspace_id: workspaceId },
        body: { emails, role, language: locale },
      },
      {
        onSuccess: (response) => {
          toast.success(t(($) => $['platformAdmin.invite.success'], { ns: 'common' }))
          setResults(response)
        },
        onError: (error) => {
          const mapped = mapPlatformAdminError(error)
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

        <div className="grid gap-1 pr-8">
          <DialogTitle className="text-xl font-semibold text-text-primary">
            {t(($) => $['platformAdmin.invite.title'], { ns: 'common' })}
          </DialogTitle>
          <DialogDescription className="text-sm text-text-tertiary">
            {t(($) => $['platformAdmin.invite.recipientsPlaceholder'], { ns: 'common' })}
          </DialogDescription>
        </div>

        {results ? (
          <div className="grid gap-4 pt-5">
            <InvitationResultList results={results.results} />
            <div className="flex justify-end">
              <Button type="button" variant="primary" onClick={() => onOpenChange(false)}>
                {t(($) => $['platformAdmin.invite.cancel'], { ns: 'common' })}
              </Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="grid gap-4 pt-5">
            <Field name="emails">
              <FieldLabel>
                {t(($) => $['platformAdmin.invite.recipientsLabel'], { ns: 'common' })}
              </FieldLabel>
              <FieldControl
                value={recipients}
                placeholder={t(($) => $['platformAdmin.invite.recipientsPlaceholder'], {
                  ns: 'common',
                })}
                onChange={(event) => setRecipients(event.target.value)}
              />
              <FieldError match="valueMissing">
                {t(($) => $['platformAdmin.invite.recipientsPlaceholder'], { ns: 'common' })}
              </FieldError>
            </Field>

            <Field name="role">
              <Select<InviteRoleValue>
                value={role}
                onValueChange={(nextRole) => {
                  if (nextRole) setRole(nextRole)
                }}
              >
                <SelectLabel>
                  {t(($) => $['platformAdmin.invite.roleLabel'], { ns: 'common' })}
                </SelectLabel>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {INVITE_ROLE_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      <SelectItemText>
                        {t(($) => $[option.labelKey], { ns: 'common' })}
                      </SelectItemText>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <FieldError match="valueMissing">
                {t(($) => $['platformAdmin.invite.roleLabel'], { ns: 'common' })}
              </FieldError>
            </Field>

            {submissionError && (
              <p role="alert" className="body-xs-regular text-text-destructive">
                {submissionError}
              </p>
            )}

            <Button
              type="submit"
              variant="primary"
              loading={isPending}
              disabled={isPending || !canSubmit}
            >
              {t(($) => $['platformAdmin.invite.send'], { ns: 'common' })}
            </Button>
          </form>
        )}
      </DialogContent>
    </Dialog>
  )
}

function parseEmails(value: string) {
  return value
    .split(/[\s,]+/)
    .map((email) => email.trim())
    .filter(Boolean)
}
