import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Play, Pause, XCircle, CheckCircle, AlertCircle, Clock, FileText, Languages,
  Activity, TrendingUp, Zap, Database, Cpu, BarChart3, ChevronDown, ChevronUp,
  Download, Film, Music, Subtitles
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import api from '@/lib/api'
import { subscribeToJobProgress } from '@/lib/sse'
import { getLanguageName } from '@/lib/utils'
import type { JobListResponse, ProgressEvent, TranslationJob } from '@/types/api'
import { useTranslation } from 'react-i18next'

// Extend ProgressEvent with timestamp for display
// Omit the string timestamp from ProgressEvent and add Date timestamp
interface TimestampedProgressEvent extends Omit<ProgressEvent, 'timestamp'> {
  timestamp: Date
}

interface JobProgressState {
  job: TranslationJob
  events: TimestampedProgressEvent[]
  currentPhase: string | null
  phaseProgress: Record<string, number>
  startTime: Date
  estimatedTimeRemaining: number | null
  eventsPerSecond: number
  expanded: boolean
}

export function LiveProgress() {
  const { t } = useTranslation()
  const [jobStates, setJobStates] = useState<Map<string, JobProgressState>>(new Map())
  const subscriptionsRef = useRef<Map<string, { unsubscribe: () => void }>>(new Map())
  const [systemStats, setSystemStats] = useState({
    totalProcessed: 0,
    avgSpeed: 0,
    peakSpeed: 0,
  })
  const [, forceUpdate] = useState(0)

  // Force re-render every second to update elapsed time display
  useEffect(() => {
    const timer = setInterval(() => {
      // Only force update if there are active jobs
      if (jobStates.size > 0) {
        forceUpdate(prev => prev + 1)
      }
    }, 1000) // Update every second

    return () => clearInterval(timer)
  }, [jobStates.size])

  // Fetch running jobs
  const { data: runningData, refetch: refetchRunning } = useQuery<JobListResponse>({
    queryKey: ['jobs', { status: 'running' }],
    queryFn: () => api.getJobs({ status: 'running', page: 1, page_size: 50 }),
    refetchInterval: 3000,
  })

  // Fetch queued jobs
  const { data: queuedData } = useQuery<JobListResponse>({
    queryKey: ['jobs', 'queued'],
    queryFn: () => api.getJobs({ status: 'queued', page: 1, page_size: 20 }),
    refetchInterval: 5000,
  })

  // Fetch paused jobs
  const { data: pausedData } = useQuery<JobListResponse>({
    queryKey: ['jobs', 'paused'],
    queryFn: () => api.getJobs({ status: 'paused', page: 1, page_size: 20 }),
    refetchInterval: 5000,
  })

  // Fetch recent completed jobs
  const { data: completedData } = useQuery<JobListResponse>({
    queryKey: ['jobs', 'completed'],
    queryFn: () => api.getJobs({ status: 'success', page: 1, page_size: 10 }),
    refetchInterval: 10000,
  })

  // Fetch recent failed jobs
  const { data: failedData } = useQuery<JobListResponse>({
    queryKey: ['jobs', 'failed'],
    queryFn: () => api.getJobs({ status: 'failed', page: 1, page_size: 5 }),
    refetchInterval: 10000,
  })

  // Initialize job states and SSE subscriptions
  useEffect(() => {
    const runningJobs = runningData?.jobs || []
    const currentJobIds = new Set(runningJobs.map((j) => j.id))

    // Remove jobs that are no longer running
    const newJobStates = new Map(jobStates)
    jobStates.forEach((_, jobId) => {
      if (!currentJobIds.has(jobId)) {
        newJobStates.delete(jobId)
        subscriptionsRef.current.get(jobId)?.unsubscribe()
        subscriptionsRef.current.delete(jobId)
      }
    })

    // Add new running jobs
    runningJobs.forEach((job) => {
      if (!jobStates.has(job.id)) {
        // Initialize job state
        newJobStates.set(job.id, {
          job,
          events: [],
          currentPhase: job.current_phase,
          phaseProgress: {},
          startTime: job.started_at ? new Date(job.started_at) : new Date(),
          estimatedTimeRemaining: null,
          eventsPerSecond: 0,
          expanded: true,
        })

        // Subscribe to SSE events
        const subscription = subscribeToJobProgress(
          job.id,
          (event: ProgressEvent) => {
            setJobStates((prevStates) => {
              const newStates = new Map(prevStates)
              const state = newStates.get(job.id)
              if (state) {
                // Update events log with timestamp
                // Use server-provided timestamp if available, otherwise use client time as fallback
                const timestamp = event.timestamp
                  ? new Date(event.timestamp)
                  : new Date()
                const timestampedEvent: TimestampedProgressEvent = { ...event, timestamp }
                const updatedEvents = [...state.events, timestampedEvent].slice(-100) // Keep last 100 events

                // Update phase progress
                const updatedPhaseProgress = { ...state.phaseProgress }
                if (event.phase) {
                  updatedPhaseProgress[event.phase] = event.progress
                }

                // Calculate estimated time remaining
                const elapsed = Date.now() - state.startTime.getTime()
                const estimatedTotal = event.progress > 0 ? (elapsed / event.progress) * 100 : null
                const estimatedRemaining = estimatedTotal ? estimatedTotal - elapsed : null

                // Calculate events per second (simplified calculation)
                const eventsInLastSecond = updatedEvents.length > 10 ? 5 : updatedEvents.length

                newStates.set(job.id, {
                  ...state,
                  events: updatedEvents,
                  currentPhase: event.phase,
                  phaseProgress: updatedPhaseProgress,
                  estimatedTimeRemaining: estimatedRemaining,
                  eventsPerSecond: eventsInLastSecond,
                  job: { ...state.job, progress: event.progress, current_phase: event.phase },
                })
              }
              return newStates
            })
          },
          (error) => {
            console.error(`SSE error for job ${job.id}:`, error)
          }
        )

        subscriptionsRef.current.set(job.id, subscription)
      }
    })

    setJobStates(newJobStates)

    return () => {
      // Cleanup all subscriptions on unmount
      subscriptionsRef.current.forEach((sub) => sub.unsubscribe())
      subscriptionsRef.current.clear()
    }
  }, [runningData?.jobs])

  // Calculate system stats
  useEffect(() => {
    const jobStatesArray = Array.from(jobStates.values())
    if (jobStatesArray.length > 0) {
      const totalProcessed = jobStatesArray.reduce((sum, state) => sum + state.job.progress, 0)
      const avgSpeed = jobStatesArray.reduce((sum, state) => sum + state.eventsPerSecond, 0) / jobStatesArray.length
      const peakSpeed = Math.max(...jobStatesArray.map((state) => state.eventsPerSecond))

      setSystemStats({ totalProcessed, avgSpeed, peakSpeed })
    }
  }, [jobStates])

  // Cancel job handler
  const handleCancelJob = async (jobId: string) => {
    try {
      await api.cancelJob(jobId)
      refetchRunning()
    } catch (error) {
      console.error('Failed to cancel job:', error)
    }
  }

  // Toggle job expansion
  const toggleJobExpansion = (jobId: string) => {
    setJobStates((prevStates) => {
      const newStates = new Map(prevStates)
      const state = newStates.get(jobId)
      if (state) {
        newStates.set(jobId, { ...state, expanded: !state.expanded })
      }
      return newStates
    })
  }

  // Phase labels and icons
  const phaseInfo: Record<string, { label: string; icon: any; color: string }> = {
    pull: { label: t('liveProgress.pullModel'), icon: Download, color: 'text-purple-500' },
    extract: { label: t('liveProgress.extractAudio'), icon: Music, color: 'text-blue-500' },
    asr: { label: t('liveProgress.asr'), icon: Languages, color: 'text-green-500' },
    mt: { label: t('liveProgress.mt'), icon: Languages, color: 'text-yellow-500' },
    post: { label: t('liveProgress.post'), icon: CheckCircle, color: 'text-orange-500' },
    writeback: { label: t('liveProgress.writeback'), icon: Subtitles, color: 'text-cyan-500' },
  }

  const getPhaseInfo = (phase: string) => phaseInfo[phase] || { label: phase, icon: Play, color: 'text-gray-500' }

  // Format time
  const formatTime = (ms: number | null): string => {
    if (!ms || ms < 0) return '--'
    const seconds = Math.floor(ms / 1000)
    const minutes = Math.floor(seconds / 60)
    const hours = Math.floor(minutes / 60)

    if (hours > 0) {
      return `${hours}${t('liveProgress.hour')}${minutes % 60}${t('liveProgress.minute')}`
    } else if (minutes > 0) {
      return `${minutes}${t('liveProgress.minute')}${seconds % 60}${t('liveProgress.second')}`
    } else {
      return `${seconds}${t('liveProgress.second')}`
    }
  }

  const jobStatesArray = Array.from(jobStates.values())
  const queuedJobs = queuedData?.jobs || []
  const pausedJobs = pausedData?.jobs || []
  const completedJobs = completedData?.jobs || []
  const failedJobs = failedData?.jobs || []

  return (
    <div className="space-y-6 overflow-x-hidden max-w-full">
      {/* Header Statistics Dashboard */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        <Card className="border-blue-500/50 bg-gradient-to-br from-blue-500/10 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('common.running')}</p>
                <p className="text-3xl font-bold text-blue-500">{jobStatesArray.length}</p>
              </div>
              <Activity className="h-10 w-10 text-blue-500 animate-pulse" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-yellow-500/50 bg-gradient-to-br from-yellow-500/10 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('liveProgress.queued')}</p>
                <p className="text-3xl font-bold text-yellow-500">{queuedJobs.length}</p>
              </div>
              <Clock className="h-10 w-10 text-yellow-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-amber-500/50 bg-gradient-to-br from-amber-500/10 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('jobs.paused')}</p>
                <p className="text-3xl font-bold text-amber-500">{pausedJobs.length}</p>
              </div>
              <Pause className="h-10 w-10 text-amber-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-500/50 bg-gradient-to-br from-green-500/10 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('liveProgress.recentCompleted')}</p>
                <p className="text-3xl font-bold text-green-500">{completedJobs.length}</p>
              </div>
              <CheckCircle className="h-10 w-10 text-green-500" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-red-500/50 bg-gradient-to-br from-red-500/10 to-transparent">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">{t('liveProgress.recentFailed')}</p>
                <p className="text-3xl font-bold text-red-500">{failedJobs.length}</p>
              </div>
              <AlertCircle className="h-10 w-10 text-red-500" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* System Performance Metrics */}
      {jobStatesArray.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5" />
  {t('liveProgress.systemMetrics')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <TrendingUp className="h-4 w-4" />
{t('liveProgress.avgSpeed')}
                </div>
                <div className="text-2xl font-bold">{systemStats.avgSpeed.toFixed(1)} {t('liveProgress.eventsPerSecond')}</div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Zap className="h-4 w-4" />
{t('liveProgress.peakSpeed')}
                </div>
                <div className="text-2xl font-bold">{systemStats.peakSpeed.toFixed(1)} {t('liveProgress.eventsPerSecond')}</div>
              </div>
              <div className="space-y-2">
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Database className="h-4 w-4" />
{t('liveProgress.cumulativeProgress')}
                </div>
                <div className="text-2xl font-bold">{systemStats.totalProcessed.toFixed(0)}%</div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Active Tasks */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <div className="h-3 w-3 bg-blue-500 rounded-full animate-pulse" />
            {t('liveProgress.currentRunningTasks')} ({jobStatesArray.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {jobStatesArray.length === 0 ? (
            <div className="py-12 sm:py-16 text-center">
              <Pause className="h-12 w-12 sm:h-16 sm:w-16 mx-auto text-muted-foreground mb-4" />
              <p className="text-base sm:text-lg text-muted-foreground">{t('liveProgress.noRunningTranslationTasks')}</p>
              <p className="text-xs sm:text-sm text-muted-foreground mt-2">
                {t('liveProgress.goToLibraryOrTranslate')} <a href="/library" className="text-blue-500 hover:underline">{t('nav.library')}</a> {t('liveProgress.orText')}{' '}
                <a href="/translate" className="text-blue-500 hover:underline">{t('nav.translate')}</a> {t('liveProgress.pageToStartTask')}
              </p>
            </div>
          ) : (
            <div className="space-y-3 sm:space-y-4">
              {jobStatesArray.map((state) => {
                const PhaseIcon = state.currentPhase ? getPhaseInfo(state.currentPhase).icon : Play
                const phaseColor = state.currentPhase ? getPhaseInfo(state.currentPhase).color : 'text-gray-500'

                return (
                  <div key={state.job.id} className="border rounded-md sm:rounded-lg p-3 sm:p-5 bg-gradient-to-br from-blue-500/5 to-transparent hover:from-blue-500/10 transition-colors">
                    {/* Job Header */}
                    <div className="flex items-start justify-between mb-3 sm:mb-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 sm:gap-3 mb-2">
                          <Film className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500 shrink-0" />
                          <h3 className="text-base sm:text-lg font-bold truncate">{state.job.source_type}</h3>
                          <Badge className="bg-blue-500/10 text-blue-500 border-blue-500/20 shrink-0 text-xs">{t('common.executing')}</Badge>
                        </div>
                        <div className="space-y-1 text-xs sm:text-sm text-muted-foreground">
                          <div className="flex items-center gap-2">
                            <FileText className="h-3 w-3 sm:h-4 sm:w-4 shrink-0" />
                            <span className="font-mono truncate">ID: {state.job.id.slice(0, 8)}...</span>
                          </div>
                          {state.job.source_path && (
                            <div className="hidden sm:flex items-center gap-2 min-w-0">
                              <FileText className="h-4 w-4 shrink-0" />
                              <span className="truncate" title={state.job.source_path}>
                                {state.job.source_path}
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                      <div className="flex gap-1 sm:gap-2 shrink-0">
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => toggleJobExpansion(state.job.id)}
                        >
                          {state.expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => handleCancelJob(state.job.id)}>
                          <XCircle className="h-4 w-4" />
                          <span className="hidden sm:inline ml-2">{t('liveProgress.cancel')}</span>
                        </Button>
                      </div>
                    </div>

                    {/* Overall Progress */}
                    <div className="space-y-2 sm:space-y-3 mb-3 sm:mb-4">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 sm:gap-3">
                          <PhaseIcon className={`h-4 w-4 sm:h-5 sm:w-5 ${phaseColor}`} />
                          <span className="text-sm sm:text-base font-semibold">
{state.currentPhase ? getPhaseInfo(state.currentPhase).label : t('liveProgress.inProgress')}
                          </span>
                        </div>
                        <span className="text-2xl sm:text-3xl font-bold text-blue-500">{state.job.progress}%</span>
                      </div>
                      <Progress value={state.job.progress} className="h-2 sm:h-3" />

                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3 text-xs sm:text-sm">
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Clock className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
                          <span className="text-muted-foreground">{t('liveProgress.elapsed')}:</span>
                          <span className="font-medium truncate">{formatTime(Date.now() - state.startTime.getTime())}</span>
                        </div>
                        <div className="flex items-center gap-1.5 sm:gap-2">
                          <Clock className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
                          <span className="text-muted-foreground">{t('liveProgress.remaining')}:</span>
                          <span className="font-medium truncate">{formatTime(state.estimatedTimeRemaining)}</span>
                        </div>
                        <div className="hidden sm:flex items-center gap-2">
                          <Activity className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="text-muted-foreground">{t('liveProgress.speed')}:</span>
                          <span className="font-medium">{state.eventsPerSecond.toFixed(1)} evt/s</span>
                        </div>
                        <div className="hidden sm:flex items-center gap-2">
                          <Database className="h-4 w-4 text-muted-foreground shrink-0" />
                          <span className="text-muted-foreground">{t('liveProgress.events')}:</span>
                          <span className="font-medium">{state.events.length}</span>
                        </div>
                      </div>
                    </div>

                    {state.expanded && (
                      <>
                        {/* Language and Model Info */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 p-3 sm:p-4 rounded-md sm:rounded-lg bg-background/80 border mb-3 sm:mb-4">
                          <div>
                            <span className="text-xs text-muted-foreground">{t('liveProgress.sourceLanguage')}</span>
                            <div className="text-sm sm:text-base font-medium mt-1 flex items-center gap-1">
                              <Languages className="h-3 w-3 sm:h-4 sm:w-4" />
                              {state.job.source_lang ? getLanguageName(state.job.source_lang) : t('liveProgress.autoDetect')}
                            </div>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground">{t('liveProgress.targetLanguages')}</span>
                            <div className="text-sm sm:text-base font-medium mt-1 truncate">
                              {state.job.target_langs.map(getLanguageName).join(', ')}
                            </div>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground">{t('liveProgress.translationModel')}</span>
                            <div className="text-sm sm:text-base font-medium mt-1 flex items-center gap-1">
                              <Cpu className="h-3 w-3 sm:h-4 sm:w-4" />
                              <span className="truncate">{state.job.model || t('liveProgress.default')}</span>
                            </div>
                          </div>
                          <div>
                            <span className="text-xs text-muted-foreground">{t('liveProgress.startTime')}</span>
                            <div className="text-sm sm:text-base font-medium mt-1">
                              {state.startTime.toLocaleTimeString()}
                            </div>
                          </div>
                        </div>

                        {/* Phase Progress */}
                        {Object.keys(state.phaseProgress).length > 0 && (
                          <div className="space-y-2 sm:space-y-3 mb-3 sm:mb-4">
                            <h4 className="font-semibold text-xs sm:text-sm flex items-center gap-2">
                              <BarChart3 className="h-3 w-3 sm:h-4 sm:w-4" />
{t('liveProgress.detailedPhaseProgress')}
                            </h4>
                            <div className="grid gap-2">
                              {(['pull', 'extract', 'asr', 'mt', 'post', 'writeback'] as const).map((phase) => {
                                const progress = state.phaseProgress[phase]
                                if (progress === undefined) return null

                                const info = getPhaseInfo(phase)
                                const Icon = info.icon
                                const isActive = state.currentPhase === phase

                                return (
                                  <div
                                    key={phase}
                                    className={`space-y-1 p-2 rounded ${isActive ? 'bg-blue-500/10 border border-blue-500/20' : ''}`}
                                  >
                                    <div className="flex items-center justify-between text-xs sm:text-sm">
                                      <div className="flex items-center gap-1.5 sm:gap-2">
                                        <Icon className={`h-3 w-3 sm:h-4 sm:w-4 ${info.color}`} />
                                        <span className="font-medium">{info.label}</span>
                                        {isActive && <Badge className="bg-blue-500/20 text-blue-500 text-xs">{t('common.inProgress')}</Badge>}
                                      </div>
                                      <span className="font-bold text-blue-500">{progress}%</span>
                                    </div>
                                    <Progress value={progress} className="h-1.5 sm:h-2" />
                                  </div>
                                )
                              })}
                            </div>
                          </div>
                        )}

                        {/* Live Event Log */}
                        <div className="space-y-2">
                          <h4 className="font-semibold text-xs sm:text-sm flex items-center gap-2">
                            <Activity className="h-3 w-3 sm:h-4 sm:w-4" />
{t('liveProgress.liveEventLog')} ({state.events.length})
                          </h4>
                          <div className="rounded-md sm:rounded-lg border bg-black/90 p-2 sm:p-3 max-h-40 sm:max-h-48 overflow-y-auto overflow-x-hidden font-mono text-xs space-y-0.5">
                            {state.events.length === 0 ? (
                              <div className="text-gray-500 text-center py-8">{t('liveProgress.waitingForEvents')}</div>
                            ) : (
                              [...state.events].reverse().map((event, idx) => (
                                <div
                                  key={idx}
                                  className={`flex items-start gap-2 min-w-0 ${event.status === 'error' ? 'text-red-400' :
                                    event.status === 'completed' ? 'text-green-400' :
                                      'text-gray-300'
                                    }`}
                                >
                                  <span className="text-gray-600 shrink-0">{event.timestamp.toLocaleTimeString()}</span>
                                  <span className="flex-1 min-w-0 break-all">
                                    <span className={`${getPhaseInfo(event.phase).color}`}>
                                      [{getPhaseInfo(event.phase).label}]
                                    </span>
                                    {' '}{event.status}
                                    {event.message && `: ${event.message}`}
                                    {event.error && ` - ERROR: ${event.error}`}
                                    {event.completed !== undefined && event.total !== undefined &&
                                      ` (${event.completed}/${event.total})`
                                    }
                                  </span>
                                </div>
                              ))
                            )}
                          </div>
                        </div>

                        {/* Error Display */}
                        {state.job.error && (
                          <div className="flex items-start gap-2 sm:gap-3 p-3 sm:p-4 rounded-md sm:rounded-lg bg-red-500/10 border border-red-500/20 text-red-500 mt-3 sm:mt-4">
                            <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 mt-0.5 flex-shrink-0" />
                            <div className="flex-1 min-w-0">
                              <p className="font-semibold text-sm sm:text-base">{t('liveProgress.errorMessage')}</p>
                              <p className="text-xs sm:text-sm mt-1 break-words">{state.job.error}</p>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Queued Tasks */}
      {queuedJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Clock className="h-4 w-4 sm:h-5 sm:w-5 text-yellow-500" />
{t('liveProgress.queuedTasks')} ({queuedJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {queuedJobs.slice(0, 5).map((job) => (
                <div key={job.id} className="flex items-center justify-between p-2 sm:p-3 rounded-md sm:rounded-lg border bg-yellow-500/5">
                  <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                    <Clock className="h-3 w-3 sm:h-4 sm:w-4 text-yellow-500 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm sm:text-base font-medium truncate">{job.source_type}</div>
                      <div className="text-xs text-muted-foreground truncate">
{job.source_lang ? getLanguageName(job.source_lang) : t('liveProgress.autoDetect')} → {job.target_langs.map(getLanguageName).join(', ')}
                      </div>
                    </div>
                  </div>
                  <Badge className="bg-yellow-500/10 text-yellow-500 border-yellow-500/20 text-xs shrink-0">{t('liveProgress.queuedStatus')}</Badge>
                </div>
              ))}
              {queuedJobs.length > 5 && (
                <div className="text-center text-xs sm:text-sm text-muted-foreground pt-2">
{t('liveProgress.moreTasksInQueue', { count: queuedJobs.length - 5 })}
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Paused Tasks */}
      {pausedJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <Pause className="h-4 w-4 sm:h-5 sm:w-5 text-amber-500" />
              {t('jobs.paused')} ({pausedJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {pausedJobs.slice(0, 5).map((job) => (
                <div key={job.id} className="flex items-center justify-between p-2 sm:p-3 rounded-md sm:rounded-lg border bg-amber-500/5">
                  <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                    <Pause className="h-3 w-3 sm:h-4 sm:w-4 text-amber-500 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm sm:text-base font-medium truncate">{job.source_type}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        {job.source_lang ? getLanguageName(job.source_lang) : t('liveProgress.autoDetect')} → {job.target_langs.map(getLanguageName).join(', ')}
                      </div>
                    </div>
                  </div>
                  <Badge className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-xs shrink-0">{t('jobs.paused')}</Badge>
                </div>
              ))}
              {pausedJobs.length > 5 && (
                <div className="text-center text-xs sm:text-sm text-muted-foreground pt-2">
                  {pausedJobs.length - 5} more paused tasks...
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Completed Tasks */}
      {completedJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <CheckCircle className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
{t('liveProgress.recentCompleted')} ({completedJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {completedJobs.slice(0, 5).map((job) => (
                <div key={job.id} className="flex items-center justify-between p-2 sm:p-3 rounded-md sm:rounded-lg border bg-green-500/5">
                  <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                    <CheckCircle className="h-3 w-3 sm:h-4 sm:w-4 text-green-500 shrink-0" />
                    <div className="min-w-0 flex-1">
                      <div className="text-sm sm:text-base font-medium truncate">{job.source_type}</div>
                      <div className="text-xs text-muted-foreground truncate">
                        {t('common.completedAt')} {new Date(job.finished_at || '').toLocaleString()}
                      </div>
                    </div>
                  </div>
                  <Badge className="bg-green-500/10 text-green-500 border-green-500/20 text-xs shrink-0">{t('common.completed')}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Recent Failed Tasks */}
      {failedJobs.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
              <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5 text-red-500" />
              {t('liveProgress.recentFailed')} ({failedJobs.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {failedJobs.map((job) => (
                <div key={job.id} className="flex items-center justify-between p-2 sm:p-3 rounded-md sm:rounded-lg border bg-red-500/5">
                  <div className="flex items-center gap-2 sm:gap-3 flex-1 min-w-0">
                    <AlertCircle className="h-3 w-3 sm:h-4 sm:w-4 text-red-500 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm sm:text-base font-medium truncate">{job.source_type}</div>
                      <div className="text-xs text-red-500 truncate">
                        {job.error || t('components.taskLogs.unknownError')}
                      </div>
                    </div>
                  </div>
                  <Badge className="bg-red-500/10 text-red-500 border-red-500/20 text-xs shrink-0">{t('liveProgress.failed')}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
