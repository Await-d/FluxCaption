import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { Dashboard } from '@/pages/Dashboard'
import { Library } from '@/pages/Library'
import { Jobs } from '@/pages/Jobs'
import { Translate } from '@/pages/Translate'
import { Models } from '@/pages/Models'
import { Settings } from '@/pages/Settings'
import { Cache } from '@/pages/Cache'

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
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="library" element={<Library />} />
            <Route path="jobs" element={<Jobs />} />
            <Route path="translate" element={<Translate />} />
            <Route path="models" element={<Models />} />
            <Route path="cache" element={<Cache />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
