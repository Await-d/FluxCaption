import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Database, Search, Filter, BookOpen, Edit2, Trash2, Wand2, CheckSquare, Square, X, RefreshCw } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Button } from '@/components/ui/Button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/AlertDialog'
import { Textarea } from '@/components/ui/Textarea'
import { Checkbox } from '@/components/ui/Checkbox'
import { Label } from '@/components/ui/Label'
import { useToast } from '@/hooks/use-toast'
import api from '@/lib/api'
import { getLanguageName } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

interface TranslationPair {
  id: string
  source_text: string
  target_text: string
  source_lang: string
  target_lang: string
  context?: string
  media_name?: string
  line_number?: number
  start_time?: number
  end_time?: number
  word_count_source?: number
  word_count_target?: number
  translation_model?: string
  created_at: string
}

export function TranslationMemory() {
  const { t, i18n } = useTranslation()
  const [search, setSearch] = useState('')
  const [sourceLangFilter, setSourceLangFilter] = useState<string>('all')
  const [targetLangFilter, setTargetLangFilter] = useState<string>('all')
  const [offset, setOffset] = useState(0)

  // Selection and operations state
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [editingPair, setEditingPair] = useState<TranslationPair | null>(null)
  const [editedText, setEditedText] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [proofreadingPair, setProofreadingPair] = useState<TranslationPair | null>(null)
  const [proofreadResult, setProofreadResult] = useState<any>(null)

  // Batch operations state
  const [isBatchReplaceOpen, setIsBatchReplaceOpen] = useState(false)
  const [batchFind, setBatchFind] = useState('')
  const [batchReplace, setBatchReplace] = useState('')
  const [useRegex, setUseRegex] = useState(false)
  const [caseSensitive, setCaseSensitive] = useState(true)

  const { toast } = useToast()
  const queryClient = useQueryClient()

  const limit = 50

  // Mutations
  const updateMutation = useMutation({
    mutationFn: ({ id, targetText }: { id: string; targetText: string }) =>
      api.updateTranslationPair(id, targetText),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['translation-memory'] })
      toast({ title: t('translationMemory.updateSuccess'), description: t('translationMemory.updated') })
      setEditingPair(null)
    },
    onError: (error: any) => {
      toast({
        title: t('translationMemory.updateFailed'),
        description: error.response?.data?.detail || t('translationMemory.updateError'),
        variant: 'destructive',
      })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteTranslationPair(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['translation-memory'] })
      queryClient.invalidateQueries({ queryKey: ['translation-memory-stats'] })
      toast({ title: t('translationMemory.deleteSuccess'), description: t('translationMemory.deleted') })
      const idToDelete = deletingId
      setDeletingId(null)
      setSelectedIds(prev => {
        const newSet = new Set(prev)
        if (idToDelete) newSet.delete(idToDelete)
        return newSet
      })
    },
    onError: (error: any) => {
      toast({
        title: t('translationMemory.deleteFailed'),
        description: error.response?.data?.detail || t('translationMemory.deleteError'),
        variant: 'destructive',
      })
    },
  })

  const batchDeleteMutation = useMutation({
    mutationFn: (ids: string[]) => api.batchDeleteTranslationPairs(ids),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['translation-memory'] })
      queryClient.invalidateQueries({ queryKey: ['translation-memory-stats'] })
      toast({ title: t('translationMemory.batchDeleteSuccess'), description: t('translationMemory.deletedCount', { count: selectedIds.size }) })
      setSelectedIds(new Set())
    },
    onError: (error: any) => {
      toast({
        title: t('translationMemory.batchDeleteFailed'),
        description: error.response?.data?.detail || t('translationMemory.batchDeleteError'),
        variant: 'destructive',
      })
    },
  })

  const batchReplaceMutation = useMutation({
    mutationFn: (params: {
      ids: string[]
      find: string
      replace: string
      use_regex: boolean
      case_sensitive: boolean
    }) => api.batchReplaceTranslation(params),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['translation-memory'] })
      toast({
        title: t('translationMemory.batchReplaceSuccess'),
        description: t('translationMemory.updatedCount', { updated: data.updated, total: data.total }),
      })
      setIsBatchReplaceOpen(false)
      setBatchFind('')
      setBatchReplace('')
    },
    onError: (error: any) => {
      toast({
        title: t('translationMemory.batchReplaceFailed'),
        description: error.response?.data?.detail || t('translationMemory.batchReplaceError'),
        variant: 'destructive',
      })
    },
  })

  const proofreadMutation = useMutation({
    mutationFn: (id: string) => api.reProofreadTranslation(id),
    onSuccess: (data) => {
      setProofreadResult(data)
    },
    onError: (error: any) => {
      toast({
        title: t('translationMemory.aiProofreadFailed'),
        description: error.response?.data?.detail || t('translationMemory.aiProofreadError'),
        variant: 'destructive',
      })
      setProofreadingPair(null)
    },
  })

  // Event handlers
  const handleSelectAll = () => {
    if (selectedIds.size === memory?.pairs.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(memory?.pairs.map((p: TranslationPair) => p.id) || []))
    }
  }

  const handleToggleSelect = (id: string) => {
    setSelectedIds(prev => {
      const newSet = new Set(prev)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return newSet
    })
  }

  const handleEdit = (pair: TranslationPair) => {
    setEditingPair(pair)
    setEditedText(pair.target_text)
  }

  const handleSaveEdit = () => {
    if (editingPair && editedText.trim()) {
      updateMutation.mutate({ id: editingPair.id, targetText: editedText.trim() })
    }
  }

  const handleDelete = (id: string) => {
    setDeletingId(id)
  }

  const handleConfirmDelete = () => {
    if (deletingId) {
      deleteMutation.mutate(deletingId)
    }
  }

  const handleBatchDelete = () => {
    if (selectedIds.size > 0) {
      batchDeleteMutation.mutate(Array.from(selectedIds))
    }
  }

  const handleBatchReplace = () => {
    if (selectedIds.size > 0 && batchFind) {
      batchReplaceMutation.mutate({
        ids: Array.from(selectedIds),
        find: batchFind,
        replace: batchReplace,
        use_regex: useRegex,
        case_sensitive: caseSensitive,
      })
    }
  }

  const handleProofread = (pair: TranslationPair) => {
    setProofreadingPair(pair)
    setProofreadResult(null)
    proofreadMutation.mutate(pair.id)
  }

  const handleAcceptProofread = () => {
    if (proofreadingPair && proofreadResult) {
      updateMutation.mutate({
        id: proofreadingPair.id,
        targetText: proofreadResult.proofread_text,
      })
      setProofreadingPair(null)
      setProofreadResult(null)
    }
  }

  // Fetch translation memory pairs
  const { data: memory, isLoading } = useQuery({
    queryKey: ['translation-memory', {
      limit,
      offset,
      source_lang: sourceLangFilter !== 'all' ? sourceLangFilter : undefined,
      target_lang: targetLangFilter !== 'all' ? targetLangFilter : undefined,
      search: search || undefined,
    }],
    queryFn: () => api.getTranslationPairs({
      limit,
      offset,
      source_lang: sourceLangFilter !== 'all' ? sourceLangFilter : undefined,
      target_lang: targetLangFilter !== 'all' ? targetLangFilter : undefined,
      search: search || undefined,
    }),
  })

  // Fetch stats
  const { data: stats } = useQuery({
    queryKey: ['translation-memory-stats'],
    queryFn: () => api.getTranslationMemoryStats(),
  })

  const formatTime = (seconds?: number) => {
    if (!seconds) return 'N/A'
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  // Get unique languages from stats
  const uniqueSourceLanguages = stats?.by_language_pair
    ? Array.from(new Set(Object.keys(stats.by_language_pair).map(pair => pair.split(' → ')[0])))
    : []

  const uniqueTargetLanguages = stats?.by_language_pair
    ? Array.from(new Set(Object.keys(stats.by_language_pair).map(pair => pair.split(' → ')[1])))
    : []

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('translationMemory.total')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
            <p className="text-xs text-muted-foreground mt-1">{t('translationMemory.entries')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('translationMemory.languagePairs')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.by_language_pair ? Object.keys(stats.by_language_pair).length : 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('translationMemory.supportedCombinations')}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">{t('translationMemory.translationModels')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {stats?.by_model ? Object.keys(stats.by_model).length : 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">{t('translationMemory.modelsUsed')}</p>
          </CardContent>
        </Card>
      </div>

      {/* Language Pair Distribution */}
      {stats?.by_language_pair && Object.keys(stats.by_language_pair).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('translationMemory.languagePairDistribution')}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
              {Object.entries(stats.by_language_pair).map(([pair, count]) => (
                <div key={pair} className="flex items-center justify-between p-3 rounded-lg border bg-card">
                  <div className="flex items-center gap-2">
                    <BookOpen className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm font-medium">{pair}</span>
                  </div>
                  <Badge variant="outline">{count as number}</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder={t('translationMemory.searchPlaceholder')}
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
              value={sourceLangFilter}
              onValueChange={(value) => {
                setSourceLangFilter(value)
                setOffset(0)
              }}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder={t('translationMemory.sourceLanguage')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('translationMemory.allSourceLanguages')}</SelectItem>
                {uniqueSourceLanguages.map((lang) => (
                  <SelectItem key={lang} value={lang}>
                    {getLanguageName(lang)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={targetLangFilter}
              onValueChange={(value) => {
                setTargetLangFilter(value)
                setOffset(0)
              }}
            >
              <SelectTrigger className="w-full md:w-[180px]">
                <Filter className="mr-2 h-4 w-4" />
                <SelectValue placeholder={t('translationMemory.targetLanguage')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">{t('translationMemory.allTargetLanguages')}</SelectItem>
                {uniqueTargetLanguages.map((lang) => (
                  <SelectItem key={lang} value={lang}>
                    {getLanguageName(lang)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Translation Pairs List */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5" />
{t('translationMemory.title')} ({memory?.total || 0})
            </div>
            {memory?.pairs && memory.pairs.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleSelectAll}
                className="flex items-center gap-2"
              >
                {selectedIds.size === memory.pairs.length ? (
                  <CheckSquare className="h-4 w-4" />
                ) : (
                  <Square className="h-4 w-4" />
                )}
{selectedIds.size === memory.pairs.length ? t('common.cancel') : t('translationMemory.selectAll')}
              </Button>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {/* Batch Operations Toolbar */}
          {selectedIds.size > 0 && (
            <div className="mb-4 p-3 rounded-lg bg-primary/10 border border-primary/20 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">{t('translationMemory.selectedCount', { count: selectedIds.size })}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedIds(new Set())}
                  className="h-7"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setIsBatchReplaceOpen(true)}
                  className="flex items-center gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
{t('translationMemory.batchReplace')}
                </Button>
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={handleBatchDelete}
                  disabled={batchDeleteMutation.isPending}
                  className="flex items-center gap-2"
                >
                  <Trash2 className="h-4 w-4" />
{t('translationMemory.batchDelete')}
                </Button>
              </div>
            </div>
          )}

          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">{t('translationMemory.loading')}</div>
          ) : memory?.pairs && memory.pairs.length > 0 ? (
            <div className="space-y-3">
              {memory.pairs.map((pair: TranslationPair) => (
                <div
                  key={pair.id}
                  className="p-4 rounded-lg border bg-card hover:bg-accent/30 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    {/* Checkbox */}
                    <Checkbox
                      checked={selectedIds.has(pair.id)}
                      onCheckedChange={() => handleToggleSelect(pair.id)}
                      className="mt-1"
                    />

                    <div className="flex-1 space-y-3">
                      {/* Media info and metadata */}
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-2 flex-wrap">
                          {pair.media_name && (
                            <span className="text-sm font-medium text-foreground">
                              {pair.media_name}
                            </span>
                          )}
                          {pair.line_number && (
                            <Badge variant="outline" className="text-xs">
                              {t('translationMemory.lineNumber')} {pair.line_number}
                            </Badge>
                          )}
                          {pair.start_time !== undefined && pair.end_time !== undefined && (
                            <Badge variant="outline" className="text-xs">
                              {formatTime(pair.start_time)} - {formatTime(pair.end_time)}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline">
                            {getLanguageName(pair.source_lang)} → {getLanguageName(pair.target_lang)}
                          </Badge>
                        </div>
                      </div>

                      {/* Translation pair */}
                      <div className="space-y-2">
                        <div className="p-3 rounded-md bg-muted/30 border">
                          <div className="text-xs text-muted-foreground mb-1">
{t('translationMemory.sourceText')} ({pair.source_lang})
                          </div>
                          <div className="text-sm">{pair.source_text}</div>
                        </div>
                        <div className="p-3 rounded-md bg-primary/5 border border-primary/20">
                          <div className="text-xs text-muted-foreground mb-1">
{t('translationMemory.targetText')} ({pair.target_lang})
                          </div>
                          <div className="text-sm font-medium">{pair.target_text}</div>
                        </div>
                      </div>

                      {/* Additional metadata */}
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          {pair.word_count_source && (
                            <span>{t('translationMemory.wordCountFormat', { source: pair.word_count_source, target: pair.word_count_target })}</span>
                          )}
                          {pair.translation_model && (
                            <span>{t('common.model')}: {pair.translation_model}</span>
                          )}
                          <span>{new Date(pair.created_at).toLocaleString(i18n.language)}</span>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleProofread(pair)}
                            disabled={proofreadMutation.isPending && proofreadingPair?.id === pair.id}
                            className="h-8 px-2"
                          >
                            <Wand2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleEdit(pair)}
                            className="h-8 px-2"
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleDelete(pair.id)}
                            className="h-8 px-2 text-destructive hover:text-destructive"
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t">
                <div className="text-sm text-muted-foreground">
{t('translationMemory.showing')} {offset + 1} - {Math.min(offset + limit, memory.total)} / {t('translationMemory.total')} {memory.total} {t('translationMemory.items')}
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
                    disabled={offset + limit >= memory.total}
                  >
{t('common.nextPage')}
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">{t('translationMemory.empty')}</div>
          )}
        </CardContent>
      </Card>

      {/* Edit Dialog */}
      <Dialog open={editingPair !== null} onOpenChange={(open) => !open && setEditingPair(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('translationMemory.editTranslation')}</DialogTitle>
            <DialogDescription>
              {t('translationMemory.editDescription')}
            </DialogDescription>
          </DialogHeader>
          {editingPair && (
            <div className="space-y-4">
              <div>
                <Label className="text-xs text-muted-foreground">{t('translationMemory.sourceText')}</Label>
                <div className="mt-1 p-3 rounded-md bg-muted/30 border text-sm">
                  {editingPair.source_text}
                </div>
              </div>
              <div>
                <Label htmlFor="edit-translation">{t('translationMemory.targetText')}</Label>
                <Textarea
                  id="edit-translation"
                  value={editedText}
                  onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) => setEditedText(e.target.value)}
                  rows={4}
                  className="mt-1"
                />
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditingPair(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleSaveEdit}
              disabled={updateMutation.isPending || !editedText.trim()}
            >
              {t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deletingId !== null} onOpenChange={(open) => !open && setDeletingId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('translationMemory.confirmDelete')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('translationMemory.confirmDeleteMessage')}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleConfirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('common.delete')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Proofreading Dialog */}
      <Dialog
        open={proofreadingPair !== null}
        onOpenChange={(open) => {
          if (!open) {
            setProofreadingPair(null)
            setProofreadResult(null)
          }
        }}
      >
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>{t('translationMemory.aiProofreadResult')}</DialogTitle>
            <DialogDescription>
              {t('translationMemory.proofreadImprovedDesc')}
            </DialogDescription>
          </DialogHeader>
          {proofreadingPair && (
            <div className="space-y-4">
              <div>
                <Label className="text-xs text-muted-foreground">{t('translationMemory.sourceText')}</Label>
                <div className="mt-1 p-3 rounded-md bg-muted/30 border text-sm">
                  {proofreadingPair.source_text}
                </div>
              </div>
              {proofreadMutation.isPending ? (
                <div className="text-center py-8">
                  <div className="inline-flex items-center gap-2">
                    <RefreshCw className="h-4 w-4 animate-spin" />
                    <span>{t('translationMemory.aiProofreadInProgress')}</span>
                  </div>
                </div>
              ) : proofreadResult ? (
                <>
                  <div>
                    <Label className="text-xs text-muted-foreground">{t('translationMemory.currentTranslation')}</Label>
                    <div className="mt-1 p-3 rounded-md bg-muted/30 border text-sm">
                      {proofreadResult.original_text}
                    </div>
                  </div>
                  <div>
                    <Label className="text-xs text-muted-foreground">
                      {t('translationMemory.proofreadTranslation')}
                      {proofreadResult.changed && (
                        <Badge variant="outline" className="ml-2">{t('translationMemory.changed')}</Badge>
                      )}
                    </Label>
                    <div className={`mt-1 p-3 rounded-md border text-sm ${
                      proofreadResult.changed ? 'bg-green-50 dark:bg-green-950 border-green-200 dark:border-green-800' : 'bg-muted/30'
                    }`}>
                      {proofreadResult.proofread_text}
                    </div>
                  </div>
                </>
              ) : null}
            </div>
          )}
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setProofreadingPair(null)
                setProofreadResult(null)
              }}
            >
              {t('common.cancel')}
            </Button>
            {proofreadResult?.changed && (
              <Button
                onClick={handleAcceptProofread}
                disabled={updateMutation.isPending}
              >
                {t('translationMemory.acceptProofread')}
              </Button>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Batch Replace Dialog */}
      <Dialog open={isBatchReplaceOpen} onOpenChange={setIsBatchReplaceOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('translationMemory.batchReplace')}</DialogTitle>
            <DialogDescription>
              {t('translationMemory.batchReplaceDesc', { count: selectedIds.size })}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label htmlFor="batch-find">{t('translationMemory.findText')}</Label>
              <Input
                id="batch-find"
                value={batchFind}
                onChange={(e) => setBatchFind(e.target.value)}
                placeholder={t('translationMemory.findTextPlaceholder')}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="batch-replace">{t('translationMemory.replaceWith')}</Label>
              <Input
                id="batch-replace"
                value={batchReplace}
                onChange={(e) => setBatchReplace(e.target.value)}
                placeholder={t('translationMemory.replaceWithPlaceholder')}
                className="mt-1"
              />
            </div>
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="use-regex"
                  checked={useRegex}
                  onCheckedChange={(checked) => setUseRegex(checked as boolean)}
                />
                <Label htmlFor="use-regex" className="text-sm font-normal">
{t('translationMemory.useRegex')}
                </Label>
              </div>
              <div className="flex items-center space-x-2">
                <Checkbox
                  id="case-sensitive"
                  checked={caseSensitive}
                  onCheckedChange={(checked) => setCaseSensitive(checked as boolean)}
                />
                <Label htmlFor="case-sensitive" className="text-sm font-normal">
{t('translationMemory.caseSensitive')}
                </Label>
              </div>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsBatchReplaceOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleBatchReplace}
              disabled={!batchFind || batchReplaceMutation.isPending}
            >
              {t('translationMemory.replace')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
