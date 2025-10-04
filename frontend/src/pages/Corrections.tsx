import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Edit, Trash2, FileUp, Download } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import api from '@/lib/api'

interface CorrectionRule {
  id: string
  name: string
  source_pattern: string
  target_text: string
  is_regex: boolean
  is_case_sensitive: boolean
  is_active: boolean
  source_lang: string | null
  target_lang: string | null
  priority: number
  description: string | null
  created_at: string
  updated_at: string
}

export function Corrections() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [isAddingRule, setIsAddingRule] = useState(false)
  const [editingRule, setEditingRule] = useState<CorrectionRule | null>(null)
  const [importText, setImportText] = useState('')
  const [showImport, setShowImport] = useState(false)

  // Form state
  const [formData, setFormData] = useState({
    name: '',
    source_pattern: '',
    target_text: '',
    is_regex: false,
    is_case_sensitive: true,
    is_active: true,
    source_lang: '',
    target_lang: '',
    priority: 50,
    description: '',
  })

  // Fetch correction rules
  const { data: rulesData, isLoading } = useQuery({
    queryKey: ['correction-rules'],
    queryFn: () => api.getCorrectionRules(),
  })

  // Create mutation
  const createMutation = useMutation({
    mutationFn: (data: any) => api.createCorrectionRule(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['correction-rules'] })
      resetForm()
      setIsAddingRule(false)
    },
  })

  // Update mutation
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: any }) =>
      api.updateCorrectionRule(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['correction-rules'] })
      resetForm()
      setEditingRule(null)
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (id: string) => api.deleteCorrectionRule(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['correction-rules'] })
    },
  })

  // Batch import mutation
  const importMutation = useMutation({
    mutationFn: (text: string) => api.importCorrectionRules(text),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['correction-rules'] })
      setImportText('')
      setShowImport(false)
    },
  })

  const resetForm = () => {
    setFormData({
      name: '',
      source_pattern: '',
      target_text: '',
      is_regex: false,
      is_case_sensitive: true,
      is_active: true,
      source_lang: '',
      target_lang: '',
      priority: 50,
      description: '',
    })
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const data = {
      ...formData,
      source_lang: formData.source_lang || null,
      target_lang: formData.target_lang || null,
    }

    if (editingRule) {
      updateMutation.mutate({ id: editingRule.id, data })
    } else {
      createMutation.mutate(data)
    }
  }

  const handleEdit = (rule: CorrectionRule) => {
    setFormData({
      name: rule.name,
      source_pattern: rule.source_pattern,
      target_text: rule.target_text,
      is_regex: rule.is_regex,
      is_case_sensitive: rule.is_case_sensitive,
      is_active: rule.is_active,
      source_lang: rule.source_lang || '',
      target_lang: rule.target_lang || '',
      priority: rule.priority,
      description: rule.description || '',
    })
    setEditingRule(rule)
    setIsAddingRule(true)
  }

  const handleExport = () => {
    if (!rulesData?.rules) return
    const exportData = rulesData.rules.map((rule: CorrectionRule) => ({
      name: rule.name,
      source_pattern: rule.source_pattern,
      target_text: rule.target_text,
      is_regex: rule.is_regex,
      is_case_sensitive: rule.is_case_sensitive,
      source_lang: rule.source_lang,
      target_lang: rule.target_lang,
      priority: rule.priority,
      description: rule.description,
    }))

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `correction-rules-${new Date().toISOString().split('T')[0]}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleImport = () => {
    try {
      const rules = JSON.parse(importText)
      if (!Array.isArray(rules)) {
        throw new Error('导入数据必须是数组格式')
      }
      importMutation.mutate(importText)
    } catch (error: any) {
      alert(t('corrections.importFailed', { error: error.message }))
    }
  }

  if (isLoading) {
    return <div className="text-muted-foreground">加载中...</div>
  }

  return (
    <div className="max-w-6xl space-y-6">
      <div className="flex justify-end gap-2">
        <Button variant="outline" onClick={() => setShowImport(true)}>
          <FileUp className="mr-2 h-4 w-4" />
          批量导入
        </Button>
        <Button variant="outline" onClick={handleExport}>
          <Download className="mr-2 h-4 w-4" />
          导出规则
        </Button>
        <Button onClick={() => setIsAddingRule(true)}>
          <Plus className="mr-2 h-4 w-4" />
          添加规则
        </Button>
      </div>

      {/* Import Dialog */}
      {showImport && (
        <Card>
          <CardHeader>
            <CardTitle>批量导入纠正规则</CardTitle>
            <CardDescription>
              粘贴 JSON 格式的规则数据，或从文件中导入
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <textarea
              className="w-full h-64 p-3 border rounded-md font-mono text-sm"
              placeholder='[\n  {\n    "name": "规则名称",\n    "source_pattern": "源文本",\n    "target_text": "目标文本",\n    "is_regex": false\n  }\n]'
              value={importText}
              onChange={(e) => setImportText(e.target.value)}
            />
            <div className="flex gap-2 justify-end">
              <Button
                variant="outline"
                onClick={() => {
                  setShowImport(false)
                  setImportText('')
                }}
              >
                取消
              </Button>
              <Button
                onClick={handleImport}
                disabled={importMutation.isPending || !importText.trim()}
              >
                {importMutation.isPending ? '导入中...' : '开始导入'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Add/Edit Form */}
      {isAddingRule && (
        <Card>
          <CardHeader>
            <CardTitle>{editingRule ? '编辑规则' : '添加新规则'}</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    规则名称 *
                  </label>
                  <Input
                    value={formData.name}
                    onChange={(e) =>
                      setFormData({ ...formData, name: e.target.value })
                    }
                    required
                    placeholder="例如：修正专有名词"
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    优先级 (0-100)
                  </label>
                  <Input
                    type="number"
                    min="0"
                    max="100"
                    value={formData.priority}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        priority: parseInt(e.target.value),
                      })
                    }
                  />
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    源语言 (可选)
                  </label>
                  <Input
                    value={formData.source_lang}
                    onChange={(e) =>
                      setFormData({ ...formData, source_lang: e.target.value })
                    }
                    placeholder="zh-CN, en, ja..."
                  />
                </div>
                <div>
                  <label className="text-sm font-medium mb-2 block">
                    目标语言 (可选)
                  </label>
                  <Input
                    value={formData.target_lang}
                    onChange={(e) =>
                      setFormData({ ...formData, target_lang: e.target.value })
                    }
                    placeholder="zh-CN, en, ja..."
                  />
                </div>
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  源文本/模式 *
                </label>
                <Input
                  value={formData.source_pattern}
                  onChange={(e) =>
                    setFormData({ ...formData, source_pattern: e.target.value })
                  }
                  required
                  placeholder="要替换的文本或正则表达式"
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  目标文本 *
                </label>
                <Input
                  value={formData.target_text}
                  onChange={(e) =>
                    setFormData({ ...formData, target_text: e.target.value })
                  }
                  required
                  placeholder="替换后的文本"
                />
              </div>

              <div>
                <label className="text-sm font-medium mb-2 block">
                  描述 (可选)
                </label>
                <textarea
                  className="w-full p-2 border rounded-md text-sm"
                  rows={2}
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="规则说明"
                />
              </div>

              <div className="flex gap-4 flex-wrap">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_regex}
                    onChange={(e) =>
                      setFormData({ ...formData, is_regex: e.target.checked })
                    }
                  />
                  <span className="text-sm">使用正则表达式</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_case_sensitive}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        is_case_sensitive: e.target.checked,
                      })
                    }
                  />
                  <span className="text-sm">区分大小写</span>
                </label>
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={formData.is_active}
                    onChange={(e) =>
                      setFormData({ ...formData, is_active: e.target.checked })
                    }
                  />
                  <span className="text-sm">启用规则</span>
                </label>
              </div>

              <div className="flex gap-2 justify-end">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => {
                    setIsAddingRule(false)
                    setEditingRule(null)
                    resetForm()
                  }}
                >
                  取消
                </Button>
                <Button
                  type="submit"
                  disabled={
                    createMutation.isPending || updateMutation.isPending
                  }
                >
                  {editingRule ? '更新规则' : '添加规则'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}

      {/* Rules List */}
      <div className="space-y-4">
        {rulesData?.rules && rulesData.rules.length > 0 ? (
          rulesData.rules.map((rule: CorrectionRule) => (
            <Card key={rule.id}>
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <h3 className="font-semibold">{rule.name}</h3>
                      {rule.is_active ? (
                        <span className="text-xs bg-green-100 text-green-800 px-2 py-0.5 rounded">
                          启用
                        </span>
                      ) : (
                        <span className="text-xs bg-gray-100 text-gray-800 px-2 py-0.5 rounded">
                          禁用
                        </span>
                      )}
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                        优先级: {rule.priority}
                      </span>
                    </div>

                    {rule.description && (
                      <p className="text-sm text-muted-foreground mb-2">
                        {rule.description}
                      </p>
                    )}

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                      <div>
                        <span className="font-medium">源文本: </span>
                        <code className="bg-muted px-2 py-0.5 rounded">
                          {rule.source_pattern}
                        </code>
                      </div>
                      <div>
                        <span className="font-medium">目标文本: </span>
                        <code className="bg-muted px-2 py-0.5 rounded">
                          {rule.target_text}
                        </code>
                      </div>
                    </div>

                    <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
                      {rule.source_lang && (
                        <span>源语言: {rule.source_lang}</span>
                      )}
                      {rule.target_lang && (
                        <span>目标语言: {rule.target_lang}</span>
                      )}
                      {rule.is_regex && <span>正则表达式</span>}
                      {rule.is_case_sensitive && <span>区分大小写</span>}
                    </div>
                  </div>

                  <div className="flex gap-2 ml-4">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleEdit(rule)}
                    >
                      <Edit className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        if (
                          confirm('确定要删除这条规则吗？')
                        ) {
                          deleteMutation.mutate(rule.id)
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        ) : (
          <Card>
            <CardContent className="py-12 text-center text-muted-foreground">
              <p>暂无纠正规则</p>
              <p className="text-sm mt-1">点击"添加规则"按钮创建第一条规则</p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
