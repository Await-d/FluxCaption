import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Save, FolderOpen, Plus, X, Bot, ArrowRight, CheckCircle2, AlertCircle, RefreshCw, Clock3, Link2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Checkbox } from '../components/ui/Checkbox'
import { Input } from '../components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import api from '../lib/api'
import type { AppSettings } from '../types/api'
import { useTranslation } from 'react-i18next'
import { aiProviderApi } from '../api/aiProviders'
import * as aiModelsApi from '../api/aiModels'
import { useNavigate } from 'react-router-dom'
import { PageHero } from '../components/ui/PageHero'

export function Settings() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [newPath, setNewPath] = useState('')
  
  // Fetch settings
  const { data: settings, isLoading, refetch } = useQuery<AppSettings>({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })

  const { data: providers } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiProviderApi.listProviders(false),
  })

  const { data: availableModels } = useQuery({
    queryKey: ['ai-models', 'settings-default-mt'],
    queryFn: () => aiModelsApi.listModels({ enabled_only: true, page: 1, page_size: 100 }),
  })

  // Update settings mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<AppSettings>) => api.updateSettings(data),
    onSuccess: () => refetch(),
  })

  if (isLoading) {
    return <div className="text-muted-foreground">{t('settings.loading')}</div>
  }

  const defaultMtModel = settings?.default_mt_model || ''
  const defaultMtModels = availableModels?.models ?? []
  const hasDefaultMtModel = defaultMtModels.some((model) => model.model_name === defaultMtModel)

  return (
    <div className="max-w-6xl space-y-4 sm:space-y-6 lg:space-y-8">
      <PageHero
        eyebrow={t('pageHero.settings.eyebrow')}
        title={t('settings.settings', 'Settings')}
        description={t('pageHero.settings.description')}
        actions={
          <Button onClick={() => refetch()} disabled={updateMutation.isPending}>
            <Save className="mr-2 h-4 w-4" />
            {updateMutation.isPending ? t('settings.saving') : t('settings.refresh')}
          </Button>
        }
        metrics={[
          { label: t('pageHero.settings.metrics.providers.label'), value: String(providers?.length ?? 0), detail: t('pageHero.settings.metrics.providers.detail') },
          { label: t('pageHero.settings.metrics.models.label'), value: String(defaultMtModels.length), detail: t('pageHero.settings.metrics.models.detail') },
          { label: t('pageHero.settings.metrics.catalog.label'), value: settings?.ai_models_auto_sync_enabled ? t('common.enabled') : t('common.disabled'), detail: settings?.ai_models_last_catalog_sync_at ? new Date(settings.ai_models_last_catalog_sync_at).toLocaleDateString() : t('settings.neverSynced') },
        ]}
      />

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle>{t('settings.jellyfinIntegration')}</CardTitle>
          <CardDescription>{t('settings.jellyfinDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.jellyfinBaseUrl')}</label>
            <Input
              defaultValue={settings?.jellyfin_base_url}
              onBlur={(e) => updateMutation.mutate({ jellyfin_base_url: e.target.value })}
              placeholder="http://jellyfin:8096"
            />
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              {t('settings.jellyfinBaseUrlDesc')}
            </p>
          </div>

          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.jellyfinApiKey')}</label>
            <Input
              type="password"
              defaultValue={settings?.jellyfin_api_key}
              onBlur={(e) => updateMutation.mutate({ jellyfin_api_key: e.target.value })}
              placeholder="API Key"
            />
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              {t('settings.jellyfinApiKeyDesc')}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.jellyfinTimeout')}</label>
              <Input
                type="number"
                defaultValue={settings?.jellyfin_timeout}
                onBlur={(e) => updateMutation.mutate({ jellyfin_timeout: parseInt(e.target.value) })}
                placeholder="30"
              />
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.jellyfinMaxRetries')}</label>
              <Input
                type="number"
                defaultValue={settings?.jellyfin_max_retries}
                onBlur={(e) => updateMutation.mutate({ jellyfin_max_retries: parseInt(e.target.value) })}
                placeholder="3"
              />
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.jellyfinRateLimit')}</label>
              <Input
                type="number"
                defaultValue={settings?.jellyfin_rate_limit_per_second}
                onBlur={(e) => updateMutation.mutate({ jellyfin_rate_limit_per_second: parseInt(e.target.value) })}
                placeholder="10"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle>{t('settings.ollamaConfig')}</CardTitle>
          <CardDescription>{t('settings.ollamaConfigDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.ollamaBaseUrl')}</label>
            <Input
              defaultValue={settings?.ollama_base_url}
              onBlur={(e) => updateMutation.mutate({ ollama_base_url: e.target.value })}
              placeholder="http://ollama:11434"
            />
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
              {t('settings.ollamaBaseUrlDesc')}
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.ollamaTimeout')}</label>
              <Input
                type="number"
                defaultValue={settings?.ollama_timeout}
                onBlur={(e) => updateMutation.mutate({ ollama_timeout: parseInt(e.target.value) })}
                placeholder="300"
              />
              <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
                {t('settings.ollamaTimeoutDesc')}
              </p>
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.ollamaKeepAlive')}</label>
              <Input
                defaultValue={settings?.ollama_keep_alive}
                onBlur={(e) => updateMutation.mutate({ ollama_keep_alive: e.target.value })}
                placeholder="30m"
              />
              <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
                {t('settings.ollamaKeepAliveDesc')}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bot className="h-5 w-5" />
            {t('settings.aiProviders')}
          </CardTitle>
          <CardDescription>
            {t('settings.aiProvidersDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-[22px] border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">{t('settings.providersTotal')}</p>
              <p className="text-lg font-semibold">{providers?.length ?? 0}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">{t('settings.providersConfigured')}</p>
              <p className="text-lg font-semibold">{providers?.filter((p) => p.has_api_key).length ?? 0}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground">{t('settings.providersEnabled')}</p>
              <p className="text-lg font-semibold">{providers?.filter((p) => p.is_enabled).length ?? 0}</p>
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {(providers ?? []).slice(0, 4).map((provider) => (
              <div
                key={provider.id}
                className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs"
              >
                {provider.is_enabled ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <AlertCircle className="h-3.5 w-3.5 text-muted-foreground" />
                )}
                <span>{provider.display_name}</span>
                <span className="text-muted-foreground">{provider.has_api_key ? t('settings.apiKeySet') : t('settings.apiKeyMissing')}</span>
              </div>
            ))}
          </div>

          <Button onClick={() => navigate('/ai-providers')}>
            <ArrowRight className="mr-2 h-4 w-4" />
            {t('settings.openAiProviders')}
          </Button>
        </CardContent>
      </Card>

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle>{t('settings.automation')}</CardTitle>
          <CardDescription>
            {t('settings.automationDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {[
              {
                key: 'enable_auto_scan' as const,
                title: t('settings.enableAutoScan'),
                desc: t('settings.enableAutoScanDesc'),
              },
              {
                key: 'enable_auto_pull_models' as const,
                title: t('settings.enableAutoPullModels'),
                desc: t('settings.enableAutoPullModelsDesc'),
              },
              {
                key: 'enable_sidecar_writeback' as const,
                title: t('settings.enableSidecarWriteback'),
                desc: t('settings.enableSidecarWritebackDesc'),
              },
              {
                key: 'enable_metrics' as const,
                title: t('settings.enableMetrics'),
                desc: t('settings.enableMetricsDesc'),
              },
            ].map((item) => (
              <label key={item.key} className="flex cursor-pointer items-start gap-3 rounded-[22px] border border-border/70 p-4 transition-colors hover:bg-muted/30">
                <Checkbox
                  checked={settings?.[item.key] ?? false}
                  onCheckedChange={(checked) => updateMutation.mutate({ [item.key]: !!checked } as Partial<AppSettings>)}
                  className="mt-0.5"
                />
                <div className="space-y-1">
                  <p className="text-sm font-medium leading-none">{item.title}</p>
                  <p className="text-xs text-muted-foreground">{item.desc}</p>
                </div>
              </label>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 border-t pt-4">
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.writebackMode')}</label>
              <Select
                defaultValue={settings?.writeback_mode}
                onValueChange={(value) => updateMutation.mutate({ writeback_mode: value as 'upload' | 'sidecar' })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="upload">{t('settings.uploadMode')}</SelectItem>
                  <SelectItem value="sidecar">{t('settings.sidecarMode')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.defaultFormat')}</label>
              <Select
                defaultValue={settings?.default_subtitle_format}
                onValueChange={(value) =>
                  updateMutation.mutate({ default_subtitle_format: value as 'srt' | 'ass' | 'vtt' })
                }
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="srt">SRT</SelectItem>
                  <SelectItem value="ass">ASS</SelectItem>
                  <SelectItem value="vtt">VTT</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.translationBatchSize')}</label>
              <Input
                type="number"
                defaultValue={settings?.translation_batch_size}
                onBlur={(e) => updateMutation.mutate({ translation_batch_size: parseInt(e.target.value) })}
                placeholder="10"
              />
            </div>

            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.translationLineConcurrency')}</label>
              <Input
                type="number"
                defaultValue={settings?.translation_line_concurrency}
                onBlur={(e) => updateMutation.mutate({ translation_line_concurrency: parseInt(e.target.value, 10) })}
                placeholder="3"
              />
            </div>

            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.aiProviderMaxConcurrency')}</label>
              <Input
                type="number"
                defaultValue={settings?.ai_provider_max_concurrency}
                onBlur={(e) => updateMutation.mutate({ ai_provider_max_concurrency: parseInt(e.target.value, 10) })}
                placeholder="6"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5" />
            {t('settings.aiModelCatalog')}
          </CardTitle>
          <CardDescription>{t('settings.aiModelCatalogDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="rounded-[22px] border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <RefreshCw className="h-3.5 w-3.5" />
                {t('settings.autoSyncStatus')}
              </p>
              <p className="text-lg font-semibold">
                {settings?.ai_models_auto_sync_enabled ? t('common.enabled') : t('common.disabled')}
              </p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock3 className="h-3.5 w-3.5" />
                {t('settings.autoSyncInterval')}
              </p>
              <p className="text-lg font-semibold">{Math.round((settings?.ai_models_auto_sync_interval_seconds ?? 3600) / 60)} {t('common.minutes')}</p>
            </div>
            <div className="rounded-[22px] border border-border/70 bg-muted/30 p-3">
              <p className="text-xs text-muted-foreground flex items-center gap-1">
                <Link2 className="h-3.5 w-3.5" />
                {t('settings.lastCatalogSync')}
              </p>
              <p className="text-sm font-medium break-all">
                {settings?.ai_models_last_catalog_sync_at
                  ? new Date(settings.ai_models_last_catalog_sync_at).toLocaleString()
                  : t('settings.neverSynced')}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="flex cursor-pointer items-start gap-3 rounded-[22px] border border-border/70 p-4 transition-colors hover:bg-muted/30">
              <Checkbox
                checked={settings?.ai_models_auto_sync_enabled ?? false}
                onCheckedChange={(checked) => updateMutation.mutate({ ai_models_auto_sync_enabled: !!checked })}
                className="mt-0.5"
              />
              <div className="space-y-1">
                <p className="text-sm font-medium leading-none">{t('settings.aiModelAutoSync')}</p>
                <p className="text-xs text-muted-foreground">{t('settings.aiModelAutoSyncDesc')}</p>
              </div>
            </label>

            <div className="space-y-2 rounded-[22px] border border-border/70 p-4">
              <label className="text-xs sm:text-sm font-medium block">{t('settings.autoSyncIntervalSeconds')}</label>
              <Input
                type="number"
                defaultValue={settings?.ai_models_auto_sync_interval_seconds}
                onBlur={(e) => updateMutation.mutate({ ai_models_auto_sync_interval_seconds: parseInt(e.target.value, 10) })}
                placeholder="3600"
              />
              <p className="text-xs text-muted-foreground">{t('settings.autoSyncIntervalDesc')}</p>
            </div>
          </div>

          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.catalogSourceUrl')}</label>
            <Input
              defaultValue={settings?.ai_models_catalog_url}
              onBlur={(e) => updateMutation.mutate({ ai_models_catalog_url: e.target.value })}
              placeholder="https://models.dev"
            />
            <p className="text-xs text-muted-foreground mt-1">{t('settings.catalogSourceUrlDesc')}</p>
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle>{t('settings.translationSettings')}</CardTitle>
          <CardDescription>{t('settings.translationDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.defaultMtModel')}</label>
            <Select
              value={defaultMtModel}
              onValueChange={(value) => updateMutation.mutate({ default_mt_model: value })}
            >
              <SelectTrigger>
                  <SelectValue placeholder={t('common.select')} />
              </SelectTrigger>
              <SelectContent>
                {defaultMtModel && !hasDefaultMtModel && (
                  <SelectItem value={defaultMtModel}>{defaultMtModel}</SelectItem>
                )}
                {defaultMtModels.map((model) => (
                  <SelectItem key={model.id} value={model.model_name}>
                    {model.display_name || model.model_name} ({model.provider_name})
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground mt-1">
              {t('settings.selectDefaultMtModel')}
            </p>
          </div>

          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.translationMaxLineLength')}</label>
            <Input
              type="number"
              defaultValue={settings?.translation_max_line_length}
              onBlur={(e) => updateMutation.mutate({ translation_max_line_length: parseInt(e.target.value) })}
              placeholder="42"
            />
          </div>

          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.translationPreserveFormatting')}</label>
            <Select
              defaultValue={settings?.translation_preserve_formatting ? 'true' : 'false'}
              onValueChange={(value) => updateMutation.mutate({ translation_preserve_formatting: value === 'true' })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="true">{t('common.enabled')}</SelectItem>
                <SelectItem value="false">{t('common.disabled')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('settings.asrSettings')}</CardTitle>
          <CardDescription>{t('settings.asrDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.asrEngine')}</label>
            <Select
              defaultValue={settings?.asr_engine}
              onValueChange={(value) => updateMutation.mutate({ asr_engine: value as 'faster-whisper' | 'funasr' })}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="faster-whisper">Faster Whisper</SelectItem>
                <SelectItem value="funasr">FunASR</SelectItem>
              </SelectContent>
            </Select>
            <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
{t('settings.asrEngineDesc')}
            </p>
          </div>

          {settings?.asr_engine === 'faster-whisper' && (
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.asrModel')}</label>
              <Select
                defaultValue={settings?.asr_model}
                onValueChange={(value) => updateMutation.mutate({ asr_model: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="tiny">Tiny</SelectItem>
                  <SelectItem value="base">Base</SelectItem>
                  <SelectItem value="small">Small</SelectItem>
                  <SelectItem value="medium">Medium</SelectItem>
                  <SelectItem value="large-v2">Large v2</SelectItem>
                  <SelectItem value="large-v3">Large v3</SelectItem>
                </SelectContent>
              </Select>
            </div>
          )}

          {settings?.asr_engine === 'funasr' && (
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.funasrModel')}</label>
              <Select
                defaultValue={settings?.funasr_model}
                onValueChange={(value) => updateMutation.mutate({ funasr_model: value })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="paraformer-zh">{t('settings.paraformerZh')}</SelectItem>
                  <SelectItem value="paraformer-en">{t('settings.paraformerEn')}</SelectItem>
                  <SelectItem value="sensevoicesmall">{t('settings.sensevoicesmall')}</SelectItem>
                </SelectContent>
              </Select>
              <p className="text-[10px] sm:text-xs text-muted-foreground mt-1">
{t('settings.funasrDesc')}
              </p>
            </div>
          )}

          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.asrLanguage')}</label>
            <Input
              defaultValue={settings?.asr_language}
              onBlur={(e) => updateMutation.mutate({ asr_language: e.target.value })}
              placeholder={t('settings.asrLanguagePlaceholder')}
            />
          </div>
        </CardContent>
      </Card>

      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle>{t('settings.processingLimits', 'Processing Limits')}</CardTitle>
          <CardDescription>{t('settings.performanceDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.maxScanTasks')}</label>
              <Input
                type="number"
                defaultValue={settings?.max_concurrent_scan_tasks}
                onBlur={(e) => updateMutation.mutate({ max_concurrent_scan_tasks: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.maxTranslateTasks')}</label>
              <Input
                type="number"
                defaultValue={settings?.max_concurrent_translate_tasks}
                onBlur={(e) => updateMutation.mutate({ max_concurrent_translate_tasks: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.maxAsrTasks')}</label>
              <Input
                type="number"
                defaultValue={settings?.max_concurrent_asr_tasks}
                onBlur={(e) => updateMutation.mutate({ max_concurrent_asr_tasks: parseInt(e.target.value) })}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border-t pt-4">
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.scanTaskTimeout')}</label>
              <Input
                type="number"
                defaultValue={settings?.scan_task_timeout}
                onBlur={(e) => updateMutation.mutate({ scan_task_timeout: parseInt(e.target.value) })}
                placeholder="300"
              />
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.translateTaskTimeout')}</label>
              <Input
                type="number"
                defaultValue={settings?.translate_task_timeout}
                onBlur={(e) => updateMutation.mutate({ translate_task_timeout: parseInt(e.target.value) })}
                placeholder="1800"
              />
            </div>
            <div>
              <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.asrTaskTimeout')}</label>
              <Input
                type="number"
                defaultValue={settings?.asr_task_timeout}
                onBlur={(e) => updateMutation.mutate({ asr_task_timeout: parseInt(e.target.value) })}
                placeholder="3600"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Local Media Paths Management */}
      <Card className="rounded-[30px]">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <FolderOpen className="h-4 w-4 sm:h-5 sm:w-5" />
{t('settings.favoriteMediaPaths')}
          </CardTitle>
          <CardDescription className="text-[10px] sm:text-xs">
            {t('settings.favoriteMediaPathsDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          {/* Add new path */}
          <div className="flex gap-2">
            <Input
              placeholder={t('settings.pathPlaceholder')}
              value={newPath}
              onChange={(e) => setNewPath(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && newPath.trim()) {
                  const currentPaths = settings?.favorite_media_paths || []
                  if (!currentPaths.includes(newPath.trim())) {
                    updateMutation.mutate({
                      favorite_media_paths: [...currentPaths, newPath.trim()],
                    })
                    setNewPath('')
                  }
                }
              }}
              className="text-xs sm:text-sm"
            />
            <Button
              onClick={() => {
                if (newPath.trim()) {
                  const currentPaths = settings?.favorite_media_paths || []
                  if (!currentPaths.includes(newPath.trim())) {
                    updateMutation.mutate({
                      favorite_media_paths: [...currentPaths, newPath.trim()],
                    })
                    setNewPath('')
                  }
                }
              }}
              disabled={!newPath.trim() || updateMutation.isPending}
              className="shrink-0"
            >
              <Plus className="h-4 w-4" />
              <span className="hidden sm:inline ml-2">{t('settings.addPath')}</span>
            </Button>
          </div>

          {/* Favorite paths list */}
          <div className="space-y-1.5 sm:space-y-2">
            {settings?.favorite_media_paths && settings.favorite_media_paths.length > 0 ? (
              settings.favorite_media_paths.map((path, index) => (
                <div
                  key={index}
                 className="flex items-center justify-between rounded-[18px] bg-muted/45 p-2 sm:p-3"
                >
                  <div className="flex items-center gap-2 flex-1 min-w-0">
                    <FolderOpen className="h-3 w-3 sm:h-4 sm:w-4 text-muted-foreground shrink-0" />
                    <span className="text-xs sm:text-sm font-mono truncate">{path}</span>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const currentPaths = settings.favorite_media_paths || []
                      updateMutation.mutate({
                        favorite_media_paths: currentPaths.filter((_, i) => i !== index),
                      })
                    }}
                    disabled={updateMutation.isPending}
                    className="shrink-0 h-7 w-7 sm:h-8 sm:w-8 p-0"
                  >
                    <X className="h-3 w-3 sm:h-4 sm:w-4" />
                  </Button>
                </div>
              ))
            ) : (
              <p className="text-xs sm:text-sm text-muted-foreground text-center py-4">
{t('settings.noFavoritePaths')}
              </p>
            )}
          </div>
        </CardContent>
      </Card>

    </div>
  )
}
