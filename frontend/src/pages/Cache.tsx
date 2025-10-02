import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { RefreshCw, Trash2, AlertTriangle, Database } from 'lucide-react'
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
  AlertDialogTrigger,
} from '@/components/ui/AlertDialog'
import api from '@/lib/api'
import type { CacheEntry } from '@/types/api'

export function Cache() {
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

  const handleClearOld = () => {
    clearOldMutation.mutate(90)
  }

  const handleClearAll = () => {
    clearAllMutation.mutate()
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
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总缓存条目</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : stats?.total_entries.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总命中次数</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : stats?.total_hits.toLocaleString()}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">命中率</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : `${stats?.hit_rate.toFixed(1)}%`}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">语言对</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : stats?.unique_language_pairs}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">模型数</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {statsLoading ? '-' : stats?.unique_models}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters and Actions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>翻译缓存</CardTitle>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={() => refetch()}>
                <RefreshCw className="mr-2 h-4 w-4" />
                刷新
              </Button>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="outline" size="sm">
                    <Trash2 className="mr-2 h-4 w-4" />
                    清理旧缓存
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>清理未使用的缓存</AlertDialogTitle>
                    <AlertDialogDescription>
                      这将删除90天内未使用且命中次数为0的缓存条目。此操作不可撤销。
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction onClick={handleClearOld}>
                      确认清理
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button variant="destructive" size="sm">
                    <AlertTriangle className="mr-2 h-4 w-4" />
                    清空所有缓存
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>清空所有缓存？</AlertDialogTitle>
                    <AlertDialogDescription>
                      这将删除所有翻译缓存条目。此操作不可撤销，将影响翻译性能。
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>取消</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={handleClearAll}
                      className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
                    >
                      确认清空
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
            <div className="grid gap-4 md:grid-cols-4">
              <Input
                placeholder="搜索文本..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <Select value={sourceLang} onValueChange={setSourceLang}>
                <SelectTrigger>
                  <SelectValue placeholder="源语言" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有源语言</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh-CN">简体中文</SelectItem>
                  <SelectItem value="ja">日本语</SelectItem>
                </SelectContent>
              </Select>
              <Select value={targetLang} onValueChange={setTargetLang}>
                <SelectTrigger>
                  <SelectValue placeholder="目标语言" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">所有目标语言</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                  <SelectItem value="zh-CN">简体中文</SelectItem>
                  <SelectItem value="ja">日本语</SelectItem>
                </SelectContent>
              </Select>
              <Select value={sortBy} onValueChange={setSortBy}>
                <SelectTrigger>
                  <SelectValue placeholder="排序方式" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="last_used_at">最后使用时间</SelectItem>
                  <SelectItem value="hit_count">命中次数</SelectItem>
                  <SelectItem value="created_at">创建时间</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Cache Entries Table */}
            <div className="rounded-md border">
              <div className="max-h-[600px] overflow-y-auto">
                {entriesLoading ? (
                  <div className="p-8 text-center text-muted-foreground">
                    加载中...
                  </div>
                ) : cacheData?.entries.length === 0 ? (
                  <div className="p-8 text-center text-muted-foreground">
                    暂无缓存数据
                  </div>
                ) : (
                  <table className="w-full">
                    <thead className="sticky top-0 bg-muted">
                      <tr>
                        <th className="p-3 text-left text-sm font-medium">
                          源文本
                        </th>
                        <th className="p-3 text-left text-sm font-medium">
                          翻译文本
                        </th>
                        <th className="p-3 text-left text-sm font-medium">
                          语言对
                        </th>
                        <th className="p-3 text-left text-sm font-medium">
                          模型
                        </th>
                        <th className="p-3 text-left text-sm font-medium">
                          命中次数
                        </th>
                        <th className="p-3 text-left text-sm font-medium">
                          最后使用
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {cacheData?.entries.map((entry: CacheEntry) => (
                        <tr
                          key={entry.content_hash}
                          className="border-t hover:bg-muted/50"
                        >
                          <td className="p-3 text-sm max-w-xs">
                            <div className="whitespace-pre-wrap break-words">
                              {truncateText(entry.source_text, 150)}
                            </div>
                          </td>
                          <td className="p-3 text-sm max-w-xs">
                            <div className="whitespace-pre-wrap break-words">
                              {truncateText(entry.translated_text, 150)}
                            </div>
                          </td>
                          <td className="p-3 text-sm whitespace-nowrap">
                            <Badge variant="outline">
                              {entry.source_lang} → {entry.target_lang}
                            </Badge>
                          </td>
                          <td className="p-3 text-sm whitespace-nowrap">
                            <code className="text-xs">{entry.model}</code>
                          </td>
                          <td className="p-3 text-sm text-center">
                            <Badge>{entry.hit_count}</Badge>
                          </td>
                          <td className="p-3 text-sm text-muted-foreground whitespace-nowrap">
                            {formatDate(entry.last_used_at)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Pagination */}
            {cacheData && cacheData.total > 0 && (
              <div className="flex items-center justify-between">
                <div className="text-sm text-muted-foreground">
                  显示 {offset + 1} - {offset + cacheData.entries.length} / 共{' '}
                  {cacheData.total} 条
                </div>
                <div className="flex gap-2">
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
                    disabled={!cacheData.has_more}
                  >
                    下一页
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
