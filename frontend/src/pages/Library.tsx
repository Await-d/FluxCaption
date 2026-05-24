import { useState, useMemo, useEffect } from 'react'
import { keepPreviousData, useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Library as LibraryIcon,
  Play,
  Star,
  Clock,
  HardDrive,
  Film,
  Tv,
  Filter,
  Languages,
  Info,
  CheckCircle2,
  Loader2,
} from 'lucide-react'
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
} from '../components/ui/AlertDialog'
import api from '../lib/api'
import { formatBytes, formatDuration, getLanguageName } from '../lib/utils'
import type { JellyfinItemListResponse, JellyfinLibrary, JellyfinMediaItem } from '../types/api'
import { useTranslation } from 'react-i18next'
import { PageHero } from '../components/ui/PageHero'

export function Library() {
  const { t } = useTranslation()
  const [selectedLibrary, setSelectedLibrary] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [yearFilter, setYearFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [translateDialogOpen, setTranslateDialogOpen] = useState(false)
  const [detailDialogOpen, setDetailDialogOpen] = useState(false)
  const [seriesDialogOpen, setSeriesDialogOpen] = useState(false)
  const [selectedItem, setSelectedItem] = useState<JellyfinMediaItem | null>(null)
  const [selectedSeries, setSelectedSeries] = useState<JellyfinMediaItem[]>([])
  const [selectedTargetLangs, setSelectedTargetLangs] = useState<string[]>([])
  const queryClient = useQueryClient()

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearchQuery(searchQuery.trim())
      setPage(1)
    }, 300)

    return () => window.clearTimeout(timer)
  }, [searchQuery])

  // Fetch libraries
  const { data: libraries, isLoading: librariesLoading } = useQuery<JellyfinLibrary[]>({
    queryKey: ['jellyfin-libraries'],
    queryFn: () => api.getJellyfinLibraries(),
  })

  // Fetch library items
  const {
    data: itemsResponse,
    isLoading: itemsLoading,
    isFetching: itemsFetching,
  } = useQuery<JellyfinItemListResponse>({
    queryKey: [
      'jellyfin-library-items',
      selectedLibrary,
      {
        page,
        pageSize,
        search: debouncedSearchQuery,
        type: typeFilter,
        year: yearFilter,
      },
    ],
    queryFn: () =>
      api.getJellyfinLibraryItems(selectedLibrary!, {
        limit: pageSize,
        offset: (page - 1) * pageSize,
        search: debouncedSearchQuery || undefined,
        item_type: typeFilter !== 'all' ? typeFilter : undefined,
        year: yearFilter !== 'all' ? Number(yearFilter) : undefined,
      }),
    enabled: !!selectedLibrary,
    placeholderData: keepPreviousData,
    staleTime: 10 * 60 * 1000,
  })

  const items = itemsResponse?.items ?? []
  const totalItems = itemsResponse?.total ?? 0

  // Scan library mutation
  const scanMutation = useMutation({
    mutationFn: (libraryId: string) =>
      api.scanJellyfinLibrary({
        library_id: libraryId,
        // required_langs will be inferred from auto translation rules
        auto_process: true,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
    },
  })

  // Create translation job mutation
  const createJobMutation = useMutation({
    mutationFn: async ({ itemId, targetLangs }: { itemId: string; targetLangs: string[] }) => {
      return await api.createJob({
        source_type: 'jellyfin',
        item_id: itemId,
        target_langs: targetLangs,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setTranslateDialogOpen(false)
      setSelectedItem(null)
      setSelectedTargetLangs([])
    },
  })

  // Handle quick translate action
  const handleQuickTranslate = (item: JellyfinMediaItem) => {
    // Check if this is a Series item (from backend)
    if (item.type === 'Series') {
      // Open series dialog to show all episodes
      handleViewSeries(item)
    } else {
      // Single item (movie), open translate dialog
      setSelectedItem(item)
      setSelectedTargetLangs([])  // Don't auto-select, let user choose
      setTranslateDialogOpen(true)
    }
  }

  // Handle view series - fetch episodes from backend API
  const handleViewSeries = async (item: JellyfinMediaItem) => {
    if (item.type !== 'Series') return

    try {
      // Fetch episodes for this series using the new API endpoint
      let response = queryClient.getQueryData<JellyfinItemListResponse>([
        'jellyfin-series-episodes',
        item.id,
      ])
      if (!response) {
        response = await queryClient.fetchQuery<JellyfinItemListResponse>({
          queryKey: ['jellyfin-series-episodes', item.id],
          queryFn: () => api.getSeriesEpisodes(item.id),
          staleTime: 10 * 60 * 1000,
        })
      }
      console.log(`[Library] Fetched ${response.items.length} episodes for series: ${item.name}`)
      setSelectedSeries(response.items)
      setSeriesDialogOpen(true)
    } catch (error) {
      console.error('[Library] Failed to fetch series episodes:', error)
    }
  }

  // Handle view details action
  const handleViewDetails = (item: JellyfinMediaItem) => {
    setSelectedItem(item)
    setDetailDialogOpen(true)
  }

  // Handle translate confirm
  const handleTranslateConfirm = () => {
    if (selectedItem && selectedTargetLangs.length > 0) {
      createJobMutation.mutate({
        itemId: selectedItem.id,
        targetLangs: selectedTargetLangs,
      })
    }
  }

  // Handle batch translate all episodes in series
  const handleBatchTranslateSeries = () => {
    // Find episodes that have missing languages
    const episodesNeedingTranslation = selectedSeries.filter(ep => ep.missing_languages.length > 0)

    if (episodesNeedingTranslation.length === 0) {
      return // All episodes already have complete subtitles
    }

    // Don't pre-select languages, let user choose
    setSelectedTargetLangs([])
    setSelectedItem(null) // Clear single item
    setTranslateDialogOpen(true)
  }

  // Handle batch translate confirm
  const handleBatchTranslateConfirm = async () => {
    if (selectedTargetLangs.length === 0) return

    // Filter episodes that need the selected target languages
    const episodesToTranslate = selectedSeries.filter(ep => {
      return selectedTargetLangs.some(lang => ep.missing_languages.includes(lang))
    })

    // Create translation job for each episode sequentially to avoid race conditions
    for (const episode of episodesToTranslate) {
      const episodeMissingLangs = selectedTargetLangs.filter(lang =>
        episode.missing_languages.includes(lang)
      )

      if (episodeMissingLangs.length > 0) {
        try {
          await createJobMutation.mutateAsync({
            itemId: episode.id,
            targetLangs: episodeMissingLangs,
          })
        } catch (error) {
          console.error(`Failed to create job for episode ${episode.id}:`, error)
          // Continue with next episode even if one fails
        }
      }
    }

    // Close dialogs after all jobs are created
    setTranslateDialogOpen(false)
    setSeriesDialogOpen(false)
  }

  // Toggle target language selection
  const toggleTargetLang = (lang: string) => {
    setSelectedTargetLangs((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    )
  }

  // Available languages for translation
  const LANGUAGES = [
    { code: 'zh-CN', name: t('languages.zh-CN') },
    { code: 'en', name: t('languages.en') },
    { code: 'ja', name: t('languages.ja') },
    { code: 'ko', name: t('languages.ko') },
  ]

  const paginatedItems = items

  const totalPages = Math.ceil(totalItems / pageSize)
  const loadedRangeStart = totalItems > 0 ? (page - 1) * pageSize + 1 : 0
  const loadedRangeEnd = Math.min(page * pageSize, totalItems)
  const currentPageMissingCount = useMemo(
    () => paginatedItems.filter((item) => item.missing_languages.length > 0).length,
    [paginatedItems]
  )
  const selectedLibraryInfo = useMemo(
    () => libraries?.find((library) => library.id === selectedLibrary),
    [libraries, selectedLibrary]
  )

  // Reset page to 1 if current page exceeds total pages
  useEffect(() => {
    if (page > totalPages && totalPages > 0) {
      setPage(totalPages)
    }
  }, [page, totalPages])

  // Reset page when filters change
  const handleFilterChange = () => {
    setPage(1)
  }

  // Extract unique types and years
  const availableTypes = useMemo(() => {
    if (selectedLibraryInfo?.type === 'movies') return ['Movie']
    if (selectedLibraryInfo?.type === 'tvshows') return ['Series']
    return ['Movie', 'Series']
  }, [selectedLibraryInfo])

  const availableYears = useMemo(() => {
    if (!items.length) return []
    const years = new Set(
      items
        .map(item => item.production_year)
        .filter((year): year is number => year !== null)
    )
    return Array.from(years).sort((a, b) => b - a)
  }, [items])

  const selectedSeriesMissingCount = useMemo(
    () => selectedSeries.filter((episode) => episode.missing_languages.length > 0).length,
    [selectedSeries]
  )

  const sortedSelectedSeries = useMemo(
    () => [...selectedSeries].sort((a, b) => {
      if (a.season_number !== b.season_number) {
        return (a.season_number || 0) - (b.season_number || 0)
      }
      return (a.episode_number || 0) - (b.episode_number || 0)
    }),
    [selectedSeries]
  )

  return (
    <div className="space-y-6 lg:space-y-8">
      <PageHero
        eyebrow={t('pageHero.library.eyebrow')}
        title={t('library.libraries')}
        description={t('pageHero.library.description')}
        actions={selectedLibrary ? (
          <Button onClick={() => scanMutation.mutate(selectedLibrary)} disabled={scanMutation.isPending}>
            <Play className="mr-2 h-4 w-4" />
            {scanMutation.isPending ? t('common.loading') : t('library.scanLibrary')}
          </Button>
        ) : undefined}
        metrics={[
          { label: t('pageHero.library.metrics.libraries.label'), value: String(libraries?.length ?? 0), detail: t('pageHero.library.metrics.libraries.detail') },
          { label: t('pageHero.library.metrics.loaded.label'), value: String(totalItems), detail: selectedLibrary ? t('pageHero.library.metrics.loaded.detailSelected') : t('pageHero.library.metrics.loaded.detailEmpty') },
          { label: t('pageHero.library.metrics.filtered.label'), value: String(items.length), detail: t('pageHero.library.metrics.filtered.detail') },
        ]}
      />

      {/* Libraries */}
      <Card className="overflow-hidden rounded-[30px]">
        <CardHeader className="border-b border-border/60 p-4 sm:p-5">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <div className="eyebrow-label mb-2">Jellyfin</div>
              <CardTitle className="text-xl sm:text-2xl">{t('library.libraries')}</CardTitle>
            </div>
            <Badge variant="outline" className="w-fit rounded-full px-3 py-1 text-xs">
              {libraries?.length ?? 0} {t('library.libraries')}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="p-4 sm:p-5">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
            {librariesLoading ? (
              <p className="text-muted-foreground col-span-full">{t('library.loadingLibraries')}</p>
            ) : (
              libraries?.map((lib) => (
                <div
                  key={lib.id}
                  className={`group cursor-pointer overflow-hidden rounded-[26px] border bg-background/35 transition-all duration-200 hover:-translate-y-1 hover:border-primary/60 hover:bg-background/55 hover:shadow-[0_18px_46px_-32px_rgba(0,0,0,0.65)] ${selectedLibrary === lib.id ? 'border-primary bg-primary/10 shadow-[0_18px_48px_-34px_hsl(var(--primary))] ring-2 ring-primary/40' : 'border-border/70'
                    }`}
                  onClick={() => {
                    setSelectedLibrary(lib.id)
                    setPage(1) // Reset to first page when selecting library
                  }}
                >
                  {/* Library Cover Image */}
                  <div className="relative aspect-[16/9] overflow-hidden bg-muted">
                    {lib.image_url ? (
                      <img
                        src={lib.image_url}
                        alt={lib.name}
                        className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                        loading="lazy"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-[radial-gradient(circle_at_top_left,hsl(var(--primary)/0.28),transparent_34%),linear-gradient(135deg,hsl(var(--muted)),hsl(var(--background)))]">
                        <div className="flex h-16 w-16 items-center justify-center rounded-[24px] border border-border/70 bg-background/45 backdrop-blur">
                          <LibraryIcon className="h-8 w-8 text-primary" />
                        </div>
                      </div>
                    )}
                    <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-black/55 to-transparent" />
                    {/* Selected indicator */}
                    {selectedLibrary === lib.id && (
                      <div className="absolute top-1.5 right-1.5">
                        <Badge variant="default" className="text-xs">{t('library.selected')}</Badge>
                      </div>
                    )}
                  </div>

                  {/* Library Info */}
                  <div className="space-y-3 p-3 sm:p-4">
                    <div>
                      <h3 className="truncate text-base font-bold" title={lib.name}>{lib.name}</h3>
                      <p className="mt-1 text-xs text-muted-foreground truncate">
                        {lib.type || t('library.uncategorized')}
                      </p>
                    </div>
                    <div className="grid grid-cols-[1fr_auto] items-center gap-3 rounded-[20px] border border-border/60 bg-background/35 px-3 py-2">
                      <div>
                        <div className="text-[10px] font-semibold uppercase tracking-[0.2em] text-muted-foreground">{t('library.items')}</div>
                        <div className="text-lg font-extrabold">{lib.item_count}</div>
                      </div>
                      <Button
                        size="sm"
                        variant={selectedLibrary === lib.id ? 'default' : 'outline'}
                        onClick={(e) => {
                          e.stopPropagation()
                          scanMutation.mutate(lib.id)
                        }}
                        disabled={scanMutation.isPending}
                        className="rounded-full"
                      >
                        <Play className="mr-1.5 h-3.5 w-3.5" />
                        <span className="text-xs">{t('library.scan')}</span>
                      </Button>
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Media Items */}
      {selectedLibrary && (
        <Card className="overflow-hidden rounded-[30px]">
          <CardHeader className="space-y-4 border-b border-border/60 p-4 sm:p-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-muted-foreground">
                  {selectedLibraryInfo?.name || t('library.mediaItems')}
                </div>
                <CardTitle className="mt-2 text-xl sm:text-2xl">{t('library.mediaItems')}</CardTitle>
              </div>
              <div className="grid grid-cols-3 gap-2 text-center sm:min-w-[360px]">
                <div className="rounded-[20px] border border-border/70 bg-background/35 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{t('library.showing')}</div>
                  <div className="mt-1 text-lg font-extrabold">{itemsFetching ? '...' : items.length}</div>
                </div>
                <div className="rounded-[20px] border border-border/70 bg-background/35 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{t('library.totalItems')}</div>
                  <div className="mt-1 text-lg font-extrabold">{totalItems}</div>
                </div>
                <div className="rounded-[20px] border border-destructive/30 bg-destructive/10 px-3 py-2">
                  <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground">{t('library.missing')}</div>
                  <div className="mt-1 text-lg font-extrabold text-destructive">{currentPageMissingCount}</div>
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="grid gap-2 rounded-[24px] border border-border/70 bg-background/35 p-3 sm:gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,1fr)_180px_160px_auto]">
              <Input
                placeholder={t('library.searchPlaceholder')}
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                }}
              />
              <Select value={typeFilter} onValueChange={(value) => {
                setTypeFilter(value)
                handleFilterChange()
              }}>
                <SelectTrigger>
                  <SelectValue placeholder={t('library.mediaType')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('library.allTypes')}</SelectItem>
                  {availableTypes.map(type => (
                    <SelectItem key={type} value={type}>
                      {type === 'Movie' ? t('library.movie') : type === 'Episode' ? t('library.episode') : type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={yearFilter} onValueChange={(value) => {
                setYearFilter(value)
                handleFilterChange()
              }}>
                <SelectTrigger>
                  <SelectValue placeholder={t('library.year')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('library.allYears')}</SelectItem>
                  {availableYears.map(year => (
                    <SelectItem key={year} value={year.toString()}>
                      {year}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {(searchQuery || typeFilter !== 'all' || yearFilter !== 'all') && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    setSearchQuery('')
                    setTypeFilter('all')
                    setYearFilter('all')
                    setPage(1)
                  }}
                >
                  <Filter className="mr-1 sm:mr-2 h-4 w-4" />
                  <span className="hidden sm:inline">{t('library.clearFilters')}</span>
                  <span className="sm:hidden">{t('library.clear')}</span>
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-4 sm:p-5">
            {itemsLoading ? (
              <p className="text-muted-foreground">{t('library.loadingItems')}</p>
            ) : paginatedItems.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                {totalItems === 0 ? t('library.noItems') : t('library.noMatchingItems')}
              </p>
            ) : (
              <div className="grid grid-cols-[repeat(auto-fill,minmax(190px,1fr))] gap-4">
                {paginatedItems.map((item) => (
                  <Card key={item.id} className="group overflow-hidden rounded-[28px] border-border/70 bg-background/45 transition-all duration-200 hover:-translate-y-1 hover:border-primary/50 hover:bg-background/65 hover:shadow-[0_22px_55px_-38px_rgba(0,0,0,0.7)]">
                    {/* Poster Image */}
                    <div className="relative aspect-[2/3] overflow-hidden bg-muted">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="h-full w-full object-cover transition duration-300 group-hover:scale-105"
                          loading="lazy"
                        />
                      ) : (
                        <div className="flex h-full w-full items-center justify-center bg-[radial-gradient(circle_at_35%_20%,hsl(var(--primary)/0.22),transparent_32%),linear-gradient(145deg,hsl(var(--muted)),hsl(var(--background)))]">
                          <div className="flex h-20 w-20 items-center justify-center rounded-[28px] border border-border/70 bg-background/45 backdrop-blur">
                            {item.type === 'Movie' ? (
                              <Film className="h-10 w-10 text-primary" />
                            ) : (
                              <Tv className="h-10 w-10 text-primary" />
                            )}
                          </div>
                        </div>
                      )}
                      <div className="absolute inset-x-0 bottom-0 h-28 bg-gradient-to-t from-black/70 via-black/20 to-transparent" />
                      {/* Type Badge */}
                      <div className="absolute top-2 right-2">
                        <Badge variant={item.type === 'Movie' ? 'default' : 'secondary'} className="shadow-sm backdrop-blur">
                          {item.type === 'Series' && item.child_count
                            ? `${t('library.series')} ${item.child_count}${t('library.episodes')}`
                            : item.type === 'Movie' ? t('library.movie') : item.type === 'Series' ? t('library.series') : item.type}
                        </Badge>
                      </div>
                      {/* Missing Languages Badge */}
                      {item.missing_languages.length > 0 && (
                        <div className="absolute top-2 left-2">
                          <Badge variant="destructive" className="shadow-sm">
                            {t('library.missing')} {item.missing_languages.length}
                          </Badge>
                        </div>
                      )}
                    </div>

                    <CardContent className="space-y-3 p-3">
                      {/* Title */}
                      <div>
                        <h3 className="line-clamp-2 min-h-[2.5rem] text-sm font-bold leading-snug">
                          {item.name}
                        </h3>
                        {item.type === 'Series' && item.child_count ? (
                          <p className="text-[10px] sm:text-xs text-muted-foreground">
                            {t('library.totalEpisodes', { count: item.child_count })}
                          </p>
                        ) : item.series_name && (
                          <p className="text-[10px] sm:text-xs text-muted-foreground">
                            {item.series_name}
                            {item.season_number && ` S${item.season_number}`}
                            {item.episode_number && `E${item.episode_number}`}
                          </p>
                        )}
                      </div>

                      {/* Metadata */}
                      <div className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
                        {item.production_year && (
                          <span>{item.production_year}</span>
                        )}
                        {item.community_rating && (
                          <div className="flex items-center gap-1">
                            <Star className="h-3 w-3 fill-primary text-primary" />
                            <span>{item.community_rating.toFixed(1)}</span>
                          </div>
                        )}
                        {item.official_rating && (
                          <Badge variant="outline" className="text-xs">
                            {item.official_rating}
                          </Badge>
                        )}
                      </div>

                      {/* Genres */}
                      {item.genres && item.genres.length > 0 && (
                        <div className="flex gap-1 flex-wrap">
                          {item.genres.slice(0, 3).map((genre) => (
                            <Badge key={genre} variant="secondary" className="text-xs">
                              {genre}
                            </Badge>
                          ))}
                        </div>
                      )}

                      {/* Duration and Size */}
                      <div className="flex items-center gap-3 rounded-[18px] border border-border/60 bg-muted/25 px-3 py-2 text-xs text-muted-foreground">
                        {item.duration_seconds && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDuration(item.duration_seconds)}</span>
                          </div>
                        )}
                        {item.file_size_bytes && (
                          <div className="flex items-center gap-1 hidden sm:flex">
                            <HardDrive className="h-3 w-3" />
                            <span>{formatBytes(item.file_size_bytes)}</span>
                          </div>
                        )}
                      </div>

                      {/* Languages */}
                      <div className="space-y-2 rounded-[18px] border border-border/60 bg-background/30 p-2.5">
                        {/* Audio Languages */}
                        {item.audio_languages.length > 0 && (
                          <div className="flex items-start gap-1.5 sm:gap-2">
                            <span className="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">{t('library.audio')}:</span>
                            <div className="flex gap-1 flex-wrap">
                              {item.audio_languages.map((lang) => (
                                <Badge key={lang} variant="outline" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Subtitle Streams - Detailed View */}
                        {item.subtitle_streams && item.subtitle_streams.length > 0 && (
                          <div className="flex items-start gap-1.5 sm:gap-2">
                            <span className="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">{t('library.subtitles')}:</span>
                            <div className="flex gap-1 flex-wrap">
                              {item.subtitle_streams.slice(0, 4).map((stream) => (
                                <Badge
                                  key={stream.index}
                                  variant="secondary"
                                  className="text-xs flex items-center gap-1"
                                  title={`${stream.display_title} • ${stream.codec.toUpperCase()} • ${stream.is_external ? t('library.externalFile') : t('library.embedded')}`}
                                >
                                  {getLanguageName(stream.language)}
                                  {stream.is_external && (
                                    <span className="text-[9px] opacity-70">[{t('library.ext')}]</span>
                                  )}
                                  {stream.is_default && (
                                    <span className="text-[9px] opacity-70">⭐</span>
                                  )}
                                </Badge>
                              ))}
                              {item.subtitle_streams.length > 4 && (
                                <Badge variant="outline" className="text-xs">
                                  +{item.subtitle_streams.length - 4}
                                </Badge>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Missing Languages */}
                        {item.missing_languages.length > 0 && (
                          <div className="flex items-start gap-1.5 sm:gap-2">
                            <span className="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">{t('library.missing')}:</span>
                            <div className="flex gap-1 flex-wrap">
                              {item.missing_languages.slice(0, 3).map((lang) => (
                                <Badge key={lang} variant="destructive" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))}
                              {item.missing_languages.length > 3 && (
                                <Badge variant="destructive" className="text-xs">
                                  +{item.missing_languages.length - 3}
                                </Badge>
                              )}
                            </div>
                          </div>
                        )}
                      </div>

                      {/* Overview (truncated) */}
                      {item.overview && (
                        <p className="text-[10px] sm:text-xs text-muted-foreground line-clamp-3 hidden sm:block">
                          {item.overview}
                        </p>
                      )}

                      {/* Quick Actions */}
                      <div className="flex gap-2 border-t border-border/60 pt-2">
                        {/* Quick Translate Button */}
                        {item.missing_languages.length > 0 ? (
                          <Button
                            size="sm"
                            variant="default"
                            className="flex-1 rounded-full"
                            onClick={() => handleQuickTranslate(item)}
                          >
                            <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                            <span className="hidden sm:inline">{t('library.quickTranslate')}</span>
                            <span className="sm:hidden">{t('library.translate')}</span>
                          </Button>
                        ) : (
                          <div className="flex flex-1 items-center justify-center gap-1 text-[10px] text-foreground sm:gap-2 sm:text-xs">
                            <CheckCircle2 className="h-4 w-4" />
                            {t('library.subtitleComplete')}
                          </div>
                        )}

                        {/* View Details Button */}
                        <Button
                          size="sm"
                          variant="outline"
                          className="rounded-full"
                          onClick={() => {
                            if (item.type === 'Series') {
                              handleViewSeries(item)
                            } else {
                              handleViewDetails(item)
                            }
                          }}
                          title={item.type === 'Series' ? t('library.viewSeriesList') : t('library.viewDetails')}
                        >
                          <Info className="h-4 w-4" />
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Pagination Controls */}
            {totalItems > pageSize && (
              <div className="mt-5 flex flex-wrap items-center justify-between gap-3 rounded-[24px] border border-border/70 bg-background/35 p-3">
                <div className="text-xs sm:text-sm text-muted-foreground">
                  {t('library.page', { current: page, total: totalPages })}
                  <span className="hidden sm:inline">
                    ，{t('library.pageRange', { from: loadedRangeStart, to: loadedRangeEnd, total: totalItems })}
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                  >
                    {t('library.previousPage')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page + 1)}
                    disabled={page >= totalPages || itemsFetching}
                  >
                    {t('library.nextPage')}
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Quick Translate Dialog */}
      <AlertDialog open={translateDialogOpen} onOpenChange={setTranslateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('library.createTranslationTask')}</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedItem ? (
                <>{t('library.createTaskFor')} <strong>{selectedItem.name}</strong> {t('library.createSubtitleTask')}</>
              ) : (
                <>
                  {t('library.batchCreateFor')} <strong>{selectedSeries[0]?.series_name}</strong> {t('library.of')}{' '}
                  <strong className="text-destructive">
                    {selectedSeriesMissingCount} {t('library.episodes')}
                  </strong>{' '}
                  {t('library.batchCreateTasks')}
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* Media Info */}
            {selectedItem && (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">{t('library.type')}:</span>
                  <Badge variant="outline">
                    {selectedItem?.type === 'Movie' ? t('library.movie') : selectedItem?.type === 'Episode' ? t('library.episode') : selectedItem?.type}
                  </Badge>
                </div>
                {selectedItem?.series_name && (
                  <div className="flex items-center gap-2">
                    <span className="text-muted-foreground">{t('library.series')}:</span>
                    <span>{selectedItem.series_name}</span>
                  </div>
                )}
                {selectedItem?.audio_languages && selectedItem.audio_languages.length > 0 && (
                  <div className="flex items-start gap-2">
                    <span className="text-muted-foreground">{t('library.existingAudio')}:</span>
                    <div className="flex gap-1 flex-wrap">
                      {selectedItem.audio_languages.map((lang) => (
                        <Badge key={lang} variant="outline" className="text-xs">
                          {getLanguageName(lang)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
                {selectedItem?.subtitle_languages && selectedItem.subtitle_languages.length > 0 && (
                  <div className="flex items-start gap-2">
                    <span className="text-muted-foreground">{t('library.existingSubtitles')}:</span>
                    <div className="flex gap-1 flex-wrap">
                      {selectedItem.subtitle_languages.map((lang) => (
                        <Badge key={lang} variant="secondary" className="text-xs">
                          {getLanguageName(lang)}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Batch Translation Info */}
            {!selectedItem && selectedSeries.length > 0 && (
              <div className="space-y-2 p-3 bg-muted rounded-lg text-sm">
                <div className="font-medium">{t('library.batchTranslateInfo')}：</div>
                <ul className="space-y-1 text-muted-foreground ml-4 list-disc">
                  <li>{t('library.batchTranslateDesc1')}</li>
                  <li>{t('library.batchTranslateDesc2')}</li>
                  <li>{t('library.totalEpisodesNeedTranslation', { count: selectedSeriesMissingCount })}</li>
                </ul>
              </div>
            )}

            {/* Target Languages Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('library.selectTargetLanguages')}:</label>
              <div className="flex flex-wrap gap-2">
                {LANGUAGES.map((lang) => (
                  <Badge
                    key={lang.code}
                    variant={selectedTargetLangs.includes(lang.code) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleTargetLang(lang.code)}
                  >
                    {lang.name}
                    {selectedItem?.missing_languages.includes(lang.code) && (
                      <span className="ml-1 text-xs">({t('library.missing')})</span>
                    )}
                  </Badge>
                ))}
              </div>
              {selectedTargetLangs.length === 0 && (
                <p className="text-xs text-destructive">{t('library.selectAtLeastOne')}</p>
              )}
            </div>

            {/* Task Info */}
            <div className="text-xs text-muted-foreground space-y-1">
              <p>• {t('library.taskInfo1')}</p>
              <p>• {t('library.taskInfo2')}</p>
              <p>• {t('library.taskInfo3')}</p>
            </div>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={createJobMutation.isPending}>
              {t('library.cancel')}
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={selectedItem ? handleTranslateConfirm : handleBatchTranslateConfirm}
              disabled={selectedTargetLangs.length === 0 || createJobMutation.isPending}
            >
              {createJobMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {selectedItem ? t('library.createTask') : t('library.batchCreateCount', {
                  count: selectedSeries.filter(ep =>
                  selectedTargetLangs.some(lang => ep.missing_languages.includes(lang))
                ).length
              })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Media Details Dialog */}
      <AlertDialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <AlertDialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <AlertDialogHeader>
            <AlertDialogTitle>{t('library.mediaDetails')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('library.viewDetailsFor')} <strong>{selectedItem?.name}</strong> {t('library.fullInfo')}
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* Poster and Basic Info */}
            <div className="flex gap-4">
              {/* Poster */}
              <div className="flex-shrink-0 w-48">
                {selectedItem?.image_url ? (
                  <img
                    src={selectedItem.image_url}
                    alt={selectedItem.name}
                    className="w-full rounded-lg shadow-md"
                  />
                ) : (
                  <div className="w-full aspect-[2/3] bg-muted rounded-lg flex items-center justify-center">
                    {selectedItem?.type === 'Movie' ? (
                      <Film className="h-16 w-16 text-muted-foreground" />
                    ) : (
                      <Tv className="h-16 w-16 text-muted-foreground" />
                    )}
                  </div>
                )}
              </div>

              {/* Basic Info */}
              <div className="flex-1 space-y-3">
                <div>
                  <h3 className="text-xl font-bold">{selectedItem?.name}</h3>
                  {selectedItem?.series_name && (
                    <p className="text-sm text-muted-foreground mt-1">
                      {selectedItem.series_name}
                      {selectedItem.season_number && ` - ${t('library.season', { number: selectedItem.season_number })}`}
                      {selectedItem.episode_number && ` ${t('library.episodeNumber', { number: selectedItem.episode_number })}`}
                    </p>
                  )}
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {selectedItem?.type && (
                    <div>
                      <span className="text-muted-foreground">{t('library.type')}: </span>
                      <Badge variant="outline">
                        {selectedItem.type === 'Movie' ? t('library.movie') : selectedItem.type === 'Episode' ? t('library.episode') : selectedItem.type}
                      </Badge>
                    </div>
                  )}

                  {selectedItem?.production_year && (
                    <div>
                      <span className="text-muted-foreground">{t('library.year')}: </span>
                      <span className="font-medium">{selectedItem.production_year}</span>
                    </div>
                  )}

                  {selectedItem?.official_rating && (
                    <div>
                      <span className="text-muted-foreground">{t('library.rating')}: </span>
                      <Badge variant="outline">{selectedItem.official_rating}</Badge>
                    </div>
                  )}

                  {selectedItem?.community_rating && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">{t('library.score')}: </span>
                      <div className="flex items-center gap-1">
                        <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                        <span className="font-medium">{selectedItem.community_rating.toFixed(1)}</span>
                      </div>
                    </div>
                  )}

                  {selectedItem?.duration_seconds && (
                    <div className="flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      <span>{formatDuration(selectedItem.duration_seconds)}</span>
                    </div>
                  )}

                  {selectedItem?.file_size_bytes && (
                    <div className="flex items-center gap-2">
                      <HardDrive className="h-4 w-4 text-muted-foreground" />
                      <span>{formatBytes(selectedItem.file_size_bytes)}</span>
                    </div>
                  )}
                </div>

                {/* Genres */}
                {selectedItem?.genres && selectedItem.genres.length > 0 && (
                  <div>
                    <span className="text-sm text-muted-foreground">{t('library.genreTags')}: </span>
                    <div className="flex gap-1 flex-wrap mt-1">
                      {selectedItem.genres.map((genre) => (
                        <Badge key={genre} variant="secondary" className="text-xs">
                          {genre}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Overview */}
            {selectedItem?.overview && (
              <div>
                <h4 className="font-semibold mb-2">{t('library.overview')}</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {selectedItem.overview}
                </p>
              </div>
            )}

            {/* Language Information */}
            <div className="space-y-3">
              <h4 className="font-semibold">{t('library.languageInfo')}</h4>

              {/* Audio Languages */}
              <div>
                <span className="text-sm text-muted-foreground">{t('library.audioLanguages')}: </span>
                <div className="flex gap-1 flex-wrap mt-1">
                  {selectedItem?.audio_languages && selectedItem.audio_languages.length > 0 ? (
                    selectedItem.audio_languages.map((lang) => (
                      <Badge key={lang} variant="outline">
                        {getLanguageName(lang)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">{t('library.none')}</span>
                  )}
                </div>
              </div>

              {/* Subtitle Streams - Detailed Information */}
              <div>
                <span className="text-sm text-muted-foreground">{t('library.subtitleDetails')}: </span>
                <div className="space-y-2 mt-2">
                  {selectedItem?.subtitle_streams && selectedItem.subtitle_streams.length > 0 ? (
                    selectedItem.subtitle_streams.map((stream) => (
                      <div
                        key={stream.index}
                        className="flex items-center gap-2 p-2 bg-muted/50 rounded text-sm"
                      >
                        <Badge variant="secondary">
                          {getLanguageName(stream.language)}
                        </Badge>
                        <div className="flex gap-1 text-xs text-muted-foreground">
                          <Badge variant="outline" className="text-xs">
                            {stream.codec.toUpperCase()}
                          </Badge>
                          <Badge variant={stream.is_external ? "default" : "outline"} className="text-xs">
                            {stream.is_external ? t('library.externalFile') : t('library.embedded')}
                          </Badge>
                          {stream.is_default && (
                            <Badge variant="outline" className="text-xs">
                              ⭐ {t('library.default')}
                            </Badge>
                          )}
                          {stream.is_forced && (
                            <Badge variant="outline" className="text-xs">
                              {t('library.forced')}
                            </Badge>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">{t('library.none')}</span>
                  )}
                </div>
              </div>

              {/* Missing Languages */}
              {selectedItem?.missing_languages && selectedItem.missing_languages.length > 0 && (
                <div>
                  <span className="text-sm text-muted-foreground">{t('library.missingLanguages')}: </span>
                  <div className="flex gap-1 flex-wrap mt-1">
                    {selectedItem.missing_languages.map((lang) => (
                      <Badge key={lang} variant="destructive">
                        {getLanguageName(lang)}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* File Path */}
            {selectedItem?.path && (
              <div>
                <h4 className="font-semibold mb-2">{t('library.filePath')}</h4>
                <p className="text-xs text-muted-foreground font-mono bg-muted p-2 rounded">
                  {selectedItem.path}
                </p>
              </div>
            )}

            {/* Quick Actions in Details */}
            {selectedItem?.missing_languages && selectedItem.missing_languages.length > 0 && (
              <div className="flex gap-2 pt-2 border-t">
                <Button
                  className="flex-1"
                  onClick={() => {
                    setDetailDialogOpen(false)
                    handleQuickTranslate(selectedItem)
                  }}
                >
                  <Languages className="mr-2 h-4 w-4" />
                  {t('library.createTranslationTask')}
                </Button>
              </div>
            )}
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel>{t('library.close')}</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Series Episodes Dialog */}
      <AlertDialog open={seriesDialogOpen} onOpenChange={setSeriesDialogOpen}>
        <AlertDialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
          <AlertDialogHeader className="flex-shrink-0">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <AlertDialogTitle>{t('library.episodeList')}</AlertDialogTitle>
                <AlertDialogDescription>
                  <strong>{selectedSeries[0]?.series_name}</strong> {t('library.totalEpisodesCount', { count: selectedSeries.length })}
                  {selectedSeriesMissingCount > 0 && (
                    <span className="text-destructive ml-2">
                       • {t('library.episodesMissingSubtitles', { count: selectedSeriesMissingCount })}
                    </span>
                  )}
                </AlertDialogDescription>
              </div>
              {/* Batch Translate Button */}
              {selectedSeriesMissingCount > 0 && (
                <Button
                  size="sm"
                  onClick={handleBatchTranslateSeries}
                  className="flex-shrink-0"
                >
                  <Languages className="mr-2 h-4 w-4" />
                  {t('library.translateAll')}
                </Button>
              )}
            </div>
          </AlertDialogHeader>

          {/* Scrollable Episodes Container */}
          <div className="flex-1 overflow-y-auto px-1 py-4 -mx-1">
            <div className="grid gap-3 pr-3">
              {sortedSelectedSeries.map((episode) => (
                  <Card key={episode.id} className="overflow-hidden">
                    <CardContent className="p-3 sm:p-4">
                      <div className="flex gap-3 sm:gap-4">
                        {/* Episode Thumbnail */}
                        <div className="flex-shrink-0 w-28 sm:w-40">
                          {episode.image_url ? (
                            <img
                              src={episode.image_url}
                              alt={episode.name}
                              className="w-full aspect-video object-cover rounded"
                            />
                          ) : (
                            <div className="w-full aspect-video bg-muted rounded flex items-center justify-center">
                              <Play className="h-8 w-8 text-muted-foreground" />
                            </div>
                          )}
                        </div>

                        {/* Episode Info */}
                        <div className="flex-1 space-y-1.5 sm:space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-1.5 sm:gap-2 flex-wrap">
                                <Badge variant="outline" className="text-xs shrink-0">
                                  S{episode.season_number || 0}E{episode.episode_number || 0}
                                </Badge>
                                <h4 className="font-semibold text-sm sm:text-base truncate">{episode.name}</h4>
                              </div>
                              {episode.overview && (
                                <p className="text-xs sm:text-sm text-muted-foreground mt-1 line-clamp-2 hidden sm:block">
                                  {episode.overview}
                                </p>
                              )}
                            </div>

                            {/* Episode Actions */}
                            <div className="flex gap-1.5 sm:gap-2 shrink-0">
                              {episode.missing_languages.length > 0 ? (
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={() => {
                                    setSeriesDialogOpen(false)
                                    handleQuickTranslate(episode)
                                  }}
                                >
                                  <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                                  <span className="hidden sm:inline">{t('library.translate')}</span>
                                </Button>
                              ) : (
                                <div className="flex items-center gap-1 text-[10px] sm:text-xs text-green-600 dark:text-green-400">
                                  <CheckCircle2 className="h-4 w-4" />
                                  <span className="hidden sm:inline">{t('library.complete')}</span>
                                </div>
                              )}
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setSeriesDialogOpen(false)
                                  handleViewDetails(episode)
                                }}
                              >
                                <Info className="h-4 w-4" />
                              </Button>
                            </div>
                          </div>

                          {/* Episode Metadata */}
                          <div className="flex items-center gap-2 sm:gap-3 text-[10px] sm:text-xs text-muted-foreground">
                            {episode.duration_seconds && (
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatDuration(episode.duration_seconds)}
                              </div>
                            )}
                            {episode.community_rating && (
                              <div className="flex items-center gap-1 hidden sm:flex">
                                <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                                {episode.community_rating.toFixed(1)}
                              </div>
                            )}
                          </div>

                          {/* Language Status */}
                          <div className="flex items-center gap-2 flex-wrap text-[10px] sm:text-xs">
                            {episode.subtitle_streams && episode.subtitle_streams.length > 0 && (
                              <div className="flex items-center gap-1 flex-wrap">
                                <span className="text-muted-foreground">{t('library.subtitles')}:</span>
                                {episode.subtitle_streams.slice(0, 3).map((stream) => (
                                  <Badge
                                    key={stream.index}
                                    variant="secondary"
                                    className="text-xs flex items-center gap-0.5"
                                    title={`${stream.display_title} • ${stream.codec.toUpperCase()} • ${stream.is_external ? t('library.externalFile') : t('library.embedded')}`}
                                  >
                                    {getLanguageName(stream.language)}
                                    {stream.is_external && (
                                      <span className="text-[8px] opacity-70">[{t('library.ext')}]</span>
                                    )}
                                    {stream.is_default && (
                                      <span className="text-[8px]">⭐</span>
                                    )}
                                  </Badge>
                                ))}
                                {episode.subtitle_streams.length > 3 && (
                                  <span className="text-muted-foreground">
                                    +{episode.subtitle_streams.length - 3}
                                  </span>
                                )}
                              </div>
                            )}
                            {episode.missing_languages.length > 0 && (
                              <div className="flex items-center gap-1">
                                <span className="text-muted-foreground">{t('library.missing')}:</span>
                                {episode.missing_languages.slice(0, 1).map((lang) => (
                                  <Badge key={lang} variant="destructive" className="text-xs">
                                    {getLanguageName(lang)}
                                  </Badge>
                                ))}
                                {episode.missing_languages.length > 1 && (
                                  <span className="text-destructive">
                                    +{episode.missing_languages.length - 1}
                                  </span>
                                )}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
            </div>
          </div>

          <AlertDialogFooter className="flex-shrink-0 border-t pt-4 mt-0">
            <AlertDialogCancel>{t('library.close')}</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
