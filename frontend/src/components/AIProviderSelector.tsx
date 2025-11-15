/**
 * AI Provider Selector Component
 *
 * Allows users to select AI provider and model for translation tasks.
 * Displays enabled providers with their health status and configured models with pricing.
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Cloud, Check, AlertCircle, Loader2, DollarSign, ChevronDown } from 'lucide-react';
import * as aiProviderApi from '../api/aiProviders';
import * as aiModelsApi from '../api/aiModels';

interface AIProviderSelectorProps {
  value?: {
    provider?: string;
    model?: string;
  };
  onChange: (selection: { provider?: string; model?: string }) => void;
  disabled?: boolean;
}

export function AIProviderSelector({
  value = {},
  onChange,
  disabled = false,
}: AIProviderSelectorProps) {
  const { t } = useTranslation();
  const [selectedProvider, setSelectedProvider] = useState<string | undefined>(
    value.provider
  );
  const [selectedModel, setSelectedModel] = useState<string | undefined>(value.model);

  // Fetch enabled providers
  const { data: providers, isLoading: isLoadingProviders } = useQuery({
    queryKey: ['ai-providers', 'enabled'],
    queryFn: async () => {
      const all = await aiProviderApi.listProviders();
      return all.filter(p => p.is_enabled).sort((a, b) => b.priority - a.priority);
    },
  });

  // Fetch available models for selected provider
  const { data: modelsData, isLoading: isLoadingModels } = useQuery({
    queryKey: ['ai-models', 'provider', selectedProvider],
    queryFn: () => aiModelsApi.listModels({
      provider: selectedProvider,
      enabled_only: true,
      page: 1,
      page_size: 100,
    }),
    enabled: !!selectedProvider,
  });

  // Update selection when value prop changes
  useEffect(() => {
    setSelectedProvider(value.provider);
    setSelectedModel(value.model);
  }, [value]);

  const handleProviderChange = (providerName: string) => {
    const newProvider = providerName === selectedProvider ? undefined : providerName;
    setSelectedProvider(newProvider);
    setSelectedModel(undefined); // Reset model when provider changes
    onChange({ provider: newProvider, model: undefined });
  };

  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newModel = e.target.value || undefined;
    setSelectedModel(newModel);
    onChange({ provider: selectedProvider, model: newModel });
  };

  if (isLoadingProviders) {
    return (
      <div className="space-y-4 opacity-50 pointer-events-none">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>Loading AI providers...</span>
        </div>
      </div>
    );
  }

  if (!providers || providers.length === 0) {
    return (
      <div className="rounded-md border border-warning/50 bg-warning/10 p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-warning flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">No AI Providers Enabled</p>
            <p className="text-xs text-muted-foreground mt-1">
              Please enable at least one AI provider in Settings → AI Providers
            </p>
          </div>
        </div>
      </div>
    );
  }

  const availableModels = modelsData?.models || [];
  const selectedModelData = availableModels.find(m => m.model_name === selectedModel);

  return (
    <div className="space-y-4">
      {/* Provider Selection */}
      <div>
        <label className="text-sm font-medium mb-2 block">
          {t('translate.selectProvider', 'Select AI Provider')}
          <span className="text-muted-foreground ml-2 font-normal">
            (Optional - Auto-selects if not specified)
          </span>
        </label>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {providers.map((provider) => {
            const isSelected = selectedProvider === provider.provider_name;
            const isHealthy = provider.is_healthy;

            return (
              <button
                key={provider.id}
                type="button"
                disabled={disabled || !isHealthy}
                onClick={() => handleProviderChange(provider.provider_name)}
                className={`
                  relative p-3 rounded-lg border-2 transition-all text-left
                  ${
                    isSelected
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50'
                  }
                  ${!isHealthy ? 'opacity-50 cursor-not-allowed' : ''}
                  ${disabled ? 'opacity-50 cursor-not-allowed' : ''}
                `}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Cloud className={`h-4 w-4 flex-shrink-0 ${isSelected ? 'text-primary' : 'text-muted-foreground'}`} />
                      <span className="text-sm font-medium truncate">
                        {provider.display_name}
                      </span>
                    </div>
                    <div className="flex items-center gap-1.5 text-xs">
                      <div
                        className={`h-2 w-2 rounded-full ${
                          isHealthy ? 'bg-green-500' : 'bg-red-500'
                        }`}
                      />
                      <span className="text-muted-foreground">
                        {isHealthy ? 'Healthy' : 'Unhealthy'}
                      </span>
                    </div>
                  </div>
                  {isSelected && (
                    <Check className="h-5 w-5 text-primary flex-shrink-0" />
                  )}
                </div>
                {provider.priority > 5 && (
                  <div className="absolute top-1 right-1">
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded bg-primary/20 text-primary">
                      HIGH
                    </span>
                  </div>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Model Selection (Dropdown) */}
      {selectedProvider && (
        <div>
          <label htmlFor="model-select" className="text-sm font-medium mb-2 block">
            {t('translate.model', 'Translation Model')}
            <span className="text-muted-foreground ml-2 font-normal">
              (Optional - Uses default if not specified)
            </span>
          </label>

          {isLoadingModels ? (
            <div className="flex items-center gap-2 px-3 py-2 border rounded-md">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">Loading models...</span>
            </div>
          ) : availableModels.length > 0 ? (
            <>
              <div className="relative">
                <select
                  id="model-select"
                  value={selectedModel || ''}
                  onChange={handleModelChange}
                  disabled={disabled}
                  className="w-full px-3 py-2 pr-10 border border-border rounded-md bg-background text-foreground focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-50 appearance-none"
                >
                  <option value="">
                    {t('translate.useDefault', 'Use default model')}
                  </option>
                  {availableModels.map(model => (
                    <option key={model.id} value={model.model_name}>
                      {model.display_name}
                      {model.is_default && ' (Default)'}
                      {model.input_price !== null && model.output_price !== null &&
                        ` - $${model.input_price}/$${model.output_price}`
                      }
                      {model.input_price === 0 && model.output_price === 0 && ' - Free'}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
              </div>

              {/* Selected Model Details */}
              {selectedModelData && (
                <div className="mt-2 p-3 rounded-md bg-muted/50 space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1">
                      <p className="text-sm font-medium">{selectedModelData.display_name}</p>
                      {selectedModelData.description && (
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {selectedModelData.description}
                        </p>
                      )}
                    </div>
                    {selectedModelData.is_default && (
                      <span className="px-2 py-0.5 text-xs rounded bg-primary/20 text-primary">
                        Default
                      </span>
                    )}
                  </div>

                  {/* Specs */}
                  {(selectedModelData.context_window || selectedModelData.max_output_tokens) && (
                    <div className="flex gap-4 text-xs text-muted-foreground">
                      {selectedModelData.context_window && (
                        <div>
                          Context: {selectedModelData.context_window.toLocaleString()} tokens
                        </div>
                      )}
                      {selectedModelData.max_output_tokens && (
                        <div>
                          Max Output: {selectedModelData.max_output_tokens.toLocaleString()} tokens
                        </div>
                      )}
                    </div>
                  )}

                  {/* Pricing */}
                  {(selectedModelData.input_price !== null || selectedModelData.output_price !== null) && (
                    <div className="flex items-start gap-2 pt-2 border-t border-border/50">
                      <DollarSign className="h-4 w-4 mt-0.5 text-muted-foreground flex-shrink-0" />
                      <div className="text-xs space-y-0.5">
                        {selectedModelData.input_price !== null && (
                          <div>Input: ${selectedModelData.input_price}/1M tokens</div>
                        )}
                        {selectedModelData.output_price !== null && (
                          <div>Output: ${selectedModelData.output_price}/1M tokens</div>
                        )}
                        {selectedModelData.input_price === 0 && selectedModelData.output_price === 0 && (
                          <div className="text-green-600 font-medium">Free (Local Model)</div>
                        )}
                        {selectedModelData.pricing_notes && (
                          <div className="text-muted-foreground italic mt-1">
                            {selectedModelData.pricing_notes}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Tags */}
                  {selectedModelData.tags && (() => {
                    try {
                      const tags = JSON.parse(selectedModelData.tags);
                      return tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 pt-2 border-t border-border/50">
                          {tags.map((tag: string) => (
                            <span
                              key={tag}
                              className="px-2 py-0.5 text-xs rounded bg-primary/10 text-primary"
                            >
                              {tag}
                            </span>
                          ))}
                        </div>
                      );
                    } catch {
                      return null;
                    }
                  })()}
                </div>
              )}
            </>
          ) : (
            <div className="px-3 py-2 border border-warning/50 bg-warning/10 rounded-md text-sm">
              <p className="text-foreground">No models configured for {selectedProvider}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Please add models in AI Models management page
              </p>
            </div>
          )}
        </div>
      )}

      {/* Selection Summary */}
      {(selectedProvider || selectedModel) && (
        <div className="rounded-md bg-muted/50 p-3 text-sm">
          <p className="font-medium mb-1">Selection Summary:</p>
          <ul className="space-y-1 text-muted-foreground">
            {selectedProvider && (
              <li>
                • Provider: <span className="text-foreground font-medium">{selectedProvider}</span>
              </li>
            )}
            {selectedModel && (
              <li>
                • Model: <span className="text-foreground font-medium">
                  {selectedModelData?.display_name || selectedModel}
                </span>
              </li>
            )}
            {!selectedProvider && !selectedModel && (
              <li className="text-primary">
                • Using auto-selection (best available provider and model)
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
