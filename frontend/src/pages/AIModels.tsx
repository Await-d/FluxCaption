/**
 * AI Model Configuration Management Page
 *
 * Allows administrators to configure available models for each AI provider
 * with pricing information.
 */

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Plus, Edit2, Trash2, DollarSign, Check, X, Loader2 } from 'lucide-react';
import * as aiModelsApi from '../api/aiModels';
import type { AIModelConfig, AIModelConfigCreate, AIModelConfigUpdate } from '../api/aiModels';
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

  // Create model mutation
  const createMutation = useMutation({
    mutationFn: aiModelsApi.createModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] });
      setShowCreateDialog(false);
      toast.success('Model configuration created successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to create model: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Update model mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AIModelConfigUpdate }) =>
      aiModelsApi.updateModel(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] });
      setEditingModel(null);
      toast.success('Model configuration updated successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to update model: ${error.response?.data?.detail || error.message}`);
    },
  });

  // Delete model mutation
  const deleteMutation = useMutation({
    mutationFn: aiModelsApi.deleteModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-models'] });
      toast.success('Model configuration deleted successfully');
    },
    onError: (error: any) => {
      toast.error(`Failed to delete model: ${error.response?.data?.detail || error.message}`);
    },
  });

  const handleDelete = (model: AIModelConfig) => {
    if (confirm(`确定要删除模型 "${model.display_name}" 吗？`)) {
      deleteMutation.mutate(model.id);
    }
  };

  // Get unique providers
  const providers = Array.from(
    new Set(modelsData?.models.map(m => m.provider_name) || [])
  ).sort();

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">AI Model Configuration</h1>
          <p className="text-muted-foreground mt-1">
            Configure available models and pricing for each AI provider
          </p>
        </div>
        <button
          onClick={() => setShowCreateDialog(true)}
          className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
        >
          <Plus className="h-4 w-4" />
          Add Model
        </button>
      </div>

      {/* Provider Filter */}
      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => setSelectedProvider(null)}
          className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
            selectedProvider === null
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted hover:bg-muted/80'
          }`}
        >
          All Providers
        </button>
        {providers.map(provider => (
          <button
            key={provider}
            onClick={() => setSelectedProvider(provider)}
            className={`px-3 py-1.5 rounded-md text-sm transition-colors ${
              selectedProvider === provider
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted hover:bg-muted/80'
            }`}
          >
            {provider}
          </button>
        ))}
      </div>

      {/* Models List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
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
        <div className="text-center py-12 text-muted-foreground">
          <p>No models configured yet</p>
          <p className="text-sm mt-1">Click "Add Model" to create your first model configuration</p>
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
                Default
              </span>
            )}
          </div>
          <p className="text-sm text-muted-foreground truncate mt-0.5">
            {model.provider_name}:{model.model_name}
          </p>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={onEdit}
            className="p-1.5 hover:bg-muted rounded transition-colors"
            title="Edit"
          >
            <Edit2 className="h-4 w-4" />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-destructive/10 hover:text-destructive rounded transition-colors"
            title="Delete"
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
            <span>Enabled</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 text-muted-foreground">
            <X className="h-3.5 w-3.5" />
            <span>Disabled</span>
          </div>
        )}
        {model.model_type && (
          <span className="px-2 py-0.5 rounded bg-muted text-xs">
            {model.model_type}
          </span>
        )}
      </div>

      {/* Specs */}
      {(model.context_window || model.max_output_tokens) && (
        <div className="text-xs text-muted-foreground space-y-1">
          {model.context_window && (
            <div>Context: {model.context_window.toLocaleString()} tokens</div>
          )}
          {model.max_output_tokens && (
            <div>Max Output: {model.max_output_tokens.toLocaleString()} tokens</div>
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
              <div className="text-green-600 font-medium">Free</div>
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
          Used {model.usage_count} times
        </div>
      )}
    </div>
  );
}

// Model Dialog Component
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

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSubmit(formData as any);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-background rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <h2 className="text-xl font-bold">
            {model ? 'Edit Model Configuration' : 'Add Model Configuration'}
          </h2>

          <div className="grid grid-cols-2 gap-4">
            {/* Provider */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Provider *
              </label>
              <select
                required
                disabled={!!model}
                value={formData.provider_name}
                onChange={(e) =>
                  setFormData({ ...formData, provider_name: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="">Select provider</option>
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

            {/* Model Name */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Model Name *
              </label>
              <input
                required
                disabled={!!model}
                type="text"
                value={formData.model_name}
                onChange={(e) =>
                  setFormData({ ...formData, model_name: e.target.value })
                }
                placeholder="e.g., gpt-4o"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            {/* Display Name */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Display Name *
              </label>
              <input
                required
                type="text"
                value={formData.display_name}
                onChange={(e) =>
                  setFormData({ ...formData, display_name: e.target.value })
                }
                placeholder="e.g., GPT-4o"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            {/* Model Type */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Model Type
              </label>
              <select
                value={formData.model_type}
                onChange={(e) =>
                  setFormData({ ...formData, model_type: e.target.value })
                }
                className="w-full px-3 py-2 border rounded-md"
              >
                <option value="chat">Chat</option>
                <option value="completion">Completion</option>
                <option value="reasoning">Reasoning</option>
                <option value="translation">Translation</option>
              </select>
            </div>

            {/* Context Window */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Context Window
              </label>
              <input
                type="number"
                value={formData.context_window || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    context_window: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                placeholder="e.g., 128000"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            {/* Max Output Tokens */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Max Output Tokens
              </label>
              <input
                type="number"
                value={formData.max_output_tokens || ''}
                onChange={(e) =>
                  setFormData({
                    ...formData,
                    max_output_tokens: e.target.value ? parseInt(e.target.value) : undefined,
                  })
                }
                placeholder="e.g., 4096"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            {/* Input Price */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Input Price ($/1M tokens)
              </label>
              <input
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
                placeholder="e.g., 2.50"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>

            {/* Output Price */}
            <div>
              <label className="block text-sm font-medium mb-1">
                Output Price ($/1M tokens)
              </label>
              <input
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
                placeholder="e.g., 10.00"
                className="w-full px-3 py-2 border rounded-md"
              />
            </div>
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Description
            </label>
            <textarea
              value={formData.description}
              onChange={(e) =>
                setFormData({ ...formData, description: e.target.value })
              }
              rows={2}
              placeholder="Model description..."
              className="w-full px-3 py-2 border rounded-md"
            />
          </div>

          {/* Tags */}
          <div>
            <label className="block text-sm font-medium mb-1">
              Tags (JSON array)
            </label>
            <input
              type="text"
              value={formData.tags}
              onChange={(e) =>
                setFormData({ ...formData, tags: e.target.value })
              }
              placeholder='["fast", "cheap", "recommended"]'
              className="w-full px-3 py-2 border rounded-md"
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
              <span className="text-sm">Enabled</span>
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formData.is_default}
                onChange={(e) =>
                  setFormData({ ...formData, is_default: e.target.checked })
                }
              />
              <span className="text-sm">Set as Default</span>
            </label>
          </div>

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-4 border-t">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 border rounded-md hover:bg-muted transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {isSubmitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {model ? 'Update' : 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
