/**
 * Live Translation Preview Component
 *
 * Shows real-time translation progress with line-by-line animations
 */

import { useEffect, useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card'
import { Badge } from '../ui/Badge'
import { Progress } from '../ui/Progress'
import { CheckCircle2, Loader2, Languages } from 'lucide-react'
import { cn } from '../../lib/utils'
import { subscribeToJobProgress, type SSESubscription } from '../../lib/sse'
import type { ProgressEvent } from '../../types/api'

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
  const [totalLines, setTotalLines] = useState(0)
  const [phase, setPhase] = useState('init')
  const [statusMessage, setStatusMessage] = useState('')
  const [status, setStatus] = useState<'connecting' | 'translating' | 'completed' | 'error'>('connecting')
  const subscriptionRef = useRef<SSESubscription | null>(null)
  const terminalStateReachedRef = useRef(false)
  const linesEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to latest translated line
  const scrollToBottom = () => {
    linesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [currentLine])

  useEffect(() => {
    terminalStateReachedRef.current = false
    setStatus('connecting')

    const handleProgress = (event: ProgressEvent) => {
      const normalizedStatus = (event.status || '').toLowerCase()
      const normalizedPhase = (event.phase || '').toLowerCase()

      if (typeof event.progress === 'number') {
        setProgress(event.progress || 0)
      }

      if (typeof event.phase === 'string') {
        setPhase(event.phase)
      }

      if (typeof event.status === 'string') {
        setStatusMessage(event.status)
      }

      if (
        normalizedStatus === 'completed'
        || normalizedStatus === 'success'
        || normalizedPhase === 'completed'
      ) {
        terminalStateReachedRef.current = true
        setStatus('completed')
        setProgress(100)
        onComplete?.()
        return
      }

      if (
        normalizedStatus === 'failed'
        || normalizedStatus === 'error'
        || normalizedStatus === 'cancelled'
        || normalizedStatus === 'canceled'
      ) {
        terminalStateReachedRef.current = true
        setStatus('error')
        onError?.(event.error || event.message || t('translation.translationFailed'))
        return
      }

      setStatus('translating')

      if (event.type === 'line' && typeof event.index === 'number') {
        const lineIndex = event.index

        setLines(prev => {
          const newLines = [...prev]
          const existingIndex = newLines.findIndex(line => line.index === lineIndex)

          const line: TranslationLine = {
            index: lineIndex,
            source: event.source || '',
            translated: event.translated || '',
            status: 'completed',
          }

          if (typeof event.total === 'number' && event.total > 0) {
            setTotalLines(event.total)
          }

          if (existingIndex >= 0) {
            newLines[existingIndex] = line
          } else {
            newLines.push(line)
          }

          return newLines.sort((a, b) => a.index - b.index)
        })

        setCurrentLine(lineIndex)
      }
    }

    subscriptionRef.current = subscribeToJobProgress(jobId, handleProgress, () => {
      if (terminalStateReachedRef.current) {
        return
      }

      setStatus('error')
      onError?.(t('translation.connectionLost'))
    })

    return () => {
      subscriptionRef.current?.unsubscribe()
      subscriptionRef.current = null
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
          {progress.toFixed(1)}% - {phase === 'ocr'
            ? t('components.liveTranslation.ocrPhase', '正在识别图片字幕文本')
            : `${currentLine} / ${totalLines || lines.length} ${t('components.liveTranslation.lines')}`}
        </p>
        {statusMessage ? (
          <p className="text-xs text-muted-foreground mt-1">{statusMessage}</p>
        ) : null}
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
