import axios, { type AxiosInstance, type AxiosError } from 'axios'
import type {
  HealthResponse,
  JellyfinLibrary,
  JellyfinMediaItem,
  ScanLibraryRequest,
  ScanLibraryResponse,
  TranslationJob,
  CreateJobRequest,
  CreateJobResponse,
  JobListParams,
  JobListResponse,
  OllamaModelListResponse,
  PullModelRequest,
  UploadSubtitleResponse,
  AppSettings,
  UpdateSettingsRequest,
  APIError,
  SubtitlePreviewResponse,
  CacheStats,
  CacheListResponse,
  ClearEntriesResponse,
  ScanDirectoryRequest,
  ScanDirectoryResponse,
  DirectoryStatsResponse,
  CreateLocalJobRequest,
  ModelListResponse,
} from '../types/api'

/**
 * API Client for FluxCaption Backend
 */
class APIClient {
  private client: AxiosInstance

  constructor(baseURL: string = '/api') {
    this.client = axios.create({
      baseURL,
      headers: {
        'Content-Type': 'application/json',
      },
      timeout: 30000, // 30 seconds default timeout
    })

    // Request interceptor for adding auth token
    this.client.interceptors.request.use(
      (config) => {
        const token = this.getToken()
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<APIError>) => {
        const apiError: APIError = {
          detail: error.response?.data?.detail || error.message || 'Unknown error occurred',
          status_code: error.response?.status,
          error_code: error.response?.data?.error_code,
        }
        return Promise.reject(apiError)
      }
    )
  }

  /**
   * Get auth token from localStorage (zustand persist storage)
   */
  private getToken(): string | null {
    try {
      const authStorage = localStorage.getItem('auth-storage')
      if (authStorage) {
        const parsed = JSON.parse(authStorage)
        return parsed.state?.token || null
      }
    } catch {
      return null
    }
    return null
  }

  // =============================================================================
  // Health & System
  // =============================================================================

  async health(): Promise<HealthResponse> {
    const { data } = await this.client.get<HealthResponse>('/health')
    return data
  }

  // =============================================================================
  // Jellyfin Integration
  // =============================================================================

  async getJellyfinLibraries(): Promise<JellyfinLibrary[]> {
    const { data } = await this.client.get<{
      libraries: Array<{
        ItemId: string
        Name: string
        CollectionType: string | null
        ChildCount: number | null
        ImageTags?: Record<string, string> | null
        image_tags?: Record<string, string> | null
        image_url?: string | null
        image_item_id?: string | null
      }>
      total: number
    }>('/jellyfin/libraries')

    // Map PascalCase API response to camelCase frontend format
    return data.libraries.map(lib => ({
      id: lib.ItemId,
      name: lib.Name,
      type: lib.CollectionType || '',
      item_count: lib.ChildCount || 0,
      image_url: lib.image_url || null,
      image_tags: lib.image_tags || lib.ImageTags || null,
      image_item_id: lib.image_item_id || null,
    }))
  }

  async getJellyfinLibraryItems(libraryId: string): Promise<JellyfinMediaItem[]> {
    const { data } = await this.client.get<{ items: JellyfinMediaItem[]; total: number; limit: number; offset: number }>(
      `/jellyfin/libraries/${libraryId}/items`
    )
    return data.items
  }

  async getSeriesEpisodes(
    seriesId: string,
    limit: number = 200,
    offset: number = 0
  ): Promise<{ items: JellyfinMediaItem[]; total: number; limit: number; offset: number }> {
    const { data } = await this.client.get<{ items: JellyfinMediaItem[]; total: number; limit: number; offset: number }>(
      `/jellyfin/series/${seriesId}/episodes`,
      {
        params: { limit, offset },
      }
    )
    return data
  }

  async scanJellyfinLibrary(request: ScanLibraryRequest): Promise<ScanLibraryResponse> {
    const { data } = await this.client.post<ScanLibraryResponse>(
      '/jellyfin/scan',
      request
    )
    return data
  }

  // =============================================================================
  // Translation Jobs
  // =============================================================================

  async getJobs(params?: JobListParams): Promise<JobListResponse> {
    const { data } = await this.client.get<JobListResponse>('/jobs', { params })
    return data
  }

  async getJob(jobId: string): Promise<TranslationJob> {
    const { data } = await this.client.get<TranslationJob>(`/jobs/${jobId}`)
    return data
  }

  async createJob(request: CreateJobRequest): Promise<TranslationJob> {
    const { data } = await this.client.post<TranslationJob>('/jobs/translate', request)
    return data
  }

  async cancelJob(jobId: string): Promise<void> {
    await this.client.post(`/jobs/${jobId}/cancel`)
  }

  async retryJob(jobId: string): Promise<CreateJobResponse> {
    const { data } = await this.client.post<CreateJobResponse>(`/jobs/${jobId}/retry`)
    return data
  }

  async resumeJob(jobId: string): Promise<TranslationJob> {
    const { data } = await this.client.post<TranslationJob>(`/jobs/${jobId}/resume`)
    return data
  }

  async startJob(jobId: string): Promise<TranslationJob> {
    const { data } = await this.client.post<TranslationJob>(`/jobs/${jobId}/start`)
    return data
  }

  async batchStartJobs(jobIds: string[]): Promise<{
    started: string[]
    failed: Array<{ job_id: string; reason: string }>
    total_started: number
    total_failed: number
  }> {
    const { data } = await this.client.post('/jobs/batch/start', { job_ids: jobIds })
    return data
  }

  async deleteJob(jobId: string): Promise<void> {
    await this.client.delete(`/jobs/${jobId}`)
  }

  async downloadSubtitle(jobId: string, fileIndex: number = 0): Promise<Blob> {
    const response = await this.client.get(
      `/jobs/${jobId}/download/${fileIndex}`,
      {
        responseType: 'blob',
      }
    )
    return response.data
  }

  async previewSourceSubtitle(
    jobId: string,
    limit: number = 100,
    offset: number = 0
  ): Promise<SubtitlePreviewResponse> {
    const { data } = await this.client.get<SubtitlePreviewResponse>(
      `/jobs/${jobId}/preview/source`,
      {
        params: { limit, offset },
      }
    )
    return data
  }

  async previewResultSubtitle(
    jobId: string,
    fileIndex: number = 0,
    limit: number = 100,
    offset: number = 0
  ): Promise<SubtitlePreviewResponse> {
    const { data } = await this.client.get<SubtitlePreviewResponse>(
      `/jobs/${jobId}/preview/result/${fileIndex}`,
      {
        params: { limit, offset },
      }
    )
    return data
  }

  async updateSubtitleEntries(
    jobId: string,
    fileIndex: number,
    entries: Record<number, string>
  ): Promise<{ message: string; updated_count: number; total_entries: number }> {
    const { data } = await this.client.patch(
      `/jobs/${jobId}/subtitle/${fileIndex}`,
      entries
    )
    return data
  }

  async getJobLogs(jobId: string): Promise<{
    job_id: string
    job_status: string
    total_logs: number
    logs: Array<{
      id: string
      timestamp: string
      phase: string
      status: string
      progress: number
      completed?: number
      total?: number
      extra_data?: any
    }>
  }> {
    const { data } = await this.client.get(`/jobs/${jobId}/logs`)
    return data
  }

  // =============================================================================
  // Ollama Models
  // =============================================================================

  async getOllamaModels(): Promise<OllamaModelListResponse> {
    const { data } = await this.client.get<{
      models: Array<{
        name: string
        status: string
        size_bytes: number
        family?: string
        parameter_size?: string
        quantization?: string
        last_checked: string
        last_used?: string
        usage_count?: number
        is_default?: boolean
      }>
      total: number
    }>('/models')

    // Map API response to frontend format
    return {
      models: data.models.map(model => ({
        name: model.name,
        size: model.size_bytes,
        digest: model.name, // Use name as digest since digest not provided
        modified_at: model.last_checked,
        details: {
          format: model.quantization,
          family: model.family,
          parameter_size: model.parameter_size,
          quantization_level: model.quantization,
        },
      })),
    }
  }

  async getModels(): Promise<ModelListResponse> {
    const { data } = await this.client.get<ModelListResponse>('/models')
    return data
  }

  async pullOllamaModel(request: PullModelRequest): Promise<CreateJobResponse> {
    const { data } = await this.client.post<CreateJobResponse>('/models/pull', request)
    return data
  }

  async deleteOllamaModel(modelName: string): Promise<void> {
    await this.client.delete(`/models/${modelName}`)
  }

  async testOllamaModel(modelName: string): Promise<{
    success: boolean
    model: string
    test_prompt: string
    response: string
    response_time_seconds: number
    status: string
  }> {
    const { data } = await this.client.post(`/models/${modelName}/test`)
    return data
  }

  async setDefaultModel(modelName: string): Promise<{
    success: boolean
    message: string
    default_model: string
  }> {
    const { data } = await this.client.post(`/models/${modelName}/set-default`)
    return data
  }

  async getRecommendedModels(): Promise<{
    recommended_models: Array<{
      name: string
      display_name: string
      description: string
      size_estimate: string
      performance: string
      quality: string
      recommended_for: string
    }>
    total: number
  }> {
    const { data } = await this.client.get('/models/recommended/list')
    return data
  }

  async syncModels(): Promise<{
    success: boolean
    message: string
    total_models: number
  }> {
    const { data } = await this.client.post('/models/sync')
    return data
  }

  // =============================================================================
  // File Upload
  // =============================================================================

  async uploadSubtitle(
    file: File
  ): Promise<UploadSubtitleResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await this.client.post<UploadSubtitleResponse>(
      '/upload/subtitle',
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        timeout: 120000, // 2 minutes for file upload
      }
    )
    return data
  }

  // =============================================================================
  // Settings
  // =============================================================================

  async getSettings(): Promise<AppSettings> {
    const { data } = await this.client.get<AppSettings>('/settings')
    return data
  }

  async updateSettings(settings: UpdateSettingsRequest): Promise<AppSettings> {
    const { data } = await this.client.patch<AppSettings>('/settings', settings)
    return data
  }

  // =============================================================================
  // Translation Cache
  // =============================================================================

  async getCacheStats(): Promise<CacheStats> {
    const { data } = await this.client.get<CacheStats>('/cache/stats')
    return data
  }

  async getCacheEntries(params?: {
    limit?: number
    offset?: number
    source_lang?: string
    target_lang?: string
    model?: string
    search?: string
    sort_by?: string
    sort_order?: string
  }): Promise<CacheListResponse> {
    const { data } = await this.client.get<CacheListResponse>('/cache/entries', { params })
    return data
  }

  async clearOldCacheEntries(days: number = 90): Promise<ClearEntriesResponse> {
    const { data} = await this.client.delete<ClearEntriesResponse>('/cache/old', {
      data: { days }
    })
    return data
  }

  async clearAllCacheEntries(confirm: boolean): Promise<ClearEntriesResponse> {
    const { data } = await this.client.delete<ClearEntriesResponse>('/cache/all', {
      data: { confirm }
    })
    return data
  }

  async getTempFileStats(): Promise<{
    total_size_mb: number
    total_files: number
    total_dirs: number
    old_files: number
    old_dirs: number
    old_size_mb: number
    orphaned_dirs: number
    orphaned_size_mb: number
    cleanable_size_mb: number
    threshold_hours: number
  }> {
    const { data } = await this.client.get('/cache/temp-stats')
    return data
  }

  async cleanupTempFiles(): Promise<{
    status: string
    task_id: string
    estimated: {
      dirs_to_clean: number
      files_to_clean: number
      space_to_free_mb: number
    }
    message: string
  }> {
    const { data } = await this.client.post('/cache/cleanup-temp')
    return data
  }

  // =============================================================================
  // Local Media Files
  // =============================================================================

  async scanLocalDirectory(request: ScanDirectoryRequest): Promise<ScanDirectoryResponse> {
    const { data } = await this.client.post<ScanDirectoryResponse>(
      '/local-media/scan',
      request
    )
    return data
  }

  async getLocalDirectoryStats(
    directory: string,
    recursive: boolean = true
  ): Promise<DirectoryStatsResponse> {
    const { data } = await this.client.get<DirectoryStatsResponse>(
      '/local-media/stats',
      {
        params: { directory, recursive },
      }
    )
    return data
  }

  async createLocalMediaJob(request: CreateLocalJobRequest): Promise<TranslationJob> {
    const { data } = await this.client.post<TranslationJob>(
      '/local-media/jobs',
      request
    )
    return data
  }

  // =============================================================================
  // Subtitle Library
  // =============================================================================

  async getSubtitles(params?: {
    limit?: number
    offset?: number
    lang?: string
    origin?: string
    search?: string
  }): Promise<any> {
    const { data } = await this.client.get('/subtitles', { params })
    return data
  }

  async getSubtitleContent(subtitleId: string, maxLines?: number): Promise<any> {
    const { data} = await this.client.get(`/subtitles/${subtitleId}/content`, {
      params: { max_lines: maxLines }
    })
    return data
  }

  async getSubtitleStats(): Promise<any> {
    const { data } = await this.client.get('/subtitles/stats')
    return data
  }

  async deleteSubtitle(subtitleId: string, deleteFile: boolean = false): Promise<any> {
    const { data } = await this.client.delete(`/subtitles/${subtitleId}`, {
      params: { delete_file: deleteFile },
    })
    return data
  }

  async batchDeleteSubtitles(subtitleIds: string[], deleteFiles: boolean = false): Promise<any> {
    const { data } = await this.client.post('/subtitles/batch-delete', {
      subtitle_ids: subtitleIds,
      delete_files: deleteFiles,
    })
    return data
  }

  // =============================================================================
  // Correction Rules
  // =============================================================================

  async getCorrectionRules(params?: {
    page?: number
    page_size?: number
    is_active?: boolean
    source_lang?: string
    target_lang?: string
  }): Promise<any> {
    const { data } = await this.client.get('/corrections', { params })
    return data
  }

  async getCorrectionRule(ruleId: string): Promise<any> {
    const { data } = await this.client.get(`/corrections/${ruleId}`)
    return data
  }

  async createCorrectionRule(rule: any): Promise<any> {
    const { data } = await this.client.post('/corrections', rule)
    return data
  }

  async updateCorrectionRule(ruleId: string, rule: any): Promise<any> {
    const { data } = await this.client.patch(`/corrections/${ruleId}`, rule)
    return data
  }

  async deleteCorrectionRule(ruleId: string): Promise<void> {
    await this.client.delete(`/corrections/${ruleId}`)
  }

  async applyCorrectionRules(text: string, source_lang?: string, target_lang?: string): Promise<any> {
    const { data } = await this.client.post('/corrections/apply', {
      text,
      source_lang,
      target_lang,
    })
    return data
  }

  async importCorrectionRules(rulesJson: string): Promise<any> {
    const rules = JSON.parse(rulesJson)
    const results = []
    for (const rule of rules) {
      try {
        const result = await this.createCorrectionRule(rule)
        results.push(result)
      } catch (error) {
        console.error('Failed to import rule:', rule, error)
      }
    }
    return { imported: results.length, total: rules.length }
  }

  // =============================================================================
  // Translation Memory
  // =============================================================================

  async getTranslationPairs(params?: {
    limit?: number
    offset?: number
    source_lang?: string
    target_lang?: string
    search?: string
  }): Promise<any> {
    const { data } = await this.client.get('/translation-memory', { params })
    return data
  }

  async getTranslationMemoryStats(): Promise<any> {
    const { data } = await this.client.get('/translation-memory/stats')
    return data
  }

  async getTranslationPair(pairId: string): Promise<any> {
    const { data } = await this.client.get(`/translation-memory/${pairId}`)
    return data
  }

  async updateTranslationPair(pairId: string, targetText: string): Promise<any> {
    const { data } = await this.client.put(`/translation-memory/${pairId}`, { target_text: targetText })
    return data
  }

  async deleteTranslationPair(pairId: string): Promise<any> {
    const { data } = await this.client.delete(`/translation-memory/${pairId}`)
    return data
  }

  async batchDeleteTranslationPairs(ids: string[]): Promise<any> {
    const { data } = await this.client.post('/translation-memory/batch-delete', { ids })
    return data
  }

  async batchReplaceTranslation(params: {
    ids: string[]
    find: string
    replace: string
    use_regex?: boolean
    case_sensitive?: boolean
  }): Promise<any> {
    const { data } = await this.client.post('/translation-memory/batch-replace', params)
    return data
  }

  async reProofreadTranslation(pairId: string): Promise<any> {
    const { data} = await this.client.post(`/translation-memory/${pairId}/re-proofread`)
    return data
  }

  // =============================================================================
  // Auto Translation Rules
  // =============================================================================

  async getAutoTranslationRules(): Promise<import('../types/api').AutoTranslationRuleListResponse> {
    const { data } = await this.client.get('/auto-translation-rules')
    return data
  }

  async getAutoTranslationRule(ruleId: string): Promise<import('../types/api').AutoTranslationRule> {
    const { data } = await this.client.get(`/auto-translation-rules/${ruleId}`)
    return data
  }

  async createAutoTranslationRule(
    ruleData: import('../types/api').AutoTranslationRuleCreate
  ): Promise<import('../types/api').AutoTranslationRule> {
    const { data } = await this.client.post('/auto-translation-rules', ruleData)
    return data
  }

  async updateAutoTranslationRule(
    ruleId: string,
    ruleData: import('../types/api').AutoTranslationRuleUpdate
  ): Promise<import('../types/api').AutoTranslationRule> {
    const { data } = await this.client.put(`/auto-translation-rules/${ruleId}`, ruleData)
    return data
  }

  async deleteAutoTranslationRule(ruleId: string): Promise<void> {
    await this.client.delete(`/auto-translation-rules/${ruleId}`)
  }

  async toggleAutoTranslationRule(ruleId: string): Promise<import('../types/api').AutoTranslationRule> {
    const { data } = await this.client.patch(`/auto-translation-rules/${ruleId}/toggle`)
    return data
  }

  // System Management APIs
  async batchStartAllQueued(): Promise<import('../types/api').BatchOperationResponse> {
    const { data } = await this.client.post('/system/batch/start-all-queued')
    return data
  }

  async batchCancelAllRunning(): Promise<import('../types/api').BatchOperationResponse> {
    const { data } = await this.client.post('/system/batch/cancel-all-running')
    return data
  }

  async batchDeleteCompleted(): Promise<import('../types/api').BatchOperationResponse> {
    const { data } = await this.client.post('/system/batch/delete-completed')
    return data
  }

  async scanAllLibraries(
    request: import('../types/api').ScanAllLibrariesRequest
  ): Promise<import('../types/api').ScanAllLibrariesResponse> {
    const { data } = await this.client.post('/system/scan/all-libraries', request)
    return data
  }

  async getSystemStats(): Promise<import('../types/api').SystemStats> {
    const { data } = await this.client.get('/system/stats')
    return data
  }

  async getQueueStats(): Promise<import('../types/api').QueueStats> {
    const { data } = await this.client.get('/system/queue-stats')
    return data
  }

  async getWorkerStats(): Promise<import('../types/api').WorkerStats> {
    const { data } = await this.client.get('/system/worker-stats')
    return data
  }

  // =============================================================================
  // Subtitle Sync APIs
  // =============================================================================

  async syncSubtitle(request: {
    subtitle_id: string
    mode?: string
    paired_subtitle_id?: string
  }, background: boolean = true): Promise<any> {
    const { data } = await this.client.post('/subtitle-sync/sync', request, {
      params: { background }
    })
    return data
  }

  async syncAssetSubtitles(request: {
    asset_id: string
    mode?: string
    auto_pair?: boolean
  }, background: boolean = true): Promise<any> {
    const { data } = await this.client.post('/subtitle-sync/sync/asset', request, {
      params: { background }
    })
    return data
  }

  async batchSyncSubtitles(request: {
    subtitle_ids?: string[]
    mode?: string
    auto_pair?: boolean
    limit?: number
  }): Promise<any> {
    const { data } = await this.client.post('/subtitle-sync/sync/batch', request)
    return data
  }

  async getSyncStatus(subtitleId: string): Promise<any> {
    const { data } = await this.client.get(`/subtitle-sync/status/${subtitleId}`)
    return data
  }

  async discoverSubtitlePairs(assetId: string): Promise<any> {
    const { data } = await this.client.get(`/subtitle-sync/pairs/${assetId}`)
    return data
  }

  async listSyncRecords(params?: {
    subtitle_id?: string
    asset_id?: string
    status?: string
    limit?: number
    offset?: number
  }): Promise<any> {
    const { data } = await this.client.get('/subtitle-sync/records', { params })
    return data
  }

  async deleteSyncRecord(recordId: string): Promise<any> {
    const { data } = await this.client.delete(`/subtitle-sync/records/${recordId}`)
    return data
  }

  // =============================================================================
  // System Configuration
  // =============================================================================

  async getSystemConfig(): Promise<import('../types/api').SystemConfigCategory[]> {
    const { data } = await this.client.get('/system/config')
    return data
  }

  async getSystemConfigByKey(key: string): Promise<import('../types/api').SystemSetting> {
    const { data } = await this.client.get(`/system/config/${key}`)
    return data
  }

  async updateSystemConfig(key: string, value: string, change_reason?: string): Promise<import('../types/api').SystemSetting> {
    const { data } = await this.client.put(`/system/config/${key}`, {
      value,
      change_reason
    })
    return data
  }

  async resetSystemConfig(key: string): Promise<import('../types/api').SystemSetting> {
    const { data } = await this.client.post(`/system/config/${key}/reset`)
    return data
  }

  async getSettingChangeHistory(key: string, limit: number = 50): Promise<import('../types/api').SettingChangeHistory[]> {
    const { data } = await this.client.get(`/system/config/${key}/history`, {
      params: { limit }
    })
    return data
  }

  async getAllConfigChanges(limit: number = 100): Promise<import('../types/api').SettingChangeHistory[]> {
    const { data } = await this.client.get('/system/config-history', {
      params: { limit }
    })
    return data
  }

}

// =============================================================================
// Export Singleton Instance
// =============================================================================

export const api = new APIClient()
export default api
