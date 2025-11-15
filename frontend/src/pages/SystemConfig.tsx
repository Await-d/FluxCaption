import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import {
  Settings,
  Save,
  RotateCcw,
  Info,
  AlertTriangle,
  CheckCircle2,
  History,
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Label } from '../components/ui/Label'
import { Badge } from '../components/ui/Badge'
import { Textarea } from '../components/ui/Textarea'
import api from '../lib/api'
import type { SystemConfigCategory, SettingChangeHistory } from '../types/api'

export function SystemConfig() {
  const { t } = useTranslation()
  const queryClient = useQueryClient()
  const [editedValues, setEditedValues] = useState<Record<string, string>>({})
  const [changeReasons, setChangeReasons] = useState<Record<string, string>>({})
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null)
  const [validationErrors, setValidationErrors] = useState<Record<string, string>>({})
  const [showHistory, setShowHistory] = useState<string | null>(null)

  // Fetch system configuration
  const { data: categories, isLoading } = useQuery<SystemConfigCategory[]>({
    queryKey: ['system-config'],
    queryFn: () => api.getSystemConfig(),
  })

  // Fetch change history for a specific setting
  const { data: changeHistory, isLoading: isLoadingHistory, error: historyError } = useQuery<SettingChangeHistory[]>({
    queryKey: ['setting-history', showHistory],
    queryFn: () => showHistory ? api.getSettingChangeHistory(showHistory) : Promise.resolve([]),
    enabled: !!showHistory,
  })

  // Update configuration mutation
  const updateMutation = useMutation({
    mutationFn: ({ key, value, reason }: { key: string; value: string; reason?: string }) =>
      api.updateSystemConfig(key, value, reason),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] })
      queryClient.invalidateQueries({ queryKey: ['setting-history', variables.key] })
      setSaveSuccess(variables.key)
      setTimeout(() => setSaveSuccess(null), 3000)
      // Clear edited value, reason, and validation error after successful save
      setEditedValues((prev) => {
        const newValues = { ...prev }
        delete newValues[variables.key]
        return newValues
      })
      setChangeReasons((prev) => {
        const newReasons = { ...prev }
        delete newReasons[variables.key]
        return newReasons
      })
      setValidationErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[variables.key]
        return newErrors
      })
    },
    onError: (error: any, variables) => {
      // Set validation error from backend
      const errorMessage = error?.detail || 'Failed to update setting'
      setValidationErrors((prev) => ({
        ...prev,
        [variables.key]: errorMessage,
      }))
    },
  })

  // Reset configuration mutation
  const resetMutation = useMutation({
    mutationFn: (key: string) => api.resetSystemConfig(key),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-config'] })
    },
  })

  // Client-side validation
  const validateValue = (
    _key: string,
    value: string,
    valueType: string,
    constraints?: { min?: number; max?: number; unit?: string; description_suffix?: string }
  ): string | null => {
    // Type validation
    if (valueType === 'int') {
      const numValue = parseInt(value, 10)
      if (isNaN(numValue)) {
        return 'Value must be a valid integer'
      }

      // Range validation
      if (constraints) {
        if (constraints.min !== undefined && numValue < constraints.min) {
          return `Value must be at least ${constraints.min} ${constraints.unit || ''}`
        }
        if (constraints.max !== undefined && numValue > constraints.max) {
          return `Value must not exceed ${constraints.max} ${constraints.unit || ''}`
        }
      }
    }

    return null
  }

  const handleValueChange = (
    key: string,
    value: string,
    valueType: string,
    constraints?: { min?: number; max?: number; unit?: string; description_suffix?: string }
  ) => {
    setEditedValues((prev) => ({ ...prev, [key]: value }))

    // Validate on change
    const error = validateValue(key, value, valueType, constraints)
    if (error) {
      setValidationErrors((prev) => ({ ...prev, [key]: error }))
    } else {
      setValidationErrors((prev) => {
        const newErrors = { ...prev }
        delete newErrors[key]
        return newErrors
      })
    }
  }

  const handleSave = (key: string) => {
    const value = editedValues[key]
    const reason = changeReasons[key]
    if (value !== undefined && !validationErrors[key]) {
      updateMutation.mutate({ key, value, reason })
    }
  }

  const handleReset = (key: string) => {
    if (confirm(t('systemConfig.confirmReset'))) {
      resetMutation.mutate(key)
    }
  }

  const isValueChanged = (key: string, originalValue: string) => {
    return editedValues[key] !== undefined && editedValues[key] !== originalValue
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold flex items-center gap-2">
            <Settings className="h-6 w-6 sm:h-8 sm:w-8" />
            {t('systemConfig.title')}
          </h1>
          <p className="text-muted-foreground mt-2">
            {t('systemConfig.description')}
          </p>
        </div>
      </div>

      {/* Restart Warning */}
      <Card className="border-amber-500/50 bg-amber-500/10">
        <CardContent className="pt-6">
          <div className="flex items-start gap-3">
            <AlertTriangle className="h-5 w-5 text-amber-500 mt-0.5" />
            <div>
              <p className="font-medium text-amber-900 dark:text-amber-100">
                {t('systemConfig.restartWarning')}
              </p>
              <p className="text-sm text-amber-800 dark:text-amber-200 mt-1">
                {t('systemConfig.restartDescription')}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Configuration Categories */}
      {categories?.map((category) => (
        <Card key={category.category}>
          <CardHeader>
            <CardTitle className="text-lg sm:text-xl">{category.label}</CardTitle>
            <CardDescription>{category.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {category.settings.map((setting) => {
                const currentValue = editedValues[setting.key] ?? setting.value
                const hasChanged = isValueChanged(setting.key, setting.value)

                return (
                  <div
                    key={setting.key}
                    className="flex flex-col sm:flex-row sm:items-start gap-4 pb-6 border-b last:border-0 last:pb-0"
                  >
                    {/* Setting Info */}
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <Label htmlFor={setting.key} className="text-base font-medium">
                          {setting.key.split('_').map(word =>
                            word.charAt(0).toUpperCase() + word.slice(1)
                          ).join(' ')}
                        </Label>
                        <Badge variant="outline" className="text-xs">
                          {setting.value_type}
                        </Badge>
                        {saveSuccess === setting.key && (
                          <Badge variant="default" className="text-xs bg-green-500">
                            <CheckCircle2 className="h-3 w-3 mr-1" />
                            Saved
                          </Badge>
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground">
                        {setting.description}
                      </p>
                      {setting.constraints && (
                        <p className="text-xs text-blue-600 dark:text-blue-400">
                          <Info className="h-3 w-3 inline mr-1" />
                          Range: {setting.constraints.min} - {setting.constraints.max} {setting.constraints.unit}
                        </p>
                      )}
                      {validationErrors[setting.key] && (
                        <p className="text-xs text-red-600 dark:text-red-400">
                          <AlertTriangle className="h-3 w-3 inline mr-1" />
                          {validationErrors[setting.key]}
                        </p>
                      )}
                      {setting.updated_by && (
                        <p className="text-xs text-muted-foreground">
                          <Info className="h-3 w-3 inline mr-1" />
                          {t('systemConfig.lastUpdatedBy', {
                            user: setting.updated_by,
                            time: new Date(setting.updated_at).toLocaleString(),
                          })}
                        </p>
                      )}
                    </div>

                    {/* Setting Controls */}
                    <div className="flex flex-col gap-2 sm:min-w-[300px]">
                      <div className="flex items-center gap-2">
                        <Input
                          id={setting.key}
                          type={setting.value_type === 'int' ? 'number' : 'text'}
                          value={currentValue}
                          onChange={(e) => handleValueChange(
                            setting.key,
                            e.target.value,
                            setting.value_type,
                            setting.constraints
                          )}
                          className={
                            validationErrors[setting.key]
                              ? 'border-red-500 focus:border-red-500'
                              : hasChanged
                                ? 'border-primary'
                                : ''
                          }
                          disabled={!setting.is_editable}
                          min={setting.constraints?.min}
                          max={setting.constraints?.max}
                          step={setting.constraints?.step}
                        />

                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setShowHistory(setting.key)}
                          className="shrink-0"
                          title={t('systemConfig.viewHistory')}
                        >
                          <History className="h-4 w-4" />
                        </Button>

                        {hasChanged && (
                          <Button
                            size="sm"
                            onClick={() => handleSave(setting.key)}
                            disabled={updateMutation.isPending || !!validationErrors[setting.key]}
                            className="shrink-0"
                          >
                            {updateMutation.isPending ? (
                              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white" />
                            ) : (
                              <>
                                <Save className="h-4 w-4 sm:mr-2" />
                                <span className="hidden sm:inline">{t('common.save')}</span>
                              </>
                            )}
                          </Button>
                        )}

                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleReset(setting.key)}
                          disabled={resetMutation.isPending}
                          className="shrink-0"
                        >
                          <RotateCcw className="h-4 w-4" />
                        </Button>

                        {saveSuccess === setting.key && (
                          <CheckCircle2 className="h-5 w-5 text-green-500 animate-in fade-in zoom-in" />
                        )}
                      </div>

                      {/* Change Reason Input (shown when value is changed) */}
                      {hasChanged && (
                        <Textarea
                          placeholder={t('systemConfig.changeReasonPlaceholder')}
                          value={changeReasons[setting.key] || ''}
                          onChange={(e) => setChangeReasons(prev => ({
                            ...prev,
                            [setting.key]: e.target.value
                          }))}
                          className="text-xs h-16 resize-none"
                        />
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      ))}

      {/* Change History Dialog */}
      {showHistory && (
        <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
          <Card className="w-full max-w-3xl max-h-[80vh] flex flex-col">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="flex items-center gap-2">
                    <History className="h-5 w-5" />
                    {t('systemConfig.changeHistory')}
                  </CardTitle>
                  <CardDescription className="mt-1">
                    {showHistory.split('_').map(word =>
                      word.charAt(0).toUpperCase() + word.slice(1)
                    ).join(' ')}
                  </CardDescription>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => setShowHistory(null)}
                >
                  {t('common.close')}
                </Button>
              </div>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto">
              {isLoadingHistory ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
                </div>
              ) : historyError ? (
                <div className="text-center py-8">
                  <AlertTriangle className="h-12 w-12 mx-auto mb-2 text-red-500" />
                  <p className="text-red-600 dark:text-red-400 font-medium mb-2">
                    Failed to load history
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {(historyError as any)?.detail || (historyError as Error)?.message || 'Unknown error'}
                  </p>
                </div>
              ) : changeHistory && changeHistory.length > 0 ? (
                <div className="space-y-4">
                  {changeHistory.map((record) => (
                    <div
                      key={record.id}
                      className="border-l-2 border-primary pl-4 pb-4 relative"
                    >
                      <div className="absolute -left-[9px] top-0 w-4 h-4 rounded-full bg-primary border-2 border-background" />

                      <div className="flex items-start justify-between gap-4 mb-2">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <Badge variant="outline" className="text-xs">
                              {record.changed_by}
                            </Badge>
                            <span className="text-xs text-muted-foreground">
                              {new Date(record.created_at).toLocaleString()}
                            </span>
                          </div>

                          <div className="text-sm space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">{t('systemConfig.oldValue')}:</span>
                              <code className="px-2 py-1 bg-muted rounded text-xs">
                                {record.old_value || t('systemConfig.notSet')}
                              </code>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">{t('systemConfig.newValue')}:</span>
                              <code className="px-2 py-1 bg-primary/10 rounded text-xs font-semibold">
                                {record.new_value}
                              </code>
                            </div>
                          </div>

                          {record.change_reason && (
                            <div className="mt-2 text-sm">
                              <span className="text-muted-foreground">{t('systemConfig.reason')}:</span>
                              <p className="mt-1 text-xs italic bg-muted p-2 rounded">
                                "{record.change_reason}"
                              </p>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center text-muted-foreground py-8">
                  <Info className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>{t('systemConfig.noHistory')}</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
