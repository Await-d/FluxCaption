import { useState, useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Save, Edit2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '../components/ui/Dialog'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import api from '../lib/api'
import type { SubtitleEntry } from '../types/api'
import { useTranslation } from 'react-i18next'

interface SubtitlePreviewDialogProps {
  jobId: string
  fileIndex?: number
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SubtitlePreviewDialog({
  jobId,
  fileIndex = 0,
  open,
  onOpenChange,
}: SubtitlePreviewDialogProps) {
  const { t } = useTranslation()
  const [limit, setLimit] = useState(100)
  const [offset] = useState(0)
  const [editedEntries, setEditedEntries] = useState<Record<number, string>>({})
  const [isEditing, setIsEditing] = useState(false)
  const queryClient = useQueryClient()

  // Refs for scroll containers
  const sourceScrollRef = useRef<HTMLDivElement>(null)
  const resultScrollRef = useRef<HTMLDivElement>(null)

  // Store scroll positions before loading more
  const [scrollPositions, setScrollPositions] = useState({ source: 0, result: 0 })

  // Fetch source subtitle
  const { data: sourceData, isLoading: sourceLoading, error: sourceError } = useQuery({
    queryKey: ['subtitle-preview', jobId, 'source', limit, offset],
    queryFn: () => api.previewSourceSubtitle(jobId, limit, offset),
    enabled: open,
  })

  // Fetch result subtitle
  const { data: resultData, isLoading: resultLoading, error: resultError } = useQuery({
    queryKey: ['subtitle-preview', jobId, 'result', fileIndex, limit, offset],
    queryFn: () => api.previewResultSubtitle(jobId, fileIndex, limit, offset),
    enabled: open,
  })

  // Reset edited entries and limit when dialog opens
  useEffect(() => {
    if (open) {
      setEditedEntries({})
      setIsEditing(false)
      setLimit(100) // Reset to initial limit
      setScrollPositions({ source: 0, result: 0 })
    }
  }, [open])

  // Restore scroll positions after data loads
  useEffect(() => {
    if (sourceData && sourceScrollRef.current) {
      sourceScrollRef.current.scrollTop = scrollPositions.source
    }
    if (resultData && resultScrollRef.current) {
      resultScrollRef.current.scrollTop = scrollPositions.result
    }
  }, [sourceData, resultData, scrollPositions])

  // Handle load more - save scroll position first
  const handleLoadMore = () => {
    // Save current scroll positions
    if (sourceScrollRef.current || resultScrollRef.current) {
      setScrollPositions({
        source: sourceScrollRef.current?.scrollTop || 0,
        result: resultScrollRef.current?.scrollTop || 0,
      })
    }
    setLimit(prev => prev + 100)
  }

  // Save mutation
  const saveMutation = useMutation({
    mutationFn: async (entries: Record<number, string>) => {
      return await api.updateSubtitleEntries(jobId, fileIndex, entries)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subtitle-preview', jobId, 'result'] })
      setIsEditing(false)
      setEditedEntries({})
    },
  })

  const handleDownload = async () => {
    try {
      const blob = await api.downloadSubtitle(jobId, fileIndex)
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `subtitle_${jobId}.srt`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)
    } catch (error) {
      console.error('Failed to download subtitle:', error)
    }
  }

  const handleEditEntry = (index: number, text: string) => {
    setEditedEntries(prev => ({
      ...prev,
      [index]: text,
    }))
  }

  const handleSave = () => {
    if (Object.keys(editedEntries).length > 0) {
      saveMutation.mutate(editedEntries)
    }
  }

  const hasUnsavedChanges = Object.keys(editedEntries).length > 0

  const isLoading = sourceLoading || resultLoading
  const error = sourceError || resultError

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-[95vw] h-[90vh] w-full !flex !flex-col !gap-0 p-0">
        <DialogHeader className="flex-shrink-0 p-6 pb-4">
          <div className="flex items-center justify-between">
            <DialogTitle>{t('components.subtitlePreview.title')}</DialogTitle>
            <div className="flex items-center gap-2">
              {resultData && !resultError && (
                !isEditing ? (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setIsEditing(true)}
                      disabled={resultLoading}
                    >
                      <Edit2 className="mr-2 h-4 w-4" />
                      {t('components.subtitlePreview.edit')}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownload}
                      disabled={resultLoading}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      {t('components.subtitlePreview.download')}
                    </Button>
                  </>
                ) : (
                  <>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setIsEditing(false)
                        setEditedEntries({})
                      }}
                    >
                      {t('components.subtitlePreview.cancel')}
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleSave}
                      disabled={!hasUnsavedChanges || saveMutation.isPending}
                    >
                      <Save className="mr-2 h-4 w-4" />
                      {saveMutation.isPending ? t('components.subtitlePreview.saving') : t('components.subtitlePreview.save')}
                    </Button>
                  </>
                )
              )}
            </div>
          </div>
        </DialogHeader>

        <div className="flex-1 min-h-0 overflow-hidden flex flex-col px-6">
          {/* Subtitle Info */}
          {(sourceData || resultData) && (
            <div className="flex items-center gap-4 text-sm text-muted-foreground flex-shrink-0 pb-4">
              {sourceData && (
                <>
                  <Badge variant="outline">{sourceData.format.toUpperCase()}</Badge>
                  <span>{t('components.subtitlePreview.total')} {sourceData.total_lines} {t('components.subtitlePreview.lines')}</span>
                  <span>
                    {t('components.subtitlePreview.showing')} {sourceData.offset + 1} - {sourceData.offset + sourceData.entries.length}
                  </span>
                </>
              )}
              {isEditing && hasUnsavedChanges && (
                <Badge variant="default">{t('components.subtitlePreview.modified')} {Object.keys(editedEntries).length} {t('components.subtitlePreview.items')}</Badge>
              )}
            </div>
          )}

          {/* Subtitle Content - Side by Side */}
          <div className="flex-1 min-h-0 rounded-md border overflow-hidden mb-6">
            <div className="grid grid-cols-2 h-full">
              {/* Left Panel - Source Subtitle */}
              <div className="border-r flex flex-col overflow-hidden">
                <div className="bg-muted/50 p-3 border-b flex-shrink-0">
                  <h3 className="font-semibold text-sm">{t('components.subtitlePreview.sourceSubtitle')} {sourceError && t('components.subtitlePreview.asrRecognized')}</h3>
                </div>
                <div ref={sourceScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                  {sourceLoading && (
                    <div className="text-center text-muted-foreground">
                      {t('components.subtitlePreview.loading')}
                    </div>
                  )}

                  {/* 如果源字幕加载失败（ASR任务），显示说明信息 */}
                  {sourceError && (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center space-y-2 max-w-md p-6">
                        <p className="text-sm text-muted-foreground">
                          {t('components.subtitlePreview.asrTaskInfo')}
                        </p>
                        <p className="text-sm text-muted-foreground">
                          {t('components.subtitlePreview.asrTaskInfo2')}
                        </p>
                        <p className="text-sm font-medium">
                          {t('components.subtitlePreview.asrTaskInfo3')}
                        </p>
                      </div>
                    </div>
                  )}

                  {!sourceError && sourceData?.entries.map((entry: SubtitleEntry) => (
                    <div
                      key={entry.index}
                      className="space-y-2 p-3 rounded-lg bg-muted/30"
                    >
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-mono text-muted-foreground">
                          #{entry.index}
                        </span>
                        <span className="font-mono text-xs text-muted-foreground">
                          {entry.start} → {entry.end}
                        </span>
                      </div>
                      <div className="text-sm leading-relaxed whitespace-pre-wrap">
                        {entry.text}
                      </div>
                    </div>
                  ))}

                  {!sourceError && sourceData && sourceData.entries.length === 0 && (
                    <div className="text-center text-muted-foreground">
                      {t('components.subtitlePreview.noSubtitles')}
                    </div>
                  )}

                  {!sourceError && sourceData && sourceData.has_more && (
                    <div className="text-center py-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleLoadMore}
                        disabled={sourceLoading}
                      >
                        {t('components.subtitlePreview.loadMore')} ({sourceData.total_lines - sourceData.entries.length} {t('components.subtitlePreview.linesRemaining')})
                      </Button>
                    </div>
                  )}
                </div>
              </div>

              {/* Right Panel - Translated Subtitle */}
              <div className="flex flex-col overflow-hidden">
                <div className="bg-muted/50 p-3 border-b flex-shrink-0">
                  <h3 className="font-semibold text-sm">{t('components.subtitlePreview.translatedSubtitle')} {isEditing && <span className="text-xs text-muted-foreground">{t('components.subtitlePreview.editable')}</span>}</h3>
                </div>
                <div ref={resultScrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
                  {isLoading && (
                    <div className="text-center text-muted-foreground">
                      {t('components.subtitlePreview.loading')}
                    </div>
                  )}

                  {error && (
                    <div className="text-center text-destructive">
                      {t('components.subtitlePreview.loadFailed', { message: (error as Error).message })}
                    </div>
                  )}

                  {resultData?.entries.map((entry: SubtitleEntry) => {
                    const currentText = editedEntries[entry.index] ?? entry.text
                    const isModified = editedEntries[entry.index] !== undefined

                    return (
                      <div
                        key={entry.index}
                        className={`space-y-2 p-3 rounded-lg transition-colors ${
                          isModified
                            ? 'bg-blue-500/10 border border-blue-500/30'
                            : 'bg-muted/30'
                        }`}
                      >
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-mono text-muted-foreground">
                            #{entry.index}
                          </span>
                          <span className="font-mono text-xs text-muted-foreground">
                            {entry.start} → {entry.end}
                          </span>
                        </div>
                        {isEditing ? (
                          <textarea
                            value={currentText}
                            onChange={(e) => handleEditEntry(entry.index, e.target.value)}
                            className="w-full text-sm leading-relaxed whitespace-pre-wrap bg-background border rounded p-2 min-h-[60px] resize-y"
                            placeholder={t('components.subtitlePreview.enterTranslation')}
                          />
                        ) : (
                          <div className="text-sm leading-relaxed whitespace-pre-wrap">
                            {currentText}
                          </div>
                        )}
                        {isModified && (
                          <div className="text-xs text-blue-600">{t('components.subtitlePreview.modified2')}</div>
                        )}
                      </div>
                    )
                  })}

                  {resultData && resultData.entries.length === 0 && (
                    <div className="text-center text-muted-foreground">
                      {t('components.subtitlePreview.noSubtitles')}
                    </div>
                  )}

                  {resultData && resultData.has_more && (
                    <div className="text-center py-4">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={handleLoadMore}
                        disabled={resultLoading}
                      >
                        {t('components.subtitlePreview.loadMore')} ({resultData.total_lines - resultData.entries.length} {t('components.subtitlePreview.linesRemaining')})
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
