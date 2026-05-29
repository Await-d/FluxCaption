import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Label } from '../components/ui/Label'
import { Alert } from '../components/ui/Alert'
import { useAuthStore } from '../stores/authStore'
import authApi from '../lib/authApi'
import { AlertCircle } from 'lucide-react'

export function Login() {
  const { t } = useTranslation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const setAuth = useAuthStore((state) => state.setAuth)

  const getErrorMessage = (err: any): string => {
    // Check for specific error messages from backend
    const errorDetail = err.detail || err.message || ''

    // Check for authentication failure (401 Unauthorized)
    if (errorDetail.includes('Incorrect username or password') ||
        errorDetail.includes('Invalid credentials') ||
        err.response?.status === 401) {
      return t('auth.errors.invalidCredentials')
    }

    // Check for network errors
    if (err.code === 'ERR_NETWORK' || errorDetail.includes('Network')) {
      return t('auth.errors.networkError')
    }

    // Check for server errors (5xx)
    if (err.response?.status >= 500) {
      return t('auth.errors.serverError')
    }

    return t('auth.errors.unknown')
  }

  const loginMutation = useMutation({
    mutationFn: () => authApi.login({ username, password }),
    onSuccess: (data) => {
      setAuth(data.user, data.access_token)
      navigate('/')
    },
    onError: (err: any) => {
      setError(getErrorMessage(err))
    },
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    loginMutation.mutate()
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,163,74,0.22),transparent_28%),radial-gradient(circle_at_85%_15%,rgba(59,130,246,0.18),transparent_24%),linear-gradient(180deg,rgba(7,12,21,0.28),transparent)] dark:block" />
      <div className="relative grid w-full max-w-6xl gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center">
        <div className="hidden rounded-[36px] border border-border/70 bg-card/40 p-10 backdrop-blur-xl lg:block">
          <div className="eyebrow-label">{t('login.heroEyebrow')}</div>
          <h1 className="section-title mt-6 max-w-xl text-6xl leading-[0.92]">{t('login.heroTitle')}</h1>
          <p className="mt-6 max-w-xl text-base leading-8 text-muted-foreground">
            {t('login.heroDescription')}
          </p>
        </div>

        <Card className="mx-auto w-full max-w-md rounded-[32px]">
          <CardHeader className="space-y-2 text-center">
            <div className="eyebrow-label mx-auto">{t('login.welcomeBack')}</div>
            <CardTitle className="section-title text-4xl">{t('app.title')}</CardTitle>
            <CardDescription className="text-center text-sm leading-6">
              {t('app.subtitle')}
            </CardDescription>
          </CardHeader>
          <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {error && (
              <Alert variant="destructive">
                <AlertCircle className="h-4 w-4" />
                <span>{error}</span>
              </Alert>
            )}

            <div className="space-y-2">
              <Label htmlFor="username">{t('auth.username')}</Label>
              <Input
                id="username"
                type="text"
                placeholder={t('auth.usernamePlaceholder')}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
                autoFocus
                disabled={loginMutation.isPending}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <Input
                id="password"
                type="password"
                placeholder={t('auth.passwordPlaceholder')}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
                disabled={loginMutation.isPending}
              />
            </div>

            <Button
              type="submit"
              className="w-full"
              disabled={loginMutation.isPending || !username || !password}
            >
              {loginMutation.isPending ? t('auth.loggingIn') : t('auth.login')}
            </Button>

            <div className="mt-4 text-center text-sm text-muted-foreground">
              <p>{t('auth.defaultAdminHint')}</p>
              <p>{t('auth.passwordInLogsHint')}</p>
            </div>
          </form>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
