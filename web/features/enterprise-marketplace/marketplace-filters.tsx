/* oxlint-disable react/only-export-components -- the nuqs query-state parsers are shared constants consumed by the browse page and the filters surface. */
'use client'

import { Button } from '@langgenius/dify-ui/button'
import { Input } from '@langgenius/dify-ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectItemText,
  SelectTrigger,
  SelectValue,
} from '@langgenius/dify-ui/select'
import { parseAsInteger, parseAsString, parseAsStringEnum, useQueryState } from 'nuqs'
import { useState } from 'react'
import { useTranslation } from 'react-i18next'

export const MARKETPLACE_PAGE_SIZE = 24

export const MARKETPLACE_SORT_VALUES = ['created_at_desc', 'title_asc', 'updated_at_desc'] as const
export type MarketplaceSort = (typeof MARKETPLACE_SORT_VALUES)[number]

export const marketplacePageQueryState = parseAsInteger.withDefault(1)
export const marketplaceSearchQueryState = parseAsString.withDefault('')
export const marketplaceCategoryQueryState = parseAsString.withDefault('')
export const marketplaceSortQueryState = parseAsStringEnum<MarketplaceSort>([
  ...MARKETPLACE_SORT_VALUES,
]).withDefault('created_at_desc')

type MarketplaceFiltersProps = {
  categories: string[]
}

export function MarketplaceFilters({ categories }: MarketplaceFiltersProps) {
  const { t } = useTranslation()
  const [search, setSearch] = useQueryState('search', marketplaceSearchQueryState)
  const [category, setCategory] = useQueryState('category', marketplaceCategoryQueryState)
  const [_page, setPage] = useQueryState('page', marketplacePageQueryState)
  const [searchDraft, setSearchDraft] = useState(search)

  const allCategoriesLabel = t(($) => $['enterpriseMarketplace.browse.categoryAll'], {
    ns: 'common',
  })

  function commitSearch() {
    const keyword = searchDraft.trim()

    void setPage(1)
    void setSearch(keyword || null)
  }

  function commitCategory(nextCategory: string) {
    void setPage(1)
    void setCategory(nextCategory === '' ? null : nextCategory)
  }

  return (
    <div className="flex min-w-0 flex-wrap items-center gap-2">
      <form
        role="search"
        className="flex min-w-0 items-center gap-2"
        onSubmit={(event) => {
          event.preventDefault()
          commitSearch()
        }}
      >
        <Input
          aria-label={t(($) => $['enterpriseMarketplace.browse.searchPlaceholder'], {
            ns: 'common',
          })}
          className="h-8 w-60"
          placeholder={t(($) => $['enterpriseMarketplace.browse.searchPlaceholder'], {
            ns: 'common',
          })}
          value={searchDraft}
          onChange={(event) => setSearchDraft(event.target.value)}
        />
        <Button type="submit" size="small">
          {t(($) => $['enterpriseMarketplace.browse.searchButton'], { ns: 'common' })}
        </Button>
      </form>
      <Select<string>
        value={category}
        onValueChange={(nextCategory) => {
          if (nextCategory) commitCategory(nextCategory)
        }}
      >
        <SelectTrigger aria-label={allCategoriesLabel} className="h-8 w-44">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="">
            <SelectItemText>{allCategoriesLabel}</SelectItemText>
          </SelectItem>
          {categories.map((item) => (
            <SelectItem key={item} value={item}>
              <SelectItemText>{item}</SelectItemText>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
