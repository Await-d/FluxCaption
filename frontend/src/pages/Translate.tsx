import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Upload, FileText } from 'lucide-react'
import { useDropzone } from 'react-dropzone'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/Select'
import { Badge } from '@/components/ui/Badge'
import api from '@/lib/api'
import { cn } from '@/lib/utils'
import type { OllamaModelListResponse } from '@/types/api'
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
  const [selectedModel, setSelectedModel] = useState<string>('default')
  const queryClient = useQueryClient()
  const { t } = useTranslation()

  // Fetch available models
  const { data: modelsData } = useQuery<OllamaModelListResponse>({
    queryKey: ['ollama-models'],
    queryFn: () => api.getOllamaModels(),
  })

  // File upload dropzone
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      'text/plain': ['.srt', '.ass', '.vtt'],
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
      await api.createJob({
        source_type: 'subtitle',
        source_path: uploadResult.path,
        source_lang: sourceLang,
        target_langs: targetLangs,
        model: selectedModel === 'default' ? undefined : selectedModel,
      })

      return uploadResult
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['jobs'] })
      setFile(null)
    },
  })

  const toggleTargetLang = (lang: string) => {
    setTargetLangs((prev) =>
      prev.includes(lang) ? prev.filter((l) => l !== lang) : [...prev, lang]
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t('translate.title')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* File Dropzone */}
          <div
            {...getRootProps()}
            className={cn(
              'border-2 border-dashed rounded-lg p-12 text-center cursor-pointer transition-colors',
              isDragActive ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50'
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
                <p className="text-lg font-medium">
                  {isDragActive ? t('translate.dropzoneActive') : t('translate.dropzone')}
                </p>
                <p className="text-sm text-muted-foreground mt-2">
                  {t('translate.formats')}
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
            <label className="text-sm font-medium mb-2 block">{t('translate.model')}</label>
            <Select value={selectedModel} onValueChange={setSelectedModel}>
              <SelectTrigger>
                <SelectValue placeholder={t('translate.useDefault')} />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="default">{t('translate.defaultModel')}</SelectItem>
                {modelsData?.models.map((model) => (
                  <SelectItem key={model.name} value={model.name}>
                    {model.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
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
    </div>
  )
}
