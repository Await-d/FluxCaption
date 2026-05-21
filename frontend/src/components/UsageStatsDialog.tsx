import React from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { TrendingUp, DollarSign, Clock, AlertTriangle, Loader2 } from 'lucide-react'
import { aiProviderApi } from '../api/aiProviders'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/Dialog'
import { Button } from './ui/Button'
import { Card, CardContent } from './ui/Card'

interface UsageStatsDialogProps {
  providerName: string
  onClose: () => void
}

const UsageStatsDialog: React.FC<UsageStatsDialogProps> = ({ providerName, onClose }) => {
  const { t } = useTranslation()

  // Fetch usage stats for the last 7 days
  const { data: stats, isLoading } = useQuery({
    queryKey: ['provider-usage-stats', providerName],
    queryFn: () => aiProviderApi.getUsageStats(providerName, 7),
  })

  const latestStats = stats && stats.length > 0 ? stats[stats.length - 1] : null

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {t('ai_providers.usage_statistics', 'Usage Statistics')}
          </DialogTitle>
          <DialogDescription>
            {providerName} • {t('ai_providers.last_7_days', 'Last 7 days')}
          </DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : latestStats ? (
          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
              <Card>
                <CardContent className="pt-6 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {t('ai_providers.total_requests', 'Total Requests')}
                    </span>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="text-2xl font-bold">
                    {latestStats.request_count.toLocaleString()}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {t('ai_providers.total_tokens', 'Total Tokens')}
                    </span>
                    <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="text-2xl font-bold">
                    {latestStats.total_tokens.toLocaleString()}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {t('ai_providers.total_cost', 'Total Cost')}
                    </span>
                    <DollarSign className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="text-2xl font-bold">
                    ${latestStats.total_cost.toFixed(4)}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="pt-6 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-medium text-muted-foreground">
                      {t('ai_providers.avg_response_time', 'Avg Response Time')}
                    </span>
                    <Clock className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <p className="text-2xl font-bold">
                    {latestStats.avg_response_time_ms.toFixed(0)}ms
                  </p>
                </CardContent>
              </Card>
            </div>

            {/* Error Stats */}
            <Card className="border-destructive/40 bg-destructive/5">
              <CardContent className="pt-6">
                <div className="flex items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="h-6 w-6 text-destructive" />
                    <div>
                      <p className="text-sm font-medium text-destructive">
                        {t('ai_providers.error_rate', 'Error Rate')}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {latestStats.error_count} {t('ai_providers.errors_out_of', 'errors out of')}{' '}
                        {latestStats.request_count} {t('ai_providers.requests', 'requests')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold">
                      {((1 - latestStats.success_rate) * 100).toFixed(2)}%
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {t('ai_providers.success_rate', 'Success')}:{' '}
                      {(latestStats.success_rate * 100).toFixed(2)}%
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        ) : (
          <div className="text-center py-12 text-muted-foreground">
            {t('ai_providers.no_usage_data', 'No usage data available for the selected period')}
          </div>
        )}

        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            {t('common.close', 'Close')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default UsageStatsDialog
