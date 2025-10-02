import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Download, Save, Edit2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import api from '@/lib/api'
import type { SubtitleEntry } from '@/types/api'

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
  const [limit] = useState(100)
  const [offset] = useState(0)
  const [editedEntries, setEditedEntries] = useState<Record<number, string>>({})
  const [isEditing, setIsEditing] = useState(false)
  const queryClient = useQueryClient()

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

  // Reset edited entries when dialog opens
  useEffect(() => {
    if (open) {
      setEditedEntries({})
      setIsEditing(false)
    }
  }, [open])

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
      <DialogContent className="max-w-[95vw] max-h-[90vh] w-full">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle>字幕对比预览</DialogTitle>
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
                      编辑
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleDownload}
                      disabled={resultLoading}
                    >
                      <Download className="mr-2 h-4 w-4" />
                      下载
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
                      取消
                    </Button>
                    <Button
                      variant="default"
                      size="sm"
                      onClick={handleSave}
                      disabled={!hasUnsavedChanges || saveMutation.isPending}
                    >
                      <Save className="mr-2 h-4 w-4" />
                      {saveMutation.isPending ? '保存中...' : '保存'}
                    </Button>
                  </>
                )
              )}
            </div>
          </div>
        </DialogHeader>

        <div className="space-y-4">
          {/* Subtitle Info */}
          {(sourceData || resultData) && (
            <div className="flex items-center gap-4 text-sm text-muted-foreground">
              {sourceData && (
                <>
                  <Badge variant="outline">{sourceData.format.toUpperCase()}</Badge>
                  <span>总计 {sourceData.total_lines} 行</span>
                  <span>
                    显示 {sourceData.offset + 1} - {sourceData.offset + sourceData.entries.length}
                  </span>
                </>
              )}
              {isEditing && hasUnsavedChanges && (
                <Badge variant="default">已修改 {Object.keys(editedEntries).length} 项</Badge>
              )}
            </div>
          )}

          {/* Subtitle Content - Side by Side */}
          <div className="h-[600px] rounded-md border">
            <div className="grid grid-cols-2 h-full">
              {/* Left Panel - Source Subtitle */}
              <div className="border-r">
                <div className="bg-muted/50 p-3 border-b">
                  <h3 className="font-semibold text-sm">源字幕</h3>
                </div>
                <div className="h-[calc(100%-48px)] overflow-y-auto p-4 space-y-4">
                  {isLoading && (
                    <div className="text-center text-muted-foreground">
                      加载中...
                    </div>
                  )}

                  {error && (
                    <div className="text-center text-destructive">
                      加载失败: {(error as Error).message}
                    </div>
                  )}

                  {sourceData?.entries.map((entry: SubtitleEntry) => (
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

                  {sourceData && sourceData.entries.length === 0 && (
                    <div className="text-center text-muted-foreground">
                      暂无字幕内容
                    </div>
                  )}

                  {sourceData && sourceData.has_more && (
                    <div className="text-center text-sm text-muted-foreground py-4">
                      还有更多内容...
                    </div>
                  )}
                </div>
              </div>

              {/* Right Panel - Translated Subtitle */}
              <div>
                <div className="bg-muted/50 p-3 border-b">
                  <h3 className="font-semibold text-sm">翻译字幕 {isEditing && <span className="text-xs text-muted-foreground">(可编辑)</span>}</h3>
                </div>
                <div className="h-[calc(100%-48px)] overflow-y-auto p-4 space-y-4">
                  {isLoading && (
                    <div className="text-center text-muted-foreground">
                      加载中...
                    </div>
                  )}

                  {error && (
                    <div className="text-center text-destructive">
                      加载失败: {(error as Error).message}
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
                            placeholder="输入翻译文本..."
                          />
                        ) : (
                          <div className="text-sm leading-relaxed whitespace-pre-wrap">
                            {currentText}
                          </div>
                        )}
                        {isModified && (
                          <div className="text-xs text-blue-600">已修改</div>
                        )}
                      </div>
                    )
                  })}

                  {resultData && resultData.entries.length === 0 && (
                    <div className="text-center text-muted-foreground">
                      暂无字幕内容
                    </div>
                  )}

                  {resultData && resultData.has_more && (
                    <div className="text-center text-sm text-muted-foreground py-4">
                      还有更多内容...
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
