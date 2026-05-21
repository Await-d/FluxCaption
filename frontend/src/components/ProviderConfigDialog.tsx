import React, { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'
import { AIProviderConfig } from '../api/aiProviders'
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

interface ProviderConfigDialogProps {
  provider: AIProviderConfig
  onClose: () => void
  onSave: (config: Partial<AIProviderConfig>) => void
  isSaving?: boolean
}

const ProviderConfigDialog: React.FC<ProviderConfigDialogProps> = ({
  provider,
  onClose,
  onSave,
  isSaving = false,
}) => {
  const { t } = useTranslation()
  const [formData, setFormData] = useState({
    base_url: provider.base_url || '',
    timeout: provider.timeout || 30,
    default_model: provider.default_model || '',
    priority: provider.priority || 0,
  })

  useEffect(() => {
    setFormData({
      base_url: provider.base_url || '',
      timeout: provider.timeout || 30,
      default_model: provider.default_model || '',
      priority: provider.priority || 0,
    })
  }, [provider])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSave({
      provider_name: provider.provider_name,
      display_name: provider.display_name,
      is_enabled: provider.is_enabled,
      ...formData,
    })
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>
            {t('ai_providers.configure_provider', 'Configure Provider')}
          </DialogTitle>
          <DialogDescription>
            {provider.display_name} ({provider.provider_name})
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="provider-base-url">
              {t('ai_providers.base_url', 'Base URL')}
            </Label>
            <Input
              id="provider-base-url"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={t('ai_providers.base_url_placeholder', 'https://api.example.com')}
            />
            <p className="text-xs text-muted-foreground">
              {t('ai_providers.base_url_hint', 'API endpoint URL for this provider')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-timeout">
              {t('ai_providers.timeout', 'Timeout (seconds)')}
            </Label>
            <Input
              id="provider-timeout"
              type="number"
              value={formData.timeout}
              onChange={(e) =>
                setFormData({ ...formData, timeout: parseInt(e.target.value, 10) || 30 })
              }
              min={1}
              max={300}
            />
            <p className="text-xs text-muted-foreground">
              {t('ai_providers.timeout_hint', 'Maximum wait time for API requests (1-300 seconds)')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-default-model">
              {t('ai_providers.default_model', 'Default Model')}
            </Label>
            <Input
              id="provider-default-model"
              value={formData.default_model}
              onChange={(e) => setFormData({ ...formData, default_model: e.target.value })}
              placeholder={t('ai_providers.default_model_placeholder', 'gpt-4, claude-3-opus-20240229, etc.')}
            />
            <p className="text-xs text-muted-foreground">
              {t('ai_providers.default_model_hint', 'Default model to use for this provider')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-priority">
              {t('ai_providers.priority', 'Priority')}
            </Label>
            <Input
              id="provider-priority"
              type="number"
              value={formData.priority}
              onChange={(e) =>
                setFormData({ ...formData, priority: parseInt(e.target.value, 10) || 0 })
              }
              min={0}
              max={100}
            />
            <p className="text-xs text-muted-foreground">
              {t('ai_providers.priority_hint', 'Higher priority providers are preferred (0-100)')}
            </p>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSaving}
            >
              {t('common.cancel', 'Cancel')}
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.saving', 'Saving...')}
                </>
              ) : (
                t('common.save', 'Save')
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default ProviderConfigDialog
