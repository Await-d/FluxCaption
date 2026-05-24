import React, { useEffect, useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useTranslation } from 'react-i18next'
import { AlertCircle, CheckCircle2, Loader2, Send } from 'lucide-react'
import { aiProviderApi, AIProviderConfig, ProviderTestResponse } from '../api/aiProviders'
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
import { Alert, AlertDescription, AlertTitle } from './ui/Alert'
import { ProviderModelSelect } from './ProviderModelSelect'

interface ProviderConfigDialogProps {
  provider: AIProviderConfig
  openTestOnOpen?: boolean
  onClose: () => void
  onSave: (config: Partial<AIProviderConfig>) => void
  isSaving?: boolean
}

const trimToUndefined = (value: string): string | undefined => {
  const trimmed = value.trim()
  return trimmed ? trimmed : undefined
}

const ProviderConfigDialog: React.FC<ProviderConfigDialogProps> = ({
  provider,
  openTestOnOpen = false,
  onClose,
  onSave,
  isSaving = false,
}) => {
  const { t } = useTranslation()
  const isDeepLX = provider.provider_name === 'deeplx'
  const [formData, setFormData] = useState({
    api_key: '',
    base_url: provider.base_url || '',
    timeout: provider.timeout || 30,
    default_model: provider.default_model || (isDeepLX ? 'translate' : ''),
    priority: provider.priority || 0,
  })
  const [testPrompt, setTestPrompt] = useState(
    isDeepLX ? t('ai_providers.default_test_prompt_deeplx') : t('ai_providers.default_test_prompt_generic')
  )
  const [testModel, setTestModel] = useState(formData.default_model)
  const [testTargetLang, setTestTargetLang] = useState('EN')
  const [testResult, setTestResult] = useState<ProviderTestResponse | null>(null)
  const testSectionRef = useRef<HTMLDivElement | null>(null)
  const testPromptRef = useRef<HTMLTextAreaElement | null>(null)

  useEffect(() => {
    setFormData({
      api_key: '',
      base_url: provider.base_url || '',
      timeout: provider.timeout || 30,
      default_model: provider.default_model || (provider.provider_name === 'deeplx' ? 'translate' : ''),
      priority: provider.priority || 0,
    })
    setTestPrompt(provider.provider_name === 'deeplx'
      ? t('ai_providers.default_test_prompt_deeplx')
      : t('ai_providers.default_test_prompt_generic'))
    setTestModel(provider.default_model || (provider.provider_name === 'deeplx' ? 'translate' : ''))
    setTestTargetLang('EN')
    setTestResult(null)
  }, [provider])

  useEffect(() => {
    if (!openTestOnOpen) {
      return
    }

    const timer = window.setTimeout(() => {
      testSectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      testPromptRef.current?.focus()
      testPromptRef.current?.select()
    }, 50)

    return () => window.clearTimeout(timer)
  }, [openTestOnOpen, provider.provider_name])

  const testProviderMutation = useMutation({
    mutationFn: () => aiProviderApi.testProvider(provider.provider_name, {
      prompt: testPrompt,
      model: testModel || undefined,
      max_tokens: isDeepLX ? undefined : 128,
      temperature: isDeepLX ? undefined : 0.2,
      target_lang: isDeepLX ? testTargetLang : undefined,
    }),
    onSuccess: (result) => setTestResult(result),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const payload: Partial<AIProviderConfig> = {
      provider_name: provider.provider_name,
      display_name: provider.display_name,
      is_enabled: provider.is_enabled,
      base_url: trimToUndefined(formData.base_url),
      timeout: formData.timeout,
      default_model: isDeepLX
        ? (trimToUndefined(formData.default_model) || 'translate')
        : trimToUndefined(formData.default_model),
      priority: formData.priority,
    }

    const nextApiKey = trimToUndefined(formData.api_key)
    if (nextApiKey) {
      payload.api_key = nextApiKey
    }

    onSave(payload)
  }

  const handleTestProvider = () => {
    setTestResult(null)
    testProviderMutation.mutate()
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
            {t('ai_providers.configure_provider')}
          </DialogTitle>
          <DialogDescription>
            {provider.display_name} ({provider.provider_name})
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-2">
            <Label htmlFor="provider-api-key">
              {t('ai_providers.api_key')}
            </Label>
            <Input
              id="provider-api-key"
              type="password"
              value={formData.api_key}
              onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
              placeholder={isDeepLX
                ? t('ai_providers.deeplx_api_key_placeholder')
                : provider.has_api_key
                  ? t('ai_providers.api_key_set')
                  : t('ai_providers.api_key_placeholder')}
            />
            <p className="text-xs text-muted-foreground">
              {isDeepLX
                ? t('ai_providers.deeplx_api_key_hint')
                : t('ai_providers.api_key_hint')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-base-url">
              {t('ai_providers.base_url')}
            </Label>
            <Input
              id="provider-base-url"
              value={formData.base_url}
              onChange={(e) => setFormData({ ...formData, base_url: e.target.value })}
              placeholder={isDeepLX
                ? t('ai_providers.deeplx_base_url_placeholder')
                 : t('ai_providers.base_url_placeholder')}
            />
            <p className="text-xs text-muted-foreground">
              {isDeepLX
                ? t('ai_providers.deeplx_base_url_hint')
                : t('ai_providers.base_url_hint')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-timeout">
              {t('ai_providers.timeout')}
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
              {t('ai_providers.timeout_hint')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-default-model">
              {t('ai_providers.default_model')}
            </Label>
            <ProviderModelSelect
              providerName={provider.provider_name}
              value={formData.default_model}
              onValueChange={(value) => setFormData({ ...formData, default_model: value })}
              allowCustom
               emptyLabel={t('ai_providers.no_default_model')}
               customPlaceholder={isDeepLX ? 'translate' : t('ai_providers.default_model_placeholder')}
              inputId="provider-default-model"
            />
            <p className="text-xs text-muted-foreground">
              {isDeepLX
                 ? t('ai_providers.deeplx_default_model_hint')
                 : t('ai_providers.default_model_hint')}
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="provider-priority">
              {t('ai_providers.priority')}
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
              {t('ai_providers.priority_hint')}
            </p>
          </div>

          <div ref={testSectionRef} className="space-y-4 rounded-[18px] border border-border/70 bg-background/40 p-4">
            <div className="space-y-1">
              <h3 className="text-sm font-semibold">
                {t('ai_providers.test_conversation')}
              </h3>
              <p className="text-xs text-muted-foreground">
                {t('ai_providers.test_conversation_hint')}
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="provider-test-model">
                {t('ai_providers.test_model')}
              </Label>
              <ProviderModelSelect
                providerName={provider.provider_name}
                value={testModel}
                onValueChange={setTestModel}
                allowCustom
                emptyLabel={t('ai_providers.use_configured_default_model')}
                customPlaceholder={isDeepLX ? 'translate' : t('ai_providers.default_model_placeholder')}
                inputId="provider-test-model"
                disabled={testProviderMutation.isPending}
              />
            </div>

            {isDeepLX && (
              <div className="space-y-2">
                <Label htmlFor="provider-test-target-lang">
                  {t('ai_providers.target_language')}
                </Label>
                <Input
                  id="provider-test-target-lang"
                  value={testTargetLang}
                  onChange={(e) => setTestTargetLang(e.target.value.toUpperCase())}
                  maxLength={16}
                  disabled={testProviderMutation.isPending}
                />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="provider-test-prompt">
                {t('ai_providers.test_prompt')}
              </Label>
              <Textarea
                id="provider-test-prompt"
                ref={testPromptRef}
                value={testPrompt}
                onChange={(e) => setTestPrompt(e.target.value)}
                rows={3}
                maxLength={2000}
                disabled={testProviderMutation.isPending}
              />
            </div>

            {testProviderMutation.error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <AlertTitle>{t('common.error')}</AlertTitle>
                <AlertDescription>
                  {testProviderMutation.error instanceof Error
                    ? testProviderMutation.error.message
                    : t('ai_providers.test_failed')}
                </AlertDescription>
              </Alert>
            )}

            {testResult && (
              <Alert variant={testResult.success ? 'default' : 'destructive'}>
                {testResult.success ? <CheckCircle2 className="h-4 w-4" /> : <AlertCircle className="h-4 w-4" />}
                <AlertTitle>
                  {testResult.success
                    ? t('ai_providers.test_succeeded')
                    : t('ai_providers.test_failed')}
                </AlertTitle>
                <AlertDescription>
                  <div className="space-y-2">
                    <p className="text-xs text-muted-foreground">
                      {testResult.provider}{testResult.model ? ` / ${testResult.model}` : ''}
                    </p>
                    <pre className="whitespace-pre-wrap rounded-md bg-muted/60 p-3 text-xs text-foreground">
                      {testResult.success ? testResult.response_text : testResult.error}
                    </pre>
                  </div>
                </AlertDescription>
              </Alert>
            )}

            <Button
              type="button"
              variant="outline"
              onClick={handleTestProvider}
              disabled={testProviderMutation.isPending || !testPrompt.trim()}
            >
              {testProviderMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                   {t('ai_providers.testing')}
                </>
              ) : (
                <>
                  <Send className="mr-2 h-4 w-4" />
                   {t('ai_providers.test_provider')}
                </>
              )}
            </Button>
          </div>

          <DialogFooter className="gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSaving}
            >
              {t('common.cancel')}
            </Button>
            <Button type="submit" disabled={isSaving}>
              {isSaving ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {t('common.saving')}
                </>
              ) : (
                t('common.save')
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

export default ProviderConfigDialog
