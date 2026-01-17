interface StatusDotProps {
  status: 'online' | 'offline' | 'processing' | 'analyzing' | 'pending' | 'mutating' | 'idle' | 'testing' | 'waiting'
  pulse?: boolean
  size?: 'sm' | 'md' | 'lg'
  className?: string
}

export function StatusDot({ status, pulse = false, size = 'md', className = '' }: StatusDotProps) {
  const colors = {
    online: 'bg-status-accepted',
    offline: 'bg-status-rejected',
    processing: 'bg-status-processing',
    analyzing: 'bg-status-analyzing',
    pending: 'bg-status-pending',
    mutating: 'bg-status-mutating',
    idle: 'bg-status-pending',
    testing: 'bg-status-processing',
    waiting: 'bg-status-pending'
  }

  const sizes = {
    sm: 'w-1.5 h-1.5',
    md: 'w-2 h-2',
    lg: 'w-2.5 h-2.5'
  }

  const shouldPulse = pulse || ['processing', 'analyzing', 'mutating', 'testing'].includes(status)

  return (
    <span
      className={`
        inline-block rounded-full
        ${colors[status]}
        ${sizes[size]}
        ${shouldPulse ? 'animate-pulse' : ''}
        ${className}
      `}
    />
  )
}
