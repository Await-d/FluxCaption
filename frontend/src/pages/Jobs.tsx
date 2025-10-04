import { useState, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { RefreshCw, XCircle, RotateCcw, Download, Eye, PlayCircle, FileText, Trash2 } from 'lucide-react'
import { Checkbox } from '@/components/ui/Checkbox'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { SubtitlePreviewDialog } from '@/components/SubtitlePreviewDialog'
import { TaskLogsDialog } from '@/components/TaskLogsDialog'
import api from '@/lib/api'
import { subscribeToJobProgress } from '@/lib/sse'
import { getStatusColor, getStatusText, getLanguageName } from '@/lib/utils'
import type { JobListResponse, JobStatus, JobType, ProgressEvent } from '@/types/api'
import { useTranslation } from 'react-i18next'

export function Jobs() {
  const { t } = useTranslation()
  const [statusFilter, setStatusFilter] = useState<JobStatus | 'all'>('all')
  const [typeFilter, setTypeFilter] = useState<JobType | 'all'>('all')
  const [previewJob, setPreviewJob] = useState<{ jobId: string; fileIndex?: number } | null>(null)
  const [logsJobId, setLogsJobId] = useState<string | null>(null)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize] = useState(20)
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set())

  // Independent state for SSE progress updates (doesn't trigger re-subscription)
  const [jobProgress, setJobProgress] = useState<Record<string, number>>({})

  // Fetch jobs with filters and pagination
  const { data, isLoading, refetch } = useQuery<JobListResponse>({
    queryKey: ['jobs', { 
      status: statusFilter !== 'all' ? statusFilter : undefined, 
      type: typeFilter !== 'all' ? typeFilter : undefined,
      page: currentPage,
      page_size: pageSize
    }],
    queryFn: () =>
      api.getJobs({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: typeFilter !== 'all' ? typeFilter : undefined,
        page: currentPage,
        page_size: pageSize,
      }),
    refetchInterval: 5000, // Poll every 5 seconds
  })

  // Reset to page 1 when filters change
  useEffect(() => {
    setCurrentPage(1)
  }, [statusFilter, typeFilter])

  // Calculate pagination info
  const totalPages = data ? Math.ceil(data.total / data.page_size) : 0

  // Handle job cancellation
  const handleCancelJob = async (jobId: string) => {
    try {
      await api.cancelJob(jobId)
      refetch()
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  // Handle job retry
  const handleRetryJob = async (jobId: string) => {
    try {
      await api.retryJob(jobId)
      refetch()
    } catch (error) {
      console.error('Failed to retry job:', error)
    }
  }

  // Handle job deletion
  const handleDeleteJob = async (jobId: string) => {
    try {
      await api.deleteJob(jobId)
      setSelectedJobs(prev => {
        const newSet = new Set(prev)
        newSet.delete(jobId)
        return newSet
      })
      refetch()
    } catch (error) {
      console.error('Failed to delete job:', error)
    }
  }

  // Handle job start
  const handleStartJob = async (jobId: string) => {
    try {
      await api.startJob(jobId)
      refetch()
    } catch (error) {
      console.error('Failed to start job:', error)
    }
  }

  // Handle subtitle download
  const handleDownloadSubtitle = async (jobId: string, fileIndex: number = 0) => {
    try {
      const blob = await api.downloadSubtitle(jobId, fileIndex)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `subtitle_${jobId}.srt`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download subtitle:', error)
    }
  }

  // Handle batch cancel
  const handleBatchCancel = async () => {
    const cancelableJobs = Array.from(selectedJobs).filter(jobId => {
      const job = data?.jobs.find(j => j.id === jobId)
      return job && (job.status === 'queued' || job.status === 'running')
    })

    if (cancelableJobs.length === 0) {
      return
    }

    try {
      await Promise.all(cancelableJobs.map(jobId => api.cancelJob(jobId)))
      setSelectedJobs(new Set())
      refetch()
    } catch (error) {
      console.error('Failed to batch cancel jobs:', error)
    }
  }

  // Handle batch start
  const handleBatchStart = async () => {
    const startableJobs = Array.from(selectedJobs).filter(jobId => {
      const job = data?.jobs.find(j => j.id === jobId)
      return job && job.status === 'queued'
    })

    if (startableJobs.length === 0) {
      return
    }

    try {
      await api.batchStartJobs(startableJobs)
      setSelectedJobs(new Set())
      refetch()
    } catch (error) {
      console.error('Failed to batch start jobs:', error)
    }
  }

  // Toggle job selection
  const toggleJobSelection = (jobId: string) => {
    setSelectedJobs(prev => {
      const newSet = new Set(prev)
      if (newSet.has(jobId)) {
        newSet.delete(jobId)
      } else {
        newSet.add(jobId)
      }
      return newSet
    })
  }

  // Select all visible jobs
  const selectAllVisible = () => {
    const visibleJobIds = data?.jobs.map(j => j.id) || []
    setSelectedJobs(new Set(visibleJobIds))
  }

  // Clear selection
  const clearSelection = () => {
    setSelectedJobs(new Set())
  }

  // Subscribe to running jobs progress via SSE
  useEffect(() => {
    const runningJobs = data?.jobs.filter((j) => j.status === 'running') || []
    
    // Clear progress for jobs that are no longer running
    setJobProgress((prev) => {
      const newProgress = { ...prev }
      Object.keys(newProgress).forEach((jobId) => {
        if (!runningJobs.find((j) => j.id === jobId)) {
          delete newProgress[jobId]
        }
      })
      return newProgress
    })

    // Setup SSE subscriptions for all running jobs
    const subscriptions = runningJobs.map((job) =>
      subscribeToJobProgress(
        job.id,
        (event: ProgressEvent) => {
          // Update progress in independent state (doesn't trigger re-subscription)
          setJobProgress((prev) => ({
            ...prev,
            [event.job_id]: event.progress || 0,
          }))
        },
        (error) => {
          console.error(`SSE error for job ${job.id}:`, error)
        }
      )
    )

    // Cleanup all subscriptions on unmount or when job IDs change
    return () => {
      subscriptions.forEach((sub) => sub.unsubscribe())
    }
  }, [data?.jobs.filter((j) => j.status === 'running').map((j) => j.id).join(',')])

  // Separate running jobs for the active section
  const runningJobs = data?.jobs.filter((job) => job.status === 'running') || []
  const otherJobs = data?.jobs.filter((job) => job.status !== 'running') || []

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Currently Running Section */}
      {runningJobs.length > 0 && (
        <Card className="border-blue-500/50 bg-blue-500/5">
          <CardHeader className="p-3 sm:p-6">
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <div className="h-2 w-2 bg-blue-500 rounded-full animate-pulse" />
              当前正在执行的任务 ({runningJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="p-3 sm:p-6">
            <div className="space-y-3 sm:space-y-4">
              {runningJobs.map((job) => (
                <div key={job.id} className="p-3 sm:p-4 rounded-lg border border-blue-500/20 bg-background/50">
                  <div className="flex items-start justify-between gap-2 mb-2 sm:mb-3">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold text-base sm:text-lg truncate">{job.source_type}</h3>
                        <Badge className={`${getStatusColor(job.status)} text-xs`}>
                          {getStatusText(job.status)}
                        </Badge>
                      </div>
                      <p className="text-xs sm:text-sm text-muted-foreground mt-1 truncate">
                        <span className="hidden sm:inline">ID: </span>
                        <span className="sm:hidden">ID: </span>
                        {job.id.slice(0, 8)}...
                      </p>
                    </div>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleCancelJob(job.id)}
                      className="shrink-0"
                    >
                      <XCircle className="h-4 w-4 sm:mr-2" />
                      <span className="hidden sm:inline">{t('jobs.cancel')}</span>
                    </Button>
                  </div>

                  {/* Progress with larger display */}
                  <div className="space-y-1 sm:space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-xs sm:text-sm font-medium">翻译进度</span>
                      <span className="text-base sm:text-lg font-bold text-blue-500">{jobProgress[job.id] ?? job.progress}%</span>
                    </div>
                    <Progress value={jobProgress[job.id] ?? job.progress} className="h-2 sm:h-3" />
                  </div>

                  {/* Job details in compact grid */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3 text-xs sm:text-sm mt-2 sm:mt-3">
                    <div>
                      <span className="text-muted-foreground">{t('jobs.source')}:</span>{' '}
                      <span className="font-medium">
                        {job.source_lang ? getLanguageName(job.source_lang) : t('jobs.autoDetect')}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('jobs.target')}:</span>{' '}
                      <span className="font-medium">
                        {job.target_langs.map(getLanguageName).join(', ')}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardHeader className="p-3 sm:p-6">
          <div className="flex items-center justify-between gap-2">
            <CardTitle className="text-base sm:text-lg">{t('jobs.jobQueue')}</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetch()} className="shrink-0">
              <RefreshCw className="h-4 w-4 sm:mr-2" />
              <span className="hidden sm:inline">{t('jobs.refresh')}</span>
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-3 sm:p-6">
          <div className="flex gap-3 sm:gap-4">
            <div className="flex-1">
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('jobs.status')}</label>
              <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as JobStatus | 'all')}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('jobs.allStatuses')}</SelectItem>
                  <SelectItem value="queued">排队中</SelectItem>
                  <SelectItem value="running">{t('jobs.running')}</SelectItem>
                  <SelectItem value="success">成功</SelectItem>
                  <SelectItem value="failed">{t('jobs.failed')}</SelectItem>
                  <SelectItem value="cancelled">已取消</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('jobs.type')}</label>
              <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as JobType | 'all')}>
                <SelectTrigger className="h-9">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('jobs.allTypes')}</SelectItem>
                  <SelectItem value="scan">{t('jobs.scan')}</SelectItem>
                  <SelectItem value="translate">{t('jobs.translate')}</SelectItem>
                  <SelectItem value="asr_then_translate">{t('jobs.asrTranslate')}</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Batch Operations */}
      {data && data.jobs.length > 0 && (
        <Card>
          <CardContent className="p-3 sm:p-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <Checkbox
                  checked={selectedJobs.size === data.jobs.length && data.jobs.length > 0}
                  onCheckedChange={(checked: boolean) => {
                    if (checked) {
                      selectAllVisible()
                    } else {
                      clearSelection()
                    }
                  }}
                />
                <span className="text-sm text-muted-foreground">
                  {selectedJobs.size > 0 ? `已选择 ${selectedJobs.size} 个任务` : '全选'}
                </span>
              </div>
              
              {selectedJobs.size > 0 && (
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleBatchStart}
                    disabled={!Array.from(selectedJobs).some(jobId => {
                      const job = data.jobs.find(j => j.id === jobId)
                      return job && job.status === 'queued'
                    })}
                  >
                    <PlayCircle className="h-4 w-4 mr-2" />
                    批量启动
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleBatchCancel}
                    disabled={!Array.from(selectedJobs).some(jobId => {
                      const job = data.jobs.find(j => j.id === jobId)
                      return job && (job.status === 'queued' || job.status === 'running')
                    })}
                  >
                    <XCircle className="h-4 w-4 mr-2" />
                    批量取消
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={clearSelection}
                  >
                    清除选择
                  </Button>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Jobs List */}
      <div className="space-y-3 sm:space-y-4">
        {isLoading ? (
          <Card>
            <CardContent className="py-6 sm:py-8 text-center text-xs sm:text-sm text-muted-foreground">
              {t('jobs.loading')}
            </CardContent>
          </Card>
        ) : data?.jobs.length === 0 ? (
          <Card>
            <CardContent className="py-6 sm:py-8 text-center text-xs sm:text-sm text-muted-foreground">
              {t('jobs.noJobs')}
            </CardContent>
          </Card>
        ) : otherJobs.length === 0 && runningJobs.length > 0 ? (
          <Card>
            <CardContent className="py-6 sm:py-8 text-center text-xs sm:text-sm text-muted-foreground">
              没有其他任务
            </CardContent>
          </Card>
        ) : (
          otherJobs.map((job) => (
            <Card key={job.id}>
              <CardContent className="p-3 sm:p-6">
                <div className="space-y-3 sm:space-y-4">
                  {/* Job Header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex items-start gap-3 flex-1 min-w-0">
                      <Checkbox
                        checked={selectedJobs.has(job.id)}
                        onCheckedChange={() => toggleJobSelection(job.id)}
                        className="mt-1"
                      />
                      <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="font-semibold text-sm sm:text-base truncate">{job.source_type}</h3>
                        <Badge className={`${getStatusColor(job.status)} text-xs`}>
                          {getStatusText(job.status)}
                        </Badge>
                      </div>
                      <p className="text-xs sm:text-sm text-muted-foreground mt-1 truncate">
                        <span className="hidden sm:inline">ID: {job.id}</span>
                        <span className="sm:hidden">ID: {job.id.slice(0, 8)}...</span>
                      </p>
                      </div>
                    </div>
                    <div className="flex gap-1 sm:gap-2 shrink-0 flex-wrap">
                      {job.status === 'queued' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleStartJob(job.id)}
                          className="h-8 px-2 sm:px-3"
                        >
                          <PlayCircle className="h-4 w-4 sm:mr-2" />
                          <span className="hidden sm:inline">启动</span>
                        </Button>
                      )}
                      {(job.status === 'queued' || job.status === 'running') && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelJob(job.id)}
                          className="h-8 px-2 sm:px-3"
                        >
                          <XCircle className="h-4 w-4 sm:mr-2" />
                          <span className="hidden sm:inline">{t('jobs.cancel')}</span>
                        </Button>
                      )}
                      {(job.status === 'failed' || job.status === 'cancelled') && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRetryJob(job.id)}
                          className="h-8 px-2 sm:px-3"
                        >
                          <RotateCcw className="h-4 w-4 sm:mr-2" />
                          <span className="hidden sm:inline">{t('jobs.retry')}</span>
                        </Button>
                      )}
                      {(job.status === 'success' || job.status === 'failed' || job.status === 'cancelled') && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setLogsJobId(job.id)}
                            className="h-8 px-2 sm:px-3"
                          >
                            <FileText className="h-4 w-4 sm:mr-2" />
                            <span className="hidden sm:inline">日志</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDeleteJob(job.id)}
                            className="h-8 px-2 sm:px-3 text-destructive hover:bg-destructive/10"
                          >
                            <Trash2 className="h-4 w-4 sm:mr-2" />
                            <span className="hidden sm:inline">删除</span>
                          </Button>
                        </>
                      )}
                      {job.status === 'success' && job.result_paths && job.result_paths.length > 0 && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPreviewJob({ jobId: job.id, fileIndex: 0 })}
                            className="h-8 px-2 sm:px-3"
                          >
                            <Eye className="h-4 w-4 sm:mr-2" />
                            <span className="hidden sm:inline">预览</span>
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownloadSubtitle(job.id, 0)}
                            className="h-8 px-2 sm:px-3"
                          >
                            <Download className="h-4 w-4 sm:mr-2" />
                            <span className="hidden sm:inline">{t('jobs.download')}</span>
                          </Button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Job Details */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-4 text-xs sm:text-sm">
                    <div>
                      <span className="text-muted-foreground">{t('jobs.source')}:</span>{' '}
                      <span className="font-medium">
                        {job.source_lang ? getLanguageName(job.source_lang) : t('jobs.autoDetect')}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('jobs.target')}:</span>{' '}
                      <span className="font-medium">
                        {job.target_langs.map(getLanguageName).join(', ')}
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('jobs.model')}:</span>{' '}
                      <span className="font-medium">{job.model || t('jobs.default')}</span>
                    </div>
                    <div className="sm:col-span-2 lg:col-span-1">
                      <span className="text-muted-foreground">{t('jobs.created')}:</span>{' '}
                      <span className="font-medium">
                        <span className="hidden sm:inline">{new Date(job.created_at).toLocaleString()}</span>
                        <span className="sm:hidden">{new Date(job.created_at).toLocaleDateString()}</span>
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {(job.status === 'running' || job.status === 'pending') && (
                    <div className="space-y-1 sm:space-y-2">
                      <div className="flex items-center justify-between text-xs sm:text-sm">
                        <span className="text-muted-foreground">{t('jobs.progress')}</span>
                        <span className="font-medium">{jobProgress[job.id] ?? job.progress}%</span>
                      </div>
                      <Progress value={jobProgress[job.id] ?? job.progress} className="h-2 sm:h-2.5" />
                    </div>
                  )}

                  {/* Error Message */}
                  {job.error && (
                    <div className="rounded-md bg-destructive/10 p-2 sm:p-3 text-xs sm:text-sm text-destructive break-words">
                      {job.error}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <Card>
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="text-sm text-muted-foreground">
                共 {data?.total || 0} 个任务，第 {currentPage} / {totalPages} 页
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                >
                  首页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                >
                  上一页
                </Button>
                <div className="text-sm">
                  {currentPage} / {totalPages}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                >
                  下一页
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                >
                  末页
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Subtitle Preview Dialog */}
      {previewJob && (
        <SubtitlePreviewDialog
          jobId={previewJob.jobId}
          fileIndex={previewJob.fileIndex}
          open={!!previewJob}
          onOpenChange={(open) => !open && setPreviewJob(null)}
        />
      )}

      {/* Task Logs Dialog */}
      <TaskLogsDialog
        jobId={logsJobId}
        open={!!logsJobId}
        onOpenChange={(open) => !open && setLogsJobId(null)}
      />
    </div>
  )
}
