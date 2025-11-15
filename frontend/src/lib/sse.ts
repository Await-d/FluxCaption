import type { ProgressEvent } from '../types/api'

/**
 * SSE (Server-Sent Events) Client for Real-time Progress Updates
 */

export type ProgressCallback = (event: ProgressEvent) => void
export type ErrorCallback = (error: Event) => void

export interface SSESubscription {
  unsubscribe: () => void
}

/**
 * Subscribe to job progress events via SSE
 */
export function subscribeToJobProgress(
  jobId: string,
  onProgress: ProgressCallback,
  onError?: ErrorCallback
): SSESubscription {
  // Get auth token from localStorage
  const getToken = (): string | null => {
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

  const token = getToken()
  const url = token
    ? `/api/jobs/${jobId}/events?token=${encodeURIComponent(token)}`
    : `/api/jobs/${jobId}/events`

  const eventSource = new EventSource(url)

  // Handle incoming progress messages
  eventSource.onmessage = (event) => {
    try {
      const data: ProgressEvent = JSON.parse(event.data)
      onProgress(data)
    } catch (error) {
      console.error('Failed to parse SSE message:', error)
    }
  }

  // Handle errors
  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error)
    if (onError) {
      onError(error)
    }
    // Auto-close on error
    eventSource.close()
  }

  // Return unsubscribe function
  return {
    unsubscribe: () => {
      eventSource.close()
    },
  }
}

/**
 * Subscribe to model pull progress events via SSE
 */
export function subscribeToModelPullProgress(
  modelName: string,
  onProgress: ProgressCallback,
  onError?: ErrorCallback
): SSESubscription {
  const eventSource = new EventSource(`/api/models/pull/${modelName}/progress`)

  eventSource.onmessage = (event) => {
    try {
      const data: ProgressEvent = JSON.parse(event.data)
      onProgress(data)
    } catch (error) {
      console.error('Failed to parse SSE message:', error)
    }
  }

  eventSource.onerror = (error) => {
    console.error('SSE connection error:', error)
    if (onError) {
      onError(error)
    }
    eventSource.close()
  }

  return {
    unsubscribe: () => {
      eventSource.close()
    },
  }
}

/**
 * React Hook for job progress subscription
 */
export function useJobProgress(
  jobId: string | null,
  onProgress: ProgressCallback,
  onError?: ErrorCallback
) {
  const subscriptionRef = React.useRef<SSESubscription | null>(null)

  React.useEffect(() => {
    if (!jobId) return

    // Subscribe to progress
    subscriptionRef.current = subscribeToJobProgress(jobId, onProgress, onError)

    // Cleanup on unmount or jobId change
    return () => {
      subscriptionRef.current?.unsubscribe()
      subscriptionRef.current = null
    }
  }, [jobId, onProgress, onError])
}

/**
 * React Hook for model pull progress subscription
 */
export function useModelPullProgress(
  modelName: string | null,
  onProgress: ProgressCallback,
  onError?: ErrorCallback
) {
  const subscriptionRef = React.useRef<SSESubscription | null>(null)

  React.useEffect(() => {
    if (!modelName) return

    subscriptionRef.current = subscribeToModelPullProgress(modelName, onProgress, onError)

    return () => {
      subscriptionRef.current?.unsubscribe()
      subscriptionRef.current = null
    }
  }, [modelName, onProgress, onError])
}

// Import React for hooks (will be removed by bundler if not used)
import React from 'react'
