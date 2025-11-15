import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, Search, Filter, Trash2, CheckSquare, Square, ChevronDown, ChevronUp, RefreshCw, Activity, CheckCircle, XCircle, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { Checkbox } from '../components/ui/Checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../components/ui/Dialog'
import api from '../lib/api'
import { getLanguageName } from '../lib/utils'
import { useTranslation } from 'react-i18next'

interface SubtitleContentPreviewProps {
  subtitleId: string
  sourceLang?: string
  targetLang: string
  origin: string
}

function SubtitleContentPreview({ subtitleId, sourceLang, targetLang, origin }: SubtitleContentPreviewProps) {
  const { t } = useTranslation()
  const { data: content, isLoading } = useQuery({
    queryKey: ['subtitle-content', subtitleId],
    queryFn: () => api.getSubtitleContent(subtitleId, 10), // Show first 10 lines
  })

  if (isLoading) {
    return (
      <div className="mt-4 p-4 bg-muted/30 rounded-lg">
        <div className="text-sm text-muted-foreground">{t('subtitles.loading')}</div>
      </div>
    )
  }

  if (!content || !content.entries || content.entries.length === 0) {
    return (
      <div className="mt-4 p-4 bg-muted/30 rounded-lg">
        <div className="text-sm text-muted-foreground">{t('subtitles.noRecords')}</div>
      </div>
    )
  }

  return (
    <div className="mt-4 p-4 bg-muted/30 rounded-lg space-y-3">
      <div className="text-sm font-medium text-muted-foreground mb-2">
        {t('subtitles.translationRecords')} ({content.entries.length})
      </div>
      <div className="space-y-2 max-h-[400px] overflow-y-auto">
        {content.entries.map((entry: any, idx: number) => (
          <div key={idx} className="p-2 bg-background rounded border text-sm">
            <div className="text-xs text-muted-foreground mb-1">
              #{entry.index} • {entry.start} → {entry.end}
            </div>
            {origin === 'mt' && sourceLang ? (
              <div className="space-y-1">
                <div className="text-muted-foreground">
                  <span className="text-xs font-medium">{getLanguageName(sourceLang)}:</span>{' '}
                  <span className="italic">{t('library.none')}</span>
                </div>
                <div>
                  <span className="text-xs font-medium">{getLanguageName(targetLang)}:</span>{' '}
                  {entry.text}
                </div>
              </div>
            ) : (
              <div>{entry.text}</div>
            )}
          </div>
        ))}
      </div>
      {content.total > content.entries.length && (
        <div className="text-xs text-muted-foreground text-center pt-2 border-t">
          {t('subtitles.total')} {content.total} {t('subtitles.items')}，{t('subtitles.showing')} {content.entries.length} {t('subtitles.items')}
        </div>
      )}
    </div>
  )
}

interface SubtitleRecord {
  id: string
  lang: string
  format: string
  origin: string
  source_lang?: string
  is_uploaded: boolean
  line_count?: number
  word_count?: number
  created_at: string
  media_name?: string
  media_type?: string
  media_path?: string
  item_id?: string
}

export function Subtitles() {
  const { t, i18n } = useTranslation()
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [langFilter, setLangFilter] = useState<string>('all')
  const [originFilter, setOriginFilter] = useState<string>('all')
  const [offset, setOffset] = useState(0)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteFiles, setDeleteFiles] = useState(false)
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set())
  const [syncStatusDialogOpen, setSyncStatusDialogOpen] = useState(false)

  const limit = 50

  // Fetch subtitle records
  const { data: subtitles, isLoading } = useQuery({
    queryKey: ['subtitles', {
      limit,
      offset,
      lang: langFilter !== 'all' ? langFilter : undefined,
      origin: originFilter !== 'all' ? originFilter : undefined,
      search: search || undefined,
    }],
    queryFn: () => api.getSubtitles({
      limit,
      offset,
      lang: langFilter !== 'all' ? langFilter : undefined,
      origin: originFilter !== 'all' ? originFilter : undefined,
      search: search || undefined,
    }),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['subtitle-stats'],
    queryFn: () => api.getSubtitleStats(),
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: async (subtitleId: string) => {
      return await api.deleteSubtitle(subtitleId, deleteFiles)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subtitles'] })
      queryClient.invalidateQueries({ queryKey: ['subtitle-stats'] })
    },
    onError: (error: any) => {
      console.error('Failed to delete subtitle:', error)
    },
  })

  // Batch delete mutation
  const batchDeleteMutation = useMutation({
    mutationFn: async () => {
      return await api.batchDeleteSubtitles(Array.from(selectedIds), deleteFiles)
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subtitles'] })
      queryClient.invalidateQueries({ queryKey: ['subtitle-stats'] })
      setSelectedIds(new Set())
      setDeleteDialogOpen(false)
    },
    onError: (error: any) => {
      console.error('Failed to batch delete subtitles:', error)
    },
  })

  // Batch sync mutation
  const batchSyncMutation = useMutation({
    mutationFn: async () => {
      return await api.batchSyncSubtitles({
        mode: 'incremental',
        auto_pair: true
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['subtitles'] })
      queryClient.invalidateQueries({ queryKey: ['subtitle-stats'] })
      queryClient.invalidateQueries({ queryKey: ['sync-records'] })
      setSyncStatusDialogOpen(true)
    },
    onError: (error: any) => {
      console.error('Failed to sync subtitles:', error)
    },
  })

  // Fetch sync records
  const { data: syncRecords, refetch: refetchSyncRecords } = useQuery({
    queryKey: ['sync-records'],
    queryFn: () => api.listSyncRecords({ limit: 50, offset: 0 }),
    enabled: syncStatusDialogOpen,
    refetchInterval: syncStatusDialogOpen ? 5000 : false, // Refresh every 5 seconds when dialog is open
  })

  const handleSelectAll = () => {
    if (selectedIds.size === subtitles?.subtitles.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(subtitles?.subtitles.map((s: SubtitleRecord) => s.id) || []))
    }
  }

  const handleSelectOne = (id: string) => {
    const newSelected = new Set(selectedIds)
    if (newSelected.has(id)) {
      newSelected.delete(id)
    } else {
      newSelected.add(id)
    }
    setSelectedIds(newSelected)
  }

  const handleBatchDelete = () => {
    if (selectedIds.size === 0) {
      return
    }
    setDeleteDialogOpen(true)
  }

  const confirmBatchDelete = () => {
    batchDeleteMutation.mutate()
  }

  const toggleExpanded = (id: string) => {
    const newExpanded = new Set(expandedIds)
    if (newExpanded.has(id)) {
      newExpanded.delete(id)
    } else {
      newExpanded.add(id)
    }
    setExpandedIds(newExpanded)
  }

  const getOriginBadge = (origin: string) => {
    const variants: Record<string, { label: string; className: string }> = {
      asr: { label: 'ASR', className: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
      mt: { label: t('subtitles.stats.mt'), className: 'bg-purple-500/10 text-purple-500 border-purple-500/20' },
      manual: { label: t('subtitles.stats.manual'), className: 'bg-green-500/10 text-green-500 border-green-500/20' },
      jellyfin: { label: 'Jellyfin', className: 'bg-orange-500/10 text-orange-500 border-orange-500/20' },
    }
    const variant = variants[origin] || { label: origin, className: '' }
    return <Badge variant="outline" className={variant.className}>{variant.label}</Badge>
  }

  const uniqueLanguages = stats?.by_language ? Object.keys(stats.by_language) : []

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('subtitles.total')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('subtitles.uploaded')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">{stats?.uploaded || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('subtitles.notUploaded')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-500">{stats?.not_uploaded || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('subtitles.stats.byLanguage')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{uniqueLanguages.length}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Actions */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={t('subtitles.searchPlaceholder')}
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value)
                    setOffset(0)
                  }}
                  className="pl-10"
                />
              </div>
            </div>

            <Select
              value={langFilter}
              onValueChange={(value) => {
                setLangFilter(value)
                setOffset(0)
              }}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder={t('subtitles.targetLanguage')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('subtitles.allTargetLanguages')}</SelectItem>
                {uniqueLanguages.map((lang) => (
                  <SelectItem key={lang} value={lang}>
                    {getLanguageName(lang)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={originFilter}
              onValueChange={(value) => {
                setOriginFilter(value)
                setOffset(0)
              }}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder={t('subtitles.originFilter')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('subtitles.allOrigins')}</SelectItem>
                <SelectItem value="asr">ASR</SelectItem>
                <SelectItem value="mt">{t('subtitles.stats.mt')}</SelectItem>
                <SelectItem value="manual">{t('subtitles.stats.manual')}</SelectItem>
                <SelectItem value="jellyfin">Jellyfin</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant="outline"
              size="sm"
              onClick={() => batchSyncMutation.mutate()}
              disabled={batchSyncMutation.isPending}
            >
              <RefreshCw className={`mr-2 h-4 w-4 ${batchSyncMutation.isPending ? 'animate-spin' : ''}`} />
              {t('subtitles.syncToMemory')}
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setSyncStatusDialogOpen(true)}
            >
              <Activity className="mr-2 h-4 w-4" />
              {t('subtitles.viewSyncStatus')}
            </Button>

            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              disabled={selectedIds.size === 0}
            >
              <Trash2 className="mr-2 h-4 w-4" />
{t('subtitles.batchDelete')} ({selectedIds.size})
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Subtitle Records List */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
{t('subtitles.translationRecords')} ({subtitles?.total || 0})
            </CardTitle>
            {subtitles && subtitles.subtitles.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleSelectAll}
              >
                {selectedIds.size === subtitles.subtitles.length ? (
                  <>
                    <CheckSquare className="mr-2 h-4 w-4" />
{t('common.cancel')}
                  </>
                ) : (
                  <>
                    <Square className="mr-2 h-4 w-4" />
{t('subtitles.selectAll')}
                  </>
                )}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">{t('subtitles.loading')}</div>
          ) : subtitles?.subtitles && subtitles.subtitles.length > 0 ? (
            <div className="space-y-3">
              {subtitles.subtitles.map((subtitle: SubtitleRecord) => (
                <div
                  key={subtitle.id}
                  className={`p-4 rounded-lg border ${
                    selectedIds.has(subtitle.id)
                      ? 'bg-primary/5 border-primary'
                      : 'bg-card hover:bg-accent/30'
                  } transition-colors`}
                >
                  <div className="flex items-start gap-4">
                    <Checkbox
                      checked={selectedIds.has(subtitle.id)}
                      onCheckedChange={() => handleSelectOne(subtitle.id)}
                    />

                    <div className="flex-1 space-y-2">
                      {/* Media name */}
                      <div className="font-medium">
{subtitle.media_name || t('library.none')}
                      </div>

                      {/* Badges */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <Badge variant="outline">
                          {getLanguageName(subtitle.lang)}
                        </Badge>
                        {getOriginBadge(subtitle.origin)}
                        <Badge variant="outline" className="uppercase">
                          {subtitle.format}
                        </Badge>
                        {subtitle.source_lang && (
                          <Badge variant="outline" className="bg-muted">
{t('subtitles.sourceLanguage')}: {getLanguageName(subtitle.source_lang)}
                          </Badge>
                        )}
                        {subtitle.is_uploaded && (
                          <Badge variant="outline" className="bg-green-500/10 text-green-500">
{t('subtitles.uploaded')}
                          </Badge>
                        )}
                      </div>

                      {/* Meta info */}
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {subtitle.line_count && (
                          <span>{subtitle.line_count} {t('common.lines')}</span>
                        )}
                        {subtitle.word_count && (
                          <span>{subtitle.word_count} {t('common.words')}</span>
                        )}
                        {subtitle.media_type && (
                          <span>{subtitle.media_type}</span>
                        )}
                        <span>
                          {new Date(subtitle.created_at).toLocaleString(i18n.language)}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleExpanded(subtitle.id)}
                      >
                        {expandedIds.has(subtitle.id) ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deleteMutation.mutate(subtitle.id)}
                        disabled={deleteMutation.isPending}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Expandable content preview */}
                  {expandedIds.has(subtitle.id) && (
                    <SubtitleContentPreview
                      subtitleId={subtitle.id}
                      sourceLang={subtitle.source_lang}
                      targetLang={subtitle.lang}
                      origin={subtitle.origin}
                    />
                  )}
                </div>
              ))}

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t">
                <div className="text-sm text-muted-foreground">
{t('subtitles.showing')} {offset + 1} - {Math.min(offset + limit, subtitles.total)} / {t('subtitles.total')} {subtitles.total} {t('subtitles.items')}
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                  >
{t('common.previousPage')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= subtitles.total}
                  >
{t('common.nextPage')}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {search || langFilter !== 'all' || originFilter !== 'all'
? t('subtitles.noResults')
                : t('subtitles.empty')}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Batch Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('subtitles.confirmBatchDelete')}</DialogTitle>
            <DialogDescription>
              {t('subtitles.confirmBatchDeleteMessage', { count: selectedIds.size })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <Checkbox
                checked={deleteFiles}
                onCheckedChange={(checked) => setDeleteFiles(checked as boolean)}
              />
              <span className="text-sm">{t('subtitles.deleteFiles')}</span>
            </label>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
{t('common.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={confirmBatchDelete}
              disabled={batchDeleteMutation.isPending}
            >
{batchDeleteMutation.isPending ? t('subtitles.deleting') : t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Sync Status Dialog */}
      <Dialog open={syncStatusDialogOpen} onOpenChange={setSyncStatusDialogOpen}>
        <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5" />
              {t('subtitles.syncStatusTitle')}
            </DialogTitle>
            <DialogDescription>
              {t('subtitles.syncStatusDesc')}
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {/* Summary Statistics */}
            {syncRecords && (
              <div className="grid grid-cols-4 gap-4">
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-500">
                        {syncRecords.filter((r: any) => r.status === 'success').length}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {t('common.success')}
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-500">
                        {syncRecords.filter((r: any) => r.status === 'running').length}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {t('common.running')}
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-red-500">
                        {syncRecords.filter((r: any) => r.status === 'failed').length}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {t('common.failed')}
                      </div>
                    </div>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-500">
                        {syncRecords.filter((r: any) => r.status === 'pending').length}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {t('common.pending')}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Sync Records List */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-medium">
                  {t('subtitles.recentSyncRecords')}
                </h3>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => refetchSyncRecords()}
                >
                  <RefreshCw className="h-4 w-4" />
                </Button>
              </div>

              {syncRecords && syncRecords.length > 0 ? (
                <div className="space-y-2 max-h-[400px] overflow-y-auto">
                  {syncRecords.map((record: any) => (
                    <Card key={record.id} className="p-4">
                      <div className="flex items-start justify-between">
                        <div className="flex-1 space-y-2">
                          {/* Status Badge */}
                          <div className="flex items-center gap-2">
                            {record.status === 'success' && (
                              <Badge variant="outline" className="bg-green-500/10 text-green-500 border-green-500/20">
                                <CheckCircle className="mr-1 h-3 w-3" />
                                {t('common.success')}
                              </Badge>
                            )}
                            {record.status === 'running' && (
                              <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/20">
                                <RefreshCw className="mr-1 h-3 w-3 animate-spin" />
                                {t('common.running')}
                              </Badge>
                            )}
                            {record.status === 'failed' && (
                              <Badge variant="outline" className="bg-red-500/10 text-red-500 border-red-500/20">
                                <XCircle className="mr-1 h-3 w-3" />
                                {t('common.failed')}
                              </Badge>
                            )}
                            {record.status === 'pending' && (
                              <Badge variant="outline" className="bg-gray-500/10 text-gray-500 border-gray-500/20">
                                <Clock className="mr-1 h-3 w-3" />
                                {t('common.pending')}
                              </Badge>
                            )}
                            <Badge variant="outline">{record.sync_mode}</Badge>
                          </div>

                          {/* Statistics */}
                          <div className="grid grid-cols-4 gap-4 text-sm">
                            <div>
                              <div className="text-muted-foreground text-xs">
                                {t('subtitles.totalLines')}
                              </div>
                              <div className="font-medium">{record.total_lines}</div>
                            </div>
                            <div>
                              <div className="text-muted-foreground text-xs">
                                {t('subtitles.syncedLines')}
                              </div>
                              <div className="font-medium text-green-500">{record.synced_lines}</div>
                            </div>
                            <div>
                              <div className="text-muted-foreground text-xs">
                                {t('subtitles.skippedLines')}
                              </div>
                              <div className="font-medium text-blue-500">{record.skipped_lines}</div>
                            </div>
                            <div>
                              <div className="text-muted-foreground text-xs">
                                {t('subtitles.failedLines')}
                              </div>
                              <div className="font-medium text-red-500">{record.failed_lines}</div>
                            </div>
                          </div>

                          {/* Timestamps */}
                          <div className="text-xs text-muted-foreground">
                            {record.started_at && (
                              <div>
                                {t('common.started')}:{' '}
                                {new Date(record.started_at).toLocaleString(i18n.language)}
                              </div>
                            )}
                            {record.finished_at && (
                              <div>
                                {t('common.finished')}:{' '}
                                {new Date(record.finished_at).toLocaleString(i18n.language)}
                              </div>
                            )}
                          </div>

                          {/* Error Message */}
                          {record.error_message && (
                            <div className="text-xs text-red-500 bg-red-500/10 p-2 rounded">
                              {record.error_message}
                            </div>
                          )}
                        </div>
                      </div>
                    </Card>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  {t('subtitles.noSyncRecords')}
                </div>
              )}
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSyncStatusDialogOpen(false)}>
              {t('common.close')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
