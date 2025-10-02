import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Library,
  ListTodo,
  Languages,
  Cpu,
  Database,
  Settings,
  ChevronLeft,
} from 'lucide-react'
import { useUIStore } from '@/stores/useUIStore'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

const navigationItems = [
  {
    nameKey: 'nav.dashboard',
    href: '/',
    icon: LayoutDashboard,
  },
  {
    nameKey: 'nav.library',
    href: '/library',
    icon: Library,
  },
  {
    nameKey: 'nav.jobs',
    href: '/jobs',
    icon: ListTodo,
  },
  {
    nameKey: 'nav.translate',
    href: '/translate',
    icon: Languages,
  },
  {
    nameKey: 'nav.models',
    href: '/models',
    icon: Cpu,
  },
  {
    nameKey: 'nav.cache',
    href: '/cache',
    icon: Database,
  },
  {
    nameKey: 'nav.settings',
    href: '/settings',
    icon: Settings,
  },
]

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const { t } = useTranslation()

  return (
    <>
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 h-screen border-r bg-card transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-20'
        )}
      >
        {/* Logo & Toggle */}
        <div className="flex h-16 items-center justify-between border-b px-4">
          {sidebarOpen ? (
            <div className="flex items-center gap-2">
              <img src="/logo.png" alt="FluxCaption" className="h-8 w-8 object-contain" />
              <span className="text-lg font-semibold">{t('app.title')}</span>
            </div>
          ) : (
            <img src="/logo.png" alt="FluxCaption" className="h-8 w-8 object-contain" />
          )}
          <button
            onClick={toggleSidebar}
            className="rounded-lg p-2 hover:bg-accent"
            aria-label={sidebarOpen ? 'Collapse sidebar' : 'Expand sidebar'}
          >
            <ChevronLeft
              className={cn(
                'h-5 w-5 transition-transform',
                !sidebarOpen && 'rotate-180'
              )}
            />
          </button>
        </div>

        {/* Navigation */}
        <nav className="space-y-1 p-4">
          {navigationItems.map((item) => (
            <NavLink
              key={item.href}
              to={item.href}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                  'hover:bg-accent hover:text-accent-foreground',
                  isActive
                    ? 'bg-primary text-primary-foreground'
                    : 'text-muted-foreground'
                )
              }
              title={!sidebarOpen ? t(item.nameKey) : undefined}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              <span
                className={cn(
                  'transition-opacity',
                  sidebarOpen ? 'opacity-100' : 'opacity-0 hidden'
                )}
              >
                {t(item.nameKey)}
              </span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Sidebar spacer */}
      <div
        className={cn(
          'transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-20'
        )}
      />
    </>
  )
}
