import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Trash2, Cpu } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/Table'
import api from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import type { OllamaModelListResponse } from '@/types/api'
import { useTranslation } from 'react-i18next'

export function Models() {
  const { t } = useTranslation()
  const [modelName, setModelName] = useState('')
  const queryClient = useQueryClient()

  // Fetch models
  const { data, isLoading, refetch } = useQuery<OllamaModelListResponse>({
    queryKey: ['ollama-models'],
    queryFn: () => api.getOllamaModels(),
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
                  <TableHead>{t('models.modified')}</TableHead>
                  <TableHead>{t('models.actions')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data?.models.map((model) => (
                  <TableRow key={model.digest}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2">
                        <Cpu className="h-4 w-4 text-primary" />
                        {model.name}
                      </div>
                    </TableCell>
                    <TableCell>{formatBytes(model.size)}</TableCell>
                    <TableCell>{new Date(model.modified_at).toLocaleString()}</TableCell>
                    <TableCell>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteMutation.mutate(model.name)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
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
