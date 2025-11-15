/**
 * AI Provider Management API Client
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export interface AIProviderConfig {
  id: string;
  provider_name: string;
  display_name: string;
  is_enabled: boolean;
  base_url?: string;
  timeout: number;
  default_model?: string;
  last_health_check?: string;
  is_healthy: boolean;
  health_error?: string;
  priority: number;
  description?: string;
  created_at: string;
  updated_at: string;
}

export interface ProviderQuota {
  provider_name: string;
  daily_limit?: number;
  monthly_limit?: number;
  current_daily_cost: number;
  current_monthly_cost: number;
  current_daily_tokens: number;
  current_monthly_tokens: number;
  daily_remaining?: number;
  monthly_remaining?: number;
  daily_usage_percent: number;
  monthly_usage_percent: number;
  alert_threshold_percent: number;
  auto_disable_on_limit: boolean;
  daily_reset_at?: string;
  monthly_reset_at?: string;
}

export interface UsageStats {
  provider: string;
  request_count: number;
  total_tokens: number;
  total_cost: number;
  avg_response_time_ms: number;
  error_count: number;
  success_rate: number;
}

export interface UsageLog {
  id: string;
  provider: string;
  model: string;
  job_id?: string;
  request_type: string;
  input_tokens?: number;
  output_tokens?: number;
  total_cost: number;
  response_time_ms?: number;
  is_error: boolean;
  error_message?: string;
  created_at: string;
}

export interface ModelInfo {
  id: string;
  name: string;
  context_length: number;
  supports_streaming: boolean;
  cost_per_1k_input?: number;
  cost_per_1k_output?: number;
  description?: string;
}

// API functions
export const aiProviderApi = {
  // Provider management
  async listProviders(enabledOnly = false): Promise<AIProviderConfig[]> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers`, {
      params: { enabled_only: enabledOnly },
    });
    return response.data;
  },

  async getProvider(providerName: string): Promise<AIProviderConfig> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers/${providerName}`);
    return response.data;
  },

  async createOrUpdateProvider(config: Partial<AIProviderConfig>): Promise<AIProviderConfig> {
    const response = await axios.post(`${API_BASE_URL}/api/ai-providers`, config);
    return response.data;
  },

  async deleteProvider(providerName: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/ai-providers/${providerName}`);
  },

  async healthCheck(providerName: string): Promise<{ provider: string; is_healthy: boolean; checked_at: string }> {
    const response = await axios.post(`${API_BASE_URL}/api/ai-providers/${providerName}/health-check`);
    return response.data;
  },

  async listModels(providerName: string): Promise<{ provider: string; models: ModelInfo[]; count: number }> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers/${providerName}/models`);
    return response.data;
  },

  // Quota management
  async getQuota(providerName: string): Promise<ProviderQuota> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers/${providerName}/quota`);
    return response.data;
  },

  async updateQuota(
    providerName: string,
    quota: Partial<ProviderQuota>
  ): Promise<{ message: string; quota: ProviderQuota }> {
    const response = await axios.put(`${API_BASE_URL}/api/ai-providers/${providerName}/quota`, quota);
    return response.data;
  },

  async resetQuota(providerName: string, period: 'daily' | 'monthly' | 'both'): Promise<{ message: string }> {
    const response = await axios.post(`${API_BASE_URL}/api/ai-providers/${providerName}/quota/reset`, null, {
      params: { period },
    });
    return response.data;
  },

  // Usage statistics
  async getUsageStats(providerName: string, days = 7): Promise<UsageStats[]> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers/${providerName}/usage-stats`, {
      params: { days },
    });
    return response.data;
  },

  async getUsageLogs(
    providerName: string,
    params?: { limit?: number; offset?: number; job_id?: string; errors_only?: boolean }
  ): Promise<{ logs: UsageLog[]; total: number; limit: number; offset: number }> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers/${providerName}/usage-logs`, {
      params,
    });
    return response.data;
  },

  async getUsageSummary(days = 30): Promise<{
    period_days: number;
    summary: {
      total_requests: number;
      total_tokens: number;
      total_cost: number;
      avg_response_time_ms: number;
      error_count: number;
      success_rate: number;
    };
    by_provider: Array<{ provider: string; requests: number; cost: number }>;
  }> {
    const response = await axios.get(`${API_BASE_URL}/api/ai-providers/usage-report/summary`, {
      params: { days },
    });
    return response.data;
  },
};
