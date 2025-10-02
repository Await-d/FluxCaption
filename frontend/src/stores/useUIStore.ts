import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface UIStore {
  sidebarOpen: boolean
  setSidebarOpen: (open: boolean) => void
  toggleSidebar: () => void
}

/**
 * UI state store with persistence
 */
export const useUIStore = create<UIStore>()(
  persist(
    (set, get) => ({
      sidebarOpen: true,

      setSidebarOpen: (open) => {
        set({ sidebarOpen: open })
      },

      toggleSidebar: () => {
        set({ sidebarOpen: !get().sidebarOpen })
      },
    }),
    {
      name: 'flux-ui-storage',
    }
  )
)
