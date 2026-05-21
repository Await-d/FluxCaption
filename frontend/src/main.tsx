import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'sonner'
import App from './App'
import './index.css'
import './i18n/config'
import { ToastProvider } from './hooks/use-toast'
import { useThemeStore } from './stores/useThemeStore'

// Initialize theme on startup
const initialTheme = useThemeStore.getState().theme
const root = window.document.documentElement
root.classList.remove('light', 'dark')
if (initialTheme === 'system') {
  const systemTheme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  root.classList.add(systemTheme)
} else {
  root.classList.add(initialTheme)
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ToastProvider>
      <App />
      <Toaster
        richColors
        closeButton
        position="bottom-right"
        theme={initialTheme === 'system' ? 'system' : initialTheme}
      />
    </ToastProvider>
  </React.StrictMode>,
)
