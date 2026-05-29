import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'
import * as aiModelsApi from '../api/aiModels'
import { Input } from './ui/Input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/Select'

const EMPTY_MODEL_VALUE = '__fluxcaption_empty_model__'
const CUSTOM_MODEL_VALUE = '__fluxcaption_custom_model__'

export function getProviderFallbackModel(providerName?: string) {
  return providerName === 'deeplx' ? 'translate' : undefined
}

interface ProviderModelSelectProps {
  providerName?: string
  value?: string
  onValueChange: (value: string) => void
  disabled?: boolean
  enabledOnly?: boolean
  allowEmpty?: boolean
  allowCustom?: boolean
  emptyLabel?: string
  placeholder?: string
  customPlaceholder?: string
  inputId?: string
}

export function ProviderModelSelect({
  providerName,
  value = '',
  onValueChange,
  disabled = false,
  enabledOnly = true,
  allowEmpty = true,
  allowCustom = false,
  emptyLabel,
  placeholder,
  customPlaceholder,
  inputId,
}: ProviderModelSelectProps) {
  const { t } = useTranslation()
  const [customSelected, setCustomSelected] = useState(false)

  const { data, isLoading } = useQuery({
    queryKey: ['ai-models', 'provider-select', providerName, enabledOnly],
    queryFn: () =>
      aiModelsApi.listModels({
        provider: providerName,
        enabled_only: enabledOnly,
        page: 1,
        page_size: 100,
      }),
    enabled: !!providerName,
  })

  const models = data?.models ?? []
  const fallbackModel = getProviderFallbackModel(providerName)
  const modelNames = useMemo(() => new Set(models.map((model) => model.model_name)), [models])
  const hasKnownValue = !!value && (modelNames.has(value) || value === fallbackModel)
  const showCurrentValue = !!value && !hasKnownValue && !allowCustom
  const showFallbackValue = !!fallbackModel && !modelNames.has(fallbackModel)

  useEffect(() => {
    if (!allowCustom || hasKnownValue) {
      setCustomSelected(false)
      return
    }

    if (value) {
      setCustomSelected(true)
    }
  }, [allowCustom, hasKnownValue, value])

  useEffect(() => {
    setCustomSelected(false)
  }, [providerName])

  const selectValue = customSelected
    ? CUSTOM_MODEL_VALUE
    : value || (allowEmpty ? EMPTY_MODEL_VALUE : undefined)

  const handleSelectChange = (nextValue: string) => {
    if (nextValue === CUSTOM_MODEL_VALUE) {
      setCustomSelected(true)
      if (hasKnownValue) {
        onValueChange('')
      }
      return
    }

    setCustomSelected(false)
    onValueChange(nextValue === EMPTY_MODEL_VALUE ? '' : nextValue)
  }

  if (!providerName) {
    return (
      <Select disabled value={EMPTY_MODEL_VALUE}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder || t('common.select')} />
        </SelectTrigger>
      </Select>
    )
  }

  if (isLoading) {
    return (
      <div className="flex h-10 items-center gap-2 rounded-md border border-input bg-background px-3 py-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        {t('common.loading')}
      </div>
    )
  }

  return (
    <div className="space-y-2">
      <Select value={selectValue} onValueChange={handleSelectChange} disabled={disabled}>
        <SelectTrigger>
          <SelectValue placeholder={placeholder || t('common.select')} />
        </SelectTrigger>
        <SelectContent>
          {allowEmpty && (
            <SelectItem value={EMPTY_MODEL_VALUE}>
              {emptyLabel || t('translate.useDefault')}
            </SelectItem>
          )}
          {models.map((model) => (
            <SelectItem key={model.id} value={model.model_name}>
              {model.display_name || model.model_name}
              {model.is_default ? ` (${t('jobs.default')})` : ''}
            </SelectItem>
          ))}
          {showFallbackValue && (
            <SelectItem value={fallbackModel}>
              {fallbackModel}
              {providerName === 'deeplx' ? ` (${t('jobs.default')})` : ''}
            </SelectItem>
          )}
          {showCurrentValue && <SelectItem value={value}>{value}</SelectItem>}
          {allowCustom && (
            <SelectItem value={CUSTOM_MODEL_VALUE}>
              {t('aiModels.useCustom')}
            </SelectItem>
          )}
        </SelectContent>
      </Select>

      {customSelected && (
        <Input
          id={inputId}
          value={value}
          onChange={(event) => onValueChange(event.target.value)}
          placeholder={customPlaceholder || t('ai_providers.default_model_placeholder')}
          disabled={disabled}
        />
      )}
    </div>
  )
}
