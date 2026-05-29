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
  Send,
} from 'lucide-react'
import { aiProviderApi, AIProviderConfig } from '../api/aiProviders'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { cn } from '../lib/utils'
import QuotaDialog from '../components/QuotaDialog'
import ProviderConfigDialog from '../components/ProviderConfigDialog'
import UsageStatsDialog from '../components/UsageStatsDialog'
import AddProviderDialog from '../components/AddProviderDialog'
import { PageHero } from '../components/ui/PageHero'

const AIProvidersPage: React.FC = () => {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [editingProvider, setEditingProvider] = useState<AIProviderConfig | null>(null)
  const [openTestOnOpen, setOpenTestOnOpen] = useState(false)
  const [showUsageStats, setShowUsageStats] = useState<string | null>(null)
  const [showAddProvider, setShowAddProvider] = useState(false)

  // Fetch providers
  const { data: providers, isLoading } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiProviderApi.listProviders(false),
  })

  const visibleProviders = (providers ?? []).filter((provider) => {
    if (provider.provider_name === 'ollama') {
      return true
    }

    if (provider.provider_name === 'custom_openai') {
      return Boolean(provider.base_url?.trim())
    }

    if (provider.provider_name === 'deeplx') {
      return provider.is_enabled || provider.has_api_key || provider.base_url?.trim() !== 'http://localhost:1188'
    }

    return Boolean(provider.has_api_key)
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
      case 'deeplx':
        return '🌐'
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

  const handleOpenConfigure = (provider: AIProviderConfig) => {
    setOpenTestOnOpen(false)
    setEditingProvider(provider)
  }

  const handleOpenTest = (provider: AIProviderConfig) => {
    setOpenTestOnOpen(true)
    setEditingProvider(provider)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6 lg:space-y-8">
      <PageHero
        eyebrow={t('pageHero.aiProviders.eyebrow')}
        title={t('ai_providers.title', 'AI Providers')}
        description={t('ai_providers.description', 'Manage AI provider configurations and quotas')}
        actions={
          <>
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
          </>
        }
        metrics={[
          { label: t('pageHero.aiProviders.metrics.providers.label'), value: String(visibleProviders.length), detail: t('pageHero.aiProviders.metrics.providers.detail') },
          { label: t('pageHero.aiProviders.metrics.healthy.label'), value: String(visibleProviders.filter((provider) => provider.is_healthy).length), detail: t('pageHero.aiProviders.metrics.healthy.detail') },
          { label: t('pageHero.aiProviders.metrics.enabled.label'), value: String(visibleProviders.filter((provider) => provider.is_enabled).length), detail: t('pageHero.aiProviders.metrics.enabled.detail') },
        ]}
      />

      {/* Provider Cards Grid */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
        {visibleProviders.map((provider) => (
          <Card
            key={provider.id}
            className={cn(
              'rounded-[30px] transition-all duration-200 hover:-translate-y-1',
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

              <div className="flex items-center justify-between rounded-[18px] border border-border/70 bg-background/35 px-3 py-3 text-xs text-muted-foreground">
                <span>{t('ai_providers.api_key', 'API Key')}</span>
                <span>{provider.has_api_key ? t('common.configured', 'Configured') : t('common.not_set', 'Not set')}</span>
              </div>

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
              <div className="grid grid-cols-2 gap-2 border-t border-border/70 pt-2">
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
                  onClick={() => handleOpenTest(provider)}
                >
                  <Send className="mr-2 h-4 w-4" />
                  {t('ai_providers.test_provider', 'Test Provider')}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleOpenConfigure(provider)}
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
      {visibleProviders.length === 0 && (
        <Card className="rounded-[30px]">
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
          openTestOnOpen={openTestOnOpen}
          onClose={() => {
            setEditingProvider(null)
            setOpenTestOnOpen(false)
          }}
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
