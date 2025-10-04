import { useQuery } from '@tanstack/react-query'
import { FileText, X, Clock, AlertCircle } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/Dialog'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import api from '@/lib/api'

interface TaskLogsDialogProps {
  jobId: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function TaskLogsDialog({ jobId, open, onOpenChange }: TaskLogsDialogProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['job-logs', jobId],
    queryFn: () => api.getJobLogs(jobId!),
    enabled: !!jobId && open,
    refetchOnWindowFocus: false,
  })

  const getPhaseColor = (phase: string) => {
    const colors: Record<string, string> = {
      init: 'bg-gray-500/10 text-gray-500 border-gray-500/20',
      pull: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
      extract: 'bg-cyan-500/10 text-cyan-500 border-cyan-500/20',
      asr: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
      mt: 'bg-indigo-500/10 text-indigo-500 border-indigo-500/20',
      post: 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20',
      writeback: 'bg-green-500/10 text-green-500 border-green-500/20',
      completed: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
    }
    return colors[phase] || 'bg-muted'
  }

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    })
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl max-h-[80vh]">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <DialogTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              任务执行日志
            </DialogTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </DialogHeader>

        {isLoading ? (
          <div className="py-12 text-center text-muted-foreground">
            加载日志中...
          </div>
        ) : error ? (
          <div className="py-12 text-center">
            <AlertCircle className="h-12 w-12 text-destructive mx-auto mb-4" />
            <p className="text-destructive">加载日志失败</p>
            <p className="text-sm text-muted-foreground mt-2">
              {(error as any).detail || '未知错误'}
            </p>
          </div>
        ) : data && data.logs.length > 0 ? (
          <div className="space-y-4">
            {/* Stats */}
            <div className="grid grid-cols-2 gap-4 p-4 bg-muted/50 rounded-lg">
              <div>
                <div className="text-sm text-muted-foreground">任务 ID</div>
                <div className="font-mono text-xs mt-1">{data.job_id}</div>
              </div>
              <div>
                <div className="text-sm text-muted-foreground">任务状态</div>
                <div className="font-medium mt-1">{data.job_status}</div>
              </div>
              <div className="col-span-2">
                <div className="text-sm text-muted-foreground">日志条目</div>
                <div className="font-medium mt-1">{data.total_logs} 条</div>
              </div>
            </div>

            {/* Log Timeline */}
            <div className="h-[400px] pr-4 overflow-y-auto">
              <div className="space-y-3">
                {data.logs.map((log, index) => (
                  <div
                    key={log.id}
                    className="flex gap-3 p-3 rounded-lg border bg-card hover:bg-accent/30 transition-colors"
                  >
                    {/* Timeline connector */}
                    <div className="flex flex-col items-center">
                      <div className="w-2 h-2 rounded-full bg-primary" />
                      {index < data.logs.length - 1 && (
                        <div className="w-0.5 h-full bg-border mt-1" />
                      )}
                    </div>

                    {/* Log content */}
                    <div className="flex-1 min-w-0 space-y-2">
                      {/* Header */}
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Badge variant="outline" className={getPhaseColor(log.phase)}>
                            {log.phase}
                          </Badge>
                          <span className="text-sm font-medium">
                            {log.progress.toFixed(1)}%
                          </span>
                          {log.completed !== undefined && log.total !== undefined && (
                            <span className="text-sm text-muted-foreground">
                              ({log.completed}/{log.total})
                            </span>
                          )}
                        </div>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {formatTimestamp(log.timestamp)}
                        </div>
                      </div>

                      {/* Status message */}
                      <div className="text-sm break-words">
                        {log.status}
                      </div>

                      {/* Extra data (errors) */}
                      {log.extra_data && log.extra_data.error && (
                        <div className="mt-2 p-2 bg-destructive/10 text-destructive rounded text-xs break-words">
                          <div className="font-medium mb-1">错误信息:</div>
                          {log.extra_data.error}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="py-12 text-center text-muted-foreground">
            暂无日志记录
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
