'use client'

import type { PlatformAdminMemberResponse } from '@dify/contracts/api/console/platform-admin/types.gen'
import { Button } from '@langgenius/dify-ui/button'
import { useQuery } from '@tanstack/react-query'
import { useAtomValue } from 'jotai'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { consoleQuery } from '@/service/client'
import { ChangeMemberRoleDialog } from './change-member-role-dialog'
import { mapPlatformAdminError } from './errors'
import { InviteMembersDialog } from './invite-members-dialog'
import { MemberTable } from './member-table'
import { RbacUnavailableBanner } from './rbac-unavailable-banner'
import { RenameWorkspaceDialog } from './rename-workspace-dialog'
import {
  isPlatformAdminAtom,
  platformAdminMutationSupportedAtom,
  platformAdminStatusErrorAtom,
  platformAdminStatusPendingAtom,
} from './state'

function workspaceDetailQueryRetry(failureCount: number, error: unknown) {
  if (error instanceof Response) return false

  return failureCount < 2
}

export function WorkspaceDetailPage({ workspaceId }: { workspaceId: string }) {
  const statusPending = useAtomValue(platformAdminStatusPendingAtom)
  const statusError = useAtomValue(platformAdminStatusErrorAtom)
  const isPlatformAdmin = useAtomValue(isPlatformAdminAtom)

  if (statusPending) return <DetailGateState kind="loading" />

  if (statusError || !isPlatformAdmin) return <DetailGateState kind="denied" />

  return <WorkspaceDetailContent workspaceId={workspaceId} />
}

function DetailGateState({ kind }: { kind: 'loading' | 'denied' }) {
  const { t } = useTranslation()
  const message =
    kind === 'loading'
      ? t(($) => $['platformAdmin.errors.loading'], { ns: 'common' })
      : t(($) => $['platformAdmin.errors.permissionDenied'], { ns: 'common' })

  return (
    <div className="flex h-full min-h-0 flex-col items-center justify-center gap-3 bg-background-body">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
    </div>
  )
}

function WorkspaceDetailContent({ workspaceId }: { workspaceId: string }) {
  const { t } = useTranslation()
  const globalMutationSupported = useAtomValue(platformAdminMutationSupportedAtom)
  const [renameOpen, setRenameOpen] = useState(false)
  const [inviteOpen, setInviteOpen] = useState(false)
  const [roleChangeMember, setRoleChangeMember] = useState<PlatformAdminMemberResponse | null>(null)

  const detailQuery = useQuery(
    consoleQuery.platformAdmin.workspaces.byWorkspaceId.get.queryOptions({
      input: { params: { workspace_id: workspaceId } },
      retry: workspaceDetailQueryRetry,
    }),
  )
  const membersQuery = useQuery(
    consoleQuery.platformAdmin.workspaces.byWorkspaceId.members.get.queryOptions({
      input: { params: { workspace_id: workspaceId } },
      retry: workspaceDetailQueryRetry,
    }),
  )

  if (detailQuery.isPending) {
    return (
      <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
        <div className="px-8 pt-4 pb-2">
          <div className="h-4 w-40 animate-pulse rounded bg-state-base-hover motion-reduce:animate-none" />
        </div>
      </div>
    )
  }

  if (detailQuery.isError) {
    const mapped = mapPlatformAdminError(detailQuery.error)
    const message =
      mapped.kind === 'unknown'
        ? t(($) => $['platformAdmin.errors.notFound'], { ns: 'common' })
        : t(($) => $[mapped.key], { ns: 'common' })

    return (
      <div className="flex h-full min-h-0 flex-col items-center justify-center gap-3 bg-background-body">
        <p className="system-sm-regular text-text-tertiary">{message}</p>
        <Button
          type="button"
          size="small"
          variant="secondary"
          onClick={() => void detailQuery.refetch()}
        >
          {t(($) => $['platformAdmin.workspaces.retry'], { ns: 'common' })}
        </Button>
      </div>
    )
  }

  const workspace = detailQuery.data
  const members = membersQuery.data
  const workspaceMutationSupported =
    globalMutationSupported && (members?.mutation_supported ?? true)
  const hasRbacUnavailableMember =
    members?.items.some((member) => member.role_source === 'rbac_unavailable') ?? false
  const showRbacBanner = !workspaceMutationSupported || hasRbacUnavailableMember

  return (
    <div className="flex h-full min-h-0 flex-col overflow-y-auto bg-background-body">
      <div className="flex items-center justify-between gap-4 px-8 pt-4 pb-2">
        <div className="min-w-0">
          <h1 className="system-md-semibold text-text-primary">
            {t(($) => $['platformAdmin.workspaceDetail.title'], { ns: 'common' })}
          </h1>
          <p className="truncate system-xl-semibold text-text-primary">{workspace.name}</p>
        </div>
        <Button
          type="button"
          size="small"
          variant="secondary"
          disabled={!workspaceMutationSupported}
          onClick={() => setRenameOpen(true)}
        >
          {t(($) => $['platformAdmin.renameWorkspace.title'], { ns: 'common' })}
        </Button>
      </div>

      {showRbacBanner && (
        <div className="px-8 pb-2">
          <RbacUnavailableBanner />
        </div>
      )}

      <div className="flex items-center justify-between gap-4 px-8 pt-2 pb-2">
        <h2 className="system-md-semibold text-text-primary">
          {t(($) => $['platformAdmin.members.title'], { ns: 'common' })}
        </h2>
        <Button
          type="button"
          size="small"
          variant="primary"
          disabled={!workspaceMutationSupported}
          onClick={() => setInviteOpen(true)}
        >
          {t(($) => $['platformAdmin.invite.title'], { ns: 'common' })}
        </Button>
      </div>

      <div className="grow px-8 pb-8">
        {membersQuery.isPending ? (
          <div
            role="status"
            aria-label={t(($) => $['platformAdmin.members.loading'], { ns: 'common' })}
            className="flex flex-col gap-2 rounded-xl border border-components-panel-border bg-components-panel-bg p-4"
          >
            {[0, 1, 2].map((index) => (
              <div
                key={index}
                className="h-10 animate-pulse rounded-lg bg-state-base-hover motion-reduce:animate-none"
              />
            ))}
          </div>
        ) : membersQuery.isError ? (
          <MembersErrorState
            error={membersQuery.error}
            onRetry={() => void membersQuery.refetch()}
          />
        ) : membersQuery.data!.items.length === 0 ? (
          <p className="py-8 text-center system-sm-regular text-text-tertiary">
            {t(($) => $['platformAdmin.members.empty'], { ns: 'common' })}
          </p>
        ) : (
          <MemberTable
            members={membersQuery.data!.items}
            mutationSupported={workspaceMutationSupported}
            onChangeRole={setRoleChangeMember}
          />
        )}
      </div>

      <RenameWorkspaceDialog
        key={workspace.name}
        workspace={workspace}
        open={renameOpen}
        onOpenChange={setRenameOpen}
      />
      <InviteMembersDialog
        key={String(inviteOpen)}
        workspaceId={workspaceId}
        open={inviteOpen}
        onOpenChange={setInviteOpen}
      />
      {roleChangeMember && (
        <ChangeMemberRoleDialog
          member={roleChangeMember}
          workspaceId={workspaceId}
          open
          onOpenChange={(open) => {
            if (!open) setRoleChangeMember(null)
          }}
        />
      )}
    </div>
  )
}

function MembersErrorState({ error, onRetry }: { error: unknown; onRetry: () => void }) {
  const { t } = useTranslation()
  const mapped = mapPlatformAdminError(error)
  const message =
    mapped.kind === 'unknown'
      ? t(($) => $['platformAdmin.members.error'], { ns: 'common' })
      : t(($) => $[mapped.key], { ns: 'common' })

  return (
    <div className="flex flex-col items-center gap-3 py-8">
      <p className="system-sm-regular text-text-tertiary">{message}</p>
      <Button type="button" size="small" variant="secondary" onClick={onRetry}>
        {t(($) => $['platformAdmin.members.retry'], { ns: 'common' })}
      </Button>
    </div>
  )
}
