import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText, ArrowLeft } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/Select'
import { Badge } from '../components/ui/Badge'
import { PageHero } from '../components/ui/PageHero'
import { LiveTranslationPreview } from '../components/translation/LiveTranslationPreview'
import { AIProviderSelector } from '../components/AIProviderSelector'
import api from '../lib/api'
import { cn } from '../lib/utils'
import { useTranslation } from 'react-i18next'

const LANGUAGES = [
  { code: 'zh-CN', name: 'languages.zh-CN' },
  { code: 'en', name: 'languages.en' },
  { code: 'ja', name: 'languages.ja' },
  { code: 'ko', name: 'languages.ko' },
]

export function Translate() {
  const [file, setFile] = useState<File | null>(null)
  const [sourceLang, setSourceLang] = useState<string>('auto')
  const [targetLangs, setTargetLangs] = useState<string[]>(['zh-CN'])
  const [aiSelection, setAiSelection] = useState<{ provider?: string; model?: string }>({})
  const [activeJobId, setActiveJobId] = useState<string | null>(null)
  const [showLivePreview, setShowLivePreview] = useState(false)
  const queryClient = useQueryClient()
  const { t } = useTranslation()

  // File upload dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/plain': ['.srt', '.ass', '.vtt', '.sup'],
      'application/octet-stream': ['.sup'],
    },
    maxFiles: 1,
    onDrop: (acceptedFiles) => {
      if (acceptedFiles.length > 0) {
        setFile(acceptedFiles[0])
      }
    },
  })

  // Upload and translate mutation
  const uploadMutation = useMutation({
    mutationFn: async () => {
      // Step 1: Upload file
      const uploadResult = await api.uploadSubtitle(file!)

      // Step 2: Create translation job
      const jobResult = await api.createJob({
        source_type: 'subtitle',
        source_path: uploadResult.path,
        source_lang: sourceLang,
        target_langs: targetLangs,
        model: aiSelection.model,
        provider: aiSelection.provider,
      })

      return { uploadResult, jobId: jobResult.id }
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setActiveJobId(data.jobId)
      setShowLivePreview(true)
    },
  })

  const toggleTargetLang = (lang: string) => {
    setTargetLangs((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    )
  }

  return (
    <div className="mx-auto max-w-6xl space-y-6 lg:space-y-8">
      {showLivePreview && activeJobId ? (
        <>
          <Button
            variant="outline"
            onClick={() => {
              setShowLivePreview(false)
              setActiveJobId(null)
              setFile(null)
            }}
            className="mb-4"
          >
            <ArrowLeft className="h-4 w-4 mr-2" />
            {t('translate.backToUpload')}
          </Button>
          <LiveTranslationPreview
            jobId={activeJobId}
            onComplete={() => {
              setShowLivePreview(false)
              setActiveJobId(null)
            }}
            onError={(error) => {
              console.error('Translation error:', error)
            }}
          />
        </>
      ) : (
        <>
          <PageHero
            eyebrow={t('pageHero.translate.eyebrow')}
            title={t('translate.title')}
            description={t('pageHero.translate.description')}
            metrics={[
              { label: t('pageHero.translate.metrics.formats.label'), value: 'SRT / ASS / VTT', detail: t('pageHero.translate.metrics.formats.detail') },
              { label: t('pageHero.translate.metrics.targets.label'), value: String(targetLangs.length), detail: t('pageHero.translate.metrics.targets.detail') },
              { label: t('pageHero.translate.metrics.provider.label'), value: aiSelection.provider || t('pageHero.common.auto'), detail: aiSelection.model || t('pageHero.translate.metrics.provider.detail') },
            ]}
          />
          <Card className="rounded-[30px]">
            <CardHeader>
              <CardTitle>{t('translate.title')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-8">
            {/* File Dropzone */}
            <div
              {...getRootProps()}
              className={cn(
                'cursor-pointer rounded-[30px] border-2 border-dashed p-12 text-center transition-all duration-200',
                isDragActive
                  ? 'border-primary bg-primary/10 shadow-[0_24px_48px_-30px_hsl(var(--primary)/0.8)]'
                  : 'border-border bg-background/35 hover:border-primary/50 hover:bg-background/55'
              )}
            >
              <input {...getInputProps()} />
              <Upload className="mx-auto h-12 w-12 text-muted-foreground mb-4" />
              {file ? (
                <div className="space-y-2">
                  <p className="font-medium flex items-center justify-center gap-2">
                    <FileText className="h-5 w-5" />
                    {file.name}
                  </p>
                  <p className="text-sm text-muted-foreground">
                    {(file.size / 1024).toFixed(2)} KB
                  </p>
                </div>
              ) : (
                <div>
                  <p className="text-xl font-semibold">
                    {isDragActive ? t('translate.dropzoneActive') : t('translate.dropzone')}
                  </p>
                  <p className="text-sm text-muted-foreground mt-2">
                    {t('translate.formats')}
                  </p>
                  <p className="text-xs text-muted-foreground mt-2">
                    {t('translate.ocrHint', 'PGS/SUP 图片字幕会先执行 OCR，再进入翻译流程')}
                  </p>
                </div>
              )}
            </div>

            {/* Source Language */}
            <div>
              <label className="text-sm font-medium mb-2 block">{t('translate.sourceLanguage')}</label>
              <Select value={sourceLang} onValueChange={setSourceLang}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="auto">{t('translate.autoDetect')}</SelectItem>
                  {LANGUAGES.map((lang) => (
                    <SelectItem key={lang.code} value={lang.code}>
                      {t(lang.name)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* Target Languages */}
            <div>
              <label className="text-sm font-medium mb-2 block">{t('translate.targetLanguages')}</label>
              <div className="flex flex-wrap gap-2">
                {LANGUAGES.map((lang) => (
                  <Badge
                    key={lang.code}
                    variant={targetLangs.includes(lang.code) ? 'default' : 'outline'}
                    className="cursor-pointer"
                    onClick={() => toggleTargetLang(lang.code)}
                  >
                    {t(lang.name)}
                  </Badge>
                ))}
              </div>
            </div>

            {/* Model Selection */}
            <div>
              <AIProviderSelector value={aiSelection} onChange={setAiSelection} />
              <p className="text-xs text-muted-foreground mt-2">
                {t('translate.providerSelectionHint', 'The selected provider filters available models and is sent with the translation request.')}
              </p>
            </div>

            {/* Submit Button */}
            <Button
              className="w-full"
              onClick={() => uploadMutation.mutate()}
              disabled={!file || targetLangs.length === 0 || uploadMutation.isPending}
            >
              {uploadMutation.isPending ? t('translate.uploading') : t('translate.translate')}
            </Button>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
