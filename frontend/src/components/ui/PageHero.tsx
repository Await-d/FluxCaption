import type { ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface PageHeroProps {
  eyebrow: string
  title: string
  description: string
  actions?: ReactNode
  metrics?: Array<{
    label: string
    value: string
    detail?: string
  }>
  className?: string
}

export function PageHero({ eyebrow, title, description, actions, metrics = [], className }: PageHeroProps) {
  return (
    <section className={cn('panel-shell relative overflow-hidden rounded-[32px] p-6 sm:p-8', className)}>
      <div className="absolute inset-y-0 right-0 hidden w-1/2 bg-[radial-gradient(circle_at_top,rgba(255,172,84,0.24),transparent_46%),radial-gradient(circle_at_70%_50%,rgba(56,189,248,0.14),transparent_36%)] lg:block" />
      <div className="relative grid gap-6 lg:grid-cols-[1.15fr_0.85fr] lg:items-end">
        <div className="space-y-4">
          <div className="eyebrow-label">{eyebrow}</div>
          <div className="max-w-3xl space-y-3">
            <h2 className="section-title text-4xl leading-none sm:text-5xl">{title}</h2>
            <p className="max-w-2xl text-sm leading-7 text-muted-foreground sm:text-base">{description}</p>
          </div>
        </div>
        <div className="space-y-4 lg:justify-self-end">
          {actions ? <div className="flex flex-wrap gap-3 lg:justify-end">{actions}</div> : null}
          {metrics.length > 0 ? (
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
              {metrics.map((metric) => (
                <div key={metric.label} className="rounded-[26px] border border-border/70 bg-background/40 p-4">
                  <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-muted-foreground">{metric.label}</div>
                  <div className="mt-3 text-3xl font-extrabold">{metric.value}</div>
                  {metric.detail ? <div className="mt-2 text-sm text-muted-foreground">{metric.detail}</div> : null}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      </div>
    </section>
  )
}
