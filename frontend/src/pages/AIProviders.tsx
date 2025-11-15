import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import {
  Settings,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertCircle,
  DollarSign,
  Activity,
  Edit,
  Trash2,
  Plus,
} from 'lucide-react';
import { aiProviderApi, AIProviderConfig } from '../api/aiProviders';
import QuotaDialog from '../components/QuotaDialog';

const AIProvidersPage: React.FC = () => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);

  // Fetch providers
  const { data: providers, isLoading } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiProviderApi.listProviders(false),
  });

  // Health check mutation
  const healthCheckMutation = useMutation({
    mutationFn: (providerName: string) => aiProviderApi.healthCheck(providerName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] });
    },
  });

  // Toggle provider enabled
  const toggleProviderMutation = useMutation({
    mutationFn: ({ providerName, isEnabled }: { providerName: string; isEnabled: boolean }) =>
      aiProviderApi.createOrUpdateProvider({
        provider_name: providerName,
        is_enabled: !isEnabled,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] });
    },
  });

  const getProviderIcon = (providerName: string) => {
    switch (providerName) {
      case 'ollama':
        return '🦙';
      case 'openai':
        return '🤖';
      case 'deepseek':
        return '🔍';
      case 'claude':
        return '🎭';
      case 'gemini':
        return '💎';
      case 'zhipu':
        return '🧠';
      case 'moonshot':
        return '🌙';
      case 'custom_openai':
        return '⚙️';
      default:
        return '🤖';
    }
  };

  const getHealthStatusIcon = (provider: AIProviderConfig) => {
    if (!provider.last_health_check) {
      return <AlertCircle className="w-5 h-5 text-gray-400" />;
    }
    return provider.is_healthy ? (
      <CheckCircle2 className="w-5 h-5 text-green-500" />
    ) : (
      <XCircle className="w-5 h-5 text-red-500" />
    );
  };

  const handleHealthCheck = (providerName: string) => {
    healthCheckMutation.mutate(providerName);
  };

  const handleToggleProvider = (provider: AIProviderConfig) => {
    toggleProviderMutation.mutate({
      providerName: provider.provider_name,
      isEnabled: provider.is_enabled,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
              <Settings className="w-8 h-8" />
              {t('ai_providers.title', 'AI Providers')}
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-2">
              {t('ai_providers.description', 'Manage AI provider configurations and quotas')}
            </p>
          </div>
          <button
            onClick={() => queryClient.invalidateQueries({ queryKey: ['ai-providers'] })}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" />
            {t('common.refresh', 'Refresh')}
          </button>
        </div>
      </div>

      {/* Provider Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {providers?.map((provider) => (
          <div
            key={provider.id}
            className={`bg-white dark:bg-gray-800 rounded-lg shadow-lg p-6 border-2 transition-all ${
              provider.is_enabled
                ? 'border-green-500 dark:border-green-600'
                : 'border-gray-200 dark:border-gray-700'
            }`}
          >
            {/* Provider Header */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex items-center gap-3">
                <span className="text-4xl">{getProviderIcon(provider.provider_name)}</span>
                <div>
                  <h3 className="text-lg font-bold text-gray-900 dark:text-white">
                    {provider.display_name}
                  </h3>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {provider.provider_name}
                  </p>
                </div>
              </div>
              {getHealthStatusIcon(provider)}
            </div>

            {/* Description */}
            <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
              {provider.description}
            </p>

            {/* Status */}
            <div className="flex items-center justify-between mb-4">
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('ai_providers.status', 'Status')}
              </span>
              <label className="relative inline-flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  className="sr-only peer"
                  checked={provider.is_enabled}
                  onChange={() => handleToggleProvider(provider)}
                  disabled={toggleProviderMutation.isPending}
                />
                <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 dark:peer-focus:ring-blue-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-green-600"></div>
              </label>
            </div>

            {/* Default Model */}
            {provider.default_model && (
              <div className="mb-4">
                <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
                  {t('ai_providers.default_model', 'Default Model')}
                </span>
                <p className="text-sm font-mono text-gray-900 dark:text-white mt-1">
                  {provider.default_model}
                </p>
              </div>
            )}

            {/* Last Health Check */}
            {provider.last_health_check && (
              <div className="mb-4 text-xs text-gray-500 dark:text-gray-400">
                {t('ai_providers.last_checked', 'Last checked')}:{' '}
                {new Date(provider.last_health_check).toLocaleString()}
              </div>
            )}

            {/* Health Error */}
            {provider.health_error && (
              <div className="mb-4 p-2 bg-red-50 dark:bg-red-900/20 rounded text-xs text-red-600 dark:text-red-400">
                {provider.health_error}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <button
                onClick={() => handleHealthCheck(provider.provider_name)}
                disabled={healthCheckMutation.isPending}
                className="flex-1 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm flex items-center justify-center gap-2 disabled:opacity-50"
              >
                <Activity className="w-4 h-4" />
                {t('ai_providers.health_check', 'Health Check')}
              </button>
              <button
                onClick={() => setSelectedProvider(provider.provider_name)}
                className="px-3 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors text-sm flex items-center justify-center gap-2"
              >
                <DollarSign className="w-4 h-4" />
                {t('ai_providers.quota', 'Quota')}
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Empty State */}
      {providers?.length === 0 && (
        <div className="text-center py-12">
          <Settings className="w-16 h-16 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {t('ai_providers.no_providers', 'No providers configured')}
          </h3>
          <p className="text-gray-600 dark:text-gray-400">
            {t('ai_providers.configure_hint', 'Configure environment variables to enable AI providers')}
          </p>
        </div>
      )}

      {/* Quota Modal */}
      {selectedProvider && (
        <QuotaDialog providerName={selectedProvider} onClose={() => setSelectedProvider(null)} />
      )}
    </div>
  );
};

export default AIProvidersPage;
