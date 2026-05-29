import { useCallback, useEffect, useMemo, useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  FolderOpen,
  Scan,
  Film,
  Languages,
  HardDrive,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Info,
  Clock3,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '../components/ui/AlertDialog'
import { Alert, AlertDescription } from '../components/ui/Alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import api from '../lib/api'
import {
  getCachedLocalMediaScan,
  getLastCachedLocalMediaScan,
  saveCachedLocalMediaScan,
  type CachedLocalMediaScan,
} from '../lib/localMediaScanCache'
import { formatBytes, getLanguageName } from '../lib/utils'
import type {
  MediaFileResponse,
  ScanDirectoryResponse,
  DirectoryStatsResponse,
  AppSettings,
} from '../types/api'
import { useTranslation } from 'react-i18next'
import { PageHero } from '../components/ui/PageHero'

export function LocalMedia() {
  const { t } = useTranslation()
  const [directoryPath, setDirectoryPath] = useState('')
  const [scannedDirectory, setScannedDirectory] = useState<string | null>(null)
  const [scanResult, setScanResult] = useState<ScanDirectoryResponse | null>(null)
  const [selectedFile, setSelectedFile] = useState<MediaFileResponse | null>(null)
  const [translateDialogOpen, setTranslateDialogOpen] = useState(false)
  const [selectedTargetLangs, setSelectedTargetLangs] = useState<string[]>([])
  const [recursive, setRecursive] = useState(true)
  const [scannedRecursive, setScannedRecursive] = useState(true)
  const [cachedAt, setCachedAt] = useState<string | null>(null)
  const [restoredFromCache, setRestoredFromCache] = useState(false)
  const [cacheSaveFailed, setCacheSaveFailed] = useState(false)
  const [mediaPage, setMediaPage] = useState(1)
  const [mediaPageSize] = useState(50)
  const queryClient = useQueryClient()

  const hydrateCachedScan = useCallback((cachedScan: CachedLocalMediaScan, restored: boolean) => {
    setDirectoryPath(cachedScan.data.directory)
    setRecursive(cachedScan.recursive)
    setScannedDirectory(cachedScan.data.directory)
    setScanResult(cachedScan.data)
    setScannedRecursive(cachedScan.recursive)
    setCachedAt(cachedScan.cachedAt)
    setRestoredFromCache(restored)
    setCacheSaveFailed(false)
    queryClient.setQueryData(
      ['local-media-scan', cachedScan.data.directory, cachedScan.recursive],
      cachedScan.data
    )
    queryClient.setQueryData(
      ['local-media-stats', cachedScan.data.directory, cachedScan.recursive],
      cachedScan.stats
    )
  }, [queryClient])

  // Fetch settings to get favorite paths
  const { data: settings } = useQuery<AppSettings>({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })

  // Available languages for translation
  const LANGUAGES = [
    { code: 'zh-CN', name: t('languages.zh-CN') },
    { code: 'en', name: t('languages.en') },
    { code: 'ja', name: t('languages.ja') },
    { code: 'ko', name: t('languages.ko') },
  ]

  // Scan directory mutation
  const scanMutation = useMutation({
    mutationFn: ({ path, recursive }: { path: string; recursive: boolean }) =>
      api.scanLocalDirectory({
        directory: path,
        recursive,
        max_depth: 5,
        // required_langs will be inferred from auto translation rules
      }),
    onSuccess: (data, variables) => {
      const directoryStats = buildDirectoryStatsFromScan(data)
      const cacheResult = saveCachedLocalMediaScan(data, directoryStats, variables.recursive, variables.path)
      setScannedDirectory(data.directory)
      setScanResult(data)
      setScannedRecursive(variables.recursive)
      setCachedAt(cacheResult.persisted ? cacheResult.entry.cachedAt : null)
      setRestoredFromCache(false)
      setCacheSaveFailed(!cacheResult.persisted)
      queryClient.setQueryData(['local-media-scan', data.directory, variables.recursive], data)
      queryClient.setQueryData(
        ['local-media-stats', data.directory, variables.recursive],
        directoryStats
      )
      api.getSettings()
        .then((latestSettings) => {
          const favoritePaths = latestSettings.favorite_media_paths ?? []
          if (favoritePaths.includes(variables.path)) {
            queryClient.setQueryData(['settings'], latestSettings)
            return latestSettings
          }

          return api.updateSettings({ favorite_media_paths: [...favoritePaths, variables.path] })
        })
        .then((updatedSettings) => {
          queryClient.setQueryData(['settings'], updatedSettings)
          return queryClient.invalidateQueries({ queryKey: ['settings'] })
        })
        .catch((error: unknown) => {
          console.error('Failed to save favorite media path:', error)
        })
    },
  })

  // Get directory stats
  const { data: stats } = useQuery<DirectoryStatsResponse>({
    queryKey: ['local-media-stats', scannedDirectory, scannedRecursive],
    queryFn: () => api.getLocalDirectoryStats(scannedDirectory!, scannedRecursive),
    enabled: !!scannedDirectory,
    staleTime: 5 * 60 * 1000,
  })

  const mediaFiles = scanResult?.media_files ?? []
  const filesNeedingTranslation = useMemo(
    () => mediaFiles.filter((file) => file.missing_languages.length > 0),
    [mediaFiles]
  )
  const mediaTotalPages = Math.ceil(mediaFiles.length / mediaPageSize)
  const mediaRangeStart = mediaFiles.length > 0 ? (mediaPage - 1) * mediaPageSize + 1 : 0
  const mediaRangeEnd = Math.min(mediaPage * mediaPageSize, mediaFiles.length)
  const paginatedMediaFiles = useMemo(() => {
    const startIndex = (mediaPage - 1) * mediaPageSize
    return mediaFiles.slice(startIndex, startIndex + mediaPageSize)
  }, [mediaFiles, mediaPage, mediaPageSize])

  useEffect(() => {
    const cachedScan = getLastCachedLocalMediaScan()
    if (cachedScan) {
      hydrateCachedScan(cachedScan, true)
    }
  }, [hydrateCachedScan])

  useEffect(() => {
    const path = directoryPath.trim()
    if (!path || scanMutation.isPending) {
      return
    }

    const cachedScan = getCachedLocalMediaScan(path, recursive)
    if (!cachedScan) {
      return
    }

    if (scanResult?.directory === cachedScan.data.directory && scannedRecursive === cachedScan.recursive) {
      return
    }

    hydrateCachedScan(cachedScan, true)
  }, [directoryPath, hydrateCachedScan, recursive, scanMutation.isPending, scanResult?.directory, scannedRecursive])

  useEffect(() => {
    setMediaPage(1)
  }, [scanResult?.directory])

  useEffect(() => {
    const favoritePaths = settings?.favorite_media_paths ?? []
    if (!directoryPath && favoritePaths.length > 0) {
      setDirectoryPath(favoritePaths[0])
    }
  }, [directoryPath, settings?.favorite_media_paths])

  useEffect(() => {
    if (mediaPage > mediaTotalPages && mediaTotalPages > 0) {
      setMediaPage(mediaTotalPages)
    }
  }, [mediaPage, mediaTotalPages])

  // Create translation job mutation
  const createJobMutation = useMutation({
    mutationFn: async ({
      filepath,
      targetLangs,
      sourceLang,
    }: {
      filepath: string
      targetLangs: string[]
      sourceLang?: string
    }) => {
      return await api.createLocalMediaJob({
        filepath,
        target_langs: targetLangs,
        source_lang: sourceLang,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setTranslateDialogOpen(false)
      setSelectedFile(null)
      setSelectedTargetLangs([])
    },
  })

  // Handle scan directory
  const handleScan = () => {
    if (directoryPath.trim()) {
      scanMutation.mutate({ path: directoryPath.trim(), recursive })
    }
  }

  // Handle quick translate
  const handleQuickTranslate = (file: MediaFileResponse) => {
    setSelectedFile(file)
    setSelectedTargetLangs([])
    setTranslateDialogOpen(true)
  }

  // Handle translate confirm
  const handleTranslateConfirm = () => {
    if (selectedFile && selectedTargetLangs.length > 0) {
      const sourceLang = selectedFile.existing_subtitle_langs[0] // Use first existing subtitle as source
      createJobMutation.mutate({
        filepath: selectedFile.filepath,
        targetLangs: selectedTargetLangs,
        sourceLang: sourceLang || undefined,
      })
    }
  }

  // Toggle target language selection
  const toggleTargetLang = (lang: string) => {
    setSelectedTargetLangs((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    )
  }

  // Batch translate all files with missing languages
  const handleBatchTranslate = async () => {
    if (!filesNeedingTranslation.length) return

    // Create jobs for each file
    for (const file of filesNeedingTranslation) {
      try {
        const sourceLang = file.existing_subtitle_langs[0]
        await createJobMutation.mutateAsync({
          filepath: file.filepath,
          targetLangs: file.missing_languages,
          sourceLang: sourceLang || undefined,
        })
      } catch (error) {
        console.error(`Failed to create job for ${file.filename}:`, error)
      }
    }
  }

  return (
    <div className="space-y-6 lg:space-y-8">
      <PageHero
        eyebrow={t('pageHero.localMedia.eyebrow')}
        title={t('localMedia.scanDirectory')}
        description={t('localMedia.scanDirectoryDesc')}
        metrics={[
          { label: t('pageHero.localMedia.metrics.favorites.label'), value: String(settings?.favorite_media_paths?.length ?? 0), detail: t('pageHero.localMedia.metrics.favorites.detail') },
          { label: t('pageHero.localMedia.metrics.scanned.label'), value: String(mediaFiles.length), detail: scannedDirectory || t('pageHero.localMedia.metrics.scanned.detail') },
          { label: t('pageHero.localMedia.metrics.missing.label'), value: String(filesNeedingTranslation.length), detail: t('pageHero.localMedia.metrics.missing.detail') },
        ]}
      />
      {/* Scan Directory */}
      <Card className="overflow-hidden rounded-[30px]">
        <CardHeader className="border-b border-border/60 p-4 sm:p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="eyebrow-label mb-2">Filesystem</div>
              <CardTitle className="flex items-center gap-2 text-xl sm:text-2xl">
                <FolderOpen className="h-5 w-5 text-primary" />
                {t('localMedia.scanDirectory')}
              </CardTitle>
            </div>
            <Badge variant="outline" className="w-fit rounded-full px-3 py-1 text-xs">
              {recursive ? t('localMedia.recursiveScan') : t('localMedia.scan')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4 p-4 sm:p-5">
          <div className="grid gap-4 lg:grid-cols-[0.85fr_1.15fr] lg:items-stretch">
            <div className="rounded-[26px] border border-border/70 bg-background/35 p-4">
              <div className="flex items-start gap-3">
                <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] border border-border/70 bg-primary/10">
                  <Info className="h-5 w-5 text-primary" />
                </div>
                <div className="space-y-2">
                  <div className="text-sm font-bold">{t('localMedia.scanDirectory')}</div>
                  <p className="text-sm leading-6 text-muted-foreground">{t('localMedia.scanDirectoryDesc')}</p>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <div className="rounded-[18px] border border-border/60 bg-muted/25 p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{t('pageHero.localMedia.metrics.favorites.label')}</div>
                  <div className="mt-1 text-xl font-extrabold">{settings?.favorite_media_paths?.length ?? 0}</div>
                </div>
                <div className="rounded-[18px] border border-border/60 bg-muted/25 p-3">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{t('localMedia.mediaFiles')}</div>
                  <div className="mt-1 text-xl font-extrabold">{mediaFiles.length}</div>
                </div>
              </div>
            </div>

            <div className="rounded-[26px] border border-border/70 bg-background/35 p-3 sm:p-4">
              <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px]">
                <Input
                  placeholder={t('localMedia.pathPlaceholder')}
                  value={directoryPath}
                  onChange={(e) => setDirectoryPath(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') handleScan()
                  }}
                  className="h-12 rounded-[18px]"
                />
                {settings?.favorite_media_paths && settings.favorite_media_paths.length > 0 && (
                  <Select
                    value={directoryPath}
                    onValueChange={(value) => setDirectoryPath(value)}
                  >
                    <SelectTrigger className="h-12 w-full rounded-[18px]">
                      <SelectValue placeholder={t('localMedia.favoritePaths')} />
                    </SelectTrigger>
                    <SelectContent>
                      {settings.favorite_media_paths.map((path, index) => (
                        <SelectItem key={index} value={path}>
                          <div className="flex items-center gap-2">
                            <FolderOpen className="h-4 w-4" />
                            <span className="truncate max-w-[200px]">{path}</span>
                          </div>
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              <div className="mt-3 flex flex-col gap-3 rounded-[22px] border border-border/60 bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between">
                <label className="flex cursor-pointer items-center gap-3 text-sm font-medium">
                  <input
                    type="checkbox"
                    checked={recursive}
                    onChange={(e) => setRecursive(e.target.checked)}
                    className="h-4 w-4 rounded accent-primary"
                  />
                  {t('localMedia.recursiveScan')}
                </label>
                <Button
                  onClick={handleScan}
                  disabled={!directoryPath.trim() || scanMutation.isPending}
                  className="rounded-full sm:min-w-[180px]"
                >
                  {scanMutation.isPending ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      <span className="hidden sm:inline">{t('localMedia.scanning')}</span>
                      <span className="sm:hidden">{t('localMedia.scan')}</span>
                    </>
                  ) : (
                    <>
                      <Scan className="mr-2 h-4 w-4" />
                      <span className="hidden sm:inline">
                        {scanResult ? t('localMedia.refreshScan') : t('localMedia.scanDirectory_btn')}
                      </span>
                      <span className="sm:hidden">{scanResult ? t('common.refresh') : t('localMedia.scan')}</span>
                    </>
                  )}
                </Button>
              </div>
              {cachedAt && (
                <div className="mt-3 flex items-start gap-2 rounded-[18px] border border-border/60 bg-background/35 px-3 py-2 text-xs text-muted-foreground">
                  <Clock3 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-primary" />
                  <span>
                    {restoredFromCache
                      ? t('localMedia.cacheRestoredHint', { time: formatCacheTimestamp(cachedAt) })
                      : t('localMedia.cacheSavedHint', { time: formatCacheTimestamp(cachedAt) })}
                  </span>
                </div>
              )}
              {cacheSaveFailed && (
                <div className="mt-3 flex items-start gap-2 rounded-[18px] border border-orange-500/30 bg-orange-500/10 px-3 py-2 text-xs text-orange-700 dark:text-orange-300">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                  <span>{t('localMedia.cacheSaveFailedHint')}</span>
                </div>
              )}
            </div>
          </div>

          {scanMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                {t('localMedia.scanFailed', { error: scanMutation.error instanceof Error ? scanMutation.error.message : t('components.taskLogs.unknownError') })}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Directory Stats */}
      {stats && (
        <Card className="overflow-hidden rounded-[30px]">
          <CardHeader className="border-b border-border/60 p-4 sm:p-5">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
              <CardTitle className="text-xl sm:text-2xl">{t('localMedia.directoryStats')}</CardTitle>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline" className="w-fit rounded-full px-3 py-1 text-xs">
                  {scannedDirectory}
                </Badge>
                {cachedAt && (
                  <Badge variant={restoredFromCache ? 'secondary' : 'outline'} className="w-fit rounded-full px-3 py-1 text-xs">
                    {restoredFromCache ? t('localMedia.cachedResult') : t('localMedia.lastScanned')}
                    <span className="ml-1 normal-case tracking-normal">{formatCacheTimestamp(cachedAt)}</span>
                  </Badge>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4 sm:p-5">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="rounded-[26px] border border-border/70 bg-background/35 p-4">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[18px] bg-primary/10">
                  <Film className="h-5 w-5 text-primary" />
                </div>
                <p className="text-3xl font-extrabold">{stats.total_media_files}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t('localMedia.mediaFiles')}</p>
              </div>

              <div className="rounded-[26px] border border-border/70 bg-background/35 p-4">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[18px] bg-blue-500/10">
                  <Languages className="h-5 w-5 text-blue-500" />
                </div>
                <p className="text-3xl font-extrabold">{stats.total_subtitle_files}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t('localMedia.subtitleFiles')}</p>
              </div>

              <div className="rounded-[26px] border border-border/70 bg-background/35 p-4">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[18px] bg-green-500/10">
                  <HardDrive className="h-5 w-5 text-green-500" />
                </div>
                <p className="text-3xl font-extrabold">{formatBytes(stats.total_size_bytes)}</p>
                <p className="mt-1 text-sm text-muted-foreground">{t('localMedia.totalSize')}</p>
              </div>

              <div className="rounded-[26px] border border-border/70 bg-background/35 p-4">
                <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-[18px] bg-orange-500/10">
                  <Info className="h-5 w-5 text-orange-500" />
                </div>
                <p className="text-sm font-bold">{t('localMedia.formatDistribution')}</p>
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {Object.entries(stats.video_formats).map(([format, count]) => (
                    <Badge key={format} variant="outline" className="text-xs">
                      {format}: {count}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Media Files */}
      {scanResult && (
        <Card className="overflow-hidden rounded-[30px]">
          <CardHeader className="border-b border-border/60 p-4 sm:p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
              <div>
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  {scannedDirectory}
                </div>
                <CardTitle className="mt-2 text-xl sm:text-2xl">{t('localMedia.mediaFileList')}</CardTitle>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant="outline" className="rounded-full px-3 py-1">
                  {t('localMedia.files_count', { count: scanResult.total_count })}
                </Badge>
                <Badge variant="destructive" className="rounded-full px-3 py-1">
                  {filesNeedingTranslation.length} {t('library.missing')}
                </Badge>
                {filesNeedingTranslation.length > 0 && (
                  <Button size="sm" onClick={handleBatchTranslate} className="rounded-full">
                    <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">{t('localMedia.batchTranslateAll')}</span>
                    <span className="sm:hidden">{t('localMedia.batchTranslate')}</span>
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-4 sm:p-5">
            {mediaFiles.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">{t('localMedia.noMediaFiles')}</p>
            ) : (
              <div className="space-y-2.5">
                {paginatedMediaFiles.map((file) => (
                  <Card key={file.filepath} className="overflow-hidden rounded-[24px] border-border/70 bg-background/40 transition-colors hover:bg-background/60">
                    <CardContent className="p-3">
                      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(260px,0.55fr)_auto] lg:items-center">
                        <div className="flex min-w-0 items-start gap-3">
                          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[18px] border border-border/70 bg-muted/35">
                            <Film className="h-5 w-5 text-primary" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="flex min-w-0 flex-wrap items-center gap-2">
                              <h3 className="truncate text-sm font-bold sm:text-base" title={file.filename}>
                                {file.filename}
                              </h3>
                              {file.missing_languages.length === 0 ? (
                                <Badge variant="outline" className="shrink-0 text-xs">
                                  <CheckCircle2 className="mr-1 h-3 w-3 text-green-600" />
                                  <span>{t('localMedia.complete')}</span>
                                </Badge>
                              ) : (
                                <Badge variant="destructive" className="shrink-0 text-xs">
                                  {t('localMedia.missing', { count: file.missing_languages.length })}
                                </Badge>
                              )}
                            </div>
                            <p className="mt-1 truncate font-mono text-xs text-muted-foreground" title={file.filepath}>
                              {file.filepath}
                            </p>
                            <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                              <HardDrive className="h-3 w-3" />
                              <span>{formatBytes(file.size_bytes)}</span>
                            </div>
                          </div>
                        </div>

                        <div className="rounded-[20px] border border-border/60 bg-muted/20 p-2.5">
                          <div className="flex flex-wrap gap-1.5">
                            {file.existing_subtitle_langs.length > 0 ? (
                              file.existing_subtitle_langs.slice(0, 4).map((lang) => (
                                <Badge key={lang} variant="secondary" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-xs text-muted-foreground">{t('localMedia.existingSubtitles')} -</span>
                            )}
                            {file.existing_subtitle_langs.length > 4 && (
                              <Badge variant="outline" className="text-xs">
                                +{file.existing_subtitle_langs.length - 4}
                              </Badge>
                            )}
                          </div>

                          {file.missing_languages.length > 0 && (
                            <div className="mt-2 flex flex-wrap gap-1.5">
                              {file.missing_languages.slice(0, 4).map((lang) => (
                                <Badge key={lang} variant="destructive" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))}
                              {file.missing_languages.length > 4 && (
                                <Badge variant="destructive" className="text-xs">
                                  +{file.missing_languages.length - 4}
                                </Badge>
                              )}
                            </div>
                          )}

                          {file.subtitle_files.length > 0 && (
                            <p className="mt-2 truncate text-xs text-muted-foreground" title={file.subtitle_files.join(', ')}>
                              {t('localMedia.subtitleFilesList')} {file.subtitle_files.length}
                            </p>
                          )}
                        </div>

                        <div className="flex justify-end">
                          {file.missing_languages.length > 0 ? (
                            <Button
                              size="sm"
                              variant="default"
                              onClick={() => handleQuickTranslate(file)}
                              className="w-full rounded-full lg:w-auto"
                            >
                              <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                              {t('localMedia.translate')}
                            </Button>
                          ) : (
                            <div className="flex items-center gap-2 rounded-full border border-border/70 bg-background/45 px-3 py-2 text-xs text-muted-foreground">
                              <CheckCircle2 className="h-4 w-4 text-green-600" />
                              {t('localMedia.complete')}
                            </div>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
            {mediaFiles.length > mediaPageSize && (
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-border/70 bg-background/35 p-3">
                <div className="text-xs sm:text-sm text-muted-foreground">
                  {t('library.page', { current: mediaPage, total: mediaTotalPages })}
                  <span className="hidden sm:inline">
                    ，{t('library.pageRange', { from: mediaRangeStart, to: mediaRangeEnd, total: mediaFiles.length })}
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setMediaPage(mediaPage - 1)}
                    disabled={mediaPage === 1}
                  >
                    {t('library.previousPage')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setMediaPage(mediaPage + 1)}
                    disabled={mediaPage >= mediaTotalPages}
                  >
                    {t('library.nextPage')}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Translate Dialog */}
      <AlertDialog open={translateDialogOpen} onOpenChange={setTranslateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('localMedia.createTranslationTask')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('localMedia.createTaskFor', { filename: selectedFile?.filename })}
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* File Info */}
            {selectedFile && (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">{t('localMedia.fileSize')}</span>
                  <span>{formatBytes(selectedFile.size_bytes)}</span>
                </div>

                {selectedFile.existing_subtitle_langs.length > 0 && (
                  <div className="flex items-start gap-2">
                    <span className="text-muted-foreground">{t('localMedia.existingSubtitles')}</span>
                    <div className="flex gap-1 flex-wrap">
                      {selectedFile.existing_subtitle_langs.map((lang) => (
                        <Badge key={lang} variant="secondary" className="text-xs">
                          {getLanguageName(lang)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {selectedFile.missing_languages.length > 0 && (
                  <div className="flex items-start gap-2">
                    <span className="text-muted-foreground">{t('localMedia.missingLanguagesLabel')}</span>
                    <div className="flex gap-1 flex-wrap">
                      {selectedFile.missing_languages.map((lang) => (
                        <Badge key={lang} variant="destructive" className="text-xs">
                          {getLanguageName(lang)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Target Languages Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('localMedia.selectTargetLangs')}</label>
              <div className="flex flex-wrap gap-2">
                {LANGUAGES.map((lang) => (
                  <Badge
                    key={lang.code}
                    variant={selectedTargetLangs.includes(lang.code) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleTargetLang(lang.code)}
                  >
                    {lang.name}
                    {selectedFile?.missing_languages.includes(lang.code) && (
                      <span className="ml-1 text-xs">{t('localMedia.missingLang')}</span>
                    )}
                  </Badge>
                ))}
              </div>
              {selectedTargetLangs.length === 0 && (
                <p className="text-xs text-destructive">{t('localMedia.selectAtLeastOne')}</p>
              )}
            </div>

            {/* Task Info */}
            <div className="text-xs text-muted-foreground space-y-1">
              <p>
                •{' '}
                {selectedFile?.existing_subtitle_langs.length
                  ? t('localMedia.taskInfoUseExisting')
                  : t('localMedia.taskInfoASR')}
              </p>
              <p>• {t('localMedia.taskInfoBackground')}</p>
              <p>• {t('localMedia.taskInfoProgress')}</p>
            </div>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={createJobMutation.isPending}>{t('common.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleTranslateConfirm}
              disabled={selectedTargetLangs.length === 0 || createJobMutation.isPending}
            >
              {createJobMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {t('localMedia.createTask')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function formatCacheTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  if (Number.isNaN(date.getTime())) {
    return timestamp
  }

  return date.toLocaleString()
}

function buildDirectoryStatsFromScan(data: ScanDirectoryResponse): DirectoryStatsResponse {
  const subtitleFiles = new Set(data.media_files.flatMap((file) => file.subtitle_files))
  const videoFormats = data.media_files.reduce<Record<string, number>>((formats, file) => {
    const dotIndex = file.filename.lastIndexOf('.')
    const extension = dotIndex >= 0 ? file.filename.slice(dotIndex).toLowerCase() : ''
    if (extension) {
      formats[extension] = (formats[extension] ?? 0) + 1
    }
    return formats
  }, {})

  return {
    directory: data.directory,
    total_media_files: data.media_files.length,
    total_size_bytes: data.media_files.reduce((total, file) => total + file.size_bytes, 0),
    total_subtitle_files: subtitleFiles.size,
    video_formats: videoFormats,
  }
}
