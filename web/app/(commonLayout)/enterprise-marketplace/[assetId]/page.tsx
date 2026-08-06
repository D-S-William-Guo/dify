import { MarketplaceDetailPage } from '@/features/enterprise-marketplace/detail-page'

type EnterpriseMarketplaceDetailPageProps = {
  params: Promise<{ assetId: string }>
}

export default async function EnterpriseMarketplaceDetailPage({
  params,
}: EnterpriseMarketplaceDetailPageProps) {
  const { assetId } = await params

  return <MarketplaceDetailPage assetId={assetId} />
}
