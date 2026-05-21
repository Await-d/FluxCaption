/**
 * AI Model Configuration Management Page
 *
 * Allows administrators to configure available models for each AI provider
 * with pricing information.
 */

import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit2, Trash2, DollarSign, Check, X, Loader2 } from 'lucide-react'
import * as aiModelsApi from '../api/aiModels'
import type { AIModelConfig, AIModelConfigCreate, AIModelConfigUpdate } from '../api/aiModels'
import { aiProviderApi } from '../api/aiProviders'
import { toast } from 'sonner'
import { Card, CardContent } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Label } from '../components/ui/Label'
import { Textarea } from '../components/ui/Textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/Select'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/Dialog'
import { cn } from '../lib/utils'

export default function AIModelsPage() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null)
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [editingModel, setEditingModel] = useState<AIModelConfig | null>(null)

  // Fetch all models
  const { data: modelsData, isLoading } = useQuery({
    queryKey: ['ai-models', selectedProvider],
    queryFn: () =>
      aiModelsApi.listModels({
        provider: selectedProvider || undefined,
        page: 1,
        page_size: 100,
      }),
  })

  // Fetch AI providers
  const { data: providersData } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiProviderApi.listProviders(false),
  })

  // Create model mutation
  const createMutation = useMutation({
    mutationFn: aiModelsApi.createModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] })
      setShowCreateDialog(false)
      toast.success(t('common.success'))
    },
    onError: () => {
      toast.error(t('common.error'))
    },
  })

  // Update model mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AIModelConfigUpdate }) =>
      aiModelsApi.updateModel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] })
      setEditingModel(null)
      toast.success(t('common.success'))
    },
    onError: () => {
      toast.error(t('common.error'))
    },
  })

  // Delete model mutation
  const deleteMutation = useMutation({
    mutationFn: aiModelsApi.deleteModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] })
      toast.success(t('common.success'))
    },
    onError: () => {
      toast.error(t('common.error'))
    },
  })

  const handleDelete = (model: AIModelConfig) => {
    // eslint-disable-next-line no-alert
    if (confirm(`${t('common.delete')} "${model.display_name}"?`)) {
      deleteMutation.mutate(model.id)
    }
  }

  // Get providers from AI Providers API
  const providers = (providersData || []).map((p) => p.provider_name).sort()

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h2 className="text-xl font-semibold">{t('nav.aiModels')}</h2>
          <p className="text-sm text-muted-foreground mt-1">
            {t('aiModels.descHeader')}
          </p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)}>
          <Plus className="mr-2 h-4 w-4" />
          {t('aiModels.addButton')}
        </Button>
      </div>

      {/* Provider Filter */}
      <div className="flex flex-wrap items-center gap-2">
        <Button
          variant={selectedProvider === null ? 'default' : 'outline'}
          size="sm"
          onClick={() => setSelectedProvider(null)}
        >
          {t('aiModels.allProviders')}
        </Button>
        {providers.map((provider) => (
          <Button
            key={provider}
            variant={selectedProvider === provider ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedProvider(provider)}
          >
            {provider}
          </Button>
        ))}
      </div>

      {/* Models List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : modelsData && modelsData.models.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modelsData.models.map((model) => (
            <ModelCard
              key={model.id}
              model={model}
              onEdit={() => setEditingModel(model)}
              onDelete={() => handleDelete(model)}
            />
          ))}
        </div>
      ) : (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground space-y-1">
            <p>{t('aiModels.noModels')}</p>
            <p className="text-sm">{t('aiModels.clickToCreate')}</p>
          </CardContent>
        </Card>
      )}

      {/* Create/Edit Dialog */}
      {(showCreateDialog || editingModel) && (
        <ModelDialog
          model={editingModel}
          providers={providers}
          onClose={() => {
            setShowCreateDialog(false)
            setEditingModel(null)
          }}
          onSubmit={(data) => {
            if (editingModel) {
              updateMutation.mutate({ id: editingModel.id, data })
            } else {
              createMutation.mutate(data as AIModelConfigCreate)
            }
          }}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  )
}

// Model Card Component
function ModelCard({
  model,
  onEdit,
  onDelete,
}: {
  model: AIModelConfig
  onEdit: () => void
  onDelete: () => void
}) {
  const { t } = useTranslation()
  let tags: string[] = []
  try {
    tags = model.tags ? JSON.parse(model.tags) : []
  } catch {
    tags = []
  }

  return (
    <Card className="hover:border-primary/50 transition-colors">
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <h3 className="font-semibold truncate">{model.display_name}</h3>
              {model.is_default && (
                <span className="px-2 py-0.5 text-xs font-medium rounded bg-primary/20 text-primary flex-shrink-0">
                  {t('jobs.default')}
                </span>
              )}
            </div>
            <p className="text-sm text-muted-foreground truncate mt-0.5">
              {model.provider_name}:{model.model_name}
            </p>
          </div>
          <div className="flex items-center gap-1">
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8"
              onClick={onEdit}
              title={t('common.edit')}
            >
              <Edit2 className="h-4 w-4" />
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="icon"
              className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
              onClick={onDelete}
              title={t('common.delete')}
            >
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* Status */}
        <div className="flex items-center gap-2 text-sm">
          {model.is_enabled ? (
            <div className="flex items-center gap-1.5 text-green-500 dark:text-green-400">
              <Check className="h-3.5 w-3.5" />
              <span>{t('aiModels.enabled')}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <X className="h-3.5 w-3.5" />
              <span>{t('aiModels.disabled')}</span>
            </div>
          )}
        </div>

        {/* Specs */}
        {(model.context_window || model.max_output_tokens) && (
          <div className="text-xs text-muted-foreground space-y-1">
            {model.context_window && (
              <div>
                {t('aiModels.contextLabel')}: {model.context_window.toLocaleString()}{' '}
                {t('aiModels.tokens')}
              </div>
            )}
            {model.max_output_tokens && (
              <div>
                {t('aiModels.maxOutputLabel')}: {model.max_output_tokens.toLocaleString()}{' '}
                {t('aiModels.tokens')}
              </div>
            )}
          </div>
        )}

        {/* Pricing */}
        {(model.input_price !== null || model.output_price !== null) && (
          <div className="flex items-start gap-2 p-2 rounded bg-muted/50">
            <DollarSign className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
            <div className="text-xs space-y-0.5 flex-1">
              {model.input_price !== null && (
                <div>Input: ${model.input_price}/1M tokens</div>
              )}
              {model.output_price !== null && (
                <div>Output: ${model.output_price}/1M tokens</div>
              )}
              {model.input_price === 0 && model.output_price === 0 && (
                <div className="text-green-500 dark:text-green-400 font-medium">
                  {t('common.free', 'Free')}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Tags */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {tags.map((tag: string) => (
              <span
                key={tag}
                className="px-2 py-0.5 text-xs rounded bg-primary/10 text-primary"
              >
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Usage Stats */}
        {model.usage_count > 0 && (
          <div className="text-xs text-muted-foreground pt-2 border-t">
            {t('aiModels.usedTimes', { count: model.usage_count })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// Recommended models for each provider (Updated November 2025)
interface RecommendedModel {
  name: string
  display: string
  description: string
  context_window?: number
  max_output_tokens?: number
  input_price?: number
  output_price?: number
}

const RECOMMENDED_MODELS: Record<string, RecommendedModel[]> = {
  openai: [
    { name: 'gpt-4.1', display: 'GPT-4.1', description: '1M context, smartest non-reasoning', context_window: 1048576, max_output_tokens: 32768, input_price: 2.0, output_price: 8.0 },
    { name: 'gpt-4.1-mini', display: 'GPT-4.1 Mini', description: 'Cost-effective variant', context_window: 1048576, max_output_tokens: 32768, input_price: 0.1, output_price: 0.4 },
    { name: 'gpt-4o', display: 'GPT-4o', description: 'General-purpose multimodal', context_window: 128000, max_output_tokens: 16384, input_price: 2.5, output_price: 10.0 },
    { name: 'gpt-4o-mini', display: 'GPT-4o Mini', description: 'Fast and affordable', context_window: 128000, max_output_tokens: 16384, input_price: 0.15, output_price: 0.6 },
    { name: 'o3-mini', display: 'o3 Mini', description: 'Cost-efficient reasoning', context_window: 200000, max_output_tokens: 100000, input_price: 1.1, output_price: 4.4 },
    { name: 'o4-mini', display: 'o4 Mini', description: 'Fast reasoning model', context_window: 200000, max_output_tokens: 100000, input_price: 0.6, output_price: 2.4 },
  ],
  claude: [
    { name: 'claude-sonnet-4-5-20250929', display: 'Claude Sonnet 4.5', description: 'Smartest for complex agents & coding', context_window: 200000, max_output_tokens: 8192, input_price: 3.0, output_price: 15.0 },
    { name: 'claude-haiku-4-5-20251001', display: 'Claude Haiku 4.5', description: 'Fastest with near-frontier intelligence', context_window: 200000, max_output_tokens: 8192, input_price: 1.0, output_price: 5.0 },
    { name: 'claude-opus-4-1-20250805', display: 'Claude Opus 4.1', description: 'Exceptional for specialized reasoning', context_window: 200000, max_output_tokens: 8192, input_price: 15.0, output_price: 75.0 },
    { name: 'claude-sonnet-4-20250514', display: 'Claude Sonnet 4', description: 'Previous generation sonnet', context_window: 200000, max_output_tokens: 8192, input_price: 3.0, output_price: 15.0 },
  ],
  deepseek: [
    { name: 'deepseek-chat', display: 'DeepSeek V3.2', description: 'Latest chat model, 128K context', context_window: 128000, max_output_tokens: 8192, input_price: 0.27, output_price: 1.1 },
    { name: 'deepseek-reasoner', display: 'DeepSeek R1', description: 'Reasoning model with <think> tags', context_window: 128000, max_output_tokens: 65536, input_price: 0.55, output_price: 2.19 },
  ],
  gemini: [
    { name: 'gemini-2.5-pro', display: 'Gemini 2.5 Pro', description: 'State-of-the-art thinking model', context_window: 2097152, max_output_tokens: 8192, input_price: 1.25, output_price: 10.0 },
    { name: 'gemini-2.5-flash', display: 'Gemini 2.5 Flash', description: 'Fast adaptive thinking', context_window: 1048576, max_output_tokens: 8192, input_price: 0.3, output_price: 2.5 },
    { name: 'gemini-2.5-flash-lite', display: 'Gemini 2.5 Flash Lite', description: 'Fastest and most cost-efficient', context_window: 1048576, max_output_tokens: 8192, input_price: 0.1, output_price: 0.4 },
    { name: 'gemini-2.0-flash', display: 'Gemini 2.0 Flash', description: '1M token context', context_window: 1048576, max_output_tokens: 8192, input_price: 0.1, output_price: 0.4 },
  ],
  zhipu: [
    { name: 'glm-4.5', display: 'GLM-4.5', description: '355B MoE, best for agents', context_window: 128000, max_output_tokens: 4096, input_price: 0.11, output_price: 0.28 },
    { name: 'glm-4.5-air', display: 'GLM-4.5 Air', description: '106B lightweight version', context_window: 128000, max_output_tokens: 4096, input_price: 0.11, output_price: 0.28 },
    { name: 'glm-z1-airx', display: 'GLM-Z1 AirX', description: 'Fast inference model', context_window: 128000, max_output_tokens: 4096, input_price: 0.11, output_price: 0.28 },
    { name: 'glm-4-plus', display: 'GLM-4 Plus', description: 'Enhanced GLM-4', context_window: 128000, max_output_tokens: 4096, input_price: 0.5, output_price: 0.5 },
    { name: 'glm-4-flash', display: 'GLM-4 Flash', description: 'Ultra-fast, free tier', context_window: 128000, max_output_tokens: 4096, input_price: 0.0, output_price: 0.0 },
  ],
  moonshot: [
    { name: 'kimi-k2-instruct', display: 'Kimi K2 Instruct', description: '1T params, 256K context', context_window: 256000, max_output_tokens: 8192, input_price: 0.15, output_price: 2.5 },
    { name: 'kimi-k2-thinking', display: 'Kimi K2 Thinking', description: 'Advanced reasoning', context_window: 256000, max_output_tokens: 8192, input_price: 0.15, output_price: 2.5 },
    { name: 'moonshot-v1-128k', display: 'Moonshot v1 128K', description: '128K context window', context_window: 128000, max_output_tokens: 4096, input_price: 0.5, output_price: 0.5 },
    { name: 'moonshot-v1-32k', display: 'Moonshot v1 32K', description: '32K context window', context_window: 32000, max_output_tokens: 4096, input_price: 0.5, output_price: 0.5 },
  ],
  ollama: [
    { name: 'qwen2.5:latest', display: 'Qwen 2.5', description: 'Recommended for translation', context_window: 128000, max_output_tokens: 8192, input_price: 0.0, output_price: 0.0 },
    { name: 'qwen2.5:14b-instruct', display: 'Qwen2.5 14B', description: 'Better quality', context_window: 128000, max_output_tokens: 8192, input_price: 0.0, output_price: 0.0 },
    { name: 'llama3.3:latest', display: 'Llama 3.3', description: 'Meta latest model', context_window: 128000, max_output_tokens: 8192, input_price: 0.0, output_price: 0.0 },
    { name: 'deepseek-r1:latest', display: 'DeepSeek R1', description: 'Local reasoning', context_window: 128000, max_output_tokens: 8192, input_price: 0.0, output_price: 0.0 },
    { name: 'gemma3:latest', display: 'Gemma 3', description: 'Google lightweight', context_window: 8192, max_output_tokens: 8192, input_price: 0.0, output_price: 0.0 },
    { name: 'mistral:latest', display: 'Mistral', description: 'Fast and efficient', context_window: 32000, max_output_tokens: 8192, input_price: 0.0, output_price: 0.0 },
  ],
}

function ModelDialog({
  model,
  providers,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  model: AIModelConfig | null
  providers: string[]
  onClose: () => void
  onSubmit: (data: AIModelConfigCreate | AIModelConfigUpdate) => void
  isSubmitting: boolean
}) {
  const { t } = useTranslation()
  const [formData, setFormData] = useState<Partial<AIModelConfigCreate>>({
    provider_name: model?.provider_name || '',
    model_name: model?.model_name || '',
    display_name: model?.display_name || '',
    is_enabled: model?.is_enabled ?? true,
    model_type: model?.model_type || 'chat',
    context_window: model?.context_window || undefined,
    max_output_tokens: model?.max_output_tokens || undefined,
    input_price: model?.input_price || undefined,
    output_price: model?.output_price || undefined,
    pricing_notes: model?.pricing_notes || '',
    description: model?.description || '',
    tags: model?.tags || '',
    is_default: model?.is_default || false,
    priority: model?.priority || 0,
  })
  const [useCustomModel, setUseCustomModel] = useState(
    !model && formData.provider_name ? !RECOMMENDED_MODELS[formData.provider_name] : false,
  )
  const [useCustomPrice, setUseCustomPrice] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit(formData as AIModelConfigCreate | AIModelConfigUpdate)
  }

  // Handle provider change - reset model selection
  const handleProviderChange = (providerName: string) => {
    const hasRecommended = RECOMMENDED_MODELS[providerName]
    setFormData({
      ...formData,
      provider_name: providerName,
      model_name: '',
      display_name: '',
      context_window: undefined,
      max_output_tokens: undefined,
      input_price: undefined,
      output_price: undefined,
    })
    setUseCustomModel(!hasRecommended)
    setUseCustomPrice(false)
  }

  // Handle selecting a recommended model
  const handleRecommendedModelSelect = (modelInfo: RecommendedModel) => {
    setFormData({
      ...formData,
      model_name: modelInfo.name,
      display_name: modelInfo.display,
      description: modelInfo.description,
      context_window: modelInfo.context_window,
      max_output_tokens: modelInfo.max_output_tokens,
      input_price: modelInfo.input_price,
      output_price: modelInfo.output_price,
    })
  }

  const recommendedModels = formData.provider_name
    ? RECOMMENDED_MODELS[formData.provider_name] || []
    : []

  // Distinct provider list (existing + known)
  const knownProviders = ['openai', 'deepseek', 'claude', 'gemini', 'ollama', 'zhipu', 'moonshot']
  const providerOptions = Array.from(new Set([...providers, ...knownProviders]))

  const priceReadOnly = !useCustomPrice && !model

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="space-y-4">
          <DialogHeader>
            <DialogTitle>
              {model ? t('aiModels.editTitle') : t('aiModels.addTitle')}
            </DialogTitle>
          </DialogHeader>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Provider */}
            <div className="space-y-2">
              <Label htmlFor="model-provider">{t('aiModels.selectProvider')} *</Label>
              <Select
                value={formData.provider_name || ''}
                onValueChange={handleProviderChange}
                disabled={!!model}
              >
                <SelectTrigger id="model-provider">
                  <SelectValue placeholder={t('common.select')} />
                </SelectTrigger>
                <SelectContent>
                  {providerOptions.map((p) => (
                    <SelectItem key={p} value={p}>
                      {p}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Model Name - Recommended or Custom */}
            <div className="sm:col-span-2 space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="model-name">{t('models.modelName')} *</Label>
                {!model && recommendedModels.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setUseCustomModel(!useCustomModel)}
                    className="text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
                  >
                    {useCustomModel
                      ? t('aiModels.useRecommended', 'Use Recommended')
                      : t('aiModels.useCustom', 'Use Custom')}
                  </button>
                )}
              </div>

              {!model && !useCustomModel && recommendedModels.length > 0 ? (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {recommendedModels.map((modelInfo) => {
                    const isSelected = formData.model_name === modelInfo.name
                    return (
                      <button
                        key={modelInfo.name}
                        type="button"
                        onClick={() => handleRecommendedModelSelect(modelInfo)}
                        className={cn(
                          'p-3 rounded-md border text-left transition-colors',
                          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                          isSelected
                            ? 'border-primary bg-primary/10'
                            : 'border-border hover:border-primary/50 hover:bg-accent/30',
                        )}
                      >
                        <p className="font-medium text-sm">{modelInfo.display}</p>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {modelInfo.description}
                        </p>
                      </button>
                    )
                  })}
                </div>
              ) : (
                <Input
                  id="model-name"
                  required
                  disabled={!!model}
                  value={formData.model_name || ''}
                  onChange={(e) =>
                    setFormData({ ...formData, model_name: e.target.value })
                  }
                  placeholder={t('aiModels.modelNamePlaceholder')}
                />
              )}
            </div>

            {/* Display Name */}
            <div className="space-y-2">
              <Label htmlFor="model-display-name">
                {t('models.modelName')} ({t('aiModels.display')}) *
              </Label>
              <Input
                id="model-display-name"
                required
                value={formData.display_name || ''}
                onChange={(e) =>
                  setFormData({ ...formData, display_name: e.target.value })
                }
                placeholder={t('aiModels.displayNamePlaceholder')}
              />
            </div>

            {/* Context Window */}
            <div className="space-y-2">
              <Label htmlFor="model-context-window">{t('aiModels.contextWindow')}</Label>
              <Input
                id="model-context-window"
                type="number"
                value={formData.context_window || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    context_window: e.target.value ? parseInt(e.target.value, 10) : undefined,
                  })
                }
                placeholder={t('aiModels.inputPlaceholder')}
              />
            </div>

            {/* Max Output Tokens */}
            <div className="space-y-2">
              <Label htmlFor="model-max-output-tokens">
                {t('aiModels.maxOutputTokens')}
              </Label>
              <Input
                id="model-max-output-tokens"
                type="number"
                value={formData.max_output_tokens || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_output_tokens: e.target.value
                      ? parseInt(e.target.value, 10)
                      : undefined,
                  })
                }
                placeholder={t('aiModels.outputPlaceholder')}
              />
            </div>

            {/* Input Price */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="model-input-price">
                  {t('aiModels.inputPrice')} ($/1M tokens)
                </Label>
                {!model && (
                  <button
                    type="button"
                    onClick={() => setUseCustomPrice(!useCustomPrice)}
                    className="text-xs text-primary hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 rounded"
                  >
                    {useCustomPrice
                      ? t('aiModels.useRecommended', 'Use Recommended')
                      : t('aiModels.useCustom', 'Use Custom')}
                  </button>
                )}
              </div>
              <Input
                id="model-input-price"
                type="number"
                step="0.01"
                min="0"
                value={formData.input_price ?? ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    input_price: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
                placeholder={t('aiModels.inputPricePlaceholder')}
                readOnly={priceReadOnly}
                className={cn(priceReadOnly && 'bg-muted/50 cursor-not-allowed')}
              />
            </div>

            {/* Output Price */}
            <div className="space-y-2">
              <Label htmlFor="model-output-price">
                {t('aiModels.outputPrice')} ($/1M tokens)
              </Label>
              <Input
                id="model-output-price"
                type="number"
                step="0.01"
                min="0"
                value={formData.output_price ?? ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    output_price: e.target.value ? parseFloat(e.target.value) : undefined,
                  })
                }
                placeholder={t('aiModels.outputPricePlaceholder')}
                readOnly={priceReadOnly}
                className={cn(priceReadOnly && 'bg-muted/50 cursor-not-allowed')}
              />
            </div>
          </div>

          {/* Description */}
          <div className="space-y-2">
            <Label htmlFor="model-description">{t('aiModels.description')}</Label>
            <Textarea
              id="model-description"
              value={formData.description || ''}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={2}
              placeholder={t('aiModels.description')}
            />
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <Label htmlFor="model-tags">{t('aiModels.tags')}</Label>
            <Input
              id="model-tags"
              value={formData.tags || ''}
              onChange={(e) => setFormData({ ...formData, tags: e.target.value })}
              placeholder='["fast", "cheap", "recommended"]'
            />
          </div>

          {/* Checkboxes */}
          <div className="flex flex-wrap gap-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={!!formData.is_enabled}
                onChange={(e) =>
                  setFormData({ ...formData, is_enabled: e.target.checked })
                }
              />
              <span className="text-sm">{t('aiModels.enabled')}</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                className="h-4 w-4 rounded border-input accent-primary"
                checked={!!formData.is_default}
                onChange={(e) =>
                  setFormData({ ...formData, is_default: e.target.checked })
                }
              />
              <span className="text-sm">{t('jobs.default')}</span>
            </label>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSubmitting}
            >
              {t('aiModels.cancel')}
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {model ? t('aiModels.save') : t('aiModels.create')}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
