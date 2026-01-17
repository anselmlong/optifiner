import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowUp, faArrowDown } from '@fortawesome/free-solid-svg-icons'
import { IconDefinition } from '@fortawesome/fontawesome-svg-core'
import { Card } from './Card'

interface MetricCardProps {
  label: string
  value: string | number
  change?: number
  changeLabel?: string
  icon?: IconDefinition
  iconColor?: string
  prefix?: string
  suffix?: string
  className?: string
}

export function MetricCard({
  label,
  value,
  change,
  changeLabel,
  icon,
  iconColor = 'text-primary-500',
  prefix,
  suffix,
  className = ''
}: MetricCardProps) {
  const isPositive = change !== undefined && change > 0
  const isNegative = change !== undefined && change < 0

  return (
    <Card className={className} padding="md">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            {label}
          </p>
          <div className="flex items-baseline gap-1">
            {prefix && <span className="text-lg text-slate-500 dark:text-slate-400">{prefix}</span>}
            <span className="text-3xl font-bold text-slate-900 dark:text-slate-100">{value}</span>
            {suffix && <span className="text-lg text-slate-500 dark:text-slate-400">{suffix}</span>}
          </div>
          {change !== undefined && (
            <div className={`flex items-center gap-1 mt-2 text-sm ${
              isPositive ? 'text-success-solid' : isNegative ? 'text-error-solid' : 'text-slate-500'
            }`}>
              {isPositive && <FontAwesomeIcon icon={faArrowUp} className="text-xs" />}
              {isNegative && <FontAwesomeIcon icon={faArrowDown} className="text-xs" />}
              <span>{isPositive ? '+' : ''}{change}%</span>
              {changeLabel && <span className="text-slate-500 dark:text-slate-400">{changeLabel}</span>}
            </div>
          )}
        </div>
        {icon && (
          <div className={`p-2.5 rounded-lg bg-slate-100 dark:bg-slate-700 ${iconColor}`}>
            <FontAwesomeIcon icon={icon} className="text-lg" />
          </div>
        )}
      </div>
    </Card>
  )
}
