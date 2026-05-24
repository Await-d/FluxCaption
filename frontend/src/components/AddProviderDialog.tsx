import React, { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Plus } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/Dialog'
import { Button } from './ui/Button'
import { Input } from './ui/Input'
import { Label } from './ui/Label'
import { Textarea } from './ui/Textarea'
import { cn } from '../lib/utils'
import { getProviderFallbackModel, ProviderModelSelect } from './ProviderModelSelect'

interface AddProviderDialogProps {
  onClose: () => void
  onAdd: (config: {
    provider_name: string
    display_name: string
    api_key?: string
    base_url?: string
    timeout?: number
    default_model?: string
    priority?: number
    description?: string
  }) => void
  isAdding?: boolean
}

const AddProviderDialog: React.FC<AddProviderDialogProps> = ({
  onClose,
  onAdd,
  isAdding = false,
}) => {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    provider_name: '',
    display_name: '',
    api_key: '',
    base_url: '',
    timeout: 30,
    default_model: '',
    priority: 0,
    description: '',
  })
  const isDeepLX = formData.provider_name === 'deeplx'

  // Predefined providers list
  const predefinedProviders = [
    {
      provider_name: 'openai',
      display_name: t('ai_providers.predefined.openai.name'),
      description: t('ai_providers.predefined.openai.desc'),
      base_url: 'https://api.openai.com/v1',
    },
    {
      provider_name: 'claude',
      display_name: t('ai_providers.predefined.claude.name'),
      description: t('ai_providers.predefined.claude.desc'),
      base_url: 'https://api.anthropic.com/v1',
    },
    {
      provider_name: 'deepseek',
      display_name: t('ai_providers.predefined.deepseek.name'),
      description: t('ai_providers.predefined.deepseek.desc'),
      base_url: 'https://api.deepseek.com/v1',
    },
    {
      provider_name: 'deeplx',
      display_name: t('ai_providers.predefined.deeplx.name'),
      description: t('ai_providers.predefined.deeplx.desc'),
      base_url: 'http://localhost:1188/translate',
    },
    {
      provider_name: 'gemini',
      display_name: t('ai_providers.predefined.gemini.name'),
      description: t('ai_providers.predefined.gemini.desc'),
      base_url: 'https://generativelanguage.googleapis.com/v1',
    },
    {
      provider_name: 'zhipu',
      display_name: t('ai_providers.predefined.zhipu.name'),
      description: t('ai_providers.predefined.zhipu.desc'),
      base_url: 'https://open.bigmodel.cn/api/paas/v4',
    },
    {
      provider_name: 'moonshot',
      display_name: t('ai_providers.predefined.moonshot.name'),
      description: t('ai_providers.predefined.moonshot.desc'),
      base_url: 'https://api.moonshot.cn/v1',
    },
    {
      provider_name: 'custom_openai',
      display_name: t('ai_providers.predefined.custom_openai.name'),
      description: t('ai_providers.predefined.custom_openai.desc'),
      base_url: '',
    },
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.provider_name || !formData.display_name) {
      // eslint-disable-next-line no-alert
      alert(t('ai_providers.provider_name_required'))
      return
    }
    onAdd({
      ...formData,
      default_model: isDeepLX ? (formData.default_model || 'translate') : formData.default_model,
      timeout: isDeepLX ? (formData.timeout || 300) : formData.timeout,
    })
  }

  const handleSelectPredefined = (provider: typeof predefinedProviders[number]) => {
      const isDeepLXProvider = provider.provider_name === 'deeplx'
      setFormData({
        ...formData,
        provider_name: provider.provider_name,
        display_name: provider.display_name,
        description: provider.description,
        base_url: provider.base_url,
        default_model: isDeepLXProvider ? 'translate' : formData.default_model,
        timeout: isDeepLXProvider ? 300 : formData.timeout,
      })
  }

  const handleProviderNameChange = (providerName: string) => {
    const fallbackModel = getProviderFallbackModel(providerName)
    setFormData({
      ...formData,
      provider_name: providerName,
      default_model: fallbackModel ? (formData.default_model || fallbackModel) : formData.default_model,
      timeout: providerName === 'deeplx' ? (formData.timeout || 300) : formData.timeout,
    })
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('ai_providers.add_provider')}</DialogTitle>
          <DialogDescription>
            {t('ai_providers.add_provider_hint')}
          </DialogDescription>
        </DialogHeader>

        {/* Predefined Providers */}
        <div className="space-y-3 border-b pb-4">
          <h3 className="text-sm font-semibold">
              {t('ai_providers.quick_add')}
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {predefinedProviders.map((provider) => {
              const isSelected = formData.provider_name === provider.provider_name
              return (
                <button
                  type="button"
                  key={provider.provider_name}
                  onClick={() => handleSelectPredefined(provider)}
                  className={cn(
                    'p-3 rounded-md border text-left transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
                    isSelected
                      ? 'border-primary bg-primary/10'
                      : 'border-border hover:border-primary/50 hover:bg-accent/30'
                  )}
                >
                  <p className="font-medium text-sm">{provider.display_name}</p>
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                    {provider.description}
                  </p>
                </button>
              )
            })}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="add-provider-name">
                {t('ai_providers.provider_name')} *
              </Label>
              <Input
                id="add-provider-name"
                value={formData.provider_name}
                onChange={(e) => handleProviderNameChange(e.target.value)}
                placeholder={t('ai_providers.provider_name_placeholder')}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="add-display-name">
                {t('ai_providers.display_name')} *
              </Label>
              <Input
                id="add-display-name"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder={t('ai_providers.display_name_placeholder')}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="add-api-key">{t('ai_providers.api_key')}</Label>
              <Input
                id="add-api-key"
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                placeholder={isDeepLX
                  ? t('ai_providers.deeplx_api_key_placeholder', 'Optional token used with {{apiKey}} in the Base URL')
                  : t('ai_providers.api_key_placeholder')}
              />
              {isDeepLX && (
                <p className="text-xs text-muted-foreground">
                  {t(
                    'ai_providers.deeplx_api_key_hint',
                    'If your DeepLX address already contains the token, you can leave API Key empty. If you use {{apiKey}} in the Base URL, put the token here.'
                  )}
                </p>
              )}
            </div>

          <div className="space-y-2">
            <Label htmlFor="add-base-url">{t('ai_providers.base_url')}</Label>
            <Input
              id="add-base-url"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={isDeepLX
                ? t('ai_providers.deeplx_base_url_placeholder', 'https://host/translate?token={{apiKey}}')
                : t('ai_providers.base_url_placeholder')}
            />
            {isDeepLX && (
              <p className="text-xs text-muted-foreground">
                {t(
                  'ai_providers.deeplx_base_url_hint',
                  'DeepLX supports full endpoint URLs and {{apiKey}} placeholders, for example: https://host/translate, https://host/translate?token={{apiKey}}, or https://{{apiKey}}.host/translate'
                )}
              </p>
            )}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="add-timeout">
                {t('ai_providers.timeout')}
              </Label>
              <Input
                id="add-timeout"
                type="number"
                value={formData.timeout}
                onChange={(e) =>
                  setFormData({ ...formData, timeout: parseInt(e.target.value, 10) || 30 })
                }
                min={1}
                max={300}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="add-priority">
                {t('ai_providers.priority')}
              </Label>
              <Input
                id="add-priority"
                type="number"
                value={formData.priority}
                onChange={(e) =>
                  setFormData({ ...formData, priority: parseInt(e.target.value, 10) || 0 })
                }
                min={0}
                max={100}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="add-default-model">
                {t('ai_providers.default_model')}
              </Label>
              <ProviderModelSelect
                providerName={formData.provider_name}
                value={formData.default_model}
                onValueChange={(value) => setFormData({ ...formData, default_model: value })}
                allowCustom
                emptyLabel={t('ai_providers.no_default_model')}
                customPlaceholder={isDeepLX
                  ? 'translate'
                  : t('ai_providers.default_model_placeholder')}
                inputId="add-default-model"
              />
              {isDeepLX && (
                <p className="text-xs text-muted-foreground">
                  {t('ai_providers.deeplx_default_model_hint', 'Built-in default model is translate. You can leave this empty.')}
                </p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="add-description">
                {t('ai_providers.description')}
            </Label>
            <Textarea
              id="add-description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
               placeholder={t('ai_providers.description_placeholder')}
              rows={2}
            />
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isAdding}
            >
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isAdding}>
              {isAdding ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('ai_providers.adding')}
                </>
              ) : (
                <>
                  <Plus className="mr-2 h-4 w-4" />
                  {t('ai_providers.add_provider')}
                </>
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default AddProviderDialog
