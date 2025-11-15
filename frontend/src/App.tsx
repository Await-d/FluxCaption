import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { Login } from '@/pages/Login'
import { Dashboard } from '@/pages/Dashboard'
import { Library } from '@/pages/Library'
import { Jobs } from '@/pages/Jobs'
import { LiveProgress } from '@/pages/LiveProgress'
import { Translate } from '@/pages/Translate'
import { Models } from '@/pages/Models'
import { Settings } from '@/pages/Settings'
import { Cache } from '@/pages/Cache'
import { LocalMedia } from '@/pages/LocalMedia'
import { Subtitles } from '@/pages/Subtitles'
import { Corrections } from '@/pages/Corrections'
import { Profile } from '@/pages/Profile'
import { AutoTranslation } from '@/pages/AutoTranslation'
import { TaskCenter } from '@/pages/TaskCenter'
import { TranslationMemory } from '@/pages/TranslationMemory'
import { SystemConfig } from '@/pages/SystemConfig'
import AIProvidersPage from '@/pages/AIProviders'
import AIModelsPage from '@/pages/AIModels'

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="library" element={<Library />} />
              <Route path="local-media" element={<LocalMedia />} />
              <Route path="jobs" element={<Jobs />} />
              <Route path="live-progress" element={<LiveProgress />} />
              <Route path="subtitles" element={<Subtitles />} />
              <Route path="translation-memory" element={<TranslationMemory />} />
              <Route path="translate" element={<Translate />} />
              <Route path="models" element={<Models />} />
              <Route path="ai-providers" element={<AIProvidersPage />} />
              <Route path="ai-models" element={<AIModelsPage />} />
              <Route path="cache" element={<Cache />} />
              <Route path="settings" element={<Settings />} />
              <Route path="system-config" element={<SystemConfig />} />
              <Route path="corrections" element={<Corrections />} />
              <Route path="auto-translation" element={<AutoTranslation />} />
              <Route path="task-center" element={<TaskCenter />} />
              <Route path="profile" element={<Profile />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
