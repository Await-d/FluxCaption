import { useState, useMemo } from 'react'
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
    // Check if this is a series (grouped episodes)
    if ((item as any)._isSeries) {
      // Open series dialog to show all episodes
      handleViewSeries(item)
    } else {
      // Single item (movie or individual episode), open translate dialog
      setSelectedItem(item)
      setSelectedTargetLangs(item.missing_languages.length > 0 ? item.missing_languages : [])
      setTranslateDialogOpen(true)
    }
  }

  // Handle view series (for grouped episodes)
  const handleViewSeries = (item: JellyfinMediaItem) => {
    // Find all episodes for this series
    const seriesEpisodes = filteredItems.filter(
      (i) => i.type === 'Episode' && i.series_name === item.series_name
    )
    setSelectedSeries(seriesEpisodes)
    setSeriesDialogOpen(true)
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

  // Group items: Movies stay as-is, Episodes grouped by series
  const groupedItems = useMemo(() => {
    const movies: JellyfinMediaItem[] = []
    const seriesMap = new Map<string, JellyfinMediaItem[]>()

    // Filter out Series and Season types, only keep Episode and Movie
    const validItems = filteredItems.filter(item => {
      return item.type === 'Movie' || item.type === 'Episode'
    })

    console.log(`[Library] Filtered ${filteredItems.length} items to ${validItems.length} valid items (removed Series/Season types)`)

    validItems.forEach(item => {
      if (item.type === 'Movie') {
        movies.push(item)
      } else if (item.type === 'Episode' && item.series_name) {
        const key = item.series_name
        if (!seriesMap.has(key)) {
          seriesMap.set(key, [])
        }
        seriesMap.get(key)!.push(item)
      } else {
        // Episode without series_name, treat as individual item
        movies.push(item)
      }
    })

    console.log(`[Library] Grouping result: ${movies.length} movies, ${seriesMap.size} series`)

    // Convert series map to array of representative items
    const seriesItems: Array<JellyfinMediaItem & { _isSeries?: boolean; _episodeCount?: number }> = []
    seriesMap.forEach((episodes) => {
      // Use first episode as representative, but mark it as a series
      const representative = {
        ...episodes[0],
        _isSeries: true,
        _episodeCount: episodes.length
      }
      seriesItems.push(representative)
    })

    return [...movies, ...seriesItems]
  }, [filteredItems])

  // Paginated items
  const paginatedItems = useMemo(() => {
    const startIndex = (page - 1) * pageSize
    const endIndex = startIndex + pageSize
    return groupedItems.slice(startIndex, endIndex)
  }, [groupedItems, page, pageSize])

  // Total pages (based on grouped items)
  const totalPages = Math.ceil(groupedItems.length / pageSize)

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
        <CardHeader>
          <CardTitle>{t('library.libraries')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {librariesLoading ? (
              <p className="text-muted-foreground">{t('library.loadingLibraries')}</p>
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
                  <div className="relative aspect-video bg-muted">
                    {lib.image_url ? (
                      <img
                        src={lib.image_url}
                        alt={lib.name}
                        className="w-full h-full object-cover"
                        loading="lazy"
                      />
                    ) : (
                      <div className="absolute inset-0 flex items-center justify-center bg-gradient-to-br from-primary/20 to-primary/5">
                        <LibraryIcon className="h-16 w-16 text-primary/60" />
                      </div>
                    )}
                    {/* Selected indicator */}
                    {selectedLibrary === lib.id && (
                      <div className="absolute top-2 right-2">
                        <Badge variant="default">已选择</Badge>
                      </div>
                    )}
                  </div>

                  {/* Library Info */}
                  <div className="p-4">
                    <h3 className="font-semibold text-lg mb-1">{lib.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {lib.item_count} {t('library.items')} • {lib.type || '未分类'}
                    </p>
                  </div>
                  <Button
                    className="w-full mt-3"
                    size="sm"
                    variant={selectedLibrary === lib.id ? 'default' : 'outline'}
                    onClick={(e) => {
                      e.stopPropagation()
                      scanMutation.mutate(lib.id)
                    }}
                    disabled={scanMutation.isPending}
                  >
                    <Play className="mr-2 h-4 w-4" />
                    {t('library.scan')}
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
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle>{t('library.mediaItems')}</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline">
                  {filteredItems.length} / {items?.length || 0} {t('library.items')}
                </Badge>
              </div>
            </div>
            
            {/* Filters */}
            <div className="grid gap-3 md:grid-cols-4 mt-4">
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
                  <Filter className="mr-2 h-4 w-4" />
                  清除过滤
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {itemsLoading ? (
              <p className="text-muted-foreground">{t('library.loadingItems')}</p>
            ) : filteredItems.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">
                {items?.length === 0 ? t('library.noItems') : '未找到匹配的媒体项目'}
              </p>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
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
                          {(item as any)._isSeries 
                            ? `剧集 ${(item as any)._episodeCount}集`
                            : item.type === 'Movie' ? '电影' : item.type === 'Episode' ? '剧集' : item.type}
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

                    <CardContent className="p-4 space-y-3">
                      {/* Title */}
                      <div>
                        <h3 className="font-semibold line-clamp-2 min-h-[2.5rem]">
                          {(item as any)._isSeries ? item.series_name : item.name}
                        </h3>
                        {(item as any)._isSeries ? (
                          <p className="text-xs text-muted-foreground">
                            共 {(item as any)._episodeCount} 集
                          </p>
                        ) : item.series_name && (
                          <p className="text-xs text-muted-foreground">
                            {item.series_name}
                            {item.season_number && ` S${item.season_number}`}
                            {item.episode_number && `E${item.episode_number}`}
                          </p>
                        )}
                      </div>

                      {/* Metadata */}
                      <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
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
                      <div className="flex items-center gap-3 text-xs text-muted-foreground">
                        {item.duration_seconds && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDuration(item.duration_seconds)}</span>
                          </div>
                        )}
                        {item.file_size_bytes && (
                          <div className="flex items-center gap-1">
                            <HardDrive className="h-3 w-3" />
                            <span>{formatBytes(item.file_size_bytes)}</span>
                          </div>
                        )}
                      </div>

                      {/* Languages */}
                      <div className="space-y-2">
                        {/* Audio Languages */}
                        {item.audio_languages.length > 0 && (
                          <div className="flex items-start gap-2">
                            <span className="text-xs text-muted-foreground whitespace-nowrap">音频:</span>
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
                          <div className="flex items-start gap-2">
                            <span className="text-xs text-muted-foreground whitespace-nowrap">字幕:</span>
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
                          <div className="flex items-start gap-2">
                            <span className="text-xs text-muted-foreground whitespace-nowrap">缺失:</span>
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
                        <p className="text-xs text-muted-foreground line-clamp-3">
                          {item.overview}
                        </p>
                      )}

                      {/* Quick Actions */}
                      <div className="flex gap-2 pt-2 border-t">
                        {/* Quick Translate Button */}
                        {item.missing_languages.length > 0 ? (
                          <Button
                            size="sm"
                            variant="default"
                            className="flex-1"
                            onClick={() => handleQuickTranslate(item)}
                          >
                            <Languages className="mr-2 h-4 w-4" />
                            快速翻译
                          </Button>
                        ) : (
                          <div className="flex-1 flex items-center justify-center gap-2 text-xs text-green-600">
                            <CheckCircle2 className="h-4 w-4" />
                            字幕完整
                          </div>
                        )}
                        
                        {/* View Details Button */}
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleViewDetails(item)}
                          title="查看详情"
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
              <div className="flex items-center justify-between pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  显示 {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, filteredItems.length)} / 共 {filteredItems.length} 项
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
              为 <strong>{selectedItem?.name}</strong> 创建字幕翻译任务
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* Media Info */}
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
              onClick={handleTranslateConfirm}
              disabled={selectedTargetLangs.length === 0 || createJobMutation.isPending}
            >
              {createJobMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              创建任务
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
        <AlertDialogContent className="max-w-6xl max-h-[85vh] overflow-y-auto">
          <AlertDialogHeader>
            <AlertDialogTitle>剧集列表</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{selectedSeries[0]?.series_name}</strong> 共 {selectedSeries.length} 集
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-3 py-4">
            {/* Episodes Grid */}
            <div className="grid gap-3 max-h-[60vh] overflow-y-auto">
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
                    <CardContent className="p-4">
                      <div className="flex gap-4">
                        {/* Episode Thumbnail */}
                        <div className="flex-shrink-0 w-40">
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
                        <div className="flex-1 space-y-2">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1">
                              <div className="flex items-center gap-2">
                                <Badge variant="outline">
                                  S{episode.season_number || 0}E{episode.episode_number || 0}
                                </Badge>
                                <h4 className="font-semibold">{episode.name}</h4>
                              </div>
                              {episode.overview && (
                                <p className="text-sm text-muted-foreground mt-1 line-clamp-2">
                                  {episode.overview}
                                </p>
                              )}
                            </div>

                            {/* Episode Actions */}
                            <div className="flex gap-2">
                              {episode.missing_languages.length > 0 ? (
                                <Button
                                  size="sm"
                                  variant="default"
                                  onClick={() => {
                                    setSeriesDialogOpen(false)
                                    handleQuickTranslate(episode)
                                  }}
                                >
                                  <Languages className="mr-2 h-4 w-4" />
                                  翻译
                                </Button>
                              ) : (
                                <div className="flex items-center gap-2 text-xs text-green-600">
                                  <CheckCircle2 className="h-4 w-4" />
                                  字幕完整
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
                          <div className="flex items-center gap-3 text-xs text-muted-foreground">
                            {episode.duration_seconds && (
                              <div className="flex items-center gap-1">
                                <Clock className="h-3 w-3" />
                                {formatDuration(episode.duration_seconds)}
                              </div>
                            )}
                            {episode.community_rating && (
                              <div className="flex items-center gap-1">
                                <Star className="h-3 w-3 fill-yellow-400 text-yellow-400" />
                                {episode.community_rating.toFixed(1)}
                              </div>
                            )}
                          </div>

                          {/* Language Status */}
                          <div className="flex items-center gap-2 flex-wrap">
                            {episode.subtitle_languages.length > 0 && (
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-muted-foreground">字幕:</span>
                                {episode.subtitle_languages.slice(0, 3).map((lang) => (
                                  <Badge key={lang} variant="secondary" className="text-xs">
                                    {getLanguageName(lang)}
                                  </Badge>
                                ))}
                                {episode.subtitle_languages.length > 3 && (
                                  <span className="text-xs text-muted-foreground">
                                    +{episode.subtitle_languages.length - 3}
                                  </span>
                                )}
                              </div>
                            )}
                            {episode.missing_languages.length > 0 && (
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-muted-foreground">缺失:</span>
                                {episode.missing_languages.slice(0, 2).map((lang) => (
                                  <Badge key={lang} variant="destructive" className="text-xs">
                                    {getLanguageName(lang)}
                                  </Badge>
                                ))}
                                {episode.missing_languages.length > 2 && (
                                  <span className="text-xs text-destructive">
                                    +{episode.missing_languages.length - 2}
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

          <AlertDialogFooter>
            <AlertDialogCancel>关闭</AlertDialogCancel>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
