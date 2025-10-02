import { useState, useEffect } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, XCircle, RotateCcw, Download, Eye } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { SubtitlePreviewDialog } from '@/components/SubtitlePreviewDialog'
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
  const queryClient = useQueryClient()

  // Fetch jobs with filters
  const { data, isLoading, refetch } = useQuery<JobListResponse>({
    queryKey: ['jobs', { status: statusFilter !== 'all' ? statusFilter : undefined, type: typeFilter !== 'all' ? typeFilter : undefined }],
    queryFn: () =>
      api.getJobs({
        status: statusFilter !== 'all' ? statusFilter : undefined,
        type: typeFilter !== 'all' ? typeFilter : undefined,
        limit: 50,
      }),
    refetchInterval: 5000, // Poll every 5 seconds
  })

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

  // Subscribe to running jobs progress via SSE
  useEffect(() => {
    const runningJobs = data?.jobs.filter((j) => j.status === 'running') || []

    // Setup SSE subscriptions for all running jobs
    const subscriptions = runningJobs.map((job) =>
      subscribeToJobProgress(
        job.id,
        (event: ProgressEvent) => {
          // Update job progress in cache
          queryClient.setQueryData<JobListResponse>(
            ['jobs', { status: statusFilter !== 'all' ? statusFilter : undefined, type: typeFilter !== 'all' ? typeFilter : undefined }],
            (old) => {
              if (!old) return old
              return {
                ...old,
                jobs: old.jobs.map((j) =>
                  j.id === event.job_id ? { ...j, progress: event.progress } : j
                ),
              }
            }
          )
        },
        (error) => {
          console.error(`SSE error for job ${job.id}:`, error)
        }
      )
    )

    // Cleanup all subscriptions on unmount or when jobs change
    return () => {
      subscriptions.forEach((sub) => sub.unsubscribe())
    }
  }, [data?.jobs, queryClient, statusFilter, typeFilter])

  return (
    <div className="space-y-6">
      {/* Filters */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{t('jobs.jobQueue')}</CardTitle>
            <Button variant="outline" size="sm" onClick={() => refetch()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              {t('jobs.refresh')}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">{t('jobs.status')}</label>
              <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as JobStatus | 'all')}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('jobs.allStatuses')}</SelectItem>
                  <SelectItem value="pending">{t('jobs.pending')}</SelectItem>
                  <SelectItem value="running">{t('jobs.running')}</SelectItem>
                  <SelectItem value="completed">{t('jobs.completed')}</SelectItem>
                  <SelectItem value="failed">{t('jobs.failed')}</SelectItem>
                  <SelectItem value="cancelled">{t('jobs.cancelled')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <label className="text-sm font-medium mb-2 block">{t('jobs.type')}</label>
              <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as JobType | 'all')}>
                <SelectTrigger>
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

      {/* Jobs List */}
      <div className="space-y-4">
        {isLoading ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              {t('jobs.loading')}
            </CardContent>
          </Card>
        ) : data?.jobs.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center text-muted-foreground">
              {t('jobs.noJobs')}
            </CardContent>
          </Card>
        ) : (
          data?.jobs.map((job) => (
            <Card key={job.id}>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  {/* Job Header */}
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold">{job.source_type}</h3>
                        <Badge className={getStatusColor(job.status)}>
                          {getStatusText(job.status)}
                        </Badge>
                      </div>
                      <p className="text-sm text-muted-foreground mt-1">
                        ID: {job.id}
                      </p>
                    </div>
                    <div className="flex gap-2">
                      {job.status === 'running' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleCancelJob(job.id)}
                        >
                          <XCircle className="mr-2 h-4 w-4" />
                          {t('jobs.cancel')}
                        </Button>
                      )}
                      {job.status === 'failed' && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleRetryJob(job.id)}
                        >
                          <RotateCcw className="mr-2 h-4 w-4" />
                          {t('jobs.retry')}
                        </Button>
                      )}
                      {job.status === 'success' && job.result_paths && job.result_paths.length > 0 && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setPreviewJob({ jobId: job.id, fileIndex: 0 })}
                          >
                            <Eye className="mr-2 h-4 w-4" />
                            预览
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleDownloadSubtitle(job.id, 0)}
                          >
                            <Download className="mr-2 h-4 w-4" />
                            {t('jobs.download')}
                          </Button>
                        </>
                      )}
                    </div>
                  </div>

                  {/* Job Details */}
                  <div className="grid grid-cols-2 gap-4 text-sm">
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
                    <div>
                      <span className="text-muted-foreground">{t('jobs.created')}:</span>{' '}
                      <span className="font-medium">
                        {new Date(job.created_at).toLocaleString()}
                      </span>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  {(job.status === 'running' || job.status === 'pending') && (
                    <div className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-muted-foreground">{t('jobs.progress')}</span>
                        <span className="font-medium">{job.progress}%</span>
                      </div>
                      <Progress value={job.progress} />
                    </div>
                  )}

                  {/* Error Message */}
                  {job.error && (
                    <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
                      {job.error}
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Subtitle Preview Dialog */}
      {previewJob && (
        <SubtitlePreviewDialog
          jobId={previewJob.jobId}
          fileIndex={previewJob.fileIndex}
          open={!!previewJob}
          onOpenChange={(open) => !open && setPreviewJob(null)}
        />
      )}
    </div>
  )
}
