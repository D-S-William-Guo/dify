'use client'

import type { EnterpriseMarketplaceAsset } from '@/models/common'
import { useDeferredValue, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import DSLConfirmModal from '@/app/components/app/create-from-dsl-modal/dsl-confirm-modal'
import AppIcon from '@/app/components/base/app-icon'
import Button from '@/app/components/base/button'
import Input from '@/app/components/base/input'
import { Dialog, DialogContent, DialogTitle } from '@/app/components/base/ui/dialog'
import { toast } from '@/app/components/base/ui/toast'
import { useAppContext } from '@/context/app-context'
import { NEED_REFRESH_APP_LIST_KEY } from '@/config'
import { useRouter } from '@/next/navigation'
import { DSLImportStatus } from '@/models/app'
import { importDSLConfirm } from '@/service/apps'
import { useEnterpriseMarketplaceMySubmissions, useEnterpriseMarketplacePublicAssets, useUseEnterpriseMarketplaceAsset } from '@/service/use-enterprise-marketplace'
import type { AppIconType } from '@/types/app'
import { AppModeEnum } from '@/types/app'
import { cn } from '@/utils/classnames'
import { getRedirection } from '@/utils/app-redirection'

const AssetDetailDialog = ({
  asset,
  open,
  loading,
  canUse,
  onClose,
  onUse,
}: {
  asset: EnterpriseMarketplaceAsset | null
  open: boolean
  loading: boolean
  canUse: boolean
  onClose: () => void
  onUse: () => void
}) => {
  const { t } = useTranslation()

  if (!asset)
    return null

  return (
    <Dialog open={open} onOpenChange={nextOpen => !nextOpen && onClose()}>
      <DialogContent className="max-w-[720px] p-0">
        <div className="border-b border-divider-subtle p-6 pb-4">
          <DialogTitle className="text-text-primary title-2xl-semi-bold">{asset.title}</DialogTitle>
          <div className="mt-2 text-text-tertiary system-sm-regular">
            {asset.source_workspace_name || t('enterpriseMarketplace.hiddenWorkspace', { ns: 'common' })}
            {' · '}
            {asset.category}
          </div>
        </div>
        <div className="space-y-4 px-6 py-4">
          <div className="text-text-secondary system-md-regular">{asset.description || asset.app_description}</div>
          {!!asset.scenario && (
            <div className="rounded-2xl border border-divider-subtle bg-background-body p-4">
              <div className="mb-2 text-text-primary system-sm-semibold">
                {t('enterpriseMarketplace.scenarioLabel', { ns: 'common' })}
              </div>
              <div className="text-text-tertiary system-sm-regular">{asset.scenario}</div>
            </div>
          )}
          {!!asset.tags.length && (
            <div className="flex flex-wrap gap-2">
              {asset.tags.map(tag => (
                <span key={tag} className="rounded-full bg-background-default px-3 py-1 text-text-tertiary system-xs-medium-uppercase">
                  {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-divider-subtle px-6 py-4">
          <Button onClick={onClose}>{t('operation.cancel', { ns: 'common' })}</Button>
          <Button variant="primary" loading={loading} disabled={!canUse} onClick={onUse}>
            {t('enterpriseMarketplace.useAction', { ns: 'common' })}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

const EnterpriseMarketplace = () => {
  const { t } = useTranslation()
  const { isCurrentWorkspaceEditor } = useAppContext()
  const { push } = useRouter()
  const [keyword, setKeyword] = useState('')
  const deferredKeyword = useDeferredValue(keyword)
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [selectedAsset, setSelectedAsset] = useState<EnterpriseMarketplaceAsset | null>(null)
  const [showDSLConfirmModal, setShowDSLConfirmModal] = useState(false)
  const [pendingVersions, setPendingVersions] = useState<{ importedVersion: string, systemVersion: string }>()
  const [isConfirmingPendingImport, setIsConfirmingPendingImport] = useState(false)
  const pendingImportIdRef = useRef('')
  const pendingAssetIdRef = useRef('')

  const publicAssetQuery = useEnterpriseMarketplacePublicAssets({ keyword: deferredKeyword, limit: 24 })
  const mySubmissionQuery = useEnterpriseMarketplaceMySubmissions()
  const useAssetMutation = useUseEnterpriseMarketplaceAsset()

  const allAssets = publicAssetQuery.data?.items || []
  const categories = useMemo(() => Array.from(new Set(allAssets.map(item => item.category))), [allAssets])
  const visibleAssets = useMemo(() => {
    if (selectedCategory === 'all')
      return allAssets
    return allAssets.filter(item => item.category === selectedCategory)
  }, [allAssets, selectedCategory])

  return (
    <>
      <div className="flex h-full min-h-0 flex-col overflow-hidden border-l-[0.5px] border-divider-regular">
        <div className="flex flex-1 flex-col overflow-y-auto">
          <div className="sticky top-0 z-10 bg-background-body px-12 pb-4 pt-6">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-text-primary system-xl-semibold">
                  {t('enterpriseMarketplace.pageTitle', { ns: 'common' })}
                </div>
                <div className="mt-1 text-text-tertiary system-sm-regular">
                  {t('enterpriseMarketplace.pageSubtitle', { ns: 'common' })}
                </div>
              </div>
              <Input
                showLeftIcon
                showClearIcon
                wrapperClassName="w-full lg:w-[240px]"
                value={keyword}
                onChange={e => setKeyword(e.target.value)}
                onClear={() => setKeyword('')}
              />
            </div>
            <div className="mt-4 flex flex-wrap gap-2">
              <button
                type="button"
                className={cn(
                  'rounded-full border px-3 py-1.5 text-sm',
                  selectedCategory === 'all'
                    ? 'border-components-button-primary-border bg-state-base-hover text-text-primary'
                    : 'border-divider-subtle text-text-tertiary hover:bg-state-base-hover',
                )}
                onClick={() => setSelectedCategory('all')}
              >
                {t('enterpriseMarketplace.allCategories', { ns: 'common' })}
              </button>
              {categories.map(category => (
                <button
                  key={category}
                  type="button"
                  className={cn(
                    'rounded-full border px-3 py-1.5 text-sm',
                    selectedCategory === category
                      ? 'border-components-button-primary-border bg-state-base-hover text-text-primary'
                      : 'border-divider-subtle text-text-tertiary hover:bg-state-base-hover',
                  )}
                  onClick={() => setSelectedCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
          </div>

          {!!mySubmissionQuery.data?.items.length && (
            <div className="px-12 pb-2">
              <div className="rounded-2xl border border-divider-subtle bg-components-panel-bg p-4">
                <div className="mb-3 text-text-primary title-md-semi-bold">
                  {t('enterpriseMarketplace.mySubmissions', { ns: 'common' })}
                </div>
                <div className="space-y-2">
                  {mySubmissionQuery.data.items.slice(0, 3).map(item => (
                    <div key={item.id} className="flex flex-wrap items-center justify-between gap-2 rounded-xl bg-background-body px-4 py-3">
                      <div>
                        <div className="text-text-primary system-sm-semibold">{item.title}</div>
                        <div className="mt-1 text-text-tertiary system-xs-regular">
                          {t(`enterpriseMarketplace.status.${item.status}`, { ns: 'common' })}
                        </div>
                      </div>
                      {!!item.review_note && (
                        <div className="max-w-[480px] text-text-tertiary system-xs-regular">{item.review_note}</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          <div className="grid gap-4 px-12 pb-8 pt-4 xl:grid-cols-2 2xl:grid-cols-3">
            {visibleAssets.map(asset => (
              <button
                key={asset.id}
                type="button"
                className="flex min-h-[220px] flex-col rounded-2xl border border-components-panel-border bg-components-panel-on-panel-item-bg p-5 text-left shadow-sm transition-all duration-200 hover:shadow-lg"
                onClick={() => setSelectedAsset(asset)}
              >
                <div className="flex items-start gap-3">
                  <AppIcon
                    size="large"
                    iconType={asset.app_icon_type as AppIconType | null}
                    icon={asset.app_icon || ''}
                    background={asset.app_icon_background || '#FFFFFF'}
                  />
                  <div className="min-w-0">
                    <div className="truncate text-text-primary title-md-semi-bold">{asset.title}</div>
                    <div className="mt-1 text-text-tertiary system-xs-regular">
                      {asset.source_workspace_name || t('enterpriseMarketplace.hiddenWorkspace', { ns: 'common' })}
                    </div>
                  </div>
                </div>
                <div className="mt-4 line-clamp-4 text-text-secondary system-sm-regular">
                  {asset.description || asset.app_description}
                </div>
                <div className="mt-auto pt-4">
                  <div className="flex flex-wrap gap-2">
                    <span className="rounded-full bg-background-default px-3 py-1 text-text-tertiary system-2xs-medium-uppercase">
                      {asset.category}
                    </span>
                    <span className="rounded-full bg-background-default px-3 py-1 text-text-tertiary system-2xs-medium-uppercase">
                      {asset.app_mode}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {!publicAssetQuery.isLoading && !visibleAssets.length && (
            <div className="px-12 pb-10">
              <div className="rounded-2xl border border-dashed border-divider-subtle px-4 py-10 text-center text-text-tertiary system-sm-regular">
                {t('enterpriseMarketplace.emptyPublic', { ns: 'common' })}
              </div>
            </div>
          )}
        </div>
      </div>

      <AssetDetailDialog
        asset={selectedAsset}
        open={!!selectedAsset}
        loading={useAssetMutation.isPending || isConfirmingPendingImport}
        canUse={isCurrentWorkspaceEditor}
        onClose={() => setSelectedAsset(null)}
        onUse={() => {
          if (!selectedAsset)
            return

          if (pendingImportIdRef.current && pendingAssetIdRef.current === selectedAsset.id) {
            setShowDSLConfirmModal(true)
            return
          }

          useAssetMutation.mutate(selectedAsset.id, {
            onSuccess: (response) => {
              const leakedDependencies = response.leaked_dependencies || []
              if (
                response.import_result.status === DSLImportStatus.PENDING
                && response.import_result.id
              ) {
                pendingImportIdRef.current = response.import_result.id
                pendingAssetIdRef.current = selectedAsset.id
                setPendingVersions({
                  importedVersion: response.import_result.imported_dsl_version || '',
                  systemVersion: response.import_result.current_dsl_version || '',
                })
                setShowDSLConfirmModal(true)
                toast.info(t('enterpriseMarketplace.usePending', { ns: 'common' }))
                return
              }

              if (response.import_result.app_id) {
                toast.success(t('enterpriseMarketplace.useSuccess', { ns: 'common' }))
                if (leakedDependencies.length) {
                  toast.warning(t('enterpriseMarketplace.dependencyWarning', { ns: 'common', count: leakedDependencies.length }))
                }
                localStorage.setItem(NEED_REFRESH_APP_LIST_KEY, '1')
                getRedirection(isCurrentWorkspaceEditor, {
                  id: response.import_result.app_id,
                  mode: response.import_result.app_mode as AppModeEnum,
                }, push)
              }
              else {
                toast.warning(t('enterpriseMarketplace.usePending', { ns: 'common' }))
              }
            },
            onError: (error) => {
              toast.error(error instanceof Error ? error.message : t('api.actionFailed', { ns: 'common' }))
            },
          })
        }}
      />
      {showDSLConfirmModal && (
        <DSLConfirmModal
          versions={pendingVersions}
          confirmDisabled={isConfirmingPendingImport}
          onCancel={() => setShowDSLConfirmModal(false)}
          onConfirm={async () => {
            if (!pendingImportIdRef.current)
              return

            try {
              setIsConfirmingPendingImport(true)
              const response = await importDSLConfirm({
                import_id: pendingImportIdRef.current,
              })

              if (response.status === DSLImportStatus.COMPLETED && response.app_id) {
                toast.success(t('enterpriseMarketplace.useSuccess', { ns: 'common' }))
                localStorage.setItem(NEED_REFRESH_APP_LIST_KEY, '1')
                pendingImportIdRef.current = ''
                pendingAssetIdRef.current = ''
                setShowDSLConfirmModal(false)
                getRedirection(isCurrentWorkspaceEditor, {
                  id: response.app_id,
                  mode: response.app_mode as AppModeEnum,
                }, push)
                return
              }

              toast.error(t('enterpriseMarketplace.confirmFailed', { ns: 'common' }))
            }
            catch (error) {
              toast.error(error instanceof Error ? error.message : t('enterpriseMarketplace.confirmFailed', { ns: 'common' }))
            }
            finally {
              setIsConfirmingPendingImport(false)
            }
          }}
        />
      )}
    </>
  )
}

export default EnterpriseMarketplace
