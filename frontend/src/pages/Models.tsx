import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Trash2, Cpu, Star, StarOff, RefreshCw, Copy, Check } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/Table'
import { Badge } from '../components/ui/Badge'
import api from '../lib/api'
import { formatBytes } from '../lib/utils'
import type { ModelListResponse } from '../types/api'

interface RecommendedModel {
  name: string
  display_name: string
  description: string
  size_estimate: string
  performance: string
  quality: string
  recommended_for: string
}

export function Models() {
  const { t } = useTranslation()
  const [modelName, setModelName] = useState('')
  const [copiedModel, setCopiedModel] = useState<string | null>(null)
  const queryClient = useQueryClient()

  // Fetch models
  const { data, isLoading, refetch } = useQuery<ModelListResponse>({
    queryKey: ['models'],
    queryFn: () => api.getModels(),
    refetchInterval: 30000,
  })

  // Fetch recommended models
  const { data: recommendedData, isLoading: recommendedLoading } = useQuery({
    queryKey: ['recommended-models'],
    queryFn: () => api.getRecommendedModels(),
  })

  // Pull model mutation
  const pullMutation = useMutation({
    mutationFn: (name: string) => api.pullOllamaModel({ name }),
    onSuccess: () => {
      setModelName('')
      refetch()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      alert(t('models.pullSuccess'))
    },
    onError: (error: any) => {
      alert(t('models.pullFailed', {
        error: error.detail || error.response?.data?.detail || error.message
      }))
    },
  })

  // Delete model mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.deleteOllamaModel(name),
    onSuccess: () => refetch(),
    onError: (error: any) => {
      alert(t('models.deleteFailed', {
        error: error.detail || error.response?.data?.detail || error.message
      }))
    },
  })

  // Set default model mutation
  const setDefaultMutation = useMutation({
    mutationFn: (name: string) => api.setDefaultModel(name),
    onSuccess: (data) => {
      refetch()
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      alert(t('models.setDefaultSuccess', { model: data.default_model }))
    },
    onError: (error: any) => {
      alert(t('models.setDefaultFailed', { error: error.response?.data?.detail || error.message }))
    },
  })

  // Sync models mutation
  const syncMutation = useMutation({
    mutationFn: () => api.syncModels(),
    onSuccess: (data) => {
      refetch()
      alert(t('models.syncSuccess', { count: data.total_models }))
    },
    onError: (error: any) => {
      alert(t('models.syncFailed', { error: error.response?.data?.detail || error.message }))
    },
  })

  // Copy model name to clipboard
  const copyModelName = async (name: string) => {
    try {
      await navigator.clipboard.writeText(name)
      setCopiedModel(name)
      setTimeout(() => setCopiedModel(null), 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }

  return (
    <div className="space-y-6">
      {/* Pull Model */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>{t('models.pullNew')}</CardTitle>
              <CardDescription>{t('models.pullNewDesc')}</CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => syncMutation.mutate()}
              disabled={syncMutation.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${syncMutation.isPending ? 'animate-spin' : ''}`} />
              {syncMutation.isPending ? t('models.syncing') : t('models.sync')}
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder={t('models.modelPlaceholder')}
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            />
            <Button
              onClick={() => pullMutation.mutate(modelName)}
              disabled={!modelName || pullMutation.isPending}
            >
              <Download className="mr-2 h-4 w-4" />
              {pullMutation.isPending ? t('models.pulling') : t('models.pull')}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Recommended Models */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.recommendedModels')}</CardTitle>
          <CardDescription>
            {t('models.recommendedModelsDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recommendedLoading ? (
            <p className="text-muted-foreground">{t('common.loading')}</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {recommendedData?.recommended_models.map((model: RecommendedModel) => (
                <div
                  key={model.name}
                  className="border rounded-lg p-4 hover:bg-accent/50 transition-colors"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between">
                      <div>
                        <h3 className="font-semibold text-sm">{model.display_name}</h3>
                        <div className="flex items-center gap-2 mt-1">
                          <button
                            onClick={() => copyModelName(model.name)}
                            className="text-xs text-muted-foreground hover:text-primary flex items-center gap-1 group"
                            title={t('models.clickToCopyModelName')}
                          >
                            <code className="bg-muted px-1.5 py-0.5 rounded text-xs group-hover:bg-primary/10">
                              {model.name}
                            </code>
                            {copiedModel === model.name ? (
                              <Check className="h-3 w-3 text-green-500" />
                            ) : (
                              <Copy className="h-3 w-3" />
                            )}
                          </button>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        {model.size_estimate}
                      </Badge>
                    </div>

                    <p className="text-xs text-muted-foreground line-clamp-2">
                      {model.description}
                    </p>

                    <div className="flex flex-wrap gap-1">
                      <Badge
                        variant="secondary"
                        className="text-xs"
                      >
                        {model.performance === 'fast' ? `⚡ ${t('models.fast')}` :
                          model.performance === 'medium' ? `⚖️ ${t('models.balanced')}` : `🐌 ${t('models.slow')}`}
                      </Badge>
                      <Badge
                        variant="secondary"
                        className="text-xs"
                      >
                        {model.quality === 'basic' ? `📝 ${t('models.basic')}` :
                          model.quality === 'good' ? `👍 ${t('models.good')}` :
                            model.quality === 'very good' ? `⭐ ${t('models.excellent')}` : `💎 ${t('models.superior')}`}
                      </Badge>
                    </div>

                    <div className="pt-2 border-t">
                      <p className="text-xs text-muted-foreground">
                        💡 {model.recommended_for}
                      </p>
                    </div>

                    <Button
                      size="sm"
                      className="w-full"
                      variant="outline"
                      onClick={() => {
                        setModelName(model.name)
                        pullMutation.mutate(model.name)
                      }}
                      disabled={pullMutation.isPending}
                    >
                      <Download className="mr-2 h-3 w-3" />
                      {t('models.pullThisModel')}
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Installed Models */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.installed')}</CardTitle>
          <CardDescription>
            {t('models.installedDesc')}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground">{t('models.loading')}</p>
          ) : data?.models.length === 0 ? (
            <p className="text-muted-foreground">{t('models.noModels')}</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('models.modelName')}</TableHead>
                  <TableHead>{t('models.size')}</TableHead>
                  <TableHead>{t('models.status')}</TableHead>
                  <TableHead>{t('models.usageCount')}</TableHead>
                  <TableHead>{t('models.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.models.map((model) => (
                  <TableRow key={model.name}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-primary" />
                        <button
                          onClick={() => copyModelName(model.name)}
                          className="hover:text-primary flex items-center gap-1"
                          title={t('models.clickToCopy')}
                        >
                          {model.name}
                          {copiedModel === model.name && (
                            <Check className="h-3 w-3 text-green-500" />
                          )}
                        </button>
                        {model.is_default && (
                          <Badge variant="default" className="ml-2">
                            <Star className="h-3 w-3 mr-1" />
                            {t('models.default')}
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell>{formatBytes(model.size_bytes)}</TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          model.status === 'available' ? 'default' :
                            model.status === 'pulling' ? 'secondary' :
                              'destructive'
                        }
                      >
                        {model.status === 'available' ? `✓ ${t('models.available')}` :
                          model.status === 'pulling' ? `⏳ ${t('models.pullingStatus')}` :
                            model.status}
                      </Badge>
                    </TableCell>
                    <TableCell>{model.usage_count || 0}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        {!model.is_default && model.status === 'available' && (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => setDefaultMutation.mutate(model.name)}
                            disabled={setDefaultMutation.isPending}
                            title={t('models.setAsDefaultModel')}
                          >
                            <StarOff className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteMutation.mutate(model.name)}
                          disabled={deleteMutation.isPending || model.is_default}
                          title={model.is_default ? t('models.cannotDeleteDefault') : t('models.deleteModel')}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
