import { NavLink, useLocation } from 'react-router-dom'
import { useState, useEffect } from 'react'
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
} from 'lucide-react'
import { useUIStore } from '@/stores/useUIStore'
import { cn } from '@/lib/utils'
import { useTranslation } from 'react-i18next'

interface NavigationItem {
  nameKey: string
  href: string
  icon: any
}

interface NavigationGroup {
  groupKey: string
  icon: any
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
        <nav className="overflow-y-auto h-[calc(100vh-4rem)] p-3 space-y-2">
          {navigationGroups.map((group, index) => {
            const isExpanded = expandedGroups.has(group.groupKey)

            return (
              <div key={group.groupKey} className={cn(
                "space-y-1",
                !sidebarOpen && index > 0 && "pt-2 border-t border-border"
              )}>
                {/* Group Header - only show when sidebar is open */}
                {sidebarOpen && (
                  <button
                    onClick={() => toggleGroup(group.groupKey)}
                    className="w-full flex items-center justify-between px-3 py-2 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors rounded-lg hover:bg-accent/50"
                  >
                    <div className="flex items-center gap-2">
                      <group.icon className="h-4 w-4" />
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
                  <div className="space-y-1 pl-2">
                    {group.items.map((item) => (
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
                            'flex items-center justify-center rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                            'hover:bg-accent hover:text-accent-foreground',
                            isActive
                              ? 'bg-primary text-primary-foreground'
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
