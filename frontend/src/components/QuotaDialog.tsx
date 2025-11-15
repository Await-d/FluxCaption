import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { X, DollarSign, AlertTriangle, RotateCcw } from 'lucide-react';
import { aiProviderApi, ProviderQuota } from '../api/aiProviders';

interface QuotaDialogProps {
  providerName: string;
  onClose: () => void;
}

const QuotaDialog: React.FC<QuotaDialogProps> = ({ providerName, onClose }) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [dailyLimit, setDailyLimit] = useState<string>('');
  const [monthlyLimit, setMonthlyLimit] = useState<string>('');
  const [alertThreshold, setAlertThreshold] = useState<number>(80);
  const [autoDisable, setAutoDisable] = useState<boolean>(true);

  // Fetch quota data
  const { data: quota, isLoading } = useQuery({
    queryKey: ['quota', providerName],
    queryFn: () => aiProviderApi.getQuota(providerName),
  });

  // Update form when data loads
  useEffect(() => {
    if (quota) {
      setDailyLimit(quota.daily_limit?.toString() || '');
      setMonthlyLimit(quota.monthly_limit?.toString() || '');
      setAlertThreshold(quota.alert_threshold_percent);
      setAutoDisable(quota.auto_disable_on_limit);
    }
  }, [quota]);

  // Update quota mutation
  const updateQuotaMutation = useMutation({
    mutationFn: (data: Partial<ProviderQuota>) => aiProviderApi.updateQuota(providerName, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quota', providerName] });
      onClose();
    },
  });

  // Reset quota mutation
  const resetQuotaMutation = useMutation({
    mutationFn: (period: 'daily' | 'monthly' | 'both') => aiProviderApi.resetQuota(providerName, period),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['quota', providerName] });
    },
  });

  const handleSave = () => {
    updateQuotaMutation.mutate({
      daily_limit: dailyLimit ? parseFloat(dailyLimit) : undefined,
      monthly_limit: monthlyLimit ? parseFloat(monthlyLimit) : undefined,
      alert_threshold_percent: alertThreshold,
      auto_disable_on_limit: autoDisable,
    });
  };

  const handleReset = (period: 'daily' | 'monthly' | 'both') => {
    if (confirm(t('quota.confirm_reset', `Reset ${period} quota counters?`))) {
      resetQuotaMutation.mutate(period);
    }
  };

  const getUsageColor = (percent: number) => {
    if (percent >= 90) return 'text-red-600 dark:text-red-400';
    if (percent >= alertThreshold) return 'text-yellow-600 dark:text-yellow-400';
    return 'text-green-600 dark:text-green-400';
  };

  const getProgressBarColor = (percent: number) => {
    if (percent >= 90) return 'bg-red-500';
    if (percent >= alertThreshold) return 'bg-yellow-500';
    return 'bg-green-500';
  };

  if (isLoading) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg p-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <DollarSign className="w-6 h-6 text-blue-500" />
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('quota.title', 'Quota Management')}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Provider Name */}
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white capitalize">
              {providerName}
            </h3>
          </div>

          {/* Current Usage */}
          {quota && (
            <div className="space-y-4">
              <h4 className="font-semibold text-gray-900 dark:text-white">
                {t('quota.current_usage', 'Current Usage')}
              </h4>

              {/* Daily Usage */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('quota.daily', 'Daily')}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${getUsageColor(quota.daily_usage_percent)}`}>
                      ${quota.current_daily_cost.toFixed(4)}
                      {quota.daily_limit && ` / $${quota.daily_limit.toFixed(2)}`}
                    </span>
                    <span className={`text-xs ${getUsageColor(quota.daily_usage_percent)}`}>
                      ({quota.daily_usage_percent.toFixed(1)}%)
                    </span>
                  </div>
                </div>
                {quota.daily_limit && (
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${getProgressBarColor(
                        quota.daily_usage_percent
                      )}`}
                      style={{ width: `${Math.min(quota.daily_usage_percent, 100)}%` }}
                    ></div>
                  </div>
                )}
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>{quota.current_daily_tokens.toLocaleString()} tokens</span>
                  {quota.daily_remaining !== null && quota.daily_remaining !== undefined && (
                    <span>${quota.daily_remaining.toFixed(4)} remaining</span>
                  )}
                </div>
              </div>

              {/* Monthly Usage */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                    {t('quota.monthly', 'Monthly')}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className={`text-sm font-bold ${getUsageColor(quota.monthly_usage_percent)}`}>
                      ${quota.current_monthly_cost.toFixed(4)}
                      {quota.monthly_limit && ` / $${quota.monthly_limit.toFixed(2)}`}
                    </span>
                    <span className={`text-xs ${getUsageColor(quota.monthly_usage_percent)}`}>
                      ({quota.monthly_usage_percent.toFixed(1)}%)
                    </span>
                  </div>
                </div>
                {quota.monthly_limit && (
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`h-2 rounded-full transition-all ${getProgressBarColor(
                        quota.monthly_usage_percent
                      )}`}
                      style={{ width: `${Math.min(quota.monthly_usage_percent, 100)}%` }}
                    ></div>
                  </div>
                )}
                <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
                  <span>{quota.current_monthly_tokens.toLocaleString()} tokens</span>
                  {quota.monthly_remaining !== null && quota.monthly_remaining !== undefined && (
                    <span>${quota.monthly_remaining.toFixed(4)} remaining</span>
                  )}
                </div>
              </div>

              {/* Reset Buttons */}
              <div className="flex gap-2">
                <button
                  onClick={() => handleReset('daily')}
                  disabled={resetQuotaMutation.isPending}
                  className="flex-1 px-3 py-2 bg-yellow-500 text-white rounded-lg hover:bg-yellow-600 transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <RotateCcw className="w-4 h-4" />
                  {t('quota.reset_daily', 'Reset Daily')}
                </button>
                <button
                  onClick={() => handleReset('monthly')}
                  disabled={resetQuotaMutation.isPending}
                  className="flex-1 px-3 py-2 bg-orange-500 text-white rounded-lg hover:bg-orange-600 transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  <RotateCcw className="w-4 h-4" />
                  {t('quota.reset_monthly', 'Reset Monthly')}
                </button>
              </div>
            </div>
          )}

          {/* Quota Configuration */}
          <div className="space-y-4">
            <h4 className="font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
              {t('quota.configuration', 'Quota Configuration')}
            </h4>

            {/* Daily Limit */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('quota.daily_limit', 'Daily Limit (USD)')}
              </label>
              <input
                type="number"
                value={dailyLimit}
                onChange={(e) => setDailyLimit(e.target.value)}
                placeholder="e.g., 10.00"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t('quota.daily_limit_hint', 'Leave empty for no daily limit')}
              </p>
            </div>

            {/* Monthly Limit */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('quota.monthly_limit', 'Monthly Limit (USD)')}
              </label>
              <input
                type="number"
                value={monthlyLimit}
                onChange={(e) => setMonthlyLimit(e.target.value)}
                placeholder="e.g., 100.00"
                step="0.01"
                min="0"
                className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                {t('quota.monthly_limit_hint', 'Leave empty for no monthly limit')}
              </p>
            </div>

            {/* Alert Threshold */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                {t('quota.alert_threshold', 'Alert Threshold')} ({alertThreshold}%)
              </label>
              <input
                type="range"
                value={alertThreshold}
                onChange={(e) => setAlertThreshold(parseInt(e.target.value))}
                min="50"
                max="95"
                step="5"
                className="w-full"
              />
              <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mt-1">
                <span>50%</span>
                <span>95%</span>
              </div>
            </div>

            {/* Auto Disable */}
            <div className="flex items-center justify-between">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('quota.auto_disable', 'Auto-disable on limit')}
                </label>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {t('quota.auto_disable_hint', 'Automatically disable provider when quota exceeded')}
                </p>
              </div>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={autoDisable}
                  onChange={(e) => setAutoDisable(e.target.checked)}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600"></div>
              </label>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end gap-3 p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            {t('common.cancel', 'Cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={updateQuotaMutation.isPending}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors disabled:opacity-50 flex items-center gap-2"
          >
            {updateQuotaMutation.isPending && (
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            )}
            {t('common.save', 'Save')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default QuotaDialog;
