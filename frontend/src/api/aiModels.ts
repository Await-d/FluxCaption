/**
 * AI Model Configuration API Client
 */

import api from '../lib/api'

export interface AIModelConfig {
  id: string;
  provider_name: string;
  model_name: string;
  display_name: string;
  is_enabled: boolean;
  model_type?: string;
  context_window?: number;
  max_output_tokens?: number;
  input_price?: number;
  output_price?: number;
  pricing_notes?: string;
  description?: string;
  tags?: string;
  is_default: boolean;
  priority: number;
  is_available: boolean;
  usage_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  last_checked?: string;
  created_at: string;
  updated_at: string;
}

export interface AIModelConfigCreate {
  provider_name: string;
  model_name: string;
  display_name: string;
  is_enabled?: boolean;
  model_type?: string;
  context_window?: number;
  max_output_tokens?: number;
  input_price?: number;
  output_price?: number;
  pricing_notes?: string;
  description?: string;
  tags?: string;
  is_default?: boolean;
  priority?: number;
}

export interface AIModelConfigUpdate {
  display_name?: string;
  is_enabled?: boolean;
  model_type?: string;
  context_window?: number;
  max_output_tokens?: number;
  input_price?: number;
  output_price?: number;
  pricing_notes?: string;
  description?: string;
  tags?: string;
  is_default?: boolean;
  priority?: number;
}

export interface AIModelConfigListResponse {
  models: AIModelConfig[];
  total: number;
  page: number;
  page_size: number;
}

export interface AIModelCatalogSyncQueuedResponse {
  status: 'queued';
  task_id: string;
  message: string;
  source: string;
  provider?: string | null;
}

export interface PricingCalculation {
  model_name: string;
  provider_name: string;
  input_tokens: number;
  output_tokens: number;
  input_cost: number;
  output_cost: number;
  total_cost: number;
  currency: string;
}

/**
 * List all AI model configurations with optional filtering
 */
export async function listModels(params?: {
  provider?: string;
  enabled_only?: boolean;
  page?: number;
  page_size?: number;
}): Promise<AIModelConfigListResponse> {
  return api.get<AIModelConfigListResponse>('/ai-models', { params })
}

/**
 * Get detailed model configuration
 */
export async function getModel(modelId: string): Promise<AIModelConfig> {
  return api.get<AIModelConfig>(`/ai-models/${modelId}`)
}

/**
 * Create a new AI model configuration
 */
export async function createModel(data: AIModelConfigCreate): Promise<AIModelConfig> {
  return api.post<AIModelConfig>('/ai-models', data)
}

/**
 * Update an AI model configuration
 */
export async function updateModel(
  modelId: string,
  data: AIModelConfigUpdate
): Promise<AIModelConfig> {
  return api.patch<AIModelConfig>(`/ai-models/${modelId}`, data)
}

/**
 * Delete an AI model configuration
 */
export async function deleteModel(modelId: string): Promise<void> {
  await api.delete(`/ai-models/${modelId}`)
}

/**
 * Calculate pricing for token usage
 */
export async function calculatePrice(params: {
  provider_name: string;
  model_name: string;
  input_tokens: number;
  output_tokens: number;
}): Promise<PricingCalculation> {
  return api.post<PricingCalculation>('/ai-models/calculate-price', null, { params })
}

export async function syncCatalog(params?: {
  provider?: string;
}): Promise<AIModelCatalogSyncQueuedResponse> {
  return api.post<AIModelCatalogSyncQueuedResponse>('/ai-models/sync-catalog', null, { params })
}
