/**
 * Live Translation Preview Component
 *
 * Shows real-time translation progress with line-by-line animations
 */

import { useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { CheckCircle2, Loader2, Languages } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface TranslationLine {
  index: number
  source: string
  translated: string
  status: 'pending' | 'translating' | 'completed'
}

interface LiveTranslationPreviewProps {
  jobId: string
  onComplete?: () => void
  onError?: (error: string) => void
}

export function LiveTranslationPreview({
  jobId,
  onComplete,
  onError
}: LiveTranslationPreviewProps) {
  const { t } = useTranslation()
  const [lines, setLines] = useState<TranslationLine[]>([])
  const [progress, setProgress] = useState(0)
  const [currentLine, setCurrentLine] = useState(0)
  const [status, setStatus] = useState<'connecting' | 'translating' | 'completed' | 'error'>('connecting')
  const eventSourceRef = useRef<EventSource | null>(null)
  const linesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest translated line
  const scrollToBottom = () => {
    linesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentLine])

  useEffect(() => {
    // Connect to SSE endpoint
    const apiBaseUrl = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const eventSource = new EventSource(`${apiBaseUrl}/api/jobs/${jobId}/stream`)
    eventSourceRef.current = eventSource

    eventSource.onopen = () => {
      setStatus('translating')
    }

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        // Handle different event types
        if (data.type === 'progress') {
          setProgress(data.progress || 0)
        } else if (data.type === 'line') {
          // Update specific line
          setLines(prev => {
            const newLines = [...prev]
            const existingIndex = newLines.findIndex(l => l.index === data.index)

            const line: TranslationLine = {
              index: data.index,
              source: data.source || '',
              translated: data.translated || '',
              status: data.status || 'completed'
            }

            if (existingIndex >= 0) {
              newLines[existingIndex] = line
            } else {
              newLines.push(line)
            }

            return newLines.sort((a, b) => a.index - b.index)
          })

          setCurrentLine(data.index)
        } else if (data.type === 'complete') {
          setStatus('completed')
          setProgress(100)
          onComplete?.()
        } else if (data.type === 'error') {
          setStatus('error')
          onError?.(data.message || t('translation.translationFailed'))
        }
      } catch (err) {
        console.error('Failed to parse SSE message:', err)
      }
    }

    eventSource.onerror = () => {
      setStatus('error')
      onError?.(t('translation.connectionLost'))
      eventSource.close()
    }

    return () => {
      eventSource.close()
    }
  }, [jobId, onComplete, onError])

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Languages className="h-5 w-5" />
            {t('components.liveTranslation.title')}
          </CardTitle>
          <Badge variant={
            status === 'completed' ? 'default' :
            status === 'error' ? 'destructive' :
            'outline'
          }>
            {status === 'connecting' && t('components.liveTranslation.connecting')}
            {status === 'translating' && t('components.liveTranslation.translating')}
            {status === 'completed' && t('components.liveTranslation.completed')}
            {status === 'error' && t('components.liveTranslation.error')}
          </Badge>
        </div>
        <Progress value={progress} className="mt-2" />
        <p className="text-sm text-muted-foreground mt-1">
          {progress.toFixed(1)}% - {currentLine} / {lines.length} {t('components.liveTranslation.lines')}
        </p>
      </CardHeader>
      <CardContent>
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {lines.map((line) => (
            <TranslationLineItem
              key={line.index}
              line={line}
              isActive={line.index === currentLine}
            />
          ))}
          <div ref={linesEndRef} />
        </div>
      </CardContent>
    </Card>
  )
}

interface TranslationLineItemProps {
  line: TranslationLine
  isActive: boolean
}

function TranslationLineItem({ line, isActive }: TranslationLineItemProps) {
  const { t } = useTranslation()
  return (
    <div
      className={cn(
        'rounded-lg border p-4 transition-all duration-500 ease-in-out',
        isActive && 'ring-2 ring-primary shadow-lg scale-[1.02]',
        line.status === 'completed' && 'bg-accent/30',
        line.status === 'translating' && 'animate-pulse'
      )}
    >
      <div className="flex items-start gap-3">
        <div className="flex-shrink-0 mt-1">
          {line.status === 'completed' && (
            <CheckCircle2 className="h-5 w-5 text-green-500 animate-in fade-in zoom-in" />
          )}
          {line.status === 'translating' && (
            <Loader2 className="h-5 w-5 text-primary animate-spin" />
          )}
          {line.status === 'pending' && (
            <div className="h-5 w-5 rounded-full border-2 border-muted" />
          )}
        </div>

        <div className="flex-1 space-y-2 min-w-0">
          {/* Line number */}
          <div className="text-xs text-muted-foreground font-mono">
            #{line.index}
          </div>

          {/* Source text */}
          <div className="text-sm text-muted-foreground line-clamp-2">
            {line.source || '...'}
          </div>

          {/* Translated text */}
          <div
            className={cn(
              'text-base font-medium transition-all duration-300',
              line.status === 'completed' && 'animate-in slide-in-from-left-2 fade-in',
              line.translated ? 'text-foreground' : 'text-muted-foreground italic'
            )}
          >
            {line.translated || t('components.liveTranslation.waitingTranslation')}
          </div>
        </div>
      </div>
    </div>
  )
}
