import type { PluginStatus } from '@/app/components/plugins/types'
import {
  useCallback,
} from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { TaskStatus } from '@/app/components/plugins/types'
import {
  pluginTaskListQueryKey,
  useMutationClearTaskPlugin,
  usePluginTaskList,
} from '@/service/use-plugins'

export const usePluginTaskStatus = (enabled = true) => {
  const queryClient = useQueryClient()
  const {
    pluginTasks,
    handleRefetch,
  } = usePluginTaskList(undefined, enabled)
  const { mutateAsync } = useMutationClearTaskPlugin()
  const cachedTaskList = queryClient.getQueryData<{ tasks: Array<{ id: string, plugins: PluginStatus[] }> }>(pluginTaskListQueryKey)
  const activePluginTasks = enabled ? pluginTasks : (cachedTaskList?.tasks || [])
  const allPlugins = activePluginTasks.map(task => task.plugins.map((plugin) => {
    return {
      ...plugin,
      taskId: task.id,
    }
  })).flat()
  const errorPlugins: PluginStatus[] = []
  const successPlugins: PluginStatus[] = []
  const runningPlugins: PluginStatus[] = []

  allPlugins.forEach((plugin) => {
    if (plugin.status === TaskStatus.running)
      runningPlugins.push(plugin)
    if (plugin.status === TaskStatus.failed)
      errorPlugins.push(plugin)
    if (plugin.status === TaskStatus.success)
      successPlugins.push(plugin)
  })

  const handleClearErrorPlugin = useCallback(async (taskId: string, pluginId: string) => {
    await mutateAsync({
      taskId,
      pluginId,
    })
    handleRefetch()
  }, [mutateAsync, handleRefetch])
  const totalPluginsLength = allPlugins.length
  const runningPluginsLength = runningPlugins.length
  const errorPluginsLength = errorPlugins.length
  const successPluginsLength = successPlugins.length

  const isInstalling = runningPluginsLength > 0 && errorPluginsLength === 0 && successPluginsLength === 0
  const isInstallingWithSuccess = runningPluginsLength > 0 && successPluginsLength > 0 && errorPluginsLength === 0
  const isInstallingWithError = runningPluginsLength > 0 && errorPluginsLength > 0
  const isSuccess = successPluginsLength === totalPluginsLength && totalPluginsLength > 0
  const isFailed = runningPluginsLength === 0 && (errorPluginsLength + successPluginsLength) === totalPluginsLength && totalPluginsLength > 0 && errorPluginsLength > 0

  return {
    errorPlugins,
    successPlugins,
    runningPlugins,
    runningPluginsLength,
    errorPluginsLength,
    successPluginsLength,
    totalPluginsLength,
    isInstalling,
    isInstallingWithSuccess,
    isInstallingWithError,
    isSuccess,
    isFailed,
    handleClearErrorPlugin,
  }
}
