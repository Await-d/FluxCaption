import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Save, FolderOpen, Plus, X } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import api from '@/lib/api'
import type { AppSettings } from '@/types/api'
import { useTranslation } from 'react-i18next'

export function Settings() {
  const { t } = useTranslation()
  const [newPath, setNewPath] = useState('')
  
  // Fetch settings
  const { data: settings, isLoading, refetch } = useQuery<AppSettings>({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })

  // Update settings mutation
  const updateMutation = useMutation({
    mutationFn: (data: Partial<AppSettings>) => api.updateSettings(data),
    onSuccess: () => refetch(),
  })

  if (isLoading) {
    return <div className="text-muted-foreground">{t('settings.loading')}</div>
  }

  return (
    <div className="max-w-4xl space-y-4 sm:space-y-6">
      <Card>
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

      <Card>
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

      <Card>
        <CardHeader>
          <CardTitle>{t('settings.translationSettings')}</CardTitle>
          <CardDescription>{t('settings.translationDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3 sm:space-y-4">
          <div>
            <label className="text-xs sm:text-sm font-medium mb-2 block">{t('settings.defaultMtModel')}</label>
            <Input
              defaultValue={settings?.default_mt_model}
              onBlur={(e) => updateMutation.mutate({ default_mt_model: e.target.value })}
            />
          </div>

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

      <Card>
        <CardHeader>
          <CardTitle>{t('settings.performance')}</CardTitle>
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
        </CardContent>
      </Card>

      {/* Local Media Paths Management */}
      <Card>
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
                  className="flex items-center justify-between p-2 sm:p-3 bg-muted rounded-lg"
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

      <div className="flex justify-end">
        <Button onClick={() => refetch()} disabled={updateMutation.isPending}>
          <Save className="mr-2 h-4 w-4" />
          {updateMutation.isPending ? t('settings.saving') : t('settings.refresh')}
        </Button>
      </div>
    </div>
  )
}
