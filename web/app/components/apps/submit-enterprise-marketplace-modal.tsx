'use client'

import { useEffect, useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import Checkbox from '@/app/components/base/checkbox'
import Input from '@/app/components/base/input'
import Textarea from '@/app/components/base/textarea'
import { Button } from '@langgenius/dify-ui/button'
import { Dialog, DialogContent, DialogTitle } from '@langgenius/dify-ui/dialog'
import { toast } from '@langgenius/dify-ui/toast'
import { useSubmitEnterpriseMarketplaceAsset } from '@/service/use-enterprise-marketplace'

export type SubmitEnterpriseMarketplaceModalProps = {
  appId: string
  open: boolean
  defaultTitle: string
  defaultDescription?: string
  onClose: () => void
}

const SubmitEnterpriseMarketplaceModal = ({
  appId,
  open,
  defaultTitle,
  defaultDescription,
  onClose,
}: SubmitEnterpriseMarketplaceModalProps) => {
  const { t } = useTranslation()
  const submitMarketplaceMutation = useSubmitEnterpriseMarketplaceAsset(appId)
  const [title, setTitle] = useState(defaultTitle)
  const [description, setDescription] = useState(defaultDescription || '')
  const [category, setCategory] = useState('')
  const [tags, setTags] = useState('')
  const [scenario, setScenario] = useState('')
  const [allowShowWorkspaceName, setAllowShowWorkspaceName] = useState(false)

  useEffect(() => {
    if (open) {
      setTitle(defaultTitle)
      setDescription(defaultDescription || '')
      setCategory('')
      setTags('')
      setScenario('')
      setAllowShowWorkspaceName(false)
    }
  }, [defaultDescription, defaultTitle, open])

  const normalizedTags = useMemo(() => tags
    .split(',')
    .map(tag => tag.trim())
    .filter(Boolean), [tags])

  const handleSubmit = () => {
    submitMarketplaceMutation.mutate(
      {
        title: title.trim(),
        description: description.trim(),
        category: category.trim() || 'General',
        tags: normalizedTags,
        scenario: scenario.trim(),
        allow_show_workspace_name: allowShowWorkspaceName,
      },
      {
        onSuccess: () => {
          onClose()
          toast.success(t('enterpriseMarketplace.submitSuccess', { ns: 'common' }))
        },
        onError: (error) => {
          toast.error(
            error instanceof Error
              ? error.message
              : t('enterpriseMarketplace.submitFailed', { ns: 'common' }),
          )
        },
      },
    )
  }

  return (
    <Dialog open={open} onOpenChange={nextOpen => !nextOpen && onClose()}>
      <DialogContent className="max-w-[640px] p-0">
        <div className="p-6 pb-4">
          <DialogTitle className="text-text-primary title-2xl-semi-bold">
            {t('enterpriseMarketplace.submitDialogTitle', { ns: 'common' })}
          </DialogTitle>
        </div>
        <div className="space-y-4 px-6 pb-4">
          <div>
            <div className="mb-2 text-sm text-text-secondary">
              {t('enterpriseMarketplace.titleLabel', { ns: 'common' })}
            </div>
            <Input value={title} onChange={e => setTitle(e.target.value)} maxLength={255} />
          </div>
          <div>
            <div className="mb-2 text-sm text-text-secondary">
              {t('enterpriseMarketplace.descriptionLabel', { ns: 'common' })}
            </div>
            <Textarea value={description} onChange={e => setDescription(e.target.value)} maxLength={5000} />
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <div className="mb-2 text-sm text-text-secondary">
                {t('enterpriseMarketplace.categoryLabel', { ns: 'common' })}
              </div>
              <Input
                value={category}
                onChange={e => setCategory(e.target.value)}
                placeholder={t('enterpriseMarketplace.categoryPlaceholder', { ns: 'common' })}
                maxLength={255}
              />
            </div>
            <div>
              <div className="mb-2 text-sm text-text-secondary">
                {t('enterpriseMarketplace.tagsLabel', { ns: 'common' })}
              </div>
              <Input
                value={tags}
                onChange={e => setTags(e.target.value)}
                placeholder={t('enterpriseMarketplace.tagsPlaceholder', { ns: 'common' })}
              />
            </div>
          </div>
          <div>
            <div className="mb-2 text-sm text-text-secondary">
              {t('enterpriseMarketplace.scenarioLabel', { ns: 'common' })}
            </div>
            <Textarea
              value={scenario}
              onChange={e => setScenario(e.target.value)}
              placeholder={t('enterpriseMarketplace.scenarioPlaceholder', { ns: 'common' })}
              maxLength={5000}
            />
          </div>
          <label className="flex items-start gap-3 rounded-xl border border-divider-subtle bg-background-body px-4 py-3">
            <Checkbox checked={allowShowWorkspaceName} onCheck={() => setAllowShowWorkspaceName(value => !value)} />
            <div>
              <div className="text-text-primary system-sm-medium">
                {t('enterpriseMarketplace.showWorkspaceName', { ns: 'common' })}
              </div>
              <div className="mt-1 text-text-tertiary system-xs-regular">
                {t('enterpriseMarketplace.showWorkspaceNameTip', { ns: 'common' })}
              </div>
            </div>
          </label>
        </div>
        <div className="flex items-center justify-end gap-2 border-t border-divider-subtle px-6 py-4">
          <Button onClick={onClose}>
            {t('operation.cancel', { ns: 'common' })}
          </Button>
          <Button
            variant="primary"
            loading={submitMarketplaceMutation.isPending}
            disabled={!title.trim()}
            onClick={handleSubmit}
          >
            {t('enterpriseMarketplace.submitAction', { ns: 'common' })}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

export default SubmitEnterpriseMarketplaceModal
