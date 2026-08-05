'use client'

import type { PlatformAdminMemberResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import type { FormEvent } from 'react'
import { Button } from '@langgenius/dify-ui/button'
import {
  Dialog,
  DialogCloseButton,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from '@langgenius/dify-ui/dialog'
import { Field, FieldError } from '@langgenius/dify-ui/field'
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
import { consoleQuery } from '@/service/client'
import { mapPlatformAdminError } from './errors'

const ROLE_OPTIONS = [
  { value: 'admin', labelKey: 'platformAdmin.roles.admin' },
  { value: 'normal', labelKey: 'platformAdmin.roles.member' },
] as const

type MemberRoleValue = (typeof ROLE_OPTIONS)[number]['value']

type ChangeMemberRoleDialogProps = {
  member: PlatformAdminMemberResponse
  workspaceId: string
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function ChangeMemberRoleDialog({
  member,
  workspaceId,
  open,
  onOpenChange,
}: ChangeMemberRoleDialogProps) {
  const { t } = useTranslation()
  const [role, setRole] = useState<MemberRoleValue>(member.role === 'admin' ? 'admin' : 'normal')
  const [submissionError, setSubmissionError] = useState<string | null>(null)

  const { mutate, isPending } = useMutation(
    consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.byMemberId.role.patch.mutationOptions(),
  )

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (isPending) return

    setSubmissionError(null)
    mutate(
      {
        params: { workspace_id: workspaceId, member_id: member.id },
        body: { role },
      },
      {
        onSuccess: () => {
          toast.success(t(($) => $['platformAdmin.changeRole.success'], { ns: 'common' }))
          onOpenChange(false)
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

        <form onSubmit={handleSubmit} className="grid gap-4 pt-5">
          <div className="grid gap-1 pr-8">
            <DialogTitle className="text-xl font-semibold text-text-primary">
              {t(($) => $['platformAdmin.changeRole.title'], { ns: 'common' })}
            </DialogTitle>
            <DialogDescription className="text-sm text-text-tertiary">
              {t(($) => $['platformAdmin.changeRole.confirmMessage'], { ns: 'common' })}
            </DialogDescription>
          </div>

          <p className="system-sm-regular text-text-secondary">
            {member.name} · {member.email}
          </p>

          <Field name="role">
            <Select<MemberRoleValue>
              value={role}
              onValueChange={(nextRole) => {
                if (nextRole) setRole(nextRole)
              }}
            >
              <SelectLabel>
                {t(($) => $['platformAdmin.members.roleLabel'], { ns: 'common' })}
              </SelectLabel>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLE_OPTIONS.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    <SelectItemText>
                      {t(($) => $[option.labelKey], { ns: 'common' })}
                    </SelectItemText>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <FieldError match="valueMissing">
              {t(($) => $['platformAdmin.members.roleLabel'], { ns: 'common' })}
            </FieldError>
          </Field>

          {submissionError && (
            <p role="alert" className="body-xs-regular text-text-destructive">
              {submissionError}
            </p>
          )}

          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => onOpenChange(false)}>
              {t(($) => $['platformAdmin.changeRole.cancel'], { ns: 'common' })}
            </Button>
            <Button type="submit" variant="primary" loading={isPending} disabled={isPending}>
              {t(($) => $['platformAdmin.changeRole.save'], { ns: 'common' })}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
