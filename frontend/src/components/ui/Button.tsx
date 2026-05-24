import * as React from 'react'
import { cn } from '../../lib/utils'

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'destructive' | 'outline' | 'ghost' | 'link'
  size?: 'default' | 'sm' | 'lg' | 'icon'
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => {
    return (
      <button
        className={cn(
          'inline-flex items-center justify-center rounded-full text-sm font-semibold transition-all duration-200',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
          'disabled:opacity-50 disabled:pointer-events-none',
          {
            'bg-primary text-primary-foreground shadow-[0_16px_32px_-18px_hsl(var(--primary)/0.95)] hover:-translate-y-0.5 hover:bg-primary/90': variant === 'default',
            'bg-destructive text-destructive-foreground hover:bg-destructive/90':
              variant === 'destructive',
            'border border-border/80 bg-background/70 backdrop-blur hover:bg-accent hover:text-accent-foreground':
              variant === 'outline',
            'hover:bg-accent/70 hover:text-accent-foreground': variant === 'ghost',
            'text-primary underline-offset-4 hover:underline': variant === 'link',
          },
          {
            'h-11 px-5 py-2.5': size === 'default',
            'h-9 px-3.5 text-xs': size === 'sm',
            'h-12 px-8': size === 'lg',
            'h-11 w-11': size === 'icon',
          },
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)

Button.displayName = 'Button'

// Helper function for AlertDialog compatibility
export const buttonVariants = (opts?: { variant?: string; className?: string }) => {
  const variant = opts?.variant || 'default'
  return cn(
    'inline-flex items-center justify-center rounded-full text-sm font-semibold transition-all duration-200',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background',
    'disabled:opacity-50 disabled:pointer-events-none',
    {
      'bg-primary text-primary-foreground shadow-[0_16px_32px_-18px_hsl(var(--primary)/0.95)] hover:-translate-y-0.5 hover:bg-primary/90': variant === 'default',
      'bg-destructive text-destructive-foreground hover:bg-destructive/90': variant === 'destructive',
      'border border-border/80 bg-background/70 backdrop-blur hover:bg-accent hover:text-accent-foreground': variant === 'outline',
      'hover:bg-accent/70 hover:text-accent-foreground': variant === 'ghost',
      'text-primary underline-offset-4 hover:underline': variant === 'link',
    },
    'h-11 px-5 py-2.5',
    opts?.className
  )
}

export { Button }
