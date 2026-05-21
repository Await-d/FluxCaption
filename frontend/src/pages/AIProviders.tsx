import React, { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
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
  BarChart3,
  Plus,
  Loader2,
} from 'lucide-react'
import { aiProviderApi, AIProviderConfig } from '../api/aiProviders'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { cn } from '../lib/utils'
import QuotaDialog from '../components/QuotaDialog'
import ProviderConfigDialog from '../components/ProviderConfigDialog'
import UsageStatsDialog from '../components/UsageStatsDialog'
import AddProviderDialog from '../components/AddProviderDialog'

const AIProvidersPage: React.FC = () => {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [editingProvider, setEditingProvider] = useState<AIProviderConfig | null>(null)
  const [showUsageStats, setShowUsageStats] = useState<string | null>(null)
  const [showAddProvider, setShowAddProvider] = useState(false)

  // Fetch providers
  const { data: providers, isLoading } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiProviderApi.listProviders(false),
  })

  // Health check mutation
  const healthCheckMutation = useMutation({
    mutationFn: (providerName: string) => aiProviderApi.healthCheck(providerName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
    },
  })

  // Toggle provider enabled
  const toggleProviderMutation = useMutation({
    mutationFn: ({
      providerName,
      displayName,
      isEnabled,
    }: {
      providerName: string
      displayName: string
      isEnabled: boolean
    }) =>
      aiProviderApi.createOrUpdateProvider({
        provider_name: providerName,
        display_name: displayName,
        is_enabled: !isEnabled,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
    },
  })

  // Delete provider mutation
  const deleteProviderMutation = useMutation({
    mutationFn: (providerName: string) => aiProviderApi.deleteProvider(providerName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
    },
  })

  // Update provider config mutation
  const updateConfigMutation = useMutation({
    mutationFn: (config: Partial<AIProviderConfig>) =>
      aiProviderApi.createOrUpdateProvider(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
      setEditingProvider(null)
    },
  })

  // Add provider mutation
  const addProviderMutation = useMutation({
    mutationFn: (config: Partial<AIProviderConfig>) =>
      aiProviderApi.createOrUpdateProvider(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-providers'] })
      setShowAddProvider(false)
    },
  })

  const getProviderIcon = (providerName: string) => {
    switch (providerName) {
      case 'ollama':
        return '🦙'
      case 'openai':
        return '🤖'
      case 'deepseek':
        return '🔍'
      case 'claude':
        return '🎭'
      case 'gemini':
        return '💎'
      case 'zhipu':
        return '🧠'
      case 'moonshot':
        return '🌙'
      case 'custom_openai':
        return '⚙️'
      default:
        return '🤖'
    }
  }

  const getHealthStatusIcon = (provider: AIProviderConfig) => {
    if (!provider.last_health_check) {
      return <AlertCircle className="h-5 w-5 text-muted-foreground" />
    }
    return provider.is_healthy ? (
      <CheckCircle2 className="h-5 w-5 text-green-500" />
    ) : (
      <XCircle className="h-5 w-5 text-destructive" />
    )
  }

  const handleHealthCheck = (providerName: string) => {
    healthCheckMutation.mutate(providerName)
  }

  const handleToggleProvider = (provider: AIProviderConfig) => {
    toggleProviderMutation.mutate({
      providerName: provider.provider_name,
      displayName: provider.display_name,
      isEnabled: provider.is_enabled,
    })
  }

  const handleDeleteProvider = (providerName: string) => {
    // eslint-disable-next-line no-alert
    if (window.confirm(
      t('ai_providers.confirm_delete', `Are you sure you want to delete provider "${providerName}"?`),
    )) {
      deleteProviderMutation.mutate(providerName)
    }
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold flex items-center gap-2">
            <Settings className="h-5 w-5" />
            {t('ai_providers.title', 'AI Providers')}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {t('ai_providers.description', 'Manage AI provider configurations and quotas')}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => setShowAddProvider(true)}>
            <Plus className="mr-2 h-4 w-4" />
            {t('ai_providers.add_provider', 'Add Provider')}
          </Button>
          <Button
            variant="outline"
            onClick={() => queryClient.invalidateQueries({ queryKey: ['ai-providers'] })}
          >
            <RefreshCw className="mr-2 h-4 w-4" />
            {t('common.refresh', 'Refresh')}
          </Button>
        </div>
      </div>

      {/* Provider Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {providers?.map((provider) => (
          <Card
            key={provider.id}
            className={cn(
              'transition-colors',
              provider.is_enabled ? 'border-primary/40' : 'border-border',
            )}
          >
            <CardHeader>
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-3xl leading-none flex-shrink-0">
                    {getProviderIcon(provider.provider_name)}
                  </span>
                  <div className="min-w-0">
                    <CardTitle className="text-base truncate">
                      {provider.display_name}
                    </CardTitle>
                    <p className="text-xs text-muted-foreground mt-0.5 truncate">
                      {provider.provider_name}
                    </p>
                  </div>
                </div>
                {getHealthStatusIcon(provider)}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Description */}
              {provider.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {provider.description}
                </p>
              )}

              {/* Status toggle */}
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">
                  {t('ai_providers.status', 'Status')}
                </span>
                <label className="relative inline-flex h-6 w-11 cursor-pointer items-center">
                  <input
                    type="checkbox"
                    className="peer sr-only"
                    checked={provider.is_enabled}
                    onChange={() => handleToggleProvider(provider)}
                    disabled={toggleProviderMutation.isPending}
                  />
                  <span className="absolute inset-0 rounded-full bg-secondary transition-colors peer-checked:bg-primary peer-focus-visible:ring-2 peer-focus-visible:ring-ring peer-focus-visible:ring-offset-2" />
                  <span className="absolute left-0.5 top-0.5 h-5 w-5 rounded-full bg-background shadow transition-transform peer-checked:translate-x-5" />
                </label>
              </div>

              {/* Default Model */}
              {provider.default_model && (
                <div className="space-y-1">
                  <span className="text-xs font-medium text-muted-foreground">
                    {t('ai_providers.default_model', 'Default Model')}
                  </span>
                  <p className="text-sm font-mono">{provider.default_model}</p>
                </div>
              )}

              {/* Last Health Check */}
              {provider.last_health_check && (
                <p className="text-xs text-muted-foreground">
                  {t('ai_providers.last_checked', 'Last checked')}:{' '}
                  {new Date(provider.last_health_check).toLocaleString()}
                </p>
              )}

              {/* Health Error */}
              {provider.health_error && (
                <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {provider.health_error}
                </div>
              )}

              {/* Actions */}
              <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleHealthCheck(provider.provider_name)}
                  disabled={healthCheckMutation.isPending}
                >
                  <Activity className="mr-2 h-4 w-4" />
                  {t('ai_providers.health_check', 'Health Check')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setSelectedProvider(provider.provider_name)}
                >
                  <DollarSign className="mr-2 h-4 w-4" />
                  {t('ai_providers.quota', 'Quota')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setEditingProvider(provider)}
                >
                  <Edit className="mr-2 h-4 w-4" />
                  {t('ai_providers.configure', 'Configure')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setShowUsageStats(provider.provider_name)}
                >
                  <BarChart3 className="mr-2 h-4 w-4" />
                  {t('ai_providers.usage', 'Usage')}
                </Button>
                {provider.provider_name !== 'ollama' && (
                  <Button
                    variant="destructive"
                    size="sm"
                    onClick={() => handleDeleteProvider(provider.provider_name)}
                    disabled={deleteProviderMutation.isPending}
                    className="col-span-2"
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    {t('common.delete', 'Delete')}
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Empty State */}
      {providers?.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Settings className="mx-auto mb-4 h-12 w-12 text-muted-foreground" />
            <h3 className="text-base font-medium mb-1">
              {t('ai_providers.no_providers', 'No providers configured')}
            </h3>
            <p className="text-sm text-muted-foreground">
              {t('ai_providers.configure_hint', 'Configure environment variables to enable AI providers')}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Modals */}
      {selectedProvider && (
        <QuotaDialog
          providerName={selectedProvider}
          onClose={() => setSelectedProvider(null)}
        />
      )}
      {editingProvider && (
        <ProviderConfigDialog
          provider={editingProvider}
          onClose={() => setEditingProvider(null)}
          onSave={(config) => updateConfigMutation.mutate(config)}
          isSaving={updateConfigMutation.isPending}
        />
      )}
      {showUsageStats && (
        <UsageStatsDialog
          providerName={showUsageStats}
          onClose={() => setShowUsageStats(null)}
        />
      )}
      {showAddProvider && (
        <AddProviderDialog
          onClose={() => setShowAddProvider(false)}
          onAdd={(config) => addProviderMutation.mutate(config)}
          isAdding={addProviderMutation.isPending}
        />
      )}
    </div>
  )
}

export default AIProvidersPage
