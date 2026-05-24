import type { DirectoryStatsResponse, ScanDirectoryResponse } from '../types/api'

const STORAGE_KEY = 'flux-local-media-scan-cache'
const CACHE_VERSION = 1
const CACHE_TTL_MS = 24 * 60 * 60 * 1000
const CACHE_LIMIT = 5

export interface CachedLocalMediaScan {
  data: ScanDirectoryResponse
  stats: DirectoryStatsResponse
  recursive: boolean
  cachedAt: string
}

export interface SaveCachedLocalMediaScanResult {
  entry: CachedLocalMediaScan
  persisted: boolean
}

interface LocalMediaScanCacheState {
  version: number
  lastKey: string | null
  entries: Record<string, CachedLocalMediaScan>
}

export function getCachedLocalMediaScan(
  directory: string,
  recursive: boolean,
  now: number = Date.now()
): CachedLocalMediaScan | null {
  const state = readCacheState(now)
  return state.entries[getCacheKey(directory, recursive)] ?? null
}

export function getLastCachedLocalMediaScan(now: number = Date.now()): CachedLocalMediaScan | null {
  const state = readCacheState(now)
  return state.lastKey ? state.entries[state.lastKey] ?? null : null
}

export function saveCachedLocalMediaScan(
  data: ScanDirectoryResponse,
  stats: DirectoryStatsResponse,
  recursive: boolean,
  requestedDirectory?: string
): SaveCachedLocalMediaScanResult {
  const cachedAt = new Date().toISOString()
  const entry: CachedLocalMediaScan = { data, stats, recursive, cachedAt }
  const state = readCacheState()
  const primaryKey = getCacheKey(data.directory, recursive)
  const nextEntries = {
    ...state.entries,
    [primaryKey]: entry,
  }

  if (requestedDirectory) {
    nextEntries[getCacheKey(requestedDirectory, recursive)] = entry
  }

  const nextState = pruneCacheState({
    version: CACHE_VERSION,
    lastKey: primaryKey,
    entries: nextEntries,
  })

  return {
    entry,
    persisted: writeCacheState(nextState),
  }
}

function readCacheState(now: number = Date.now()): LocalMediaScanCacheState {
  if (typeof window === 'undefined') {
    return createEmptyState()
  }

  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) {
      return createEmptyState()
    }

    const parsed = JSON.parse(raw) as LocalMediaScanCacheState
    if (parsed.version !== CACHE_VERSION || !parsed.entries) {
      return createEmptyState()
    }

    return pruneCacheState(parsed, now)
  } catch {
    return createEmptyState()
  }
}

function writeCacheState(state: LocalMediaScanCacheState): boolean {
  if (typeof window === 'undefined') {
    return false
  }

  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
    return true
  } catch {
    if (!state.lastKey) {
      return false
    }

    const lastEntry = state.entries[state.lastKey]
    if (!lastEntry) {
      return false
    }

    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          version: CACHE_VERSION,
          lastKey: state.lastKey,
          entries: { [state.lastKey]: lastEntry },
        })
      )
      return true
    } catch {
      return false
    }
  }
}

function pruneCacheState(
  state: LocalMediaScanCacheState,
  now: number = Date.now()
): LocalMediaScanCacheState {
  const entries = Object.entries(state.entries)
    .filter(([, entry]) => now - Date.parse(entry.cachedAt) <= CACHE_TTL_MS)
    .sort(([, left], [, right]) => Date.parse(right.cachedAt) - Date.parse(left.cachedAt))
    .slice(0, CACHE_LIMIT)

  const nextEntries = Object.fromEntries(entries)
  const lastKey = state.lastKey && nextEntries[state.lastKey] ? state.lastKey : entries[0]?.[0] ?? null

  return {
    version: CACHE_VERSION,
    lastKey,
    entries: nextEntries,
  }
}

function createEmptyState(): LocalMediaScanCacheState {
  return {
    version: CACHE_VERSION,
    lastKey: null,
    entries: {},
  }
}

function getCacheKey(directory: string, recursive: boolean): string {
  const normalizedDirectory = directory.trim().replace(/\\+/g, '/').replace(/\/+$/g, '')
  return `${normalizedDirectory}::recursive=${recursive}`
}
