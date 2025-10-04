import { useState, useMemo, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
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
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
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
import api from '@/lib/api'
import { formatBytes, formatDuration, getLanguageName } from '@/lib/utils'
import type { JellyfinLibrary, JellyfinMediaItem } from '@/types/api'
import { useTranslation } from 'react-i18next'

export function Library() {
  const { t } = useTranslation()
  const [selectedLibrary, setSelectedLibrary] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
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

  // Fetch libraries
  const { data: libraries, isLoading: librariesLoading } = useQuery<JellyfinLibrary[]>({
    queryKey: ['jellyfin-libraries'],
    queryFn: () => api.getJellyfinLibraries(),
  })

  // Fetch library items
  const { data: items, isLoading: itemsLoading } = useQuery<JellyfinMediaItem[]>({
    queryKey: ['jellyfin-library-items', selectedLibrary],
    queryFn: () => api.getJellyfinLibraryItems(selectedLibrary!),
    enabled: !!selectedLibrary,
  })

  // Scan library mutation
  const scanMutation = useMutation({
    mutationFn: (libraryId: string) =>
      api.scanJellyfinLibrary({
        library_id: libraryId,
        required_langs: ['zh-CN', 'en', 'ja'],
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
      const response = await api.getSeriesEpisodes(item.id)
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
    { code: 'zh-CN', name: '简体中文' },
    { code: 'en', name: 'English' },
    { code: 'ja', name: '日本語' },
    { code: 'ko', name: '한국어' },
  ]

  // Filter and search items (client-side for current page)
  const filteredItems = useMemo(() => {
    if (!items) return []

    return items.filter(item => {
      // Search filter
      if (searchQuery && !item.name.toLowerCase().includes(searchQuery.toLowerCase())) {
        return false
      }

      // Type filter
      if (typeFilter !== 'all' && item.type !== typeFilter) {
        return false
      }

      // Year filter
      if (yearFilter !== 'all') {
        const year = parseInt(yearFilter)
        if (!item.production_year || item.production_year !== year) {
          return false
        }
      }

      return true
    })
  }, [items, searchQuery, typeFilter, yearFilter])

  // Paginated items (directly from filtered items, no client-side grouping)
  const paginatedItems = useMemo(() => {
    const startIndex = (page - 1) * pageSize
    const endIndex = startIndex + pageSize
    return filteredItems.slice(startIndex, endIndex)
  }, [filteredItems, page, pageSize])

  // Total pages (based on filtered items)
  const totalPages = Math.ceil(filteredItems.length / pageSize)

  // Reset page to 1 if current page exceeds total pages
  useEffect(() => {
    if (page > totalPages && totalPages > 0) {
      setPage(1)
    }
  }, [page, totalPages])

  // Reset page when filters change
  const handleFilterChange = () => {
    setPage(1)
  }

  // Extract unique types and years
  const availableTypes = useMemo(() => {
    if (!items) return []
    const types = new Set(items.map(item => item.type))
    return Array.from(types).sort()
  }, [items])

  const availableYears = useMemo(() => {
    if (!items) return []
    const years = new Set(
      items
        .map(item => item.production_year)
        .filter((year): year is number => year !== null)
    )
    return Array.from(years).sort((a, b) => b - a)
  }, [items])

  return (
    <div className="space-y-6">
      {/* Libraries */}
      <Card>
        <CardHeader className="p-3 sm:p-4">
          <CardTitle className="text-base sm:text-lg">{t('library.libraries')}</CardTitle>
        </CardHeader>
        <CardContent className="p-3 sm:p-4">
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
            {librariesLoading ? (
              <p className="text-muted-foreground col-span-full">{t('library.loadingLibraries')}</p>
            ) : (
              libraries?.map((lib) => (
                <div
                  key={lib.id}
                  className={`rounded-lg border overflow-hidden cursor-pointer transition-all hover:shadow-lg ${
                    selectedLibrary === lib.id ? 'border-primary ring-2 ring-primary' : 'hover:border-primary/50'
                  }`}
                  onClick={() => {
                    setSelectedLibrary(lib.id)
                    setPage(1) // Reset to first page when selecting library
                  }}
                >
                  {/* Library Cover Image */}
                  <div className="relative aspect-[4/3] bg-muted">
                    {lib.image_url ? (
                      <img
                        src={lib.image_url}
                        alt={lib.name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-primary/20 to-primary/5">
                        <LibraryIcon className="h-12 w-12 text-primary/60" />
                      </div>
                    )}
                    {/* Selected indicator */}
                    {selectedLibrary === lib.id && (
                      <div className="absolute top-1.5 right-1.5">
                        <Badge variant="default" className="text-xs">已选择</Badge>
                      </div>
                    )}
                  </div>

                  {/* Library Info */}
                  <div className="p-2 sm:p-2.5">
                    <h3 className="font-semibold text-sm mb-0.5 truncate" title={lib.name}>{lib.name}</h3>
                    <p className="text-xs text-muted-foreground truncate">
                      {lib.item_count} {t('library.items')} • {lib.type || '未分类'}
                    </p>
                  </div>
                  <Button
                    className="w-full"
                    size="sm"
                    variant={selectedLibrary === lib.id ? 'default' : 'outline'}
                    onClick={(e) => {
                      e.stopPropagation()
                      scanMutation.mutate(lib.id)
                    }}
                    disabled={scanMutation.isPending}
                  >
                    <Play className="mr-1.5 h-3.5 w-3.5" />
                    <span className="text-xs">{t('library.scan')}</span>
                  </Button>
                </div>
              ))
            )}
          </div>
        </CardContent>
      </Card>

      {/* Media Items */}
      {selectedLibrary && (
        <Card>
          <CardHeader className="p-3 sm:p-4">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <CardTitle className="text-base sm:text-lg">{t('library.mediaItems')}</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline" className="text-[10px] sm:text-xs">
                  显示 {filteredItems.length} 项（总计 {items?.length || 0}）
                </Badge>
              </div>
            </div>

            {/* Filters */}
            <div className="grid gap-2 sm:gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 mt-3 sm:mt-4">
              <Input
                placeholder="搜索媒体..."
                value={searchQuery}
                onChange={(e) => {
                  setSearchQuery(e.target.value)
                  handleFilterChange()
                }}
              />
              <Select value={typeFilter} onValueChange={(value) => {
                setTypeFilter(value)
                handleFilterChange()
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="媒体类型" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有类型</SelectItem>
                  {availableTypes.map(type => (
                    <SelectItem key={type} value={type}>
                      {type === 'Movie' ? '电影' : type === 'Episode' ? '剧集' : type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select value={yearFilter} onValueChange={(value) => {
                setYearFilter(value)
                handleFilterChange()
              }}>
                <SelectTrigger>
                  <SelectValue placeholder="年份" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有年份</SelectItem>
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
                  }}
                >
                  <Filter className="mr-1 sm:mr-2 h-4 w-4" />
                  <span className="hidden sm:inline">清除过滤</span>
                  <span className="sm:hidden">清除</span>
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent className="p-3 sm:p-4">
            {itemsLoading ? (
              <p className="text-muted-foreground">{t('library.loadingItems')}</p>
            ) : filteredItems.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                {items?.length === 0 ? t('library.noItems') : '未找到匹配的媒体项目'}
              </p>
            ) : (
              <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 2xl:grid-cols-6">
                {paginatedItems.map((item) => (
                  <Card key={item.id} className="overflow-hidden hover:shadow-lg transition-shadow">
                    {/* Poster Image */}
                    <div className="relative aspect-[2/3] bg-muted">
                      {item.image_url ? (
                        <img
                          src={item.image_url}
                          alt={item.name}
                          className="w-full h-full object-cover"
                          loading="lazy"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center">
                          {item.type === 'Movie' ? (
                            <Film className="h-16 w-16 text-muted-foreground" />
                          ) : (
                            <Tv className="h-16 w-16 text-muted-foreground" />
                          )}
                        </div>
                      )}
                      {/* Type Badge */}
                      <div className="absolute top-2 right-2">
                        <Badge variant={item.type === 'Movie' ? 'default' : 'secondary'}>
                          {item.type === 'Series' && item.child_count
                            ? `剧集 ${item.child_count}集`
                            : item.type === 'Movie' ? '电影' : item.type === 'Series' ? '剧集' : item.type}
                        </Badge>
                      </div>
                      {/* Missing Languages Badge */}
                      {item.missing_languages.length > 0 && (
                        <div className="absolute top-2 left-2">
                          <Badge variant="destructive">
                            缺失 {item.missing_languages.length}
                          </Badge>
                        </div>
                      )}
                    </div>

                    <CardContent className="p-2 sm:p-3 space-y-1.5 sm:space-y-2">
                      {/* Title */}
                      <div>
                        <h3 className="font-semibold text-xs sm:text-sm line-clamp-2 min-h-[2rem]">
                          {item.name}
                        </h3>
                        {item.type === 'Series' && item.child_count ? (
                          <p className="text-[10px] sm:text-xs text-muted-foreground">
                            共 {item.child_count} 集
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
                      <div className="flex items-center gap-1.5 sm:gap-2 text-[10px] sm:text-xs text-muted-foreground flex-wrap">
                        {item.production_year && (
                          <span>{item.production_year}</span>
                        )}
                        {item.community_rating && (
                          <div className="flex items-center gap-1">
                            <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
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
                      <div className="flex items-center gap-2 sm:gap-3 text-[10px] sm:text-xs text-muted-foreground">
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
                      <div className="space-y-1.5 sm:space-y-2">
                        {/* Audio Languages */}
                        {item.audio_languages.length > 0 && (
                          <div className="flex items-start gap-1.5 sm:gap-2">
                            <span className="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">音频:</span>
                            <div className="flex gap-1 flex-wrap">
                              {item.audio_languages.map((lang) => (
                                <Badge key={lang} variant="outline" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Subtitle Languages */}
                        {item.subtitle_languages.length > 0 && (
                          <div className="flex items-start gap-1.5 sm:gap-2">
                            <span className="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">字幕:</span>
                            <div className="flex gap-1 flex-wrap">
                              {item.subtitle_languages.map((lang) => (
                                <Badge key={lang} variant="secondary" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Missing Languages */}
                        {item.missing_languages.length > 0 && (
                          <div className="flex items-start gap-1.5 sm:gap-2">
                            <span className="text-[10px] sm:text-xs text-muted-foreground whitespace-nowrap">缺失:</span>
                            <div className="flex gap-1 flex-wrap">
                              {item.missing_languages.map((lang) => (
                                <Badge key={lang} variant="destructive" className="text-xs">
                                  {getLanguageName(lang)}
                                </Badge>
                              ))}
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
                      <div className="flex gap-2 pt-1.5 sm:pt-2 border-t">
                        {/* Quick Translate Button */}
                        {item.missing_languages.length > 0 ? (
                          <Button
                            size="sm"
                            variant="default"
                            className="flex-1"
                            onClick={() => handleQuickTranslate(item)}
                          >
                            <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                            <span className="hidden sm:inline">快速翻译</span>
                            <span className="sm:hidden">翻译</span>
                          </Button>
                        ) : (
                          <div className="flex-1 flex items-center justify-center gap-1 sm:gap-2 text-[10px] sm:text-xs text-green-600">
                            <CheckCircle2 className="h-4 w-4" />
                            字幕完整
                          </div>
                        )}

                        {/* View Details Button */}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            if (item.type === 'Series') {
                              handleViewSeries(item)
                            } else {
                              handleViewDetails(item)
                            }
                          }}
                          title={item.type === 'Series' ? "查看剧集列表" : "查看详情"}
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
            {filteredItems.length > pageSize && (
              <div className="flex items-center justify-between gap-3 pt-3 sm:pt-4 border-t flex-wrap">
                <div className="text-xs sm:text-sm text-muted-foreground">
                  第 {page} / {totalPages} 页
                  <span className="hidden sm:inline">
                    ，显示 {(page - 1) * pageSize + 1}-{Math.min(page * pageSize, filteredItems.length)} 项（共 {filteredItems.length} 项）
                  </span>
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page - 1)}
                    disabled={page === 1}
                  >
                    上一页
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page + 1)}
                    disabled={page >= totalPages}
                  >
                    下一页
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
            <AlertDialogTitle>创建翻译任务</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedItem ? (
                <>为 <strong>{selectedItem.name}</strong> 创建字幕翻译任务</>
              ) : (
                <>
                  为 <strong>{selectedSeries[0]?.series_name}</strong> 的{' '}
                  <strong className="text-destructive">
                    {selectedSeries.filter(ep => ep.missing_languages.length > 0).length} 集
                  </strong>{' '}
                  批量创建翻译任务
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* Media Info */}
            {selectedItem && (
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground">类型:</span>
                <Badge variant="outline">
                  {selectedItem?.type === 'Movie' ? '电影' : selectedItem?.type === 'Episode' ? '剧集' : selectedItem?.type}
                </Badge>
              </div>
              {selectedItem?.series_name && (
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">剧集:</span>
                  <span>{selectedItem.series_name}</span>
                </div>
              )}
              {selectedItem?.audio_languages && selectedItem.audio_languages.length > 0 && (
                <div className="flex items-start gap-2">
                  <span className="text-muted-foreground">现有音频:</span>
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
                  <span className="text-muted-foreground">现有字幕:</span>
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
                <div className="font-medium">批量翻译说明：</div>
                <ul className="space-y-1 text-muted-foreground ml-4 list-disc">
                  <li>将为所有缺失字幕的剧集创建翻译任务</li>
                  <li>每集将根据其缺失的语言创建独立任务</li>
                  <li>共 {selectedSeries.filter(ep => ep.missing_languages.length > 0).length} 集需要翻译</li>
                </ul>
              </div>
            )}

            {/* Target Languages Selection */}
            <div className="space-y-2">
              <label className="text-sm font-medium">选择翻译目标语言:</label>
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
                      <span className="ml-1 text-xs">(缺失)</span>
                    )}
                  </Badge>
                ))}
              </div>
              {selectedTargetLangs.length === 0 && (
                <p className="text-xs text-destructive">请至少选择一个目标语言</p>
              )}
            </div>

            {/* Task Info */}
            <div className="text-xs text-muted-foreground space-y-1">
              <p>• 如果媒体没有字幕，系统将先进行语音识别（ASR）生成字幕</p>
              <p>• 翻译任务将在后台队列中执行</p>
              <p>• 可在"任务列表"页面查看进度</p>
            </div>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={createJobMutation.isPending}>
              取消
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={selectedItem ? handleTranslateConfirm : handleBatchTranslateConfirm}
              disabled={selectedTargetLangs.length === 0 || createJobMutation.isPending}
            >
              {createJobMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {selectedItem ? '创建任务' : `批量创建 ${
                selectedSeries.filter(ep =>
                  selectedTargetLangs.some(lang => ep.missing_languages.includes(lang))
                ).length
              } 个任务`}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Media Details Dialog */}
      <AlertDialog open={detailDialogOpen} onOpenChange={setDetailDialogOpen}>
        <AlertDialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <AlertDialogHeader>
            <AlertDialogTitle>媒体详情</AlertDialogTitle>
            <AlertDialogDescription>
              查看 <strong>{selectedItem?.name}</strong> 的完整信息
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
                      {selectedItem.season_number && ` - 第${selectedItem.season_number}季`}
                      {selectedItem.episode_number && ` 第${selectedItem.episode_number}集`}
                    </p>
                  )}
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {selectedItem?.type && (
                    <div>
                      <span className="text-muted-foreground">类型: </span>
                      <Badge variant="outline">
                        {selectedItem.type === 'Movie' ? '电影' : selectedItem.type === 'Episode' ? '剧集' : selectedItem.type}
                      </Badge>
                    </div>
                  )}
                  
                  {selectedItem?.production_year && (
                    <div>
                      <span className="text-muted-foreground">年份: </span>
                      <span className="font-medium">{selectedItem.production_year}</span>
                    </div>
                  )}

                  {selectedItem?.official_rating && (
                    <div>
                      <span className="text-muted-foreground">分级: </span>
                      <Badge variant="outline">{selectedItem.official_rating}</Badge>
                    </div>
                  )}

                  {selectedItem?.community_rating && (
                    <div className="flex items-center gap-2">
                      <span className="text-muted-foreground">评分: </span>
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
                    <span className="text-sm text-muted-foreground">类型标签: </span>
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
                <h4 className="font-semibold mb-2">简介</h4>
                <p className="text-sm text-muted-foreground leading-relaxed">
                  {selectedItem.overview}
                </p>
              </div>
            )}

            {/* Language Information */}
            <div className="space-y-3">
              <h4 className="font-semibold">语言信息</h4>
              
              {/* Audio Languages */}
              <div>
                <span className="text-sm text-muted-foreground">音频语言: </span>
                <div className="flex gap-1 flex-wrap mt-1">
                  {selectedItem?.audio_languages && selectedItem.audio_languages.length > 0 ? (
                    selectedItem.audio_languages.map((lang) => (
                      <Badge key={lang} variant="outline">
                        {getLanguageName(lang)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">无</span>
                  )}
                </div>
              </div>

              {/* Subtitle Languages */}
              <div>
                <span className="text-sm text-muted-foreground">字幕语言: </span>
                <div className="flex gap-1 flex-wrap mt-1">
                  {selectedItem?.subtitle_languages && selectedItem.subtitle_languages.length > 0 ? (
                    selectedItem.subtitle_languages.map((lang) => (
                      <Badge key={lang} variant="secondary">
                        {getLanguageName(lang)}
                      </Badge>
                    ))
                  ) : (
                    <span className="text-sm text-muted-foreground">无</span>
                  )}
                </div>
              </div>

              {/* Missing Languages */}
              {selectedItem?.missing_languages && selectedItem.missing_languages.length > 0 && (
                <div>
                  <span className="text-sm text-muted-foreground">缺失语言: </span>
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
                <h4 className="font-semibold mb-2">文件路径</h4>
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
                  创建翻译任务
                </Button>
              </div>
            )}
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel>关闭</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Series Episodes Dialog */}
      <AlertDialog open={seriesDialogOpen} onOpenChange={setSeriesDialogOpen}>
        <AlertDialogContent className="max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
          <AlertDialogHeader className="flex-shrink-0">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <AlertDialogTitle>剧集列表</AlertDialogTitle>
                <AlertDialogDescription>
                  <strong>{selectedSeries[0]?.series_name}</strong> 共 {selectedSeries.length} 集
                  {selectedSeries.filter(ep => ep.missing_languages.length > 0).length > 0 && (
                    <span className="text-destructive ml-2">
                      • {selectedSeries.filter(ep => ep.missing_languages.length > 0).length} 集缺失字幕
                    </span>
                  )}
                </AlertDialogDescription>
              </div>
              {/* Batch Translate Button */}
              {selectedSeries.filter(ep => ep.missing_languages.length > 0).length > 0 && (
                <Button
                  size="sm"
                  onClick={handleBatchTranslateSeries}
                  className="flex-shrink-0"
                >
                  <Languages className="mr-2 h-4 w-4" />
                  一键翻译全部
                </Button>
              )}
            </div>
          </AlertDialogHeader>

          {/* Scrollable Episodes Container */}
          <div className="flex-1 overflow-y-auto px-1 py-4 -mx-1">
            <div className="grid gap-3 pr-3">
              {selectedSeries
                .sort((a, b) => {
                  // Sort by season then episode
                  if (a.season_number !== b.season_number) {
                    return (a.season_number || 0) - (b.season_number || 0)
                  }
                  return (a.episode_number || 0) - (b.episode_number || 0)
                })
                .map((episode) => (
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
                                  <span className="hidden sm:inline">翻译</span>
                                </Button>
                              ) : (
                                <div className="flex items-center gap-1 text-[10px] sm:text-xs text-green-600">
                                  <CheckCircle2 className="h-4 w-4" />
                                  <span className="hidden sm:inline">完整</span>
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
                            {episode.subtitle_languages.length > 0 && (
                              <div className="flex items-center gap-1">
                                <span className="text-muted-foreground">字幕:</span>
                                {episode.subtitle_languages.slice(0, 2).map((lang) => (
                                  <Badge key={lang} variant="secondary" className="text-xs">
                                    {getLanguageName(lang)}
                                  </Badge>
                                ))}
                                {episode.subtitle_languages.length > 2 && (
                                  <span className="text-muted-foreground">
                                    +{episode.subtitle_languages.length - 2}
                                  </span>
                                )}
                              </div>
                            )}
                            {episode.missing_languages.length > 0 && (
                              <div className="flex items-center gap-1">
                                <span className="text-muted-foreground">缺失:</span>
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
            <AlertDialogCancel>关闭</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
