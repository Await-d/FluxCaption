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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import api from '@/lib/api'

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
    if (confirm(`确定要启动所有 ${systemStats.queued_jobs} 个排队中的任务吗？`)) {
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
    if (confirm(`确定要取消所有 ${totalActive} 个运行中/排队中的任务吗？`)) {
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
    if (confirm(`确定要删除所有 ${totalCompleted} 个已完成/失败/取消的任务吗？此操作不可撤销！`)) {
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
      ? '确定要强制重新扫描所有媒体库吗？这会创建新的任务。'
      : '确定要扫描所有媒体库吗？'
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
        <h1 className="text-3xl font-bold">任务中心</h1>
        <p className="text-muted-foreground mt-2">
          集中管理所有后台任务和系统操作
        </p>
      </div>

      {/* System Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总任务数</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.total_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">所有任务</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">排队中</CardTitle>
            <Loader2 className="h-4 w-4 text-yellow-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.queued_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">待执行任务</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">运行中</CardTitle>
            <Activity className="h-4 w-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.running_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">正在执行</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">已完成</CardTitle>
            <CheckCircle className="h-4 w-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{systemStats?.completed_jobs || 0}</div>
            <p className="text-xs text-muted-foreground">成功完成</p>
          </CardContent>
        </Card>
      </div>

      {/* Queue Stats */}
      <Card>
        <CardHeader>
          <CardTitle>队列状态</CardTitle>
          <CardDescription>Celery 任务队列实时状态</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">翻译队列</span>
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
                <span className="text-sm font-medium">ASR 队列</span>
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
                <span className="text-sm font-medium">扫描队列</span>
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
          <CardTitle>Worker 状态</CardTitle>
          <CardDescription>Celery Worker 运行状态</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <Users className="h-8 w-8 text-muted-foreground" />
            <div>
              <div className="text-2xl font-bold">{workerStats?.active_workers || 0}</div>
              <p className="text-sm text-muted-foreground">活跃 Workers</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Operations */}
      <Card>
        <CardHeader>
          <CardTitle>批量操作</CardTitle>
          <CardDescription>对所有任务进行批量管理操作</CardDescription>
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
              启动所有排队任务
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
              取消所有运行任务
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
              删除已完成任务
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
          <CardTitle>媒体库扫描</CardTitle>
          <CardDescription>扫描 Jellyfin 媒体库并创建翻译任务</CardDescription>
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
              扫描所有媒体库
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
              强制重新扫描
            </Button>
          </div>

          <div className="rounded-lg bg-muted p-4 text-sm">
            <p className="font-medium mb-2">扫描说明：</p>
            <ul className="list-disc list-inside space-y-1 text-muted-foreground">
              <li>普通扫描：只为新发现的缺失语言创建任务</li>
              <li>强制扫描：重新检测所有媒体，可能创建重复任务</li>
              <li>扫描完成后，根据自动翻译规则决定是否自动启动任务</li>
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
              失败任务
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-destructive">
              {systemStats?.failed_jobs} 个任务失败
            </div>
            <p className="text-sm text-muted-foreground mt-2">
              建议前往任务列表页面查看详细错误信息并处理失败任务
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
