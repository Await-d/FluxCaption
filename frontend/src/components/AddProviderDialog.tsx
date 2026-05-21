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

interface AddProviderDialogProps {
  onClose: () => void
  onAdd: (config: {
    provider_name: string
    display_name: string
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
    base_url: '',
    timeout: 30,
    default_model: '',
    priority: 0,
    description: '',
  })

  // Predefined providers list
  const predefinedProviders = [
    {
      provider_name: 'openai',
      display_name: t('ai_providers.predefined.openai.name', 'OpenAI (GPT)'),
      description: t('ai_providers.predefined.openai.desc', 'OpenAI GPT models (GPT-4, GPT-3.5, etc.)'),
      base_url: 'https://api.openai.com/v1',
    },
    {
      provider_name: 'claude',
      display_name: t('ai_providers.predefined.claude.name', 'Claude (Anthropic)'),
      description: t('ai_providers.predefined.claude.desc', 'Anthropic Claude models (Opus, Sonnet, Haiku)'),
      base_url: 'https://api.anthropic.com/v1',
    },
    {
      provider_name: 'deepseek',
      display_name: t('ai_providers.predefined.deepseek.name', 'DeepSeek'),
      description: t('ai_providers.predefined.deepseek.desc', 'DeepSeek AI models (affordable and powerful)'),
      base_url: 'https://api.deepseek.com/v1',
    },
    {
      provider_name: 'gemini',
      display_name: t('ai_providers.predefined.gemini.name', 'Gemini (Google)'),
      description: t('ai_providers.predefined.gemini.desc', 'Google Gemini models'),
      base_url: 'https://generativelanguage.googleapis.com/v1',
    },
    {
      provider_name: 'zhipu',
      display_name: t('ai_providers.predefined.zhipu.name', '智谱AI (GLM)'),
      description: t('ai_providers.predefined.zhipu.desc', '智谱AI GLM models - Chinese-optimized'),
      base_url: 'https://open.bigmodel.cn/api/paas/v4',
    },
    {
      provider_name: 'moonshot',
      display_name: t('ai_providers.predefined.moonshot.name', 'Moonshot AI (Kimi)'),
      description: t('ai_providers.predefined.moonshot.desc', 'Moonshot Kimi models - Super long context'),
      base_url: 'https://api.moonshot.cn/v1',
    },
    {
      provider_name: 'custom_openai',
      display_name: t('ai_providers.predefined.custom_openai.name', 'Custom OpenAI Compatible'),
      description: t('ai_providers.predefined.custom_openai.desc', 'Custom OpenAI-compatible endpoint (OpenRouter, LocalAI, vLLM, etc.)'),
      base_url: '',
    },
  ]

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!formData.provider_name || !formData.display_name) {
      // eslint-disable-next-line no-alert
      alert(t('ai_providers.provider_name_required', 'Provider name and display name are required'))
      return
    }
    onAdd(formData)
  }

  const handleSelectPredefined = (provider: typeof predefinedProviders[number]) => {
    setFormData({
      ...formData,
      provider_name: provider.provider_name,
      display_name: provider.display_name,
      description: provider.description,
      base_url: provider.base_url,
    })
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{t('ai_providers.add_provider', 'Add Provider')}</DialogTitle>
          <DialogDescription>
            {t('ai_providers.add_provider_hint', 'Add a new AI provider or restore a deleted one')}
          </DialogDescription>
        </DialogHeader>

        {/* Predefined Providers */}
        <div className="space-y-3 border-b pb-4">
          <h3 className="text-sm font-semibold">
            {t('ai_providers.quick_add', 'Quick Add')}
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
                {t('ai_providers.provider_name', 'Provider Name')} *
              </Label>
              <Input
                id="add-provider-name"
                value={formData.provider_name}
                onChange={(e) => setFormData({ ...formData, provider_name: e.target.value })}
                placeholder={t('ai_providers.provider_name_placeholder', 'openai, claude, custom_provider')}
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="add-display-name">
                {t('ai_providers.display_name', 'Display Name')} *
              </Label>
              <Input
                id="add-display-name"
                value={formData.display_name}
                onChange={(e) => setFormData({ ...formData, display_name: e.target.value })}
                placeholder={t('ai_providers.display_name_placeholder', 'OpenAI (GPT)')}
                required
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="add-base-url">{t('ai_providers.base_url', 'Base URL')}</Label>
            <Input
              id="add-base-url"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={t('ai_providers.base_url_placeholder', 'https://api.example.com/v1')}
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="add-timeout">
                {t('ai_providers.timeout', 'Timeout (seconds)')}
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
                {t('ai_providers.priority', 'Priority')}
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
                {t('ai_providers.default_model', 'Default Model')}
              </Label>
              <Input
                id="add-default-model"
                value={formData.default_model}
                onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
                placeholder={t('ai_providers.default_model_placeholder', 'gpt-4, claude-3')}
              />
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="add-description">
              {t('ai_providers.description', 'Description')}
            </Label>
            <Textarea
              id="add-description"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder={t('ai_providers.description_placeholder', 'Provider description...')}
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
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button type="submit" disabled={isAdding}>
              {isAdding ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('ai_providers.adding', 'Adding...')}
                </>
              ) : (
                <>
                  <Plus className="mr-2 h-4 w-4" />
                  {t('ai_providers.add_provider', 'Add Provider')}
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
