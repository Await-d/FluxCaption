/**
 * AI Model Configuration Management Page
 *
 * Allows administrators to configure available models for each AI provider
 * with pricing information.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Edit2, Trash2, DollarSign, Check, X, Loader2 } from 'lucide-react';
import * as aiModelsApi from '../api/aiModels';
import type { AIModelConfig, AIModelConfigCreate, AIModelConfigUpdate } from '../api/aiModels';
import { aiProviderApi } from '../api/aiProviders';
import { toast } from 'sonner';

export default function AIModelsPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedProvider, setSelectedProvider] = useState<string | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [editingModel, setEditingModel] = useState<AIModelConfig | null>(null);

  // Fetch all models
  const { data: modelsData, isLoading } = useQuery({
    queryKey: ['ai-models', selectedProvider],
    queryFn: () => aiModelsApi.listModels({
      provider: selectedProvider || undefined,
      page: 1,
      page_size: 100,
    }),
  });

  // Fetch AI providers
  const { data: providersData } = useQuery({
    queryKey: ['ai-providers'],
    queryFn: () => aiProviderApi.listProviders(false),
  });

  // Create model mutation
  const createMutation = useMutation({
    mutationFn: aiModelsApi.createModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] });
      setShowCreateDialog(false);
      toast.success(t('common.success'));
    },
    onError: () => {
      toast.error(t('common.error'));
    },
  });

  // Update model mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AIModelConfigUpdate }) =>
      aiModelsApi.updateModel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] });
      setEditingModel(null);
      toast.success(t('common.success'));
    },
    onError: () => {
      toast.error(t('common.error'));
    },
  });

  // Delete model mutation
  const deleteMutation = useMutation({
    mutationFn: aiModelsApi.deleteModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] });
      toast.success(t('common.success'));
    },
    onError: () => {
      toast.error(t('common.error'));
    },
  });

  const handleDelete = (model: AIModelConfig) => {
    if (confirm(`${t('common.delete')} "${model.display_name}"?`)) {
      deleteMutation.mutate(model.id);
    }
  };

  // Get providers from AI Providers API
  const providers = (providersData || [])
    .map(p => p.provider_name)
    .sort();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{t('nav.aiModels')}</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            {t('aiModels.descHeader')}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateDialog(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          {t('aiModels.addButton')}
        </button>
      </div>

      {/* Provider Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          type="button"
          onClick={() => setSelectedProvider(null)}
          className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
            selectedProvider === null
              ? 'bg-primary text-primary-foreground'
              : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          {t('aiModels.allProviders')}
        </button>
        {providers.map(provider => (
          <button
            type="button"
            key={provider}
            onClick={() => setSelectedProvider(provider)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
              selectedProvider === provider
                ? 'bg-primary text-primary-foreground'
                : 'bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            {provider}
          </button>
        ))}
      </div>

      {/* Models List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-600 dark:text-gray-400" />
        </div>
      ) : modelsData && modelsData.models.length > 0 ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modelsData.models.map(model => (
            <ModelCard
              key={model.id}
              model={model}
              onEdit={() => setEditingModel(model)}
              onDelete={() => handleDelete(model)}
            />
          ))}
        </div>
      ) : (
        <div className="text-center py-12 text-gray-600 dark:text-gray-400">
          <p>{t('aiModels.noModels')}</p>
          <p className="text-sm mt-1">{t('aiModels.clickToCreate')}</p>
        </div>
      )}

      {/* Create/Edit Dialog */}
      {(showCreateDialog || editingModel) && (
        <ModelDialog
          model={editingModel}
          providers={providers}
          onClose={() => {
            setShowCreateDialog(false);
            setEditingModel(null);
          }}
          onSubmit={(data) => {
            if (editingModel) {
              updateMutation.mutate({ id: editingModel.id, data });
            } else {
              createMutation.mutate(data as AIModelConfigCreate);
            }
          }}
          isSubmitting={createMutation.isPending || updateMutation.isPending}
        />
      )}
    </div>
  );
}

// Model Card Component
function ModelCard({
  model,
  onEdit,
  onDelete,
}: {
  model: AIModelConfig;
  onEdit: () => void;
  onDelete: () => void;
}) {
  const { t } = useTranslation();
  const tags = model.tags ? JSON.parse(model.tags) : [];

  return (
    <div className="border rounded-lg p-4 space-y-3 hover:border-primary/50 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h3 className="font-semibold truncate">{model.display_name}</h3>
            {model.is_default && (
              <span className="px-2 py-0.5 text-xs font-medium rounded bg-primary/20 text-primary">
                {t('jobs.default')}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 truncate mt-0.5">
            {model.provider_name}:{model.model_name}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={onEdit}
            className="p-1.5 hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
            title={t('common.edit')}
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={onDelete}
            className="p-1.5 hover:bg-destructive/10 hover:text-destructive rounded transition-colors"
            title={t('common.delete')}
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center gap-2 text-sm">
        {model.is_enabled ? (
          <div className="flex items-center gap-1.5 text-green-600">
            <Check className="h-3.5 w-3.5" />
            <span>{t('aiModels.enabled')}</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-gray-600 dark:text-gray-400">
            <X className="h-3.5 w-3.5" />
            <span>{t('aiModels.disabled')}</span>
          </div>
        )}
      </div>

      {/* Specs */}
      {(model.context_window || model.max_output_tokens) && (
        <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
          {model.context_window && (
            <div>{t('aiModels.contextLabel')}: {model.context_window.toLocaleString()} {t('aiModels.tokens')}</div>
          )}
          {model.max_output_tokens && (
            <div>{t('aiModels.maxOutputLabel')}: {model.max_output_tokens.toLocaleString()} {t('aiModels.tokens')}</div>
          )}
        </div>
      )}

      {/* Pricing */}
      {(model.input_price !== null || model.output_price !== null) && (
        <div className="flex items-start gap-2 p-2 rounded bg-gray-100/50 dark:bg-gray-700/50">
          <DollarSign className="h-4 w-4 mt-0.5 text-gray-600 dark:text-gray-400 flex-shrink-0" />
          <div className="text-xs space-y-0.5 flex-1">
            {model.input_price !== null && (
              <div>Input: ${model.input_price}/1M tokens</div>
            )}
            {model.output_price !== null && (
              <div>Output: ${model.output_price}/1M tokens</div>
            )}
            {model.input_price === 0 && model.output_price === 0 && (
              <div className="text-green-600 font-medium">{t('common.free', 'Free')}</div>
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
        <div className="text-xs text-gray-600 dark:text-gray-400 pt-2 border-t">
          {t('aiModels.usedTimes', { count: model.usage_count })}
        </div>
      )}
    </div>
  );
}

// Model Dialog Component
// Recommended models for each provider (Updated November 2025)
interface RecommendedModel {
  name: string;
  display: string;
  description: string;
  context_window?: number;
  max_output_tokens?: number;
  input_price?: number;
  output_price?: number;
}

const RECOMMENDED_MODELS: Record<string, RecommendedModel[]> = {
  openai: [
    { name: 'gpt-4.1', display: 'GPT-4.1', description: '1M context, smartest non-reasoning', context_window: 1048576, max_output_tokens: 32768, input_price: 2.00, output_price: 8.00 },
    { name: 'gpt-4.1-mini', display: 'GPT-4.1 Mini', description: 'Cost-effective variant', context_window: 1048576, max_output_tokens: 32768, input_price: 0.10, output_price: 0.40 },
    { name: 'gpt-4o', display: 'GPT-4o', description: 'General-purpose multimodal', context_window: 128000, max_output_tokens: 16384, input_price: 2.50, output_price: 10.00 },
    { name: 'gpt-4o-mini', display: 'GPT-4o Mini', description: 'Fast and affordable', context_window: 128000, max_output_tokens: 16384, input_price: 0.15, output_price: 0.60 },
    { name: 'o3-mini', display: 'o3 Mini', description: 'Cost-efficient reasoning', context_window: 200000, max_output_tokens: 100000, input_price: 1.10, output_price: 4.40 },
    { name: 'o4-mini', display: 'o4 Mini', description: 'Fast reasoning model', context_window: 200000, max_output_tokens: 100000, input_price: 0.60, output_price: 2.40 },
  ],
  claude: [
    { name: 'claude-sonnet-4-5-20250929', display: 'Claude Sonnet 4.5', description: 'Smartest for complex agents & coding', context_window: 200000, max_output_tokens: 8192, input_price: 3.00, output_price: 15.00 },
    { name: 'claude-haiku-4-5-20251001', display: 'Claude Haiku 4.5', description: 'Fastest with near-frontier intelligence', context_window: 200000, max_output_tokens: 8192, input_price: 1.00, output_price: 5.00 },
    { name: 'claude-opus-4-1-20250805', display: 'Claude Opus 4.1', description: 'Exceptional for specialized reasoning', context_window: 200000, max_output_tokens: 8192, input_price: 15.00, output_price: 75.00 },
    { name: 'claude-sonnet-4-20250514', display: 'Claude Sonnet 4', description: 'Previous generation sonnet', context_window: 200000, max_output_tokens: 8192, input_price: 3.00, output_price: 15.00 },
  ],
  deepseek: [
    { name: 'deepseek-chat', display: 'DeepSeek V3.2', description: 'Latest chat model, 128K context', context_window: 128000, max_output_tokens: 8192, input_price: 0.27, output_price: 1.10 },
    { name: 'deepseek-reasoner', display: 'DeepSeek R1', description: 'Reasoning model with <think> tags', context_window: 128000, max_output_tokens: 65536, input_price: 0.55, output_price: 2.19 },
  ],
  gemini: [
    { name: 'gemini-2.5-pro', display: 'Gemini 2.5 Pro', description: 'State-of-the-art thinking model', context_window: 2097152, max_output_tokens: 8192, input_price: 1.25, output_price: 10.00 },
    { name: 'gemini-2.5-flash', display: 'Gemini 2.5 Flash', description: 'Fast adaptive thinking', context_window: 1048576, max_output_tokens: 8192, input_price: 0.30, output_price: 2.50 },
    { name: 'gemini-2.5-flash-lite', display: 'Gemini 2.5 Flash Lite', description: 'Fastest and most cost-efficient', context_window: 1048576, max_output_tokens: 8192, input_price: 0.10, output_price: 0.40 },
    { name: 'gemini-2.0-flash', display: 'Gemini 2.0 Flash', description: '1M token context', context_window: 1048576, max_output_tokens: 8192, input_price: 0.10, output_price: 0.40 },
  ],
  zhipu: [
    { name: 'glm-4.5', display: 'GLM-4.5', description: '355B MoE, best for agents', context_window: 128000, max_output_tokens: 4096, input_price: 0.11, output_price: 0.28 },
    { name: 'glm-4.5-air', display: 'GLM-4.5 Air', description: '106B lightweight version', context_window: 128000, max_output_tokens: 4096, input_price: 0.11, output_price: 0.28 },
    { name: 'glm-z1-airx', display: 'GLM-Z1 AirX', description: 'Fast inference model', context_window: 128000, max_output_tokens: 4096, input_price: 0.11, output_price: 0.28 },
    { name: 'glm-4-plus', display: 'GLM-4 Plus', description: 'Enhanced GLM-4', context_window: 128000, max_output_tokens: 4096, input_price: 0.50, output_price: 0.50 },
    { name: 'glm-4-flash', display: 'GLM-4 Flash', description: 'Ultra-fast, free tier', context_window: 128000, max_output_tokens: 4096, input_price: 0.00, output_price: 0.00 },
  ],
  moonshot: [
    { name: 'kimi-k2-instruct', display: 'Kimi K2 Instruct', description: '1T params, 256K context', context_window: 256000, max_output_tokens: 8192, input_price: 0.15, output_price: 2.50 },
    { name: 'kimi-k2-thinking', display: 'Kimi K2 Thinking', description: 'Advanced reasoning', context_window: 256000, max_output_tokens: 8192, input_price: 0.15, output_price: 2.50 },
    { name: 'moonshot-v1-128k', display: 'Moonshot v1 128K', description: '128K context window', context_window: 128000, max_output_tokens: 4096, input_price: 0.50, output_price: 0.50 },
    { name: 'moonshot-v1-32k', display: 'Moonshot v1 32K', description: '32K context window', context_window: 32000, max_output_tokens: 4096, input_price: 0.50, output_price: 0.50 },
  ],
  ollama: [
    { name: 'qwen2.5:latest', display: 'Qwen 2.5', description: 'Recommended for translation', context_window: 128000, max_output_tokens: 8192, input_price: 0.00, output_price: 0.00 },
    { name: 'qwen2.5:14b-instruct', display: 'Qwen2.5 14B', description: 'Better quality', context_window: 128000, max_output_tokens: 8192, input_price: 0.00, output_price: 0.00 },
    { name: 'llama3.3:latest', display: 'Llama 3.3', description: 'Meta latest model', context_window: 128000, max_output_tokens: 8192, input_price: 0.00, output_price: 0.00 },
    { name: 'deepseek-r1:latest', display: 'DeepSeek R1', description: 'Local reasoning', context_window: 128000, max_output_tokens: 8192, input_price: 0.00, output_price: 0.00 },
    { name: 'gemma3:latest', display: 'Gemma 3', description: 'Google lightweight', context_window: 8192, max_output_tokens: 8192, input_price: 0.00, output_price: 0.00 },
    { name: 'mistral:latest', display: 'Mistral', description: 'Fast and efficient', context_window: 32000, max_output_tokens: 8192, input_price: 0.00, output_price: 0.00 },
  ],
};

function ModelDialog({
  model,
  providers,
  onClose,
  onSubmit,
  isSubmitting,
}: {
  model: AIModelConfig | null;
  providers: string[];
  onClose: () => void;
  onSubmit: (data: AIModelConfigCreate | AIModelConfigUpdate) => void;
  isSubmitting: boolean;
}) {
  const { t } = useTranslation();
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
  });
  const [useCustomModel, setUseCustomModel] = useState(!model && formData.provider_name ? !RECOMMENDED_MODELS[formData.provider_name] : false);
  const [useCustomPrice, setUseCustomPrice] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData as AIModelConfigCreate | AIModelConfigUpdate);
  };

  // Handle provider change - reset model selection
  const handleProviderChange = (providerName: string) => {
    const hasRecommended = RECOMMENDED_MODELS[providerName];
    setFormData({
      ...formData,
      provider_name: providerName,
      model_name: '',
      display_name: '',
      context_window: undefined,
      max_output_tokens: undefined,
      input_price: undefined,
      output_price: undefined,
    });
    setUseCustomModel(!hasRecommended);
    setUseCustomPrice(false);
  };

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
    });
  };

  // Get recommended models for current provider
  const recommendedModels = formData.provider_name ? RECOMMENDED_MODELS[formData.provider_name] || [] : [];

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <h2 className="text-xl font-bold text-gray-900 dark:text-white">
            {model ? t('aiModels.editTitle') : t('aiModels.addTitle')}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            {/* Provider */}
            <div>
              <label htmlFor="model-provider" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('aiModels.selectProvider')} *
              </label>
              <select
                id="model-provider"
                required
                disabled={!!model}
                value={formData.provider_name}
                onChange={(e) => handleProviderChange(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">{t('common.select')}</option>
                {providers.map(p => (
                  <option key={p} value={p}>{p}</option>
                ))}
                <option value="openai">openai</option>
                <option value="deepseek">deepseek</option>
                <option value="claude">claude</option>
                <option value="gemini">gemini</option>
                <option value="ollama">ollama</option>
              </select>
            </div>

            {/* Model Name - Recommended or Custom */}
            <div className="col-span-2">
              <div className="flex items-center justify-between mb-2">
                <p className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('models.modelName')} *
                </p>
                {!model && recommendedModels.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setUseCustomModel(!useCustomModel)}
                    className="text-sm text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    {useCustomModel ? t('aiModels.useRecommended', 'Use Recommended') : t('aiModels.useCustom', 'Use Custom')}
                  </button>
                )}
              </div>

              {!model && !useCustomModel && recommendedModels.length > 0 ? (
                /* Recommended Models Grid */
                <div className="grid grid-cols-2 gap-2">
                  {recommendedModels.map((modelInfo) => (
                    <button
                      key={modelInfo.name}
                      type="button"
                      onClick={() => handleRecommendedModelSelect(modelInfo)}
                      className={`p-3 border-2 rounded-lg text-left transition-colors ${
                        formData.model_name === modelInfo.name
                          ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20'
                          : 'border-gray-200 dark:border-gray-700 hover:border-blue-300 dark:hover:border-blue-700'
                      }`}
                    >
                      <p className="font-medium text-sm text-gray-900 dark:text-white">{modelInfo.display}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{modelInfo.description}</p>
                    </button>
                  ))}
                </div>
              ) : (
                /* Custom Model Input */
                <input
                  id="model-name"
                  required
                  disabled={!!model}
                  type="text"
                  value={formData.model_name}
                  onChange={(e) =>
                    setFormData({ ...formData, model_name: e.target.value })
                  }
                  placeholder={t('aiModels.modelNamePlaceholder')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              )}
            </div>

            {/* Display Name */}
            <div>
              <label htmlFor="model-display-name" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('models.modelName')} ({t('aiModels.display')}) *
              </label>
              <input
                id="model-display-name"
                required
                type="text"
                value={formData.display_name}
                onChange={(e) =>
                  setFormData({ ...formData, display_name: e.target.value })
                }
                placeholder={t('aiModels.displayNamePlaceholder')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Context Window */}
            <div>
              <label htmlFor="model-context-window" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('aiModels.contextWindow')}
              </label>
              <input
                id="model-context-window"
                type="number"
                value={formData.context_window || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    context_window: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                placeholder={t('aiModels.inputPlaceholder')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Max Output Tokens */}
            <div>
              <label htmlFor="model-max-output-tokens" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('aiModels.maxOutputTokens')}
              </label>
              <input
                id="model-max-output-tokens"
                type="number"
                value={formData.max_output_tokens || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_output_tokens: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                placeholder={t('aiModels.outputPlaceholder')}
                className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>

            {/* Input Price */}
            <div>
              <div className="flex items-center justify-between mb-1">
                <label htmlFor="model-input-price" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('aiModels.inputPrice')} ($/1M tokens)
                </label>
                {!model && (
                  <button
                    type="button"
                    onClick={() => setUseCustomPrice(!useCustomPrice)}
                    className="text-xs text-blue-500 hover:text-blue-600 dark:text-blue-400 dark:hover:text-blue-300"
                  >
                    {useCustomPrice ? t('aiModels.useRecommended', 'Use Recommended') : t('aiModels.useCustom', 'Use Custom')}
                  </button>
                )}
              </div>
              <input
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
                readOnly={!useCustomPrice && !model}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  !useCustomPrice && !model ? 'bg-gray-50 dark:bg-gray-800 cursor-not-allowed' : ''
                }`}
              />
            </div>

            {/* Output Price */}
            <div>
              <label htmlFor="model-output-price" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                {t('aiModels.outputPrice')} ($/1M tokens)
              </label>
              <input
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
                readOnly={!useCustomPrice && !model}
                className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent ${
                  !useCustomPrice && !model ? 'bg-gray-50 dark:bg-gray-800 cursor-not-allowed' : ''
                }`}
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label htmlFor="model-description" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('aiModels.description')}
            </label>
            <textarea
              id="model-description"
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={2}
              placeholder={t('aiModels.description')}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Tags */}
          <div>
            <label htmlFor="model-tags" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
              {t('aiModels.tags')}
            </label>
            <input
              id="model-tags"
              type="text"
              value={formData.tags}
              onChange={(e) =>
                setFormData({ ...formData, tags: e.target.value })
              }
              placeholder='["fast", "cheap", "recommended"]'
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>

          {/* Checkboxes */}
          <div className="flex gap-4">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_enabled}
                onChange={(e) =>
                  setFormData({ ...formData, is_enabled: e.target.checked })
                }
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">{t('aiModels.enabled')}</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(e) =>
                  setFormData({ ...formData, is_default: e.target.checked })
                }
              />
              <span className="text-sm text-gray-700 dark:text-gray-300">{t('jobs.default')}</span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t border-gray-200 dark:border-gray-700">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            >
              {t('aiModels.cancel')}
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {model ? t('aiModels.save') : t('aiModels.create')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
