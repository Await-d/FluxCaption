import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Database, Search, Filter, Trash2, CheckSquare, Square } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Checkbox } from '@/components/ui/Checkbox'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import api from '@/lib/api'
import { getLanguageName } from '@/lib/utils'

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
  const queryClient = useQueryClient()

  const [search, setSearch] = useState('')
  const [langFilter, setLangFilter] = useState<string>('all')
  const [originFilter, setOriginFilter] = useState<string>('all')
  const [offset, setOffset] = useState(0)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [deleteFiles, setDeleteFiles] = useState(false)

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

  const getOriginBadge = (origin: string) => {
    const variants: Record<string, { label: string; className: string }> = {
      asr: { label: 'ASR', className: 'bg-blue-500/10 text-blue-500 border-blue-500/20' },
      mt: { label: '翻译', className: 'bg-purple-500/10 text-purple-500 border-purple-500/20' },
      manual: { label: '手动', className: 'bg-green-500/10 text-green-500 border-green-500/20' },
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
            <CardTitle className="text-sm font-medium text-muted-foreground">总计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats?.total || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">已上传</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-500">{stats?.uploaded || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">未上传</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-500">{stats?.not_uploaded || 0}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">语言种类</CardTitle>
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
                  placeholder="搜索媒体名称..."
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
                <SelectValue placeholder="语言" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部语言</SelectItem>
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
                <SelectValue placeholder="来源" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部来源</SelectItem>
                <SelectItem value="asr">ASR</SelectItem>
                <SelectItem value="mt">翻译</SelectItem>
                <SelectItem value="manual">手动</SelectItem>
                <SelectItem value="jellyfin">Jellyfin</SelectItem>
              </SelectContent>
            </Select>

            <Button
              variant="destructive"
              size="sm"
              onClick={handleBatchDelete}
              disabled={selectedIds.size === 0}
            >
              <Trash2 className="mr-2 h-4 w-4" />
              批量删除 ({selectedIds.size})
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
              字幕记录 ({subtitles?.total || 0})
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
                    取消全选
                  </>
                ) : (
                  <>
                    <Square className="mr-2 h-4 w-4" />
                    全选
                  </>
                )}
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="text-center py-8 text-muted-foreground">加载中...</div>
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
                        {subtitle.media_name || '未关联媒体'}
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
                            源: {getLanguageName(subtitle.source_lang)}
                          </Badge>
                        )}
                        {subtitle.is_uploaded && (
                          <Badge variant="outline" className="bg-green-500/10 text-green-500">
                            已上传
                          </Badge>
                        )}
                      </div>

                      {/* Meta info */}
                      <div className="flex items-center gap-4 text-sm text-muted-foreground">
                        {subtitle.line_count && (
                          <span>{subtitle.line_count} 行</span>
                        )}
                        {subtitle.word_count && (
                          <span>{subtitle.word_count} 词</span>
                        )}
                        {subtitle.media_type && (
                          <span>{subtitle.media_type}</span>
                        )}
                        <span>
                          {new Date(subtitle.created_at).toLocaleString('zh-CN')}
                        </span>
                      </div>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
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
                </div>
              ))}

              {/* Pagination */}
              <div className="flex items-center justify-between pt-4 border-t">
                <div className="text-sm text-muted-foreground">
                  显示 {offset + 1} - {Math.min(offset + limit, subtitles.total)} / 共 {subtitles.total} 条
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
                    disabled={offset + limit >= subtitles.total}
                  >
                    下一页
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              {search || langFilter !== 'all' || originFilter !== 'all'
                ? '没有找到匹配的字幕记录'
                : '暂无字幕记录'}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Batch Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认批量删除</DialogTitle>
            <DialogDescription>
              您确定要删除选中的 {selectedIds.size} 条字幕记录吗？
            </DialogDescription>
          </DialogHeader>
          <div className="py-4">
            <label className="flex items-center gap-2 cursor-pointer">
              <Checkbox
                checked={deleteFiles}
                onCheckedChange={(checked) => setDeleteFiles(checked as boolean)}
              />
              <span className="text-sm">同时删除物理文件</span>
            </label>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
            >
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={confirmBatchDelete}
              disabled={batchDeleteMutation.isPending}
            >
              {batchDeleteMutation.isPending ? '删除中...' : '确认删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
