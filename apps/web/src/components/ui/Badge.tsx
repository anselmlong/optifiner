import { HTMLAttributes, forwardRef } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { IconDefinition } from '@fortawesome/fontawesome-svg-core'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'info' | 'processing' | 'mutating'
  size?: 'sm' | 'md'
  icon?: IconDefinition
  dot?: boolean
  pulse?: boolean
}

export const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className = '', variant = 'default', size = 'md', icon, dot, pulse, children, ...props }, ref) => {
    const baseStyles = 'inline-flex items-center font-medium rounded-full'

    const variants = {
      default: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300',
      success: 'bg-success-bg dark:bg-success-bg-dark text-success-text dark:text-success-text-dark',
      warning: 'bg-warning-bg dark:bg-warning-bg-dark text-warning-text dark:text-warning-text-dark',
      error: 'bg-error-bg dark:bg-error-bg-dark text-error-text dark:text-error-text-dark',
      info: 'bg-info-bg dark:bg-info-bg-dark text-info-text dark:text-info-text-dark',
      processing: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400',
      mutating: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-400'
    }

    const sizes = {
      sm: 'px-2 py-0.5 text-xs gap-1',
      md: 'px-2.5 py-1 text-xs gap-1.5'
    }

    const dotColors = {
      default: 'bg-slate-400',
      success: 'bg-status-accepted',
      warning: 'bg-status-processing',
      error: 'bg-status-rejected',
      info: 'bg-status-analyzing',
      processing: 'bg-status-processing',
      mutating: 'bg-status-mutating'
    }

    return (
      <span
        ref={ref}
        className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
        {...props}
      >
        {dot && (
          <span
            className={`w-1.5 h-1.5 rounded-full ${dotColors[variant]} ${pulse ? 'animate-pulse' : ''}`}
          />
        )}
        {icon && <FontAwesomeIcon icon={icon} className="text-[0.75em]" />}
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'
