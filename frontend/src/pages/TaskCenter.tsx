import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  Play,
  XCircle,
  Trash2,
  RefreshCw,
  Loader2,
  CheckCircle,
  AlertCircle,
  Zap,
  Activity,
  Database,
  Users,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import api from '../lib/api'

export function TaskCenter() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [isOperating, setIsOperating] = useState(false)

  // Fetch system stats
  const { data: systemStats, refetch: refetchSystemStats } = useQuery({
    queryKey: ['system-stats'],
    queryFn: () => api.getSystemStats(),
    refetchInterval: 5000, // Auto refresh every 5 seconds
  })

  // Fetch queue stats
  const { data: queueStats, refetch: refetchQueueStats } = useQuery({
    queryKey: ['queue-stats'],
    queryFn: () => api.getQueueStats(),
    refetchInterval: 5000,
  })

  // Fetch worker stats
  const { data: workerStats } = useQuery({
    queryKey: ['worker-stats'],
    queryFn: () => api.getWorkerStats(),
    refetchInterval: 10000,
  })

  // Batch start all queued
  const startAllMutation = useMutation({
    mutationFn: () => api.batchStartAllQueued(),
    onSuccess: (data) => {
      alert(t('taskCenter.startSuccess', { count: data.affected_count }))
      refetchSystemStats()
      refetchQueueStats()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error: any) => {
      alert(t('taskCenter.startFailed', { error: error.message }))
    },
  })

  // Batch cancel all running
  const cancelAllMutation = useMutation({
    mutationFn: () => api.batchCancelAllRunning(),
    onSuccess: (data) => {
      alert(t('taskCenter.cancelSuccess', { count: data.affected_count }))
      refetchSystemStats()
      refetchQueueStats()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error: any) => {
      alert(t('taskCenter.cancelFailed', { error: error.message }))
    },
  })

  // Batch delete completed
  const deleteCompletedMutation = useMutation({
    mutationFn: () => api.batchDeleteCompleted(),
    onSuccess: (data) => {
      alert(t('taskCenter.deleteSuccess', { count: data.affected_count }))
      refetchSystemStats()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
    onError: (error: any) => {
      alert(t('taskCenter.deleteFailed', { error: error.message }))
    },
  })

  // Scan all libraries
  const scanAllMutation = useMutation({
    mutationFn: (forceRescan: boolean) =>
      api.scanAllLibraries({ force_rescan: forceRescan }),
    onSuccess: (data) => {
      alert(t('taskCenter.scanCreated', { message: data.message }))
      refetchQueueStats()
    },
    onError: (error: any) => {
      alert(t('taskCenter.scanFailed', { error: error.message }))
    },
  })

  const handleStartAll = async () => {
    if (!systemStats?.queued_jobs) {
      alert(t('taskCenter.noPendingTasks'))
      return
    }
    if (confirm(t('taskCenter.confirmStartAll', { count: systemStats.queued_jobs }))) {
      setIsOperating(true)
      try {
        await startAllMutation.mutateAsync()
      } finally {
        setIsOperating(false)
      }
    }
  }

  const handleCancelAll = async () => {
    const totalActive = (systemStats?.queued_jobs || 0) + (systemStats?.running_jobs || 0)
    if (!totalActive) {
      alert(t('taskCenter.noRunningTasks'))
      return
    }
    if (confirm(t('taskCenter.confirmCancelAll', { count: totalActive }))) {
      setIsOperating(true)
      try {
        await cancelAllMutation.mutateAsync()
      } finally {
        setIsOperating(false)
      }
    }
  }

  const handleDeleteCompleted = async () => {
    const totalCompleted =
      (systemStats?.completed_jobs || 0) +
      (systemStats?.failed_jobs || 0) +
      (systemStats?.cancelled_jobs || 0)
    if (!totalCompleted) {
      alert(t('taskCenter.noCompletedTasks'))
      return
    }
    if (confirm(t('taskCenter.confirmDeleteAll', { count: totalCompleted }))) {
      setIsOperating(true)
      try {
        await deleteCompletedMutation.mutateAsync()
      } finally {
        setIsOperating(false)
      }
    }
  }

  const handleScanAll = async (forceRescan: boolean) => {
    const message = forceRescan
      ? t('taskCenter.confirmForceScan')
      : t('taskCenter.confirmNormalScan')
    if (confirm(message)) {
      setIsOperating(true)
      try {
        await scanAllMutation.mutateAsync(forceRescan)
      } finally {
        setIsOperating(false)
      }
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">{t('taskCenter.title')}</h1>
        <p className="text-muted-foreground mt-2">
          {t('taskCenter.subtitle')}
        </p>
      </div>

      {/* System Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('taskCenter.totalTasks')}</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.total_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">{t('taskCenter.allTasks')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('taskCenter.queued')}</CardTitle>
            <Loader2 className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.queued_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">{t('taskCenter.pendingTasksLabel')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('taskCenter.runningLabel')}</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.running_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">{t('taskCenter.executingLabel')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('taskCenter.completedLabel')}</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.completed_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">{t('taskCenter.successfullyCompleted')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Queue Stats */}
      <Card>
        <CardHeader>
          <CardTitle>{t('taskCenter.queueStatus')}</CardTitle>
          <CardDescription>{t('taskCenter.queueStatusDesc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{t('taskCenter.translateQueue')}</span>
                <span className="text-2xl font-bold">{queueStats?.translate_queue || 0}</span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 transition-all"
                  style={{
                    width: `${Math.min(
                      ((queueStats?.translate_queue || 0) / Math.max(queueStats?.total || 1, 1)) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{t('taskCenter.asrQueue')}</span>
                <span className="text-2xl font-bold">{queueStats?.asr_queue || 0}</span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-green-500 transition-all"
                  style={{
                    width: `${Math.min(
                      ((queueStats?.asr_queue || 0) / Math.max(queueStats?.total || 1, 1)) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">{t('taskCenter.scanQueue')}</span>
                <span className="text-2xl font-bold">{queueStats?.scan_queue || 0}</span>
              </div>
              <div className="h-2 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 transition-all"
                  style={{
                    width: `${Math.min(
                      ((queueStats?.scan_queue || 0) / Math.max(queueStats?.total || 1, 1)) * 100,
                      100
                    )}%`,
                  }}
                />
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Worker Stats */}
      <Card>
        <CardHeader>
          <CardTitle>{t('taskCenter.workerStatus')}</CardTitle>
          <CardDescription>{t('taskCenter.workerStatusDesc2')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Users className="h-8 w-8 text-muted-foreground" />
            <div>
              <div className="text-2xl font-bold">{workerStats?.active_workers || 0}</div>
              <p className="text-sm text-muted-foreground">{t('taskCenter.activeWorkers')}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Operations */}
      <Card>
        <CardHeader>
          <CardTitle>{t('taskCenter.batchOperations')}</CardTitle>
          <CardDescription>{t('taskCenter.batchOperationsDesc2')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            <Button
              onClick={handleStartAll}
              disabled={!systemStats?.queued_jobs || isOperating}
              className="w-full"
              size="lg"
            >
              {isOperating ? (
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <Play className="h-5 w-5 mr-2" />
              )}
{t('taskCenter.startAllQueued')}
              {systemStats?.queued_jobs ? ` (${systemStats.queued_jobs})` : ''}
            </Button>

            <Button
              onClick={handleCancelAll}
              disabled={
                !(systemStats?.queued_jobs || systemStats?.running_jobs) || isOperating
              }
              variant="destructive"
              className="w-full"
              size="lg"
            >
              {isOperating ? (
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <XCircle className="h-5 w-5 mr-2" />
              )}
              {t('taskCenter.cancelAllRunningTasks')}
              {systemStats &&
                ` (${(systemStats.queued_jobs || 0) + (systemStats.running_jobs || 0)})`}
            </Button>

            <Button
              onClick={handleDeleteCompleted}
              disabled={
                !(
                  systemStats?.completed_jobs ||
                  systemStats?.failed_jobs ||
                  systemStats?.cancelled_jobs
                ) || isOperating
              }
              variant="outline"
              className="w-full"
              size="lg"
            >
              {isOperating ? (
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <Trash2 className="h-5 w-5 mr-2" />
              )}
              {t('taskCenter.deleteCompletedTasks')}
              {systemStats &&
                ` (${
                  (systemStats.completed_jobs || 0) +
                  (systemStats.failed_jobs || 0) +
                  (systemStats.cancelled_jobs || 0)
                })`}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Library Scanning */}
      <Card>
        <CardHeader>
          <CardTitle>{t('taskCenter.libraryScanning')}</CardTitle>
          <CardDescription>{t('taskCenter.libraryScanningDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <Button
              onClick={() => handleScanAll(false)}
              disabled={isOperating}
              className="w-full"
              size="lg"
            >
              {isOperating ? (
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <RefreshCw className="h-5 w-5 mr-2" />
              )}
{t('taskCenter.scanAllLibraries')}
            </Button>

            <Button
              onClick={() => handleScanAll(true)}
              disabled={isOperating}
              variant="outline"
              className="w-full"
              size="lg"
            >
              {isOperating ? (
                <Loader2 className="h-5 w-5 mr-2 animate-spin" />
              ) : (
                <Zap className="h-5 w-5 mr-2" />
              )}
{t('taskCenter.forceRescan')}
            </Button>
          </div>

          <div className="rounded-lg bg-muted p-4 text-sm">
            <p className="font-medium mb-2">{t('taskCenter.scanningInstructions')}</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>{t('taskCenter.normalScan')}</li>
              <li>{t('taskCenter.forceScanDesc')}</li>
              <li>{t('taskCenter.afterScanDesc')}</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Error Stats */}
      {(systemStats?.failed_jobs || 0) > 0 && (
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-destructive">
              <AlertCircle className="h-5 w-5" />
{t('taskCenter.failedTasks')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {t('taskCenter.failedTasksCount', { count: systemStats?.failed_jobs })}
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              {t('taskCenter.failedTasksDesc')}
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
