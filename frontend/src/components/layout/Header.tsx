import { Moon, Sun, Monitor, Languages } from 'lucide-react'
import { useThemeStore } from '@/stores/useThemeStore'
import { Button } from '@/components/ui/Button'
import { useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'

const routeNames: Record<string, string> = {
  '/': 'nav.dashboard',
  '/library': 'nav.library',
  '/jobs': 'nav.jobs',
  '/translate': 'nav.translate',
  '/models': 'nav.models',
  '/settings': 'nav.settings',
}

export function Header() {
  const { theme, setTheme } = useThemeStore()
  const location = useLocation()
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
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleLanguage}
          aria-label="Switch language"
          title={i18n.language === 'zh-CN' ? 'Switch to English' : '切换到中文'}
        >
          <Languages className="h-5 w-5" />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={cycleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : theme === 'dark' ? 'system' : 'light'} theme`}
        >
          {getThemeIcon()}
        </Button>
      </div>
    </header>
  )
}
