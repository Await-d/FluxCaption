import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Languages, Search, Filter, ArrowRight } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import api from '@/lib/api'
import { getLanguageName } from '@/lib/utils'

export function Subtitles() {
  const [search, setSearch] = useState('')
  const [sourceLangFilter, setSourceLangFilter] = useState<string>('all')
  const [targetLangFilter, setTargetLangFilter] = useState<string>('all')
  const [offset, setOffset] = useState(0)
  const limit = 50

  // Fetch translation memory stats
  const { data: stats } = useQuery({
    queryKey: ['tm-stats'],
    queryFn: () => api.getTranslationMemoryStats(),
    refetchInterval: 30000,
  })

  // Fetch translation pairs
  const { data: pairs, isLoading } = useQuery({
    queryKey: ['tm-pairs', {
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
    refetchInterval: 10000,
  })

  // Extract unique languages from stats
  const sourceLanguages = stats?.by_language_pair
    ? Array.from(new Set(Object.keys(stats.by_language_pair).map(pair => pair.split(' → ')[0])))
    : []

  const targetLanguages = stats?.by_language_pair
    ? Array.from(new Set(Object.keys(stats.by_language_pair).map(pair => pair.split(' → ')[1])))
    : []

  return (
    <div className="space-y-6">
      {/* Filters and Search */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="搜索原文或译文..."
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
                <SelectValue placeholder="源语言" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部源语言</SelectItem>
                {sourceLanguages.map((lang) => (
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
                <SelectValue placeholder="目标语言" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部目标语言</SelectItem>
                {targetLanguages.map((lang) => (
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
          <CardTitle className="flex items-center gap-2">
            <Languages className="h-5 w-5" />
            翻译记录 ({pairs?.total || 0})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">加载中...</div>
          ) : pairs?.pairs && pairs.pairs.length > 0 ? (
            <div className="space-y-3">
              {pairs.pairs.map((pair: any) => (
                <div
                  key={pair.id}
                  className="p-3 rounded-lg border bg-card hover:bg-accent/30 transition-colors"
                >
                  <div className="space-y-2">
                    {/* Language badges */}
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="bg-blue-500/10 text-blue-500 border-blue-500/20">
                        {getLanguageName(pair.source_lang)}
                      </Badge>
                      <ArrowRight className="h-3 w-3 text-muted-foreground" />
                      <Badge variant="outline" className="bg-purple-500/10 text-purple-500 border-purple-500/20">
                        {getLanguageName(pair.target_lang)}
                      </Badge>
                    </div>

                    {/* Source text */}
                    <div className="pl-3 border-l-2 border-blue-500/30">
                      <div className="text-sm">{pair.source_text}</div>
                    </div>

                    {/* Target text */}
                    <div className="pl-3 border-l-2 border-purple-500/30">
                      <div className="text-sm font-medium">{pair.target_text}</div>
                    </div>
                  </div>
                </div>
              ))}

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  显示 {offset + 1} - {Math.min(offset + limit, pairs.total)} / 共 {pairs.total} 条
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOffset(Math.max(0, offset - limit))}
                    disabled={offset === 0}
                  >
                    上一页
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setOffset(offset + limit)}
                    disabled={offset + limit >= pairs.total}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {search || sourceLangFilter !== 'all' || targetLangFilter !== 'all'
                ? '没有找到匹配的翻译记录'
                : '暂无翻译记录，开始翻译字幕后会自动记录'}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
