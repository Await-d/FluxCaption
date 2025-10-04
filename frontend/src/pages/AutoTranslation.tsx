import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Power, PowerOff } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/Dialog'
import { Input } from '@/components/ui/Input'
import { Label } from '@/components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import api from '@/lib/api'
import { getLanguageName } from '@/lib/utils'
import type { AutoTranslationRule, AutoTranslationRuleCreate, AutoTranslationRuleUpdate, JellyfinLibrary } from '@/types/api'

export function AutoTranslation() {
  const queryClient = useQueryClient()
  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false)
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false)
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false)
  const [selectedRule, setSelectedRule] = useState<AutoTranslationRule | null>(null)

  // Form state
  const [formData, setFormData] = useState<{
    name: string
    enabled: boolean
    jellyfin_library_ids: string[]
    source_lang: string
    target_langs: string[]
    auto_start: boolean
    priority: number
  }>({
    name: '',
    enabled: true,
    jellyfin_library_ids: [],
    source_lang: '',
    target_langs: [],
    auto_start: true,
    priority: 5,
  })

  // Fetch rules
  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['auto-translation-rules'],
    queryFn: () => api.getAutoTranslationRules(),
  })

  // Fetch Jellyfin libraries
  const { data: librariesData } = useQuery({
    queryKey: ['jellyfin-libraries'],
    queryFn: () => api.getJellyfinLibraries(),
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: AutoTranslationRuleCreate) => api.createAutoTranslationRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-translation-rules'] })
      setIsCreateDialogOpen(false)
      resetForm()
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: AutoTranslationRuleUpdate }) =>
      api.updateAutoTranslationRule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-translation-rules'] })
      setIsEditDialogOpen(false)
      setSelectedRule(null)
      resetForm()
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteAutoTranslationRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-translation-rules'] })
      setIsDeleteDialogOpen(false)
      setSelectedRule(null)
    },
  })

  // Toggle mutation
  const toggleMutation = useMutation({
    mutationFn: (id: string) => api.toggleAutoTranslationRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auto-translation-rules'] })
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      enabled: true,
      jellyfin_library_ids: [],
      source_lang: '',
      target_langs: [],
      auto_start: true,
      priority: 5,
    })
  }

  const handleCreateClick = () => {
    resetForm()
    setIsCreateDialogOpen(true)
  }

  const handleEditClick = (rule: AutoTranslationRule) => {
    setSelectedRule(rule)
    setFormData({
      name: rule.name,
      enabled: rule.enabled,
      jellyfin_library_ids: rule.jellyfin_library_ids,
      source_lang: rule.source_lang || '',
      target_langs: rule.target_langs,
      auto_start: rule.auto_start,
      priority: rule.priority,
    })
    setIsEditDialogOpen(true)
  }

  const handleDeleteClick = (rule: AutoTranslationRule) => {
    setSelectedRule(rule)
    setIsDeleteDialogOpen(true)
  }

  const handleCreateSubmit = () => {
    const payload: AutoTranslationRuleCreate = {
      name: formData.name,
      enabled: formData.enabled,
      jellyfin_library_ids: formData.jellyfin_library_ids,
      source_lang: formData.source_lang || null,
      target_langs: formData.target_langs,
      auto_start: formData.auto_start,
      priority: formData.priority,
    }
    createMutation.mutate(payload)
  }

  const handleUpdateSubmit = () => {
    if (!selectedRule) return

    const payload: AutoTranslationRuleUpdate = {
      name: formData.name,
      enabled: formData.enabled,
      jellyfin_library_ids: formData.jellyfin_library_ids,
      source_lang: formData.source_lang || null,
      target_langs: formData.target_langs,
      auto_start: formData.auto_start,
      priority: formData.priority,
    }
    updateMutation.mutate({ id: selectedRule.id, data: payload })
  }

  const handleDeleteConfirm = () => {
    if (!selectedRule) return
    deleteMutation.mutate(selectedRule.id)
  }

  const handleToggle = (rule: AutoTranslationRule) => {
    toggleMutation.mutate(rule.id)
  }

  // Language options
  const languageOptions = [
    { value: 'zh-CN', label: '简体中文' },
    { value: 'zh-TW', label: '繁體中文' },
    { value: 'en', label: 'English' },
    { value: 'ja', label: '日本語' },
    { value: 'ko', label: '한국어' },
    { value: 'es', label: 'Español' },
    { value: 'fr', label: 'Français' },
    { value: 'de', label: 'Deutsch' },
    { value: 'ru', label: 'Русский' },
    { value: 'pt', label: 'Português' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>自动翻译规则</CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                配置媒体库扫描时的自动翻译规则，匹配规则的任务可以自动启动
              </p>
            </div>
            <Button onClick={handleCreateClick}>
              <Plus className="h-4 w-4 mr-2" />
              添加规则
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Rules List */}
      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">加载中...</p>
          </CardContent>
        </Card>
      ) : rulesData && rulesData.rules.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">暂无规则，点击"添加规则"创建第一个自动翻译规则</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {rulesData?.rules.map((rule) => (
            <Card key={rule.id}>
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-3">
                      <h3 className="text-lg font-semibold">{rule.name}</h3>
                      <Badge variant={rule.enabled ? 'default' : 'secondary'}>
                        {rule.enabled ? '已启用' : '已禁用'}
                      </Badge>
                      {rule.auto_start && (
                        <Badge variant="outline">自动启动</Badge>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-muted-foreground">监听媒体库：</span>
                        <span className="ml-2">
                          {rule.jellyfin_library_ids.length === 0
                            ? '全部'
                            : rule.jellyfin_library_ids
                                .map(id => {
                                  const lib = librariesData?.find((l: JellyfinLibrary) => l.id === id)
                                  return lib?.name || id
                                })
                                .join(', ')}
                        </span>
                      </div>

                      <div>
                        <span className="text-muted-foreground">源语言：</span>
                        <span className="ml-2">{rule.source_lang ? getLanguageName(rule.source_lang) : '全部'}</span>
                      </div>

                      <div>
                        <span className="text-muted-foreground">目标语言：</span>
                        <span className="ml-2">
                          {rule.target_langs.map(getLanguageName).join(', ')}
                        </span>
                      </div>

                      <div>
                        <span className="text-muted-foreground">优先级：</span>
                        <span className="ml-2">{rule.priority}</span>
                      </div>
                    </div>
                  </div>

                  <div className="flex gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleToggle(rule)}
                      disabled={toggleMutation.isPending}
                    >
                      {rule.enabled ? (
                        <PowerOff className="h-4 w-4" />
                      ) : (
                        <Power className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEditClick(rule)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleDeleteClick(rule)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={isCreateDialogOpen || isEditDialogOpen} onOpenChange={(open) => {
        if (!open) {
          setIsCreateDialogOpen(false)
          setIsEditDialogOpen(false)
          setSelectedRule(null)
          resetForm()
        }
      }}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isCreateDialogOpen ? '添加规则' : '编辑规则'}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">规则名称 *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="例如：自动翻译中文字幕"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="libraries">监听媒体库（留空表示全部）</Label>
              <Select
                value={formData.jellyfin_library_ids[0] || 'all'}
                onValueChange={(value) => {
                  if (value === 'all') {
                    setFormData({ ...formData, jellyfin_library_ids: [] })
                  } else {
                    setFormData({ ...formData, jellyfin_library_ids: [value] })
                  }
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择媒体库" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部媒体库</SelectItem>
                  {librariesData?.map((lib: JellyfinLibrary) => (
                    <SelectItem key={lib.id} value={lib.id}>
                      {lib.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="source_lang">源语言（留空表示全部）</Label>
              <Select
                value={formData.source_lang || 'all'}
                onValueChange={(value) => {
                  setFormData({ ...formData, source_lang: value === 'all' ? '' : value })
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder="选择源语言" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">全部语言</SelectItem>
                  {languageOptions.map((lang) => (
                    <SelectItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>目标语言 * （至少选择一个）</Label>
              <div className="grid grid-cols-2 gap-2">
                {languageOptions.map((lang) => (
                  <label key={lang.value} className="flex items-center space-x-2 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={formData.target_langs.includes(lang.value)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          setFormData({
                            ...formData,
                            target_langs: [...formData.target_langs, lang.value],
                          })
                        } else {
                          setFormData({
                            ...formData,
                            target_langs: formData.target_langs.filter((l) => l !== lang.value),
                          })
                        }
                      }}
                      className="rounded border-gray-300"
                    />
                    <span className="text-sm">{lang.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="priority">优先级（1-10，数值越大优先级越高）</Label>
              <Input
                id="priority"
                type="number"
                min="1"
                max="10"
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: parseInt(e.target.value) || 5 })}
              />
            </div>

            <div className="flex items-center space-x-2">
              <input
                id="auto_start"
                type="checkbox"
                checked={formData.auto_start}
                onChange={(e) => setFormData({ ...formData, auto_start: e.target.checked })}
                className="rounded border-gray-300"
              />
              <Label htmlFor="auto_start" className="cursor-pointer">
                自动启动匹配的任务
              </Label>
            </div>

            <div className="flex items-center space-x-2">
              <input
                id="enabled"
                type="checkbox"
                checked={formData.enabled}
                onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
                className="rounded border-gray-300"
              />
              <Label htmlFor="enabled" className="cursor-pointer">
                启用此规则
              </Label>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setIsCreateDialogOpen(false)
                setIsEditDialogOpen(false)
                setSelectedRule(null)
                resetForm()
              }}
            >
              取消
            </Button>
            <Button
              onClick={isCreateDialogOpen ? handleCreateSubmit : handleUpdateSubmit}
              disabled={
                !formData.name ||
                formData.target_langs.length === 0 ||
                createMutation.isPending ||
                updateMutation.isPending
              }
            >
              {isCreateDialogOpen
                ? createMutation.isPending
                  ? '创建中...'
                  : '创建'
                : updateMutation.isPending
                ? '保存中...'
                : '保存'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认删除</DialogTitle>
          </DialogHeader>
          <p className="py-4">
            确定要删除规则 "{selectedRule?.name}" 吗？此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              取消
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? '删除中...' : '删除'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
