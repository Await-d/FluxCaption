import * as React from 'react'
import { cn } from '../../lib/utils'

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

function Badge({ className, variant = 'default', ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-[0.14em] transition-colors',
        'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
        {
            'border-transparent bg-primary/90 text-primary-foreground hover:bg-primary/80':
              variant === 'default',
          'border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80':
            variant === 'secondary',
          'border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80':
            variant === 'destructive',
            'border-border/80 bg-background/50 text-foreground': variant === 'outline',
        },
        className
        )}
      {...props}
    />
  )
}

export { Badge }
