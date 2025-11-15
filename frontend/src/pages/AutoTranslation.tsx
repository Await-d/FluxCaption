import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, Power, PowerOff } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../components/ui/Dialog'
import { Input } from '../components/ui/Input'
import { Label } from '../components/ui/Label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import api from '../lib/api'
import { getLanguageName } from '../lib/utils'
import type { AutoTranslationRule, AutoTranslationRuleCreate, AutoTranslationRuleUpdate, JellyfinLibrary } from '../types/api'
import { useTranslation } from 'react-i18next'

export function AutoTranslation() {
  const { t } = useTranslation()
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
    { value: 'zh-CN', label: t('languages.zh-CN') },
    { value: 'zh-TW', label: t('languages.zh-TW') },
    { value: 'en', label: t('languages.en') },
    { value: 'ja', label: t('languages.ja') },
    { value: 'ko', label: t('languages.ko') },
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
              <CardTitle>{t('autoTranslation.title')}</CardTitle>
              <p className="text-sm text-muted-foreground mt-2">
                {t('autoTranslation.subtitle')}
              </p>
            </div>
            <Button onClick={handleCreateClick}>
              <Plus className="h-4 w-4 mr-2" />
              {t('autoTranslation.addRule')}
            </Button>
          </div>
        </CardHeader>
      </Card>

      {/* Rules List */}
      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">{t('autoTranslation.loading')}</p>
          </CardContent>
        </Card>
      ) : rulesData && rulesData.rules.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <p className="text-muted-foreground">{t('autoTranslation.noRules')}</p>
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
                        {rule.enabled ? t('autoTranslation.enabled') : t('autoTranslation.disabled')}
                      </Badge>
                      {rule.auto_start && (
                        <Badge variant="outline">{t('autoTranslation.autoStart')}</Badge>
                      )}
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm">
                      <div>
                        <span className="text-muted-foreground">{t('autoTranslation.listenLibraries')}</span>
                        <span className="ml-2">
                          {rule.jellyfin_library_ids.length === 0
                            ? t('autoTranslation.all')
                            : rule.jellyfin_library_ids
                              .map(id => {
                                const lib = librariesData?.find((l: JellyfinLibrary) => l.id === id)
                                return lib?.name || id
                              })
                              .join(', ')}
                        </span>
                      </div>

                      <div>
                        <span className="text-muted-foreground">{t('autoTranslation.sourceLanguage')}</span>
                        <span className="ml-2">{rule.source_lang ? getLanguageName(rule.source_lang) : t('autoTranslation.all')}</span>
                      </div>

                      <div>
                        <span className="text-muted-foreground">{t('autoTranslation.targetLanguages')}</span>
                        <span className="ml-2">
                          {rule.target_langs.map(getLanguageName).join(', ')}
                        </span>
                      </div>

                      <div>
                        <span className="text-muted-foreground">{t('autoTranslation.priority')}</span>
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
            <DialogTitle>{isCreateDialogOpen ? t('autoTranslation.addRuleTitle') : t('autoTranslation.editRuleTitle')}</DialogTitle>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">{t('autoTranslation.ruleName')} *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder={t('autoTranslation.ruleNamePlaceholder')}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="libraries">{t('autoTranslation.listenLibrariesLabel')}</Label>
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
                  <SelectValue placeholder={t('autoTranslation.selectLibraryPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('autoTranslation.allLibraries')}</SelectItem>
                  {librariesData?.map((lib: JellyfinLibrary) => (
                    <SelectItem key={lib.id} value={lib.id}>
                      {lib.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="source_lang">{t('autoTranslation.sourceLanguageLabel')}</Label>
              <Select
                value={formData.source_lang || 'all'}
                onValueChange={(value) => {
                  setFormData({ ...formData, source_lang: value === 'all' ? '' : value })
                }}
              >
                <SelectTrigger>
                  <SelectValue placeholder={t('autoTranslation.selectSourceLangPlaceholder')} />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">{t('autoTranslation.allLanguages')}</SelectItem>
                  {languageOptions.map((lang) => (
                    <SelectItem key={lang.value} value={lang.value}>
                      {lang.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label>{t('autoTranslation.targetLanguagesLabel')}</Label>
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
              <Label htmlFor="priority">{t('autoTranslation.priorityLabel')}</Label>
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
                {t('autoTranslation.autoStartLabel')}
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
                {t('autoTranslation.enableRuleLabel')}
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
              {t('autoTranslation.cancel')}
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
                  ? t('autoTranslation.creating')
                  : t('autoTranslation.create')
                : updateMutation.isPending
                  ? t('autoTranslation.saving')
                  : t('autoTranslation.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('autoTranslation.deleteConfirm')}</DialogTitle>
          </DialogHeader>
          <p className="py-4">
            {t('autoTranslation.deleteConfirmDesc', { name: selectedRule?.name })}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsDeleteDialogOpen(false)}>
              {t('autoTranslation.cancel')}
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteConfirm}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? t('autoTranslation.deleting') : t('autoTranslation.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
