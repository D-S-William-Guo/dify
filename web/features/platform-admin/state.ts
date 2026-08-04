'use client'

import { atom } from 'jotai'
import { atomWithQuery } from 'jotai-tanstack-query'
import { consoleQuery } from '@/service/client'

const platformAdminStatusQueryAtom = atomWithQuery(() => {
  return consoleQuery.account.platformAdminStatus.get.queryOptions()
})

export const platformAdminStatusPendingAtom = atom((get) => {
  return get(platformAdminStatusQueryAtom).isPending
})

export const platformAdminStatusErrorAtom = atom((get) => {
  return get(platformAdminStatusQueryAtom).isError
})

export const isPlatformAdminAtom = atom((get) => {
  return get(platformAdminStatusQueryAtom).data?.is_platform_admin === true
})

export const platformAdminMutationSupportedAtom = atom((get) => {
  return get(platformAdminStatusQueryAtom).data?.mutation_supported === true
})
