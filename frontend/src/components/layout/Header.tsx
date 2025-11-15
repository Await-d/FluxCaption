import { Moon, Sun, Monitor, Languages, LogOut, User } from 'lucide-react'
import { useThemeStore } from '@/stores/useThemeStore'
import { useAuthStore } from '@/stores/authStore'
import { Button } from '@/components/ui/Button'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import authApi from '@/lib/authApi'

const routeNames: Record<string, string> = {
  '/': 'nav.dashboard',
  '/library': 'nav.library',
  '/local-media': 'nav.localMedia',
  '/jobs': 'nav.jobs',
  '/live-progress': 'nav.liveProgress',
  '/translate': 'nav.translate',
  '/models': 'nav.models',
  '/cache': 'nav.cache',
  '/settings': 'nav.settings',
  '/corrections': 'nav.corrections',
  '/profile': 'nav.profile',
  '/subtitles': 'nav.subtitles',
  '/auto-translation': 'nav.autoTranslation',
  '/task-center': 'nav.taskCenter',
}

export function Header() {
  const { theme, setTheme } = useThemeStore()
  const { user, clearAuth } = useAuthStore()
  const location = useLocation()
  const navigate = useNavigate()
  const { t, i18n } = useTranslation()

  const cycleTheme = () => {
    const themes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system']
    const currentIndex = themes.indexOf(theme)
    const nextTheme = themes[(currentIndex + 1) % themes.length]
    setTheme(nextTheme)
  }

  const toggleLanguage = () => {
    const newLang = i18n.language === 'zh-CN' ? 'en' : 'zh-CN'
    i18n.changeLanguage(newLang)
  }

  const logoutMutation = useMutation({
    mutationFn: () => authApi.logout(),
    onSettled: () => {
      clearAuth()
      navigate('/login')
    },
  })

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun className="h-5 w-5" />
      case 'dark':
        return <Moon className="h-5 w-5" />
      case 'system':
        return <Monitor className="h-5 w-5" />
    }
  }

  const pageNameKey = routeNames[location.pathname] || 'nav.dashboard'
  const pageName = t(pageNameKey)

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b bg-background/95 backdrop-blur px-6">
      <div>
        <h1 className="text-2xl font-bold">{pageName}</h1>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <User className="h-4 w-4" />
            <span>{user.username}</span>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleLanguage}
          aria-label={i18n.language === 'zh-CN' ? t('components.header.switchToEnglish') : t('components.header.switchToChinese')}
          title={i18n.language === 'zh-CN' ? t('components.header.switchToEnglish') : t('components.header.switchToChinese')}
        >
          <Languages className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={cycleTheme}
          aria-label={t('components.header.switchTheme', { theme: theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light' })}
        >
          {getThemeIcon()}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => logoutMutation.mutate()}
          aria-label={t('components.header.logout')}
          title={t('components.header.logout')}
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  )
}
