'use client'

import type { InvitationResult } from '@/models/common'
import type { RoleKey } from '../members-page/invite-modal/role-selector'
import { Avatar } from '@langgenius/dify-ui/avatar'
import { Button } from '@langgenius/dify-ui/button'
import { cn } from '@langgenius/dify-ui/cn'
import { Dialog, DialogContent, DialogTitle } from '@langgenius/dify-ui/dialog'
import { toast } from '@langgenius/dify-ui/toast'
import { useDeferredValue, useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ReactMultiEmail } from 'react-multi-email'
import { useSuspenseQuery } from '@tanstack/react-query'
import Input from '@/app/components/base/input'
import SearchInput from '@/app/components/base/search-input'
import { emailRegex } from '@/config'
import { useAppContext } from '@/context/app-context'
import { useLocale } from '@/context/i18n'
import { useProviderContext } from '@/context/provider-context'
import { systemFeaturesQueryOptions } from '@/service/system-features'
import {
  useCreatePlatformAdminWorkspace,
  useDeletePlatformAdminWorkspace,
  useDeletePlatformAdminWorkspaceMember,
  useInvitePlatformAdminWorkspaceMembers,
  usePlatformAdminWorkspaceMembers,
  usePlatformAdminWorkspaces,
  useRenamePlatformAdminWorkspace,
  useUpdatePlatformAdminWorkspaceMemberRole,
} from '@/service/use-platform-admin'
import InvitedModal from '../members-page/invited-modal'
import RoleSelector from '../members-page/invite-modal/role-selector'
import EnterpriseMarketplaceAdmin from './enterprise-marketplace-admin'
import 'react-multi-email/dist/style.css'

const roleLabels = {
  owner: 'members.owner',
  admin: 'members.admin',
  editor: 'members.editor',
  dataset_operator: 'members.datasetOperator',
  normal: 'members.normal',
} as const

type PlatformAdminDialogProps = {
  show: boolean
  title: string
  className?: string
  onClose: () => void
  footer?: React.ReactNode
  children: React.ReactNode
}

const PlatformAdminDialog = ({
  show,
  title,
  className,
  onClose,
  footer,
  children,
}: PlatformAdminDialogProps) => {
  return (
    <Dialog
      open={show}
      onOpenChange={(open) => {
        if (!open)
          onClose()
      }}
    >
      <DialogContent
        backdropProps={{ forceRender: true }}
        className={cn('max-w-[800px] p-6', className)}
      >
        <DialogTitle className="pb-3 pr-8 text-text-primary title-2xl-semi-bold">
          {title}
        </DialogTitle>
        {children}
        {footer && (
          <div className="flex items-center justify-end gap-2 px-6 pb-6 pt-3">
            {footer}
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

type CreateWorkspaceDialogProps = {
  show: boolean
  loading: boolean
  onClose: () => void
  onSubmit: (payload: { name: string, owner_email?: string, owner_name?: string }) => void
}

const CreateWorkspaceDialog = ({
  show,
  loading,
  onClose,
  onSubmit,
}: CreateWorkspaceDialogProps) => {
  const { t } = useTranslation()
  const [name, setName] = useState('')
  const [ownerEmail, setOwnerEmail] = useState('')
  const [ownerName, setOwnerName] = useState('')

  useEffect(() => {
    if (!show) {
      setName('')
      setOwnerEmail('')
      setOwnerName('')
    }
  }, [show])

  const handleSubmit = () => {
    const normalizedOwnerEmail = ownerEmail.trim().toLowerCase()
    if (normalizedOwnerEmail && !emailRegex.test(normalizedOwnerEmail)) {
      toast.error(t('members.emailInvalid', { ns: 'common' }))
      return
    }

    onSubmit({
      name: name.trim(),
      owner_email: normalizedOwnerEmail || undefined,
      owner_name: ownerName.trim() || undefined,
    })
  }

  return (
    <PlatformAdminDialog
      show={show}
      onClose={onClose}
      title={t('platformAdmin.createWorkspace', { ns: 'common' })}
      className="max-w-[560px]"
      footer={(
        <>
          <Button onClick={onClose}>{t('operation.cancel', { ns: 'common' })}</Button>
          <Button variant="primary" loading={loading} disabled={!name.trim()} onClick={handleSubmit}>
            {t('operation.create', { ns: 'common' })}
          </Button>
        </>
      )}
    >
      <div className="space-y-4 px-6 pb-2">
        <div>
          <div className="mb-2 text-sm text-text-secondary">{t('platformAdmin.workspaceName', { ns: 'common' })}</div>
          <Input value={name} onChange={e => setName(e.target.value)} maxLength={255} />
        </div>
        <div>
          <div className="mb-2 text-sm text-text-secondary">{t('platformAdmin.ownerEmail', { ns: 'common' })}</div>
          <Input
            value={ownerEmail}
            onChange={e => setOwnerEmail(e.target.value)}
            placeholder={t('platformAdmin.ownerEmailPlaceholder', { ns: 'common' })}
          />
        </div>
        <div>
          <div className="mb-2 text-sm text-text-secondary">{t('platformAdmin.ownerName', { ns: 'common' })}</div>
          <Input
            value={ownerName}
            onChange={e => setOwnerName(e.target.value)}
            placeholder={t('platformAdmin.ownerNamePlaceholder', { ns: 'common' })}
          />
        </div>
        <div className="text-xs text-text-tertiary">{t('platformAdmin.createWorkspaceTip', { ns: 'common' })}</div>
      </div>
    </PlatformAdminDialog>
  )
}

type RenameWorkspaceDialogProps = {
  show: boolean
  loading: boolean
  name: string
  onClose: () => void
  onSubmit: (name: string) => void
}

const RenameWorkspaceDialog = ({
  show,
  loading,
  name,
  onClose,
  onSubmit,
}: RenameWorkspaceDialogProps) => {
  const { t } = useTranslation()
  const [nextName, setNextName] = useState(name)

  useEffect(() => {
    if (show)
      setNextName(name)
  }, [name, show])

  return (
    <PlatformAdminDialog
      show={show}
      onClose={onClose}
      title={t('platformAdmin.renameWorkspace', { ns: 'common' })}
      className="max-w-[520px]"
      footer={(
        <>
          <Button onClick={onClose}>{t('operation.cancel', { ns: 'common' })}</Button>
          <Button variant="primary" loading={loading} disabled={!nextName.trim()} onClick={() => onSubmit(nextName.trim())}>
            {t('operation.save', { ns: 'common' })}
          </Button>
        </>
      )}
    >
      <div className="px-6 pb-2">
        <div className="mb-2 text-sm text-text-secondary">{t('platformAdmin.workspaceName', { ns: 'common' })}</div>
        <Input value={nextName} onChange={e => setNextName(e.target.value)} maxLength={255} />
      </div>
    </PlatformAdminDialog>
  )
}

type InviteMembersDialogProps = {
  show: boolean
  isEmailSetup: boolean
  loading: boolean
  onClose: () => void
  onSubmit: (payload: { emails: string[], role: RoleKey, language: string }) => void
}

const InviteMembersDialog = ({
  show,
  isEmailSetup,
  loading,
  onClose,
  onSubmit,
}: InviteMembersDialogProps) => {
  const { t } = useTranslation()
  const locale = useLocale()
  const [emails, setEmails] = useState<string[]>([])
  const [role, setRole] = useState<RoleKey>('normal')

  useEffect(() => {
    if (!show) {
      setEmails([])
      setRole('normal')
    }
  }, [show])

  const handleSubmit = () => {
    if (!emails.length)
      return

    if (!emails.every(email => emailRegex.test(email))) {
      toast.error(t('members.emailInvalid', { ns: 'common' }))
      return
    }

    onSubmit({ emails, role, language: locale })
  }

  return (
    <PlatformAdminDialog
      show={show}
      onClose={onClose}
      title={t('platformAdmin.inviteMembers', { ns: 'common' })}
      className="max-w-[560px]"
      footer={(
        <>
          <Button onClick={onClose}>{t('operation.cancel', { ns: 'common' })}</Button>
          <Button variant="primary" loading={loading} disabled={!emails.length} onClick={handleSubmit}>
            {t('members.sendInvite', { ns: 'common' })}
          </Button>
        </>
      )}
    >
      <div className="space-y-4 px-6 pb-2">
        {!isEmailSetup && (
          <div className="rounded-xl border border-components-panel-border bg-background-section-burn p-3 text-sm text-text-warning">
            {t('members.emailNotSetup', { ns: 'common' })}
          </div>
        )}
        <div>
          <div className="mb-2 text-sm text-text-secondary">{t('members.email', { ns: 'common' })}</div>
          <div className="rounded-xl border border-components-input-border-active bg-components-input-bg-normal px-3 py-2">
            <ReactMultiEmail
              className="min-h-28 !border-0 !bg-transparent p-0 text-sm !text-text-primary"
              emails={emails}
              inputClassName="bg-transparent"
              onChange={setEmails}
              placeholder={t('members.emailPlaceholder', { ns: 'common' }) || ''}
              getLabel={(email, index, removeEmail) => (
                <div data-tag key={index} className="!bg-components-button-secondary-bg">
                  <div data-tag-item>{email}</div>
                  <span data-tag-handle onClick={() => removeEmail(index)}>x</span>
                </div>
              )}
            />
          </div>
        </div>
        <RoleSelector value={role} onChange={setRole} />
      </div>
    </PlatformAdminDialog>
  )
}

const PlatformAdminPage = () => {
  const { t } = useTranslation()
  const { data: systemFeatures } = useSuspenseQuery(systemFeaturesQueryOptions())
  const { currentWorkspace } = useAppContext()
  const { datasetOperatorEnabled } = useProviderContext()
  const [section, setSection] = useState<'workspaces' | 'marketplace'>('workspaces')
  const [keyword, setKeyword] = useState('')
  const deferredKeyword = useDeferredValue(keyword)
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState('')
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [showRenameDialog, setShowRenameDialog] = useState(false)
  const [showInviteDialog, setShowInviteDialog] = useState(false)
  const [invitationResults, setInvitationResults] = useState<InvitationResult[]>([])
  const [showInvitedDialog, setShowInvitedDialog] = useState(false)

  const workspaceQuery = usePlatformAdminWorkspaces(
    { keyword: deferredKeyword },
    section === 'workspaces',
  )

  const workspaces = workspaceQuery.data?.items || []
  const selectedWorkspace = useMemo(
    () => workspaces.find(workspace => workspace.id === selectedWorkspaceId) || null,
    [selectedWorkspaceId, workspaces],
  )

  useEffect(() => {
    if (!workspaces.length) {
      setSelectedWorkspaceId('')
      return
    }

    if (!selectedWorkspaceId || !workspaces.some(workspace => workspace.id === selectedWorkspaceId)) {
      const firstWorkspace = workspaces[0]
      if (firstWorkspace)
        setSelectedWorkspaceId(firstWorkspace.id)
    }
  }, [selectedWorkspaceId, workspaces])

  const membersQuery = usePlatformAdminWorkspaceMembers(
    selectedWorkspaceId,
    section === 'workspaces' && !!selectedWorkspaceId,
  )

  const roleOptions = useMemo<RoleKey[]>(() => (
    datasetOperatorEnabled
      ? ['admin', 'editor', 'normal', 'dataset_operator']
      : ['admin', 'editor', 'normal']
  ), [datasetOperatorEnabled])

  const createWorkspaceMutation = useCreatePlatformAdminWorkspace()
  const renameWorkspaceMutation = useRenamePlatformAdminWorkspace(selectedWorkspaceId)
  const deleteWorkspaceMutation = useDeletePlatformAdminWorkspace()
  const inviteMembersMutation = useInvitePlatformAdminWorkspaceMembers(selectedWorkspaceId)
  const updateRoleMutation = useUpdatePlatformAdminWorkspaceMemberRole(selectedWorkspaceId)
  const removeMemberMutation = useDeletePlatformAdminWorkspaceMember(selectedWorkspaceId)

  const handleCreateWorkspace = (payload: { name: string, owner_email?: string, owner_name?: string }) => {
    createWorkspaceMutation.mutate(payload, {
      onSuccess: (response) => {
        setShowCreateDialog(false)
        setSelectedWorkspaceId(response.workspace.id)
        if (response.owner_invitation_url && response.workspace.owner?.email) {
          setInvitationResults([{
            status: 'success',
            email: response.workspace.owner.email,
            url: response.owner_invitation_url,
          }])
          setShowInvitedDialog(true)
        }
      },
    })
  }

  const handleRenameWorkspace = (name: string) => {
    renameWorkspaceMutation.mutate(name, {
      onSuccess: () => {
        setShowRenameDialog(false)
      },
    })
  }

  const handleDeleteWorkspace = () => {
    if (!selectedWorkspace)
      return

    if (!window.confirm(t('platformAdmin.deleteWorkspaceConfirm', { ns: 'common', name: selectedWorkspace.name }) || ''))
      return

    deleteWorkspaceMutation.mutate(selectedWorkspace.id, {
      onSuccess: () => {
        toast.success(t('platformAdmin.deleteWorkspaceSuccess', { ns: 'common' }))
        setSelectedWorkspaceId('')
      },
      onError: (error) => {
        toast.error(error.message || t('platformAdmin.deleteWorkspaceFailed', { ns: 'common' }))
      },
    })
  }

  const handleInviteMembers = (payload: { emails: string[], role: RoleKey, language: string }) => {
    inviteMembersMutation.mutate(payload, {
      onSuccess: (response) => {
        setShowInviteDialog(false)
        setInvitationResults(response.invitation_results)
        setShowInvitedDialog(true)
      },
    })
  }

  const handleUpdateMemberRole = (payload: { memberId: string, role: RoleKey }) => {
    updateRoleMutation.mutate(payload)
  }

  const handleRemoveMember = (memberId: string) => {
    removeMemberMutation.mutate(memberId)
  }

  const members = membersQuery.data?.accounts || []
  const canDeleteSelectedWorkspace = !!selectedWorkspace
    && selectedWorkspace.id !== currentWorkspace.id
    && workspaces.length > 1

  return (
    <>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            className={cn(
              'rounded-full border px-3 py-1.5 text-sm',
              section === 'workspaces'
                ? 'border-components-button-primary-border bg-state-base-hover text-text-primary'
                : 'border-divider-subtle text-text-tertiary hover:bg-state-base-hover',
            )}
            onClick={() => setSection('workspaces')}
          >
            {t('platformAdmin.workspaceList', { ns: 'common' })}
          </button>
          <button
            type="button"
            className={cn(
              'rounded-full border px-3 py-1.5 text-sm',
              section === 'marketplace'
                ? 'border-components-button-primary-border bg-state-base-hover text-text-primary'
                : 'border-divider-subtle text-text-tertiary hover:bg-state-base-hover',
            )}
            onClick={() => setSection('marketplace')}
          >
            {t('enterpriseMarketplace.adminSectionTitle', { ns: 'common' })}
          </button>
        </div>

        {section === 'workspaces' && (
          <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
            <div className="rounded-2xl border border-divider-subtle bg-components-panel-bg p-4">
              <div className="mb-4 flex items-center justify-between gap-3">
                <div>
                  <div className="text-text-primary title-lg-semi-bold">{t('platformAdmin.workspaceList', { ns: 'common' })}</div>
                  <div className="mt-1 text-text-tertiary system-xs-regular">{t('platformAdmin.workspaceCount', { ns: 'common', count: workspaces.length })}</div>
                </div>
                <Button variant="primary" size="small" onClick={() => setShowCreateDialog(true)}>
                  {t('operation.create', { ns: 'common' })}
                </Button>
              </div>
              <SearchInput className="mb-4" value={keyword} onChange={setKeyword} />
              <div className="space-y-2">
                {workspaces.map(workspace => (
                  <button
                    key={workspace.id}
                    type="button"
                    className={cn(
                      'w-full rounded-xl border p-3 text-left transition-colors',
                      workspace.id === selectedWorkspaceId
                        ? 'border-components-button-primary-border bg-state-base-hover'
                        : 'border-divider-subtle bg-background-body hover:bg-state-base-hover',
                    )}
                    onClick={() => setSelectedWorkspaceId(workspace.id)}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <div className="truncate text-text-primary system-sm-semibold">{workspace.name}</div>
                      <div className="rounded-md bg-background-default px-2 py-1 text-text-tertiary system-2xs-medium-uppercase">
                        {workspace.member_count}
                      </div>
                    </div>
                    <div className="mt-2 truncate text-text-tertiary system-xs-regular">
                      {workspace.owner?.email || t('platformAdmin.ownerless', { ns: 'common' })}
                    </div>
                  </button>
                ))}
                {!workspaceQuery.isLoading && !workspaces.length && (
                  <div className="rounded-xl border border-dashed border-divider-subtle px-4 py-10 text-center text-text-tertiary system-sm-regular">
                    {t('platformAdmin.noWorkspaces', { ns: 'common' })}
                  </div>
                )}
              </div>
            </div>

            <div className="rounded-2xl border border-divider-subtle bg-components-panel-bg p-4">
              {!selectedWorkspace && (
                <div className="flex h-full min-h-[420px] items-center justify-center text-text-tertiary system-sm-regular">
                  {t('platformAdmin.selectWorkspace', { ns: 'common' })}
                </div>
              )}

              {selectedWorkspace && (
                <>
                  <div className="mb-6 flex flex-col gap-4 rounded-2xl border border-divider-subtle bg-background-body p-4 lg:flex-row lg:items-start lg:justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <div className="text-text-primary title-xl-semi-bold">{selectedWorkspace.name}</div>
                        <button
                          type="button"
                          className="rounded-md p-1 text-text-tertiary hover:bg-state-base-hover"
                          onClick={() => setShowRenameDialog(true)}
                        >
                          <span className="i-ri-pencil-line h-4 w-4" />
                        </button>
                      </div>
                      <div className="mt-2 flex flex-wrap gap-4 text-text-tertiary system-sm-regular">
                        <span>{t('platformAdmin.memberCount', { ns: 'common', count: selectedWorkspace.member_count })}</span>
                        <span>{selectedWorkspace.owner?.email || t('platformAdmin.ownerless', { ns: 'common' })}</span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="secondary"
                        tone="destructive"
                        loading={deleteWorkspaceMutation.isPending}
                        disabled={!canDeleteSelectedWorkspace}
                        onClick={handleDeleteWorkspace}
                      >
                        {t('platformAdmin.deleteWorkspace', { ns: 'common' })}
                      </Button>
                      <Button variant="secondary" onClick={() => void membersQuery.refetch()}>{t('platformAdmin.refreshMembers', { ns: 'common' })}</Button>
                      <Button variant="primary" onClick={() => setShowInviteDialog(true)}>
                        {t('platformAdmin.inviteMembers', { ns: 'common' })}
                      </Button>
                    </div>
                  </div>

                  <div className="overflow-hidden rounded-2xl border border-divider-subtle">
                    <div className="grid grid-cols-[minmax(0,1.4fr)_140px_120px] border-b border-divider-subtle bg-background-body px-4 py-3 text-text-tertiary system-xs-medium-uppercase">
                      <div>{t('members.name', { ns: 'common' })}</div>
                      <div>{t('members.role', { ns: 'common' })}</div>
                      <div>{t('operation.delete', { ns: 'common' })}</div>
                    </div>
                    {members.map(member => (
                      <div key={member.id} className="grid grid-cols-[minmax(0,1.4fr)_140px_120px] items-center border-b border-divider-subtle px-4 py-3 last:border-b-0">
                        <div className="flex min-w-0 items-center gap-3">
                          <Avatar avatar={member.avatar_url} size="sm" className="shrink-0" name={member.name} />
                          <div className="min-w-0">
                            <div className="truncate text-text-primary system-sm-semibold">
                              {member.name}
                              {member.status === 'pending' && <span className="ml-2 text-text-warning system-xs-medium">{t('members.pending', { ns: 'common' })}</span>}
                            </div>
                            <div className="truncate text-text-tertiary system-xs-regular">{member.email}</div>
                          </div>
                        </div>
                        <div>
                          {member.role === 'owner'
                            ? (
                                <div className="text-text-secondary system-sm-medium">{t(roleLabels[member.role], { ns: 'common' })}</div>
                              )
                            : (
                                <select
                                  className="h-9 w-full rounded-lg border border-divider-subtle bg-components-input-bg-normal px-3 text-sm text-text-secondary outline-none hover:bg-state-base-hover"
                                  value={member.role}
                                  onChange={e => handleUpdateMemberRole({ memberId: member.id, role: e.target.value as RoleKey })}
                                  disabled={updateRoleMutation.isPending}
                                >
                                  {roleOptions.map(role => (
                                    <option key={role} value={role}>{t(roleLabels[role], { ns: 'common' })}</option>
                                  ))}
                                </select>
                              )}
                        </div>
                        <div>
                          <Button
                            size="small"
                            variant="tertiary"
                            tone="destructive"
                            loading={removeMemberMutation.isPending}
                            onClick={() => handleRemoveMember(member.id)}
                          >
                            {t('operation.delete', { ns: 'common' })}
                          </Button>
                        </div>
                      </div>
                    ))}
                    {!membersQuery.isLoading && !members.length && (
                      <div className="px-4 py-12 text-center text-text-tertiary system-sm-regular">
                        {t('platformAdmin.noMembers', { ns: 'common' })}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}

        {section === 'marketplace' && <EnterpriseMarketplaceAdmin />}
      </div>

      <CreateWorkspaceDialog
        show={showCreateDialog}
        loading={createWorkspaceMutation.isPending}
        onClose={() => setShowCreateDialog(false)}
        onSubmit={handleCreateWorkspace}
      />

      <RenameWorkspaceDialog
        show={showRenameDialog}
        loading={renameWorkspaceMutation.isPending}
        name={selectedWorkspace?.name || ''}
        onClose={() => setShowRenameDialog(false)}
        onSubmit={handleRenameWorkspace}
      />

      <InviteMembersDialog
        show={showInviteDialog}
        isEmailSetup={systemFeatures.is_email_setup}
        loading={inviteMembersMutation.isPending}
        onClose={() => setShowInviteDialog(false)}
        onSubmit={handleInviteMembers}
      />

      {showInvitedDialog && (
        <InvitedModal
          invitationResults={invitationResults}
          onCancel={() => setShowInvitedDialog(false)}
        />
      )}
    </>
  )
}

export default PlatformAdminPage
