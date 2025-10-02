import { useQuery, useMutation } from '@tanstack/react-query'
import { Save } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import api from '@/lib/api'
import type { AppSettings } from '@/types/api'
import { useTranslation } from 'react-i18next'

export function Settings() {
  const { t } = useTranslation()
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
    <div className="max-w-4xl space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.translationSettings')}</CardTitle>
          <CardDescription>{t('settings.translationDesc')}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">{t('settings.defaultMtModel')}</label>
            <Input
              defaultValue={settings?.default_mt_model}
              onBlur={(e) => updateMutation.mutate({ default_mt_model: e.target.value })}
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">{t('settings.requiredLangs')}</label>
            <Input
              defaultValue={settings?.required_langs.join(', ')}
              onBlur={(e) =>
                updateMutation.mutate({ required_langs: e.target.value.split(',').map((s) => s.trim()) })
              }
              placeholder="zh-CN, en, ja"
            />
          </div>

          <div>
            <label className="text-sm font-medium mb-2 block">{t('settings.writebackMode')}</label>
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
            <label className="text-sm font-medium mb-2 block">{t('settings.defaultFormat')}</label>
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
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium mb-2 block">{t('settings.asrModel')}</label>
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

          <div>
            <label className="text-sm font-medium mb-2 block">{t('settings.asrLanguage')}</label>
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
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="text-sm font-medium mb-2 block">{t('settings.maxScanTasks')}</label>
              <Input
                type="number"
                defaultValue={settings?.max_concurrent_scan_tasks}
                onBlur={(e) => updateMutation.mutate({ max_concurrent_scan_tasks: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">{t('settings.maxTranslateTasks')}</label>
              <Input
                type="number"
                defaultValue={settings?.max_concurrent_translate_tasks}
                onBlur={(e) => updateMutation.mutate({ max_concurrent_translate_tasks: parseInt(e.target.value) })}
              />
            </div>
            <div>
              <label className="text-sm font-medium mb-2 block">{t('settings.maxAsrTasks')}</label>
              <Input
                type="number"
                defaultValue={settings?.max_concurrent_asr_tasks}
                onBlur={(e) => updateMutation.mutate({ max_concurrent_asr_tasks: parseInt(e.target.value) })}
              />
            </div>
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
