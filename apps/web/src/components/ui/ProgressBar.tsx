interface ProgressBarProps {
  value: number
  max?: number
  variant?: 'default' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
  showLabel?: boolean
  striped?: boolean
  animated?: boolean
  className?: string
}

export function ProgressBar({
  value,
  max = 100,
  variant = 'default',
  size = 'md',
  showLabel = false,
  striped = false,
  animated = false,
  className = ''
}: ProgressBarProps) {
  const percentage = Math.min(Math.max((value / max) * 100, 0), 100)

  const variants = {
    default: 'bg-primary-500',
    success: 'bg-success-solid',
    warning: 'bg-warning-solid',
    error: 'bg-error-solid'
  }

  const sizes = {
    sm: 'h-1.5',
    md: 'h-2',
    lg: 'h-3'
  }

  return (
    <div className={className}>
      <div className={`w-full bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden ${sizes[size]}`}>
        <div
          className={`
            h-full rounded-full transition-all duration-300 ease-out
            ${variants[variant]}
            ${striped ? 'bg-stripes' : ''}
            ${animated ? 'animate-stripes' : ''}
          `}
          style={{ width: `${percentage}%` }}
        />
      </div>
      {showLabel && (
        <div className="flex justify-between mt-1">
          <span className="text-xs text-slate-500 dark:text-slate-400">{value}</span>
          <span className="text-xs text-slate-500 dark:text-slate-400">{max}</span>
        </div>
      )}
    </div>
  )
}
