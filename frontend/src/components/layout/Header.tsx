import { Moon, Sun, Monitor, Languages, LogOut, User, Sparkles } from 'lucide-react'
import { useThemeStore } from '../../stores/useThemeStore'
import { useAuthStore } from '../../stores/authStore'
import { useUIStore } from '../../stores/useUIStore'
import { Button } from '../ui/Button'
import { useLocation, useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@tanstack/react-query'
import authApi from '../../lib/authApi'

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
  const { sidebarOpen } = useUIStore()
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
    <header
      className="fixed top-4 right-4 z-30 flex h-20 items-center justify-between rounded-[28px] border border-border/70 bg-background/72 px-4 shadow-[0_24px_50px_-32px_rgba(0,0,0,0.55)] backdrop-blur-2xl transition-[left] duration-300 sm:px-6"
      style={{ left: sidebarOpen ? '16rem' : '5rem' }}
    >
      <div className="min-w-0">
        <div className="mb-1 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-primary">
          <Sparkles className="h-3.5 w-3.5" />
          <span>{t('app.commandDeck')}</span>
        </div>
        <h1 className="section-title truncate text-3xl md:text-[2.2rem]">{pageName}</h1>
      </div>

      <div className="flex items-center gap-2 sm:gap-3">
        {user && (
          <div className="hidden items-center gap-3 rounded-full border border-border/70 bg-card/65 px-4 py-2 text-sm text-muted-foreground md:flex">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/15 text-primary">
              <User className="h-4 w-4" />
            </div>
            <div>
              <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted-foreground/80">{t('app.operator')}</div>
              <span className="text-sm font-semibold text-foreground">{user.username}</span>
            </div>
          </div>
        )}
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleLanguage}
          className="bg-card/40"
          aria-label={i18n.language === 'zh-CN' ? t('components.header.switchToEnglish') : t('components.header.switchToChinese')}
          title={i18n.language === 'zh-CN' ? t('components.header.switchToEnglish') : t('components.header.switchToChinese')}
        >
          <Languages className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={cycleTheme}
          className="bg-card/40"
          aria-label={t('components.header.switchTheme', { theme: theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light' })}
        >
          {getThemeIcon()}
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={() => logoutMutation.mutate()}
          className="bg-card/40"
          aria-label={t('components.header.logout')}
          title={t('components.header.logout')}
        >
          <LogOut className="h-5 w-5" />
        </Button>
      </div>
    </header>
  )
}
