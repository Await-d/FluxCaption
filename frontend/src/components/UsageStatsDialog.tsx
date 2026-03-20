import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { X, TrendingUp, DollarSign, Clock, AlertTriangle } from 'lucide-react';
import { aiProviderApi } from '../api/aiProviders';

interface UsageStatsDialogProps {
  providerName: string;
  onClose: () => void;
}

const UsageStatsDialog: React.FC<UsageStatsDialogProps> = ({ providerName, onClose }) => {
  const { t } = useTranslation();

  // Fetch usage stats for the last 7 days
  const { data: stats, isLoading } = useQuery({
    queryKey: ['provider-usage-stats', providerName],
    queryFn: () => aiProviderApi.getUsageStats(providerName, 7),
  });

  // Get the latest stats
  const latestStats = stats && stats.length > 0 ? stats[stats.length - 1] : null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 dark:border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('ai_providers.usage_statistics', 'Usage Statistics')}
            </h2>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
              {providerName} - {t('ai_providers.last_7_days', 'Last 7 days')}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : latestStats ? (
            <div className="space-y-6">
              {/* Stats Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Total Requests */}
                <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-blue-600 dark:text-blue-400">
                      {t('ai_providers.total_requests', 'Total Requests')}
                    </span>
                    <TrendingUp className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {latestStats.request_count.toLocaleString()}
                  </p>
                </div>

                {/* Total Tokens */}
                <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-purple-600 dark:text-purple-400">
                      {t('ai_providers.total_tokens', 'Total Tokens')}
                    </span>
                    <TrendingUp className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {latestStats.total_tokens.toLocaleString()}
                  </p>
                </div>

                {/* Total Cost */}
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-green-600 dark:text-green-400">
                      {t('ai_providers.total_cost', 'Total Cost')}
                    </span>
                    <DollarSign className="w-5 h-5 text-green-600 dark:text-green-400" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    ${latestStats.total_cost.toFixed(4)}
                  </p>
                </div>

                {/* Avg Response Time */}
                <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-orange-600 dark:text-orange-400">
                      {t('ai_providers.avg_response_time', 'Avg Response Time')}
                    </span>
                    <Clock className="w-5 h-5 text-orange-600 dark:text-orange-400" />
                  </div>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">
                    {latestStats.avg_response_time_ms.toFixed(0)}ms
                  </p>
                </div>
              </div>

              {/* Error Stats */}
              <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" />
                    <div>
                      <p className="text-sm font-medium text-red-600 dark:text-red-400">
                        {t('ai_providers.error_rate', 'Error Rate')}
                      </p>
                      <p className="text-xs text-red-500 dark:text-red-400">
                        {latestStats.error_count} {t('ai_providers.errors_out_of', 'errors out of')}{' '}
                        {latestStats.request_count} {t('ai_providers.requests', 'requests')}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-gray-900 dark:text-white">
                      {((1 - latestStats.success_rate) * 100).toFixed(2)}%
                    </p>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      {t('ai_providers.success_rate', 'Success')}: {(latestStats.success_rate * 100).toFixed(2)}%
                    </p>
                  </div>
                </div>
              </div>

              {/* No data message */}
              {stats && stats.length === 0 && (
                <div className="text-center py-12 text-gray-500 dark:text-gray-400">
                  {t('ai_providers.no_usage_data', 'No usage data available for the selected period')}
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500 dark:text-gray-400">
              {t('ai_providers.no_usage_data', 'No usage data available for the selected period')}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
          >
            {t('common.close', 'Close')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default UsageStatsDialog;
