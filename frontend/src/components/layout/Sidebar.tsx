import { NavLink, useLocation } from 'react-router-dom'
import { useState, useEffect, type ComponentType } from 'react'
import {
  LayoutDashboard,
  Library,
  FolderOpen,
  ListTodo,
  Activity,
  FileText,
  Languages,
  Cpu,
  Database,
  Settings,
  FileEdit,
  User,
  ChevronLeft,
  ChevronDown,
  ChevronRight,
  Home,
  Folder,
  Briefcase,
  Wrench,
  Zap,
  Terminal,
  BookOpen,
  Cloud,
  Boxes,
} from 'lucide-react'
import { useUIStore } from '../../stores/useUIStore'
import { cn } from '../../lib/utils'
import { useTranslation } from 'react-i18next'

interface NavigationItem {
  nameKey: string
  href: string
  icon: ComponentType<{ className?: string }>
}

interface NavigationGroup {
  groupKey: string
  icon: ComponentType<{ className?: string }>
  items: NavigationItem[]
}

const navigationGroups: NavigationGroup[] = [
  {
    groupKey: 'nav.group.overview',
    icon: Home,
    items: [
      {
        nameKey: 'nav.dashboard',
        href: '/',
        icon: LayoutDashboard,
      },
    ],
  },
  {
    groupKey: 'nav.group.media',
    icon: Folder,
    items: [
      {
        nameKey: 'nav.library',
        href: '/library',
        icon: Library,
      },
      {
        nameKey: 'nav.localMedia',
        href: '/local-media',
        icon: FolderOpen,
      },
      {
        nameKey: 'nav.subtitles',
        href: '/subtitles',
        icon: FileText,
      },
      {
        nameKey: 'nav.translationMemory',
        href: '/translation-memory',
        icon: BookOpen,
      },
    ],
  },
  {
    groupKey: 'nav.group.tasks',
    icon: Briefcase,
    items: [
      {
        nameKey: 'nav.jobs',
        href: '/jobs',
        icon: ListTodo,
      },
      {
        nameKey: 'nav.liveProgress',
        href: '/live-progress',
        icon: Activity,
      },
      {
        nameKey: 'nav.taskCenter',
        href: '/task-center',
        icon: Terminal,
      },
      {
        nameKey: 'nav.translate',
        href: '/translate',
        icon: Languages,
      },
      {
        nameKey: 'nav.autoTranslation',
        href: '/auto-translation',
        icon: Zap,
      },
    ],
  },
  {
    groupKey: 'nav.group.system',
    icon: Wrench,
    items: [
      {
        nameKey: 'nav.models',
        href: '/models',
        icon: Cpu,
      },
      {
        nameKey: 'nav.aiProviders',
        href: '/ai-providers',
        icon: Cloud,
      },
      {
        nameKey: 'nav.aiModels',
        href: '/ai-models',
        icon: Boxes,
      },
      {
        nameKey: 'nav.cache',
        href: '/cache',
        icon: Database,
      },
      {
        nameKey: 'nav.corrections',
        href: '/corrections',
        icon: FileEdit,
      },
    ],
  },
  {
    groupKey: 'nav.group.settings',
    icon: Settings,
    items: [
      {
        nameKey: 'nav.settings',
        href: '/settings',
        icon: Settings,
      },
      {
        nameKey: 'nav.systemConfig',
        href: '/system-config',
        icon: Wrench,
      },
      {
        nameKey: 'nav.profile',
        href: '/profile',
        icon: User,
      },
    ],
  },
]

export function Sidebar() {
  const { sidebarOpen, toggleSidebar } = useUIStore()
  const { t } = useTranslation()
  const location = useLocation()

  // Find which group contains the current route
  const findActiveGroup = (pathname: string): string | null => {
    for (const group of navigationGroups) {
      if (group.items.some(item => item.href === pathname)) {
        return group.groupKey
      }
    }
    return null
  }

  // Initialize with only the active group expanded
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(() => {
    const activeGroup = findActiveGroup(location.pathname)
    return activeGroup ? new Set([activeGroup]) : new Set()
  })

  // Update expanded groups when route changes
  useEffect(() => {
    const activeGroup = findActiveGroup(location.pathname)
    if (activeGroup && !expandedGroups.has(activeGroup)) {
      setExpandedGroups(new Set([activeGroup]))
    }
  }, [location.pathname])

  const toggleGroup = (groupKey: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev)
      if (next.has(groupKey)) {
        next.delete(groupKey)
      } else {
        next.add(groupKey)
      }
      return next
    })
  }

  return (
    <>
      {/* Sidebar */}
        <aside
          className={cn(
          'fixed left-0 top-0 z-40 h-screen border-r border-border/70 bg-card/88 text-foreground shadow-[24px_0_60px_-42px_rgba(0,0,0,0.45)] backdrop-blur-2xl transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-20'
        )}
      >
        {/* Logo & Toggle */}
        <div className="flex h-20 items-center justify-between border-b border-border/60 px-4">
          {sidebarOpen ? (
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border/70 bg-background/40 shadow-inner shadow-black/5">
                <img src="/logo.png" alt="FluxCaption" className="h-7 w-7 object-contain" />
              </div>
              <div>
                <div className="text-[10px] uppercase tracking-[0.24em] text-primary/90">{t('sidebar.tagline')}</div>
                <span className="font-semibold text-foreground">{t('app.title')}</span>
              </div>
            </div>
          ) : (
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-border/70 bg-background/40">
              <img src="/logo.png" alt="FluxCaption" className="h-7 w-7 object-contain" />
            </div>
          )}
          <button
            onClick={toggleSidebar}
            className="rounded-full border border-border/70 bg-background/40 p-2 text-foreground transition hover:bg-accent/70"
            aria-label={sidebarOpen ? t('sidebar.collapse') : t('sidebar.expand')}
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
        <nav className="h-[calc(100vh-5rem)] space-y-3 overflow-y-auto px-3 py-4">
          {navigationGroups.map((group, index) => {
            const isExpanded = expandedGroups.has(group.groupKey)

            return (
              <div key={group.groupKey} className={cn(
                 "space-y-1.5",
                 !sidebarOpen && index > 0 && "pt-3 border-t border-border/70"
               )}>
                {/* Group Header - only show when sidebar is open */}
                {sidebarOpen && (
                  <button
                    onClick={() => toggleGroup(group.groupKey)}
                    className="flex w-full items-center justify-between rounded-2xl px-3 py-2.5 text-xs font-semibold uppercase tracking-[0.2em] text-muted-foreground transition-colors hover:bg-accent/60 hover:text-foreground"
                  >
                    <div className="flex items-center gap-2">
                      <group.icon className="h-4 w-4 text-primary" />
                      <span>{t(group.groupKey)}</span>
                    </div>
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                  </button>
                )}

                {/* Group Items */}
                {isExpanded && sidebarOpen && (
                  <div className="space-y-1.5 pl-1">
                    {group.items.map((item) => (
                      <NavLink
                        key={item.href}
                        to={item.href}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center gap-3 rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200',
                            'hover:bg-accent/70 hover:text-foreground',
                            isActive
                              ? 'bg-primary text-primary-foreground shadow-[0_18px_40px_-24px_hsl(var(--primary)/0.85)]'
                              : 'text-muted-foreground'
                          )
                        }
                      >
                        <item.icon className="h-5 w-5 flex-shrink-0" />
                        <span>{t(item.nameKey)}</span>
                      </NavLink>
                    ))}
                  </div>
                )}
                
                {/* Collapsed state: show items without text */}
                {!sidebarOpen && (
                  <div className="space-y-1">
                    {group.items.map((item) => (
                      <NavLink
                        key={item.href}
                        to={item.href}
                        className={({ isActive }) =>
                          cn(
                            'flex items-center justify-center rounded-2xl px-3 py-3 text-sm font-medium transition-all duration-200',
                            'hover:bg-accent/70 hover:text-foreground',
                            isActive
                              ? 'bg-primary text-primary-foreground shadow-[0_18px_40px_-24px_hsl(var(--primary)/0.85)]'
                              : 'text-muted-foreground'
                          )
                        }
                        title={t(item.nameKey)}
                      >
                        <item.icon className="h-5 w-5 flex-shrink-0" />
                      </NavLink>
                    ))}
                  </div>
                )}
              </div>
            )
          })}
        </nav>
      </aside>

      {/* Sidebar spacer */}
      <div
        className={cn(
          'shrink-0 transition-all duration-300',
          sidebarOpen ? 'w-64' : 'w-20'
        )}
      />
    </>
  )
}
