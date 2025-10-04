import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Trash2, Cpu, Star, StarOff } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import { Badge } from '@/components/ui/Badge'
import api from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import type { ModelListResponse } from '@/types/api'

export function Models() {
  const { t } = useTranslation()
  const [modelName, setModelName] = useState('')
  const queryClient = useQueryClient()

  // Fetch models
  const { data, isLoading, refetch } = useQuery<ModelListResponse>({
    queryKey: ['models'],
    queryFn: () => api.getModels(),
    refetchInterval: 30000,
  })

  // Pull model mutation
  const pullMutation = useMutation({
    mutationFn: (name: string) => api.pullOllamaModel({ model_name: name }),
    onSuccess: () => {
      setModelName('')
      refetch()
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  // Delete model mutation
  const deleteMutation = useMutation({
    mutationFn: (name: string) => api.deleteOllamaModel(name),
    onSuccess: () => refetch(),
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

  return (
    <div className="space-y-6">
      {/* Pull Model */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.pullNew')}</CardTitle>
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

      {/* Installed Models */}
      <Card>
        <CardHeader>
          <CardTitle>{t('models.installed')}</CardTitle>
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
                  <TableHead>状态</TableHead>
                  <TableHead>使用次数</TableHead>
                  <TableHead>{t('models.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.models.map((model) => (
                  <TableRow key={model.name}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-primary" />
                        {model.name}
                        {model.is_default && (
                          <Badge variant="default" className="ml-2">
                            <Star className="h-3 w-3 mr-1" />
                            默认
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
                        {model.status === 'available' ? '可用' :
                         model.status === 'pulling' ? '拉取中' :
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
                            title="设为默认翻译模型"
                          >
                            <StarOff className="h-4 w-4" />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => deleteMutation.mutate(model.name)}
                          disabled={deleteMutation.isPending || model.is_default}
                          title={model.is_default ? "无法删除默认模型" : "删除模型"}
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
