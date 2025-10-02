import { useQuery } from '@tanstack/react-query'
import { Activity, CheckCircle2, XCircle, Clock, Server } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import api from '@/lib/api'
import type { HealthResponse, JobListResponse } from '@/types/api'
import { useTranslation } from 'react-i18next'

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
    queryKey: ['jobs', { limit: 5 }],
    queryFn: () => api.getJobs({ limit: 5 }),
    refetchInterval: 10000, // Refresh every 10 seconds
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

  return (
    <div className="space-y-6">
      {/* System Status */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.systemStatus')}</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {healthLoading ? '...' : health?.status || 'Unknown'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {healthLoading ? t('common.loading') : getStatusBadge(health?.status || 'down')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.stats')}</CardTitle>
            <Server className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {healthLoading ? '...' : `${healthyServices}/${totalServices}`}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {healthLoading ? t('common.loading') : t('dashboard.stats')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.running')}</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobsLoading ? '...' : recentJobs?.jobs.filter((j) => j.status === 'running').length || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('dashboard.running')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{t('dashboard.completed')}</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {jobsLoading ? '...' : recentJobs?.jobs.filter((j) => j.status === 'completed').length || 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('dashboard.completed')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Service Health Details */}
      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.systemStatus')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.entries(services).map(([service, status]) => (
              <div key={service} className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {status === 'ok' ? (
                    <CheckCircle2 className="h-5 w-5 text-green-500" />
                  ) : (
                    <XCircle className="h-5 w-5 text-red-500" />
                  )}
                  <span className="font-medium capitalize">{service}</span>
                </div>
                <Badge variant={status === 'ok' ? 'default' : 'destructive'}>
                  {String(status)}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Recent Jobs */}
      <Card>
        <CardHeader>
          <CardTitle>{t('dashboard.recentJobs')}</CardTitle>
        </CardHeader>
        <CardContent>
          {jobsLoading ? (
            <p className="text-muted-foreground">{t('dashboard.loading')}</p>
          ) : recentJobs?.jobs.length === 0 ? (
            <p className="text-muted-foreground">{t('dashboard.noJobs')}</p>
          ) : (
            <div className="space-y-3">
              {recentJobs?.jobs.map((job) => (
                <div
                  key={job.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">{job.source_type}</span>
                      <Badge
                        variant={
                          job.status === 'completed'
                            ? 'default'
                            : job.status === 'failed'
                            ? 'destructive'
                            : 'outline'
                        }
                      >
                        {job.status}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground mt-1">
                      {job.target_langs.join(', ')} • {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{job.progress}%</p>
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
