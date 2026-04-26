'use client'

import {
  RiStore2Fill,
  RiStore2Line,
} from '@remixicon/react'
import { useTranslation } from 'react-i18next'
import Link from '@/next/link'
import { usePathname } from '@/next/navigation'
import { cn } from '@langgenius/dify-ui/cn'

type EnterpriseMarketplaceNavProps = {
  className?: string
}

const EnterpriseMarketplaceNav = ({
  className,
}: EnterpriseMarketplaceNavProps) => {
  const { t } = useTranslation()
  const pathname = usePathname()
  const activated = pathname?.startsWith('/explore/marketplace')

  return (
    <Link
      href="/explore/marketplace"
      prefetch={false}
      className={cn(
        className,
        'group',
        activated && 'bg-components-main-nav-nav-button-bg-active shadow-md',
        activated
          ? 'text-components-main-nav-nav-button-text-active'
          : 'text-components-main-nav-nav-button-text hover:bg-components-main-nav-nav-button-bg-hover',
      )}
    >
      {activated ? <RiStore2Fill className="h-4 w-4" /> : <RiStore2Line className="h-4 w-4" />}
      <div className="ml-2 max-[1024px]:hidden">
        {t('enterpriseMarketplace.sidebarTitle', { ns: 'common' })}
      </div>
    </Link>
  )
}

export default EnterpriseMarketplaceNav
