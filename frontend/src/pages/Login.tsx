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
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold text-center">{t('app.title')}</CardTitle>
          <CardDescription className="text-center">
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

            <div className="text-sm text-muted-foreground text-center mt-4">
              <p>{t('auth.defaultAdminHint')}</p>
              <p>{t('auth.passwordInLogsHint')}</p>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}
