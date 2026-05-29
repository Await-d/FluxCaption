import React, { useEffect, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { DollarSign, AlertTriangle, RotateCcw, Loader2 } from 'lucide-react'
import { aiProviderApi, ProviderQuota } from '../api/aiProviders'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/Dialog'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Label } from './ui/Label'
import { cn } from '../lib/utils'

interface QuotaDialogProps {
  providerName: string
  onClose: () => void
}

const QuotaDialog: React.FC<QuotaDialogProps> = ({ providerName, onClose }) => {
  const { t } = useTranslation()
  const queryClient = useQueryClient()

  const [dailyLimit, setDailyLimit] = useState<string>('')
  const [monthlyLimit, setMonthlyLimit] = useState<string>('')
  const [alertThreshold, setAlertThreshold] = useState<number>(80)
  const [autoDisable, setAutoDisable] = useState<boolean>(true)

  // Fetch quota data
  const { data: quota, isLoading } = useQuery({
    queryKey: ['quota', providerName],
    queryFn: () => aiProviderApi.getQuota(providerName),
  })

  useEffect(() => {
    if (quota) {
      setDailyLimit(quota.daily_limit?.toString() || '')
      setMonthlyLimit(quota.monthly_limit?.toString() || '')
      setAlertThreshold(quota.alert_threshold_percent)
      setAutoDisable(quota.auto_disable_on_limit)
    }
  }, [quota])

  // Update quota mutation
  const updateQuotaMutation = useMutation({
    mutationFn: (data: Partial<ProviderQuota>) => aiProviderApi.updateQuota(providerName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quota', providerName] })
      onClose()
    },
  })

  // Reset quota mutation
  const resetQuotaMutation = useMutation({
    mutationFn: (period: 'daily' | 'monthly' | 'both') =>
      aiProviderApi.resetQuota(providerName, period),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quota', providerName] })
    },
  })

  const handleSave = () => {
    updateQuotaMutation.mutate({
      daily_limit: dailyLimit ? parseFloat(dailyLimit) : undefined,
      monthly_limit: monthlyLimit ? parseFloat(monthlyLimit) : undefined,
      alert_threshold_percent: alertThreshold,
      auto_disable_on_limit: autoDisable,
    })
  }

  const handleReset = (period: 'daily' | 'monthly' | 'both') => {
    // eslint-disable-next-line no-alert
    if (confirm(t('quota.confirm_reset', { period }))) {
      resetQuotaMutation.mutate(period)
    }
  }

  const getUsageTextClass = (percent: number) => {
    if (percent >= 90) return 'text-destructive'
    if (percent >= alertThreshold) return 'text-yellow-500 dark:text-yellow-400'
    return 'text-green-500 dark:text-green-400'
  }

  const getProgressBarClass = (percent: number) => {
    if (percent >= 90) return 'bg-destructive'
    if (percent >= alertThreshold) return 'bg-yellow-500'
    return 'bg-green-500'
  }

  const renderUsageBlock = (
    label: string,
    currentCost: number,
    limit: number | null | undefined,
    usagePercent: number,
    tokens: number,
    remaining: number | null | undefined,
  ) => (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2 flex-wrap">
        <span className="text-sm font-medium">{label}</span>
        <div className="flex items-center gap-2">
          <span className={cn('text-sm font-semibold', getUsageTextClass(usagePercent))}>
            ${currentCost.toFixed(4)}
            {limit ? ` / $${limit.toFixed(2)}` : ''}
          </span>
          <span className={cn('text-xs', getUsageTextClass(usagePercent))}>
            ({usagePercent.toFixed(1)}%)
          </span>
        </div>
      </div>
      {limit ? (
        <div className="w-full h-2 rounded-full bg-secondary overflow-hidden">
          <div
            className={cn('h-full transition-all', getProgressBarClass(usagePercent))}
            style={{ width: `${Math.min(usagePercent, 100)}%` }}
          />
        </div>
      ) : null}
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>
          {tokens.toLocaleString()} {t('quota.tokens')}
        </span>
        {remaining !== null && remaining !== undefined && (
          <span>
            ${remaining.toFixed(4)} {t('quota.remaining')}
          </span>
        )}
      </div>
    </div>
  )

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <DollarSign className="h-5 w-5 text-primary" />
            {t('quota.title')}
          </DialogTitle>
          <DialogDescription className="capitalize">{providerName}</DialogDescription>
        </DialogHeader>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="space-y-6">
            {/* Current Usage */}
            {quota && (
              <div className="space-y-4">
                <h4 className="text-sm font-semibold">
                  {t('quota.current_usage')}
                </h4>

                {renderUsageBlock(
                  t('quota.daily'),
                  quota.current_daily_cost,
                  quota.daily_limit,
                  quota.daily_usage_percent,
                  quota.current_daily_tokens,
                  quota.daily_remaining,
                )}

                {renderUsageBlock(
                  t('quota.monthly'),
                  quota.current_monthly_cost,
                  quota.monthly_limit,
                  quota.monthly_usage_percent,
                  quota.current_monthly_tokens,
                  quota.monthly_remaining,
                )}

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleReset('daily')}
                    disabled={resetQuotaMutation.isPending}
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    {t('quota.reset_daily')}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => handleReset('monthly')}
                    disabled={resetQuotaMutation.isPending}
                  >
                    <RotateCcw className="mr-2 h-4 w-4" />
                    {t('quota.reset_monthly')}
                  </Button>
                </div>
              </div>
            )}

            {/* Quota Configuration */}
            <div className="space-y-4 border-t pt-4">
              <h4 className="text-sm font-semibold flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-yellow-500" />
                {t('quota.configuration')}
              </h4>

              <div className="space-y-2">
                <Label htmlFor="quota-daily-limit">
                  {t('quota.daily_limit')}
                </Label>
                <Input
                  id="quota-daily-limit"
                  type="number"
                  value={dailyLimit}
                  onChange={(e) => setDailyLimit(e.target.value)}
                  placeholder={t('quota.daily_limit_placeholder')}
                  step="0.01"
                  min="0"
                />
                <p className="text-xs text-muted-foreground">
                    {t('quota.daily_limit_hint')}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quota-monthly-limit">
                  {t('quota.monthly_limit')}
                </Label>
                <Input
                  id="quota-monthly-limit"
                  type="number"
                  value={monthlyLimit}
                  onChange={(e) => setMonthlyLimit(e.target.value)}
                  placeholder={t('quota.monthly_limit_placeholder')}
                  step="0.01"
                  min="0"
                />
                <p className="text-xs text-muted-foreground">
                    {t('quota.monthly_limit_hint')}
                </p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="quota-alert-threshold">
                  {t('quota.alert_threshold')} ({alertThreshold}%)
                </Label>
                <input
                  id="quota-alert-threshold"
                  type="range"
                  value={alertThreshold}
                  onChange={(e) => setAlertThreshold(parseInt(e.target.value, 10))}
                  min={50}
                  max={95}
                  step={5}
                  className="w-full accent-primary"
                />
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>50%</span>
                  <span>95%</span>
                </div>
              </div>

              <div className="flex items-center justify-between gap-4">
                <div className="space-y-1">
                  <Label htmlFor="quota-auto-disable" className="cursor-pointer">
                    {t('quota.auto_disable')}
                  </Label>
                  <p className="text-xs text-muted-foreground">
                    {t('quota.auto_disable_hint')}
                  </p>
                </div>
                <label className="relative inline-flex h-6 w-11 cursor-pointer items-center">
                  <input
                    id="quota-auto-disable"
                    type="checkbox"
                    className="peer sr-only"
                    checked={autoDisable}
                    onChange={(e) => setAutoDisable(e.target.checked)}
                  />
                  <span className="absolute inset-0 rounded-full bg-secondary transition-colors peer-checked:bg-primary peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2" />
                  <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-background shadow transition-transform peer-checked:translate-x-5" />
                </label>
              </div>
            </div>
          </div>
        )}

        <DialogFooter className="gap-2">
          <Button type="button" variant="outline" onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button
            type="button"
            onClick={handleSave}
            disabled={updateQuotaMutation.isPending}
          >
            {updateQuotaMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {t('common.save')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

export default QuotaDialog
