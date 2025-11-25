import * as ToastPrimitive from '@radix-ui/react-toast'
import { X } from 'lucide-react'
import { ReactNode, createContext, useCallback, useContext, useMemo, useState } from 'react'

import { cn } from '../lib/utils'

type ToastVariant = 'default' | 'destructive'

interface ToastOptions {
  title: string
  description?: string
  variant?: ToastVariant
}

interface ToastItem extends ToastOptions {
  id: string
}

interface ToastContextValue {
  toast: (options: ToastOptions) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

const createToastId = () =>
  typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function'
    ? crypto.randomUUID()
    : `toast-${Date.now()}-${Math.random().toString(16).slice(2)}`

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts(current => current.filter(toast => toast.id !== id))
  }, [])

  const addToast = useCallback((options: ToastOptions) => {
    setToasts(current => [...current, { ...options, id: createToastId() }])
  }, [])

  const contextValue = useMemo(() => ({ toast: addToast }), [addToast])

  return (
    <ToastPrimitive.Provider swipeDirection="right" duration={4500} label="通知">
      <ToastContext.Provider value={contextValue}>
        {children}
        {toasts.map(toast => (
          <ToastPrimitive.Root
            key={toast.id}
            onOpenChange={open => {
              if (!open) removeToast(toast.id)
            }}
            className={cn(
              'group pointer-events-auto relative w-[360px] rounded-md border bg-card/95 p-4 shadow-lg backdrop-blur transition-all',
              toast.variant === 'destructive'
                ? 'border-destructive/50 bg-destructive text-destructive-foreground'
                : 'border-border text-foreground',
            )}
          >
            <div className="flex items-start gap-3">
              <div className="flex-1 space-y-1">
                <ToastPrimitive.Title className="text-sm font-semibold leading-none">
                  {toast.title}
                </ToastPrimitive.Title>
                {toast.description ? (
                  <ToastPrimitive.Description className="text-sm text-muted-foreground">
                    {toast.description}
                  </ToastPrimitive.Description>
                ) : null}
              </div>
              <ToastPrimitive.Close asChild>
                <button
                  type="button"
                  aria-label="关闭通知"
                  className="rounded-md p-1 text-muted-foreground transition hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                >
                  <X className="h-4 w-4" />
                </button>
              </ToastPrimitive.Close>
            </div>
          </ToastPrimitive.Root>
        ))}

        <ToastPrimitive.Viewport className="fixed bottom-4 right-4 z-50 flex max-h-screen w-full max-w-sm flex-col gap-3 outline-none" />
      </ToastContext.Provider>
    </ToastPrimitive.Provider>
  )
}

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }

  return context
}
