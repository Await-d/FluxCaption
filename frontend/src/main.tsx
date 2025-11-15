import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'
import './i18n/config'

// Initialize theme on startup
import { useThemeStore } from '@/stores/useThemeStore'
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
    <App />
  </React.StrictMode>,
)
