import { useState } from 'react'
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
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Input } from '@/components/ui/Input'
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
import { Alert, AlertDescription } from '@/components/ui/Alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import api from '@/lib/api'
import { formatBytes, getLanguageName } from '@/lib/utils'
import type {
  MediaFileResponse,
  ScanDirectoryResponse,
  DirectoryStatsResponse,
  AppSettings,
} from '@/types/api'

export function LocalMedia() {
  const [directoryPath, setDirectoryPath] = useState('')
  const [scannedDirectory, setScannedDirectory] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<MediaFileResponse | null>(null)
  const [translateDialogOpen, setTranslateDialogOpen] = useState(false)
  const [selectedTargetLangs, setSelectedTargetLangs] = useState<string[]>([])
  const [recursive, setRecursive] = useState(true)
  const queryClient = useQueryClient()

  // Fetch settings to get favorite paths
  const { data: settings } = useQuery<AppSettings>({
    queryKey: ['settings'],
    queryFn: () => api.getSettings(),
  })

  // Available languages for translation
  const LANGUAGES = [
    { code: 'zh-CN', name: '简体中文' },
    { code: 'en', name: 'English' },
    { code: 'ja', name: '日本語' },
    { code: 'ko', name: '한국어' },
  ]

  // Scan directory mutation
  const scanMutation = useMutation({
    mutationFn: (path: string) =>
      api.scanLocalDirectory({
        directory: path,
        recursive,
        max_depth: 5,
        required_langs: ['zh-CN', 'en', 'ja'],
      }),
    onSuccess: (data) => {
      setScannedDirectory(data.directory)
      queryClient.setQueryData(['local-media-scan', data.directory], data)
    },
  })

  // Get directory stats
  const { data: stats } = useQuery<DirectoryStatsResponse>({
    queryKey: ['local-media-stats', scannedDirectory, recursive],
    queryFn: () => api.getLocalDirectoryStats(scannedDirectory!, recursive),
    enabled: !!scannedDirectory,
  })

  // Get scanned media files
  const { data: scanResult } = useQuery<ScanDirectoryResponse>({
    queryKey: ['local-media-scan', scannedDirectory],
    enabled: false, // Only updated via mutation
  })

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
      scanMutation.mutate(directoryPath.trim())
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
    if (!scanResult?.media_files) return

    const filesNeedingTranslation = scanResult.media_files.filter(
      (f) => f.missing_languages.length > 0
    )

    if (filesNeedingTranslation.length === 0) return

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
    <div className="space-y-6">
      {/* Scan Directory */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FolderOpen className="h-5 w-5" />
            扫描本地目录
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              输入媒体文件所在的目录路径，系统将扫描视频文件和现有字幕。支持常见视频格式（mp4,
              mkv, avi 等）。
            </AlertDescription>
          </Alert>

          <div className="space-y-3">
            {/* Input Row */}
            <div className="flex flex-col sm:flex-row gap-2">
              <Input
                placeholder="/path/to/media/directory (例如: /media/movies)"
                value={directoryPath}
                onChange={(e) => setDirectoryPath(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') handleScan()
                }}
                className="flex-1"
              />
              {settings?.favorite_media_paths && settings.favorite_media_paths.length > 0 && (
                <Select
                  value={directoryPath}
                  onValueChange={(value) => setDirectoryPath(value)}
                >
                  <SelectTrigger className="w-full sm:w-[180px]">
                    <SelectValue placeholder="收藏路径" />
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

            {/* Options Row */}
            <div className="flex items-center justify-between gap-2">
              <label className="flex items-center gap-2 text-xs sm:text-sm cursor-pointer">
                <input
                  type="checkbox"
                  checked={recursive}
                  onChange={(e) => setRecursive(e.target.checked)}
                  className="rounded"
                />
                递归扫描
              </label>
              <Button
                onClick={handleScan}
                disabled={!directoryPath.trim() || scanMutation.isPending}
                className="flex-shrink-0"
              >
                {scanMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    <span className="hidden sm:inline">扫描中...</span>
                    <span className="sm:hidden">扫描</span>
                  </>
                ) : (
                  <>
                    <Scan className="mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">扫描目录</span>
                    <span className="sm:hidden">扫描</span>
                  </>
                )}
              </Button>
            </div>
          </div>

          {scanMutation.isError && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>
                扫描失败: {(scanMutation.error as any)?.message || '未知错误'}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>

      {/* Directory Stats */}
      {stats && (
        <Card>
          <CardHeader>
            <CardTitle>目录统计</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-2 bg-primary/10 rounded-lg">
                  <Film className="h-4 w-4 sm:h-5 sm:w-5 text-primary" />
                </div>
                <div>
                  <p className="text-xl sm:text-2xl font-bold">{stats.total_media_files}</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">媒体文件</p>
                </div>
              </div>

              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Languages className="h-4 w-4 sm:h-5 sm:w-5 text-blue-500" />
                </div>
                <div>
                  <p className="text-xl sm:text-2xl font-bold">{stats.total_subtitle_files}</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">字幕文件</p>
                </div>
              </div>

              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <HardDrive className="h-4 w-4 sm:h-5 sm:w-5 text-green-500" />
                </div>
                <div>
                  <p className="text-xl sm:text-2xl font-bold">{formatBytes(stats.total_size_bytes)}</p>
                  <p className="text-xs sm:text-sm text-muted-foreground">总大小</p>
                </div>
              </div>

              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-2 bg-orange-500/10 rounded-lg">
                  <Info className="h-4 w-4 sm:h-5 sm:w-5 text-orange-500" />
                </div>
                <div>
                  <p className="text-xs sm:text-sm font-medium">格式分布</p>
                  <div className="flex gap-1 flex-wrap mt-1">
                    {Object.entries(stats.video_formats).map(([format, count]) => (
                      <Badge key={format} variant="outline" className="text-xs">
                        {format}: {count}
                      </Badge>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Media Files */}
      {scanResult && (
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <CardTitle>媒体文件列表</CardTitle>
              <div className="flex items-center gap-2">
                <Badge variant="outline">{scanResult.total_count} 个文件</Badge>
                {scanResult.media_files.filter((f) => f.missing_languages.length > 0).length >
                  0 && (
                  <Button size="sm" onClick={handleBatchTranslate}>
                    <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                    <span className="hidden sm:inline">批量翻译全部</span>
                    <span className="sm:hidden">批量翻译</span>
                  </Button>
                )}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {scanResult.media_files.length === 0 ? (
              <p className="text-muted-foreground text-center py-8">未找到媒体文件</p>
            ) : (
              <div className="space-y-3">
                {scanResult.media_files.map((file) => (
                  <Card key={file.filepath} className="overflow-hidden">
                    <CardContent className="p-3 sm:p-4">
                      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 sm:gap-4">
                        <div className="flex-1 space-y-2">
                          {/* File Name */}
                          <div className="flex items-start gap-2">
                            <Film className="h-4 w-4 text-muted-foreground flex-shrink-0 mt-0.5" />
                            <div className="flex-1 min-w-0">
                              <h3 className="font-semibold text-sm sm:text-base break-words">
                                {file.filename}
                              </h3>
                            </div>
                            {file.missing_languages.length === 0 ? (
                              <Badge variant="outline" className="flex-shrink-0 text-xs">
                                <CheckCircle2 className="mr-1 h-3 w-3 text-green-600" />
                                <span className="hidden sm:inline">字幕完整</span>
                                <span className="sm:hidden">完整</span>
                              </Badge>
                            ) : (
                              <Badge variant="destructive" className="flex-shrink-0 text-xs">
                                <span className="hidden sm:inline">缺失 {file.missing_languages.length} 种语言</span>
                                <span className="sm:hidden">缺 {file.missing_languages.length}</span>
                              </Badge>
                            )}
                          </div>

                          {/* File Path */}
                          <p className="text-xs text-muted-foreground font-mono truncate">
                            {file.filepath}
                          </p>

                          {/* File Info */}
                          <div className="flex items-center gap-2 sm:gap-4 text-xs sm:text-sm">
                            <div className="flex items-center gap-1">
                              <HardDrive className="h-3 w-3 text-muted-foreground" />
                              <span className="text-muted-foreground">
                                {formatBytes(file.size_bytes)}
                              </span>
                            </div>
                          </div>

                          {/* Subtitle Status */}
                          <div className="space-y-1.5">
                            {/* Existing Subtitles */}
                            {file.existing_subtitle_langs.length > 0 && (
                              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                                <span className="text-xs text-muted-foreground flex-shrink-0">现有字幕:</span>
                                <div className="flex gap-1 flex-wrap">
                                  {file.existing_subtitle_langs.map((lang) => (
                                    <Badge key={lang} variant="secondary" className="text-xs">
                                      {getLanguageName(lang)}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Missing Languages */}
                            {file.missing_languages.length > 0 && (
                              <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-2">
                                <span className="text-xs text-muted-foreground flex-shrink-0">缺失语言:</span>
                                <div className="flex gap-1 flex-wrap">
                                  {file.missing_languages.map((lang) => (
                                    <Badge key={lang} variant="destructive" className="text-xs">
                                      {getLanguageName(lang)}
                                    </Badge>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Subtitle Files */}
                            {file.subtitle_files.length > 0 && (
                              <div className="flex flex-col sm:flex-row sm:items-start gap-1 sm:gap-2">
                                <span className="text-xs text-muted-foreground flex-shrink-0">字幕文件:</span>
                                <div className="flex-1 text-xs text-muted-foreground break-all">
                                  {file.subtitle_files.join(', ')}
                                </div>
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Actions */}
                        {file.missing_languages.length > 0 && (
                          <div className="flex-shrink-0">
                            <Button
                              size="sm"
                              variant="default"
                              onClick={() => handleQuickTranslate(file)}
                              className="w-full sm:w-auto"
                            >
                              <Languages className="mr-1 sm:mr-2 h-4 w-4" />
                              翻译
                            </Button>
                          </div>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Translate Dialog */}
      <AlertDialog open={translateDialogOpen} onOpenChange={setTranslateDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>创建翻译任务</AlertDialogTitle>
            <AlertDialogDescription>
              为 <strong>{selectedFile?.filename}</strong> 创建字幕翻译任务
            </AlertDialogDescription>
          </AlertDialogHeader>

          <div className="space-y-4 py-4">
            {/* File Info */}
            {selectedFile && (
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-muted-foreground">文件大小:</span>
                  <span>{formatBytes(selectedFile.size_bytes)}</span>
                </div>

                {selectedFile.existing_subtitle_langs.length > 0 && (
                  <div className="flex items-start gap-2">
                    <span className="text-muted-foreground">现有字幕:</span>
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
                    <span className="text-muted-foreground">缺失语言:</span>
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
                    {selectedFile?.missing_languages.includes(lang.code) && (
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
              <p>
                •{' '}
                {selectedFile?.existing_subtitle_langs.length
                  ? '将使用现有字幕进行翻译'
                  : '没有字幕时将先进行语音识别（ASR）生成字幕'}
              </p>
              <p>• 翻译任务将在后台队列中执行</p>
              <p>• 可在"任务列表"页面查看进度</p>
            </div>
          </div>

          <AlertDialogFooter>
            <AlertDialogCancel disabled={createJobMutation.isPending}>取消</AlertDialogCancel>
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
    </div>
  )
}
