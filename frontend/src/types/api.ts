/**
 * API Types for FluxCaption Frontend
 *
 * These types match the backend Pydantic schemas.
 */

// =============================================================================
// Common Types
// =============================================================================

export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
export type JobType = 'scan' | 'translate' | 'asr_then_translate'
export type SubtitleFormat = 'srt' | 'ass' | 'vtt'
export type SubtitleOrigin = 'manual' | 'asr' | 'mt'
export type WritebackMode = 'upload' | 'sidecar'

// =============================================================================
// Health & System
// =============================================================================

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'down'
  timestamp: string
  services: {
    database: 'ok' | 'down'
    redis: 'ok' | 'down'
    ollama: 'ok' | 'down'
    jellyfin: 'ok' | 'down'
  }
  version: string
}

// =============================================================================
// Jellyfin Integration
// =============================================================================

export interface JellyfinLibrary {
  id: string
  name: string
  type: string
  item_count: number
  image_url?: string
}

export interface JellyfinMediaItem {
  id: string
  name: string
  type: string
  path: string | null
  audio_languages: string[]
  subtitle_languages: string[]
  missing_languages: string[]
  duration_seconds: number | null
  file_size_bytes: number | null
  // Extended metadata
  image_url: string | null
  backdrop_url: string | null
  production_year: number | null
  community_rating: number | null
  official_rating: string | null
  overview: string | null
  genres: string[]
  series_name: string | null
  season_name: string | null
  episode_number: number | null
  season_number: number | null
}

export interface ScanLibraryRequest {
  library_id: string
  required_langs: string[]
  auto_process?: boolean
}

export interface ScanLibraryResponse {
  job_id: string
  library_id: string
  status: JobStatus
  message: string
}

// =============================================================================
// Translation Jobs
// =============================================================================

export interface TranslationJob {
  id: string
  item_id: string | null
  source_type: string
  source_path: string | null
  source_lang: string
  target_langs: string[]
  model: string
  status: string
  progress: number
  current_phase: string | null
  error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  result_paths: string[] | null
  metrics: Record<string, any> | null
}

export interface CreateJobRequest {
  source_type: string
  source_path?: string | null
  item_id?: string | null
  source_lang?: string
  target_langs: string[]
  model?: string | null
  writeback_mode?: string
  priority?: number
}

export interface CreateJobResponse {
  job_id: string
  status: JobStatus
  message: string
}

export interface JobListParams {
  status?: JobStatus
  type?: JobType
  limit?: number
  offset?: number
}

export interface JobListResponse {
  jobs: TranslationJob[]
  total: number
  limit: number
  offset: number
}

// =============================================================================
// Ollama Models
// =============================================================================

export interface OllamaModel {
  name: string
  size: number
  digest: string
  modified_at: string
  details?: {
    format?: string
    family?: string
    parameter_size?: string
    quantization_level?: string
  }
}

export interface OllamaModelListResponse {
  models: OllamaModel[]
}

export interface PullModelRequest {
  model_name: string
  insecure?: boolean
}

export interface PullModelProgress {
  status: string
  digest?: string
  total?: number
  completed?: number
}

// =============================================================================
// File Upload
// =============================================================================

export interface UploadSubtitleRequest {
  file: File
  source_lang?: string
  target_langs: string[]
  mt_model?: string
}

export interface UploadSubtitleResponse {
  file_id: string
  filename: string
  path: string
  size: number
  format: string
}

// =============================================================================
// Media Assets
// =============================================================================

export interface MediaAsset {
  id: string
  jellyfin_item_id: string
  name: string
  path: string
  duration_seconds: number | null
  file_size_bytes: number | null
  audio_languages: string[]
  subtitle_languages: string[]
  created_at: string
  updated_at: string
}

// =============================================================================
// Subtitles
// =============================================================================

export interface Subtitle {
  id: string
  media_asset_id: string
  language: string
  format: SubtitleFormat
  origin: SubtitleOrigin
  file_path: string | null
  storage_location: string
  jellyfin_stream_index: number | null
  created_at: string
  updated_at: string
}

// =============================================================================
// Settings
// =============================================================================

export interface AppSettings {
  // Subtitle & Translation Pipeline
  required_langs: string[]
  writeback_mode: WritebackMode
  default_subtitle_format: SubtitleFormat
  preserve_ass_styles: boolean
  translation_batch_size: number
  translation_max_line_length: number
  translation_preserve_formatting: boolean

  // Model Configuration
  default_mt_model: string
  asr_model: string
  asr_language: string
  asr_compute_type: 'int8' | 'int8_float16' | 'float16' | 'float32'
  asr_device: 'cpu' | 'cuda' | 'auto'
  asr_beam_size: number
  asr_vad_filter: boolean

  // Resource Limits
  max_concurrent_scan_tasks: number
  max_concurrent_translate_tasks: number
  max_concurrent_asr_tasks: number
  max_upload_size_mb: number
  max_audio_duration_seconds: number

  // Feature Flags
  enable_auto_scan: boolean
  enable_auto_pull_models: boolean
  enable_sidecar_writeback: boolean
  enable_metrics: boolean

  // Task Timeouts
  scan_task_timeout: number
  translate_task_timeout: number
  asr_task_timeout: number

  // System Info (read-only)
  environment: 'development' | 'production' | 'testing'
  db_vendor: 'postgres' | 'mysql' | 'sqlite' | 'mssql'
  storage_backend: 'local' | 's3'
  log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
}

export interface UpdateSettingsRequest extends Partial<AppSettings> {}

// =============================================================================
// SSE Progress Events
// =============================================================================

export interface ProgressEvent {
  job_id: string
  phase: 'pull' | 'extract' | 'asr' | 'mt' | 'post' | 'writeback'
  status: 'started' | 'progress' | 'completed' | 'error'
  progress: number
  total?: number
  completed?: number
  message?: string
  error?: string
}

// =============================================================================
// API Error Response
// =============================================================================

export interface APIError {
  detail: string
  status_code?: number
  error_code?: string
}

// =============================================================================
// Subtitle Preview
// =============================================================================

export interface SubtitleEntry {
  index: number
  start: string
  end: string
  start_ms: number
  end_ms: number
  text: string
  style?: string | null
}

export interface SubtitlePreviewResponse {
  format: SubtitleFormat
  total_lines: number
  entries: SubtitleEntry[]
  has_more: boolean
  offset: number
  limit: number
}

// =============================================================================
// Translation Cache
// =============================================================================

export interface CacheEntry {
  content_hash: string
  source_text: string
  translated_text: string
  source_lang: string
  target_lang: string
  model: string
  hit_count: number
  created_at: string
  last_used_at: string
}

export interface CacheListResponse {
  entries: CacheEntry[]
  total: number
  limit: number
  offset: number
  has_more: boolean
}

export interface CacheStats {
  total_entries: number
  total_hits: number
  hit_rate: number
  unique_language_pairs: number
  unique_models: number
}

export interface ClearEntriesResponse {
  deleted_count: number
  message: string
}
