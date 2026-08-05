import { WorkspaceDetailPage } from '@/features/platform-admin/workspace-detail-page'

type PlatformAdminWorkspaceDetailPageProps = {
  params: Promise<{ workspaceId: string }>
}

export default async function PlatformAdminWorkspaceDetailPage({
  params,
}: PlatformAdminWorkspaceDetailPageProps) {
  const { workspaceId } = await params

  return <WorkspaceDetailPage workspaceId={workspaceId} />
}
