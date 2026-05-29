/**
 * AI Provider Selector Component
 *
 * Allows users to select AI provider and model for translation tasks.
 * Displays enabled providers with their health status and configured models with pricing.
 */

import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { AlertCircle, Loader2, DollarSign } from 'lucide-react';
import { aiProviderApi, AIProviderConfig } from '../api/aiProviders';
import * as aiModelsApi from '../api/aiModels';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/Select';
import { Badge } from './ui/Badge';

const AUTO_PROVIDER_VALUE = '__fluxcaption_auto_provider__';
const DEFAULT_MODEL_VALUE = '__fluxcaption_default_model__';

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
      return all.filter((p: AIProviderConfig) => p.is_enabled).sort((a: AIProviderConfig, b: AIProviderConfig) => b.priority - a.priority);
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
    const newProvider = providerName === AUTO_PROVIDER_VALUE ? undefined : providerName;
    setSelectedProvider(newProvider);
    setSelectedModel(undefined); // Reset model when provider changes
    onChange({ provider: newProvider, model: undefined });
  };

  const handleModelChange = (modelName: string) => {
    const newModel = modelName === DEFAULT_MODEL_VALUE ? undefined : modelName;
    setSelectedModel(newModel);
    onChange({ provider: selectedProvider, model: newModel });
  };

  if (isLoadingProviders) {
    return (
      <div className="space-y-4 opacity-50 pointer-events-none">
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          <span>{t('aiProviderSelector.loading')}</span>
        </div>
      </div>
    );
  }

  if (!providers || providers.length === 0) {
    return (
      <div className="rounded-md border border-yellow-500/50 bg-yellow-500/10 p-4">
        <div className="flex items-start gap-3">
          <AlertCircle className="mt-0.5 h-5 w-5 flex-shrink-0 text-primary" />
          <div className="flex-1">
            <p className="text-sm font-medium text-foreground">{t('aiProviderSelector.emptyTitle')}</p>
            <p className="text-xs text-muted-foreground mt-1">
              {t('aiProviderSelector.emptyDescription')}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const availableModels = modelsData?.models || [];
  const selectedModelData = availableModels.find(m => m.model_name === selectedModel);

  return (
    <div className="space-y-5 rounded-[28px] border border-border/70 bg-background/30 p-5 backdrop-blur-sm">
      {/* Provider Selection */}
      <div>
        <p className="text-sm font-medium mb-2 block">
          {t('translate.selectProvider')}
          <span className="text-muted-foreground ml-2 font-normal">
            {t('aiProviderSelector.providerOptionalHint')}
          </span>
        </p>
        <Select
          value={selectedProvider || AUTO_PROVIDER_VALUE}
          onValueChange={handleProviderChange}
          disabled={disabled}
        >
          <SelectTrigger>
            <SelectValue placeholder={t('translate.selectProvider')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={AUTO_PROVIDER_VALUE}>
              {t('translate.autoProvider')}
            </SelectItem>
            {providers.map((provider: AIProviderConfig) => (
              <SelectItem
                key={provider.id}
                value={provider.provider_name}
                disabled={!provider.is_healthy}
              >
                {provider.display_name} - {provider.is_healthy ? t('aiProviderSelector.healthy') : t('aiProviderSelector.unhealthy')}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Model Selection (Dropdown) */}
      {selectedProvider && (
        <div>
          <label htmlFor="model-select" className="text-sm font-medium mb-2 block">
            {t('translate.model')}
            <span className="text-muted-foreground ml-2 font-normal">
              {t('aiProviderSelector.modelOptionalHint')}
            </span>
          </label>

          {isLoadingModels ? (
            <div className="flex items-center gap-2 rounded-[18px] border border-border/70 px-3 py-3">
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
              <span className="text-sm text-muted-foreground">{t('common.loading')}</span>
            </div>
          ) : availableModels.length > 0 ? (
            <>
              <Select
                value={selectedModel || DEFAULT_MODEL_VALUE}
                onValueChange={handleModelChange}
                disabled={disabled}
              >
                <SelectTrigger id="model-select">
                  <SelectValue placeholder={t('translate.useDefault')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={DEFAULT_MODEL_VALUE}>
                    {t('translate.useDefault')}
                  </SelectItem>
                  {availableModels.map(model => (
                    <SelectItem key={model.id} value={model.model_name}>
                      {model.display_name}
                      {model.is_default && ` (${t('jobs.default')})`}
                      {model.input_price !== null && model.output_price !== null &&
                        ` - $${model.input_price}/$${model.output_price}`
                      }
                      {model.input_price === 0 && model.output_price === 0 && ` - ${t('common.free')}`}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>

              {/* Selected Model Details */}
              {selectedModelData && (
                <div className="mt-3 space-y-3 rounded-[22px] border border-border/70 bg-muted/35 p-4">
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
                      <Badge variant="secondary" className="tracking-[0.12em]">
                        {t('jobs.default')}
                      </Badge>
                    )}
                  </div>

                  {/* Specs */}
                  {(selectedModelData.context_window || selectedModelData.max_output_tokens) && (
                    <div className="flex gap-4 text-xs text-muted-foreground">
                      {selectedModelData.context_window && (
                        <div>
                          {t('aiProviderSelector.contextWindow', { count: selectedModelData.context_window })}
                        </div>
                      )}
                      {selectedModelData.max_output_tokens && (
                        <div>
                          {t('aiProviderSelector.maxOutput', { count: selectedModelData.max_output_tokens })}
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
                          <div>{t('aiProviderSelector.inputPrice', { value: selectedModelData.input_price })}</div>
                        )}
                        {selectedModelData.output_price !== null && (
                          <div>{t('aiProviderSelector.outputPrice', { value: selectedModelData.output_price })}</div>
                        )}
                        {selectedModelData.input_price === 0 && selectedModelData.output_price === 0 && (
                          <div className="font-medium text-foreground">
                            {t('common.free')} ({t('providers.local')})
                          </div>
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
                             <Badge
                               key={tag}
                               variant="outline"
                               className="tracking-[0.12em]"
                             >
                               {tag}
                             </Badge>
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
            <div className="rounded-[18px] border border-primary/30 bg-primary/10 px-3 py-3 text-sm">
              <p className="text-foreground">{t('aiModels.noModels')} ({selectedProvider})</p>
              <p className="text-xs text-muted-foreground mt-1">
                {t('aiModels.clickToCreate')}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Selection Summary */}
      {(selectedProvider || selectedModel) && (
        <div className="rounded-[18px] bg-muted/50 p-3 text-sm">
          <p className="font-medium mb-1">{t('aiProviderSelector.summaryTitle')}</p>
          <ul className="space-y-1 text-muted-foreground">
            {selectedProvider && (
              <li>
                {t('aiProviderSelector.summaryProvider', { provider: selectedProvider })}
              </li>
            )}
            {selectedModel && (
              <li>
                {t('aiProviderSelector.summaryModel', { model: selectedModelData?.display_name || selectedModel })}
              </li>
            )}
            {!selectedProvider && !selectedModel && (
              <li className="text-foreground">
                {t('aiProviderSelector.summaryAuto')}
              </li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}
