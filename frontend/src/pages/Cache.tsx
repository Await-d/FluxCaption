import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Trash2, AlertTriangle, Database, HardDrive } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/Select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '../components/ui/AlertDialog'
import api from '../lib/api'
import type { CacheEntry } from '../types/api'
import { useTranslation } from 'react-i18next'

export function Cache() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [sourceLang, setSourceLang] = useState<string>('all')
  const [targetLang, setTargetLang] = useState<string>('all')
  const [model] = useState<string>('all')
  const [sortBy, setSortBy] = useState('last_used_at')
  const [sortOrder] = useState('desc')
  const [limit] = useState(50)
  const [offset, setOffset] = useState(0)
  const queryClient = useQueryClient()

  // Fetch cache stats
  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['cache-stats'],
    queryFn: () => api.getCacheStats(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  // Fetch temp file stats
  const { data: tempStats, isLoading: tempStatsLoading } = useQuery({
    queryKey: ['temp-stats'],
    queryFn: () => api.getTempFileStats(),
    refetchInterval: 10000,
  })

  // Fetch cache entries
  const {
    data: cacheData,
    isLoading: entriesLoading,
    refetch,
  } = useQuery({
    queryKey: [
      'cache-entries',
      limit,
      offset,
      sourceLang !== 'all' ? sourceLang : undefined,
      targetLang !== 'all' ? targetLang : undefined,
      model !== 'all' ? model : undefined,
      search || undefined,
      sortBy,
      sortOrder,
    ],
    queryFn: () =>
      api.getCacheEntries({
        limit,
        offset,
        source_lang: sourceLang !== 'all' ? sourceLang : undefined,
        target_lang: targetLang !== 'all' ? targetLang : undefined,
        model: model !== 'all' ? model : undefined,
        search: search || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
      }),
    refetchInterval: 10000,
  })

  // Clear old entries mutation
  const clearOldMutation = useMutation({
    mutationFn: (days: number) => api.clearOldCacheEntries(days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] })
      queryClient.invalidateQueries({ queryKey: ['cache-entries'] })
    },
  })

  // Clear all entries mutation
  const clearAllMutation = useMutation({
    mutationFn: () => api.clearAllCacheEntries(true),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['cache-stats'] })
      queryClient.invalidateQueries({ queryKey: ['cache-entries'] })
    },
  })

  // Cleanup temp files mutation
  const cleanupTempMutation = useMutation({
    mutationFn: () => api.cleanupTempFiles(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['temp-stats'] })
    },
  })

  const handleClearOld = () => {
    clearOldMutation.mutate(90)
  }

  const handleClearAll = () => {
    clearAllMutation.mutate()
  }

  const handleCleanupTemp = () => {
    cleanupTempMutation.mutate()
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  const truncateText = (text: string, maxLength: number = 100) => {
    if (text.length <= maxLength) return text
    return text.substring(0, maxLength) + '...'
  }

  return (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('cache.totalEntries')}</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold">
              {statsLoading ? '-' : stats?.total_entries.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('cache.totalHits')}</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold">
              {statsLoading ? '-' : stats?.total_hits.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('cache.hitRate')}</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold">
              {statsLoading ? '-' : `${stats?.hit_rate.toFixed(1)}%`}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('cache.languagePairs')}</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold">
              {statsLoading ? '-' : stats?.unique_language_pairs}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs sm:text-sm font-medium">{t('cache.modelCount')}</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-xl sm:text-2xl font-bold">
              {statsLoading ? '-' : stats?.unique_models}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Temp Files Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base sm:text-lg">
            <HardDrive className="h-4 w-4 sm:h-5 sm:w-5" />
            {t('cache.tempFileStats')}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1">
              <p className="text-xs sm:text-sm text-muted-foreground">{t('cache.totalSpace')}</p>
              <p className="text-xl sm:text-2xl font-bold">
                {tempStatsLoading ? '-' : `${tempStats?.total_size_mb.toFixed(2)} MB`}
              </p>
              <p className="text-xs text-muted-foreground">
                {tempStatsLoading ? '-' : `${tempStats?.total_dirs} ${t('cache.directories')}, ${tempStats?.total_files} ${t('cache.files')}`}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs sm:text-sm text-muted-foreground">{t('cache.cleanableSpace')}</p>
              <p className="text-xl sm:text-2xl font-bold text-orange-600">
                {tempStatsLoading ? '-' : `${tempStats?.cleanable_size_mb?.toFixed(2) || '0.00'} MB`}
              </p>
              <p className="text-xs text-muted-foreground">
                {tempStatsLoading ? '-' : t('cache.oldFilesAndOrphaned')}
              </p>
            </div>
            <div className="space-y-1">
              <p className="text-xs sm:text-sm text-muted-foreground">{t('cache.orphanedFiles')}</p>
              <p className="text-xl sm:text-2xl font-bold text-destructive">
                {tempStatsLoading ? '-' : tempStats?.orphaned_dirs || 0}
              </p>
              <p className="text-xs text-muted-foreground">
                {tempStatsLoading ? '-' : `${tempStats?.orphaned_size_mb?.toFixed(2) || '0.00'} MB`}
              </p>
            </div>
            <div className="flex items-center">
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button
                    variant="outline"
                    size="default"
                    disabled={tempStatsLoading || (tempStats?.cleanable_size_mb || 0) === 0}
                    className="w-full text-xs sm:text-sm"
                  >
                    <Trash2 className="mr-1 sm:mr-2 h-4 w-4" />
                    {t('cache.cleanTempFiles')}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>{t('cache.cleanTempFilesTitle')}</AlertDialogTitle>
                    <AlertDialogDescription>
                      {t('cache.cleanTempFilesDesc')}
                      <ul className="list-disc list-inside mt-2 space-y-1">
                        <li>{t('cache.oldFilesDesc')}</li>
                        <li>{t('cache.orphanedFilesDesc')}</li>
                      </ul>
                      <p className="mt-2 font-semibold">
                        {t('cache.estimatedSpace')} {tempStats?.cleanable_size_mb?.toFixed(2) || '0.00'} MB
                      </p>
                      {(tempStats?.orphaned_dirs || 0) > 0 && (
                        <p className="mt-2 text-orange-600">
                          {t('cache.orphanedDirsWarning', { count: tempStats?.orphaned_dirs })}
                          （{tempStats?.orphaned_size_mb?.toFixed(2)} MB）
                        </p>
                      )}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t('cache.cancel')}</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleCleanupTemp}
                      disabled={cleanupTempMutation.isPending}
                    >
                      {cleanupTempMutation.isPending ? t('cache.cleaning') : t('cache.confirmClean')}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filters and Actions */}
      <Card>
        <CardHeader>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <CardTitle className="text-base sm:text-lg">{t('cache.translationCache')}</CardTitle>
            <div className="flex items-center gap-2 flex-wrap">
              <Button variant="outline" size="sm" onClick={() => refetch()} className="text-xs sm:text-sm">
                <RefreshCw className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                {t('cache.refresh')}
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm" className="text-xs sm:text-sm">
                    <Trash2 className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                    {t('cache.cleanOldCache')}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>{t('cache.cleanOldCacheTitle')}</AlertDialogTitle>
                    <AlertDialogDescription>
                      {t('cache.cleanOldCacheDesc')}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t('cache.cancel')}</AlertDialogCancel>
                    <AlertDialogAction onClick={handleClearOld}>
                      {t('cache.confirmClean')}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" size="sm" className="text-xs sm:text-sm">
                    <AlertTriangle className="mr-1 sm:mr-2 h-3 w-3 sm:h-4 sm:w-4" />
                    {t('cache.clearAllCache')}
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>{t('cache.clearAllCacheTitle')}</AlertDialogTitle>
                    <AlertDialogDescription>
                      {t('cache.clearAllCacheDesc')}
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>{t('cache.cancel')}</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleClearAll}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      {t('cache.confirmClearAll')}
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {/* Search and Filters */}
            <div className="grid gap-2 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
              <Input
                placeholder={t('cache.searchPlaceholder')}
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="text-xs sm:text-sm"
              />
              <Select value={sourceLang} onValueChange={setSourceLang}>
                <SelectTrigger className="text-xs sm:text-sm">
                  <SelectValue placeholder={t('cache.sourceLangPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('cache.allSourceLang')}</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh-CN">{t('languages.zh-CN')}</SelectItem>
                  <SelectItem value="ja">{t('languages.ja')}</SelectItem>
                </SelectContent>
              </Select>
              <Select value={targetLang} onValueChange={setTargetLang}>
                <SelectTrigger className="text-xs sm:text-sm">
                  <SelectValue placeholder={t('cache.targetLangPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('cache.allTargetLang')}</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh-CN">{t('languages.zh-CN')}</SelectItem>
                  <SelectItem value="ja">{t('languages.ja')}</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger className="text-xs sm:text-sm">
                  <SelectValue placeholder={t('cache.sortByPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="last_used_at">{t('cache.lastUsedTime')}</SelectItem>
                  <SelectItem value="hit_count">{t('cache.hitCount')}</SelectItem>
                  <SelectItem value="created_at">{t('cache.createdTime')}</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Cache Entries Table */}
            <div className="rounded-md border">
              <div className="max-h-[600px] overflow-y-auto">
                {entriesLoading ? (
                  <div className="p-6 sm:p-8 text-center text-muted-foreground text-xs sm:text-sm">
                    {t('cache.loading')}
                  </div>
                ) : cacheData?.entries.length === 0 ? (
                  <div className="p-6 sm:p-8 text-center text-muted-foreground text-xs sm:text-sm">
                    {t('cache.noData')}
                  </div>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead className="sticky top-0 bg-muted">
                        <tr>
                          <th className="p-2 sm:p-3 text-left text-xs sm:text-sm font-medium">
                            {t('cache.sourceText')}
                          </th>
                          <th className="p-2 sm:p-3 text-left text-xs sm:text-sm font-medium">
                            {t('cache.translatedText')}
                          </th>
                          <th className="p-2 sm:p-3 text-left text-xs sm:text-sm font-medium">
                            {t('cache.languagePairs')}
                          </th>
                          <th className="p-2 sm:p-3 text-left text-xs sm:text-sm font-medium hidden sm:table-cell">
                            {t('cache.model')}
                          </th>
                          <th className="p-2 sm:p-3 text-left text-xs sm:text-sm font-medium">
                            {t('cache.hits')}
                          </th>
                          <th className="p-2 sm:p-3 text-left text-xs sm:text-sm font-medium hidden md:table-cell">
                            {t('cache.lastUsed')}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {cacheData?.entries.map((entry: CacheEntry) => (
                          <tr
                            key={entry.content_hash}
                            className="border-t hover:bg-muted/50"
                          >
                            <td className="p-2 sm:p-3 text-xs sm:text-sm max-w-[120px] sm:max-w-xs">
                              <div className="whitespace-pre-wrap break-words">
                                {truncateText(entry.source_text, 80)}
                              </div>
                            </td>
                            <td className="p-2 sm:p-3 text-xs sm:text-sm max-w-[120px] sm:max-w-xs">
                              <div className="whitespace-pre-wrap break-words">
                                {truncateText(entry.translated_text, 80)}
                              </div>
                            </td>
                            <td className="p-2 sm:p-3 text-xs sm:text-sm whitespace-nowrap">
                              <Badge variant="outline" className="text-[10px] sm:text-xs">
                                {entry.source_lang} → {entry.target_lang}
                              </Badge>
                            </td>
                            <td className="p-2 sm:p-3 text-xs sm:text-sm whitespace-nowrap hidden sm:table-cell">
                              <code className="text-[10px] sm:text-xs">{entry.model}</code>
                            </td>
                            <td className="p-2 sm:p-3 text-xs sm:text-sm text-center">
                              <Badge className="text-[10px] sm:text-xs">{entry.hit_count}</Badge>
                            </td>
                            <td className="p-2 sm:p-3 text-xs sm:text-sm text-muted-foreground whitespace-nowrap hidden md:table-cell">
                              {formatDate(entry.last_used_at)}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            </div>

            {/* Pagination */}
            {cacheData && cacheData.total > 0 && (
              <div className="flex flex-col sm:flex-row items-center justify-between gap-2 sm:gap-0">
                <div className="text-xs sm:text-sm text-muted-foreground">
                  {t('cache.showing')} {offset + 1} - {offset + cacheData.entries.length} / {t('cache.total')}{' '}
                  {cacheData.total} {t('cache.items')}
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                    className="text-xs sm:text-sm"
                  >
                    {t('cache.previousPage')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOffset(offset + limit)}
                    disabled={!cacheData.has_more}
                    className="text-xs sm:text-sm"
                  >
                    {t('cache.nextPage')}
                  </Button>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
