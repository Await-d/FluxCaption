import { useQuery } from '@tanstack/react-query'
import { Activity, CheckCircle2, XCircle, Server, TrendingUp, FileText, AlertCircle, CalendarDays, Percent, BarChart3, Languages } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import api from '@/lib/api'
import type { HealthResponse, JobListResponse } from '@/types/api'
import { useTranslation } from 'react-i18next'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar, PieChart, Pie, Cell } from 'recharts'
import { useMemo } from 'react'

export function Dashboard() {
  const { t } = useTranslation()
  // Fetch health status
  const { data: health, isLoading: healthLoading } = useQuery<HealthResponse>({
    queryKey: ['health'],
    queryFn: () => api.health(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  // Fetch recent jobs
  const { data: recentJobs, isLoading: jobsLoading } = useQuery<JobListResponse>({
    queryKey: ['jobs', { page: 1, page_size: 5 }],
    queryFn: () => api.getJobs({ page: 1, page_size: 5 }),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  // Fetch all jobs for statistics
  const { data: allJobs } = useQuery<JobListResponse>({
    queryKey: ['jobs', { page: 1, page_size: 100 }],
    queryFn: () => api.getJobs({ page: 1, page_size: 100 }),
    refetchInterval: 60000, // Refresh every minute
  })

  const getStatusBadge = (status: string) => {
    const statusMap: Record<string, { variant: 'default' | 'destructive' | 'outline' }> = {
      ok: { variant: 'default' },
      degraded: { variant: 'outline' },
      down: { variant: 'destructive' },
    }
    const config = statusMap[status] || statusMap.down
    return <Badge variant={config.variant}>{status}</Badge>
  }

  const services = health?.services || {}
  const healthyServices = Object.values(services).filter((s) => s === 'ok').length
  const totalServices = Object.keys(services).length

  // Process jobs data for charts
  const chartData = useMemo(() => {
    if (!allJobs?.jobs) return []

    // Get last 7 days
    const days = 7
    const today = new Date()
    const data = []

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today)
      date.setDate(date.getDate() - i)
      date.setHours(0, 0, 0, 0)

      const nextDate = new Date(date)
      nextDate.setDate(nextDate.getDate() + 1)

      // Filter jobs created on this day
      const dayJobs = allJobs.jobs.filter((job) => {
        const jobDate = new Date(job.created_at)
        return jobDate >= date && jobDate < nextDate
      })

      // Count by status
      const created = dayJobs.length
      const completed = dayJobs.filter((j) => j.status === 'completed').length
      const failed = dayJobs.filter((j) => j.status === 'failed').length

      data.push({
        date: `${date.getMonth() + 1}/${date.getDate()}`,
        [t('dashboard.chart.createdTasks')]: created,
        [t('dashboard.chart.completedTasks')]: completed,
        [t('dashboard.chart.failedTasks')]: failed,
      })
    }

    return data
  }, [allJobs, t])

  // Calculate overall statistics
  const stats = useMemo(() => {
    if (!allJobs?.jobs) return {
      total: 0,
      completed: 0,
      failed: 0,
      running: 0,
      pending: 0,
      today: 0,
      successRate: 0
    }

    const total = allJobs.jobs.length
    const completed = allJobs.jobs.filter(j => j.status === 'completed').length
    const failed = allJobs.jobs.filter(j => j.status === 'failed').length
    const running = allJobs.jobs.filter(j => j.status === 'running').length
    const paused = allJobs.jobs.filter(j => j.status === 'paused').length
    const pending = allJobs.jobs.filter(j => j.status === 'pending').length

    // Today's jobs
    const today = new Date()
    today.setHours(0, 0, 0, 0)
    const todayJobs = allJobs.jobs.filter(job => {
      const jobDate = new Date(job.created_at)
      return jobDate >= today
    }).length

    // Success rate
    const finishedJobs = completed + failed
    const successRate = finishedJobs > 0 ? Math.round((completed / finishedJobs) * 100) : 0

    return { total, completed, failed, running, paused, pending, today: todayJobs, successRate }
  }, [allJobs])

  // Success rate trend data
  const successRateData = useMemo(() => {
    if (!allJobs?.jobs) return []

    const days = 7
    const today = new Date()
    const data = []

    for (let i = days - 1; i >= 0; i--) {
      const date = new Date(today)
      date.setDate(date.getDate() - i)
      date.setHours(0, 0, 0, 0)

      const nextDate = new Date(date)
      nextDate.setDate(nextDate.getDate() + 1)

      const dayJobs = allJobs.jobs.filter((job) => {
        const jobDate = new Date(job.created_at)
        return jobDate >= date && jobDate < nextDate
      })

      const completed = dayJobs.filter(j => j.status === 'completed').length
      const failed = dayJobs.filter(j => j.status === 'failed').length
      const finished = completed + failed
      const rate = finished > 0 ? Math.round((completed / finished) * 100) : 0

      data.push({
        date: `${date.getMonth() + 1}/${date.getDate()}`,
        [t('dashboard.chart.successRate')]: rate,
        [t('dashboard.chart.completedTasks')]: completed,
        [t('dashboard.chart.failedTasks')]: failed
      })
    }

    return data
  }, [allJobs, t])

  // Task type distribution
  const taskTypeData = useMemo(() => {
    if (!allJobs?.jobs) return []

    const typeCount: Record<string, number> = {}
    allJobs.jobs.forEach(job => {
      const type = job.source_type || 'unknown'
      typeCount[type] = (typeCount[type] || 0) + 1
    })

    return Object.entries(typeCount).map(([type, count]) => ({
      name: t(`dashboard.taskType.${type.toLowerCase()}` as const, type),
      value: count
    }))
  }, [allJobs, t])

  // Language distribution
  const languageData = useMemo(() => {
    if (!allJobs?.jobs) return []

    const langCount: Record<string, number> = {}
    allJobs.jobs.forEach(job => {
      job.target_langs.forEach(lang => {
        langCount[lang] = (langCount[lang] || 0) + 1
      })
    })

    return Object.entries(langCount)
      .map(([lang, count]) => ({ name: t(`languages.${lang}`, { defaultValue: lang }), value: count }))
      .sort((a, b) => b.value - a.value)
      .slice(0, 6) // Top 6 languages
  }, [allJobs, t])

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899']

  return (
    <div className="space-y-6">
      {/* Task Statistics Chart */}
      <Card>
        <CardHeader className="px-4 sm:px-6">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base sm:text-lg">{t('dashboard.recentTasksChart')}</CardTitle>
            <TrendingUp className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
          </div>
        </CardHeader>
        <CardContent className="px-2 sm:px-4">
          <div className="h-[250px] sm:h-[300px]">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="date"
                  className="text-xs"
                  tick={{ fontSize: 12 }}
                />
                <YAxis
                  className="text-xs"
                  tick={{ fontSize: 12 }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'hsl(var(--background))',
                    border: '1px solid hsl(var(--border))',
                    borderRadius: '6px',
                    fontSize: '12px'
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: '12px' }}
                />
                <Line
                  type="monotone"
                  dataKey={t('dashboard.chart.createdTasks')}
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey={t('dashboard.chart.completedTasks')}
                  stroke="hsl(142 76% 36%)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
                <Line
                  type="monotone"
                  dataKey={t('dashboard.chart.failedTasks')}
                  stroke="hsl(var(--destructive))"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* System Status */}
      <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('dashboard.systemStatus')}</CardTitle>
            <Activity className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="text-xl sm:text-2xl font-bold">
              {healthLoading ? '...' : health?.status || 'Unknown'}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              {healthLoading ? t('dashboard.loading') : getStatusBadge(health?.status || 'down')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('dashboard.serviceStatus')}</CardTitle>
            <Server className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="text-xl sm:text-2xl font-bold">
              {healthLoading ? '...' : `${healthyServices}/${totalServices}`}
            </div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              {healthLoading ? t('dashboard.loading') : t('dashboard.healthyServices')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('dashboard.totalJobs')}</CardTitle>
            <FileText className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="text-xl sm:text-2xl font-bold">{stats.total}</div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">{t('dashboard.cumulativeTasks')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('dashboard.todayTasks')}</CardTitle>
            <CalendarDays className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="text-xl sm:text-2xl font-bold">{stats.today}</div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">{t('dashboard.todayCreated')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('dashboard.successRate')}</CardTitle>
            <Percent className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="text-xl sm:text-2xl font-bold">{stats.successRate}%</div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">{t('dashboard.taskSuccessRate')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 px-3 sm:px-4">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('dashboard.failedTasksCount')}</CardTitle>
            <AlertCircle className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent className="px-3 sm:px-4">
            <div className="text-xl sm:text-2xl font-bold text-destructive">{stats.failed}</div>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">{t('dashboard.needsAttention')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Success Rate & Distribution Charts */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        {/* Success Rate Trend */}
        <Card>
          <CardHeader className="px-4 sm:px-6">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base sm:text-lg">{t('dashboard.successRateTrend')}</CardTitle>
              <Percent className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="px-2 sm:px-4">
            <div className="h-[250px] sm:h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={successRateData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="date" className="text-xs" tick={{ fontSize: 12 }} />
                  <YAxis className="text-xs" tick={{ fontSize: 12 }} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                  />
                  <Legend wrapperStyle={{ fontSize: '12px' }} />
                  <Line
                    type="monotone"
                    dataKey={t('dashboard.chart.successRate')}
                    stroke="hsl(142 76% 36%)"
                    strokeWidth={3}
                    dot={{ r: 4 }}
                    activeDot={{ r: 6 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Task Type Distribution */}
        <Card>
          <CardHeader className="px-4 sm:px-6">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base sm:text-lg">{t('dashboard.taskTypeDistribution')}</CardTitle>
              <BarChart3 className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="px-2 sm:px-4">
            <div className="h-[250px] sm:h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={taskTypeData} margin={{ top: 5, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" className="text-xs" tick={{ fontSize: 12 }} />
                  <YAxis className="text-xs" tick={{ fontSize: 12 }} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                  />
                  <Bar dataKey="value" fill="hsl(var(--primary))" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Language Distribution & Service Health */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        {/* Language Distribution */}
        <Card>
          <CardHeader className="px-4 sm:px-6">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base sm:text-lg">{t('dashboard.languageDistribution')}</CardTitle>
              <Languages className="h-4 w-4 sm:h-5 sm:w-5 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="px-2 sm:px-4">
            <div className="h-[250px] sm:h-[280px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={languageData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {languageData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: 'hsl(var(--background))',
                      border: '1px solid hsl(var(--border))',
                      borderRadius: '6px',
                      fontSize: '12px'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Service Health Details */}
        <Card>
          <CardHeader className="px-4 sm:px-6">
            <CardTitle className="text-base sm:text-lg">{t('dashboard.serviceHealth')}</CardTitle>
          </CardHeader>
          <CardContent className="px-4 sm:px-6">
            <div className="space-y-3 sm:space-y-4">
              {Object.entries(services).map(([service, status]) => (
                <div key={service} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    {status === 'ok' ? (
                      <CheckCircle2 className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                    ) : (
                      <XCircle className="h-4 w-4 sm:h-5 sm:w-5 text-red-500" />
                    )}
                    <span className="text-sm sm:text-base font-medium capitalize">{service}</span>
                  </div>
                  <Badge
                    variant={status === 'ok' ? 'default' : 'destructive'}
                    className="text-[10px] sm:text-xs"
                  >
                    {String(status)}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Recent Jobs */}
      <Card>
        <CardHeader className="px-4 sm:px-6">
          <CardTitle className="text-base sm:text-lg">{t('dashboard.recentJobs')}</CardTitle>
        </CardHeader>
        <CardContent className="px-4 sm:px-6">
          {jobsLoading ? (
            <p className="text-sm sm:text-base text-muted-foreground">{t('dashboard.loading')}</p>
          ) : recentJobs?.jobs.length === 0 ? (
            <p className="text-sm sm:text-base text-muted-foreground">{t('dashboard.noJobs')}</p>
          ) : (
            <div className="space-y-2 sm:space-y-3">
              {recentJobs?.jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between rounded-lg border p-2 sm:p-3"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                      <span className="text-sm sm:text-base font-medium truncate">{job.source_type}</span>
                      <Badge
                        variant={
                          job.status === 'completed'
                            ? 'default'
                            : job.status === 'failed'
                              ? 'destructive'
                              : 'outline'
                        }
                        className="text-[10px] sm:text-xs"
                      >
                        {job.status}
                      </Badge>
                    </div>
                    <p className="text-xs sm:text-sm text-muted-foreground mt-1 truncate">
                      {job.target_langs.join(', ')} • {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right ml-2 flex-shrink-0">
                    <p className="text-xs sm:text-sm font-medium">{job.progress}%</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
