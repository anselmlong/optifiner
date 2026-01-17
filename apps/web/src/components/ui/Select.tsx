import { SelectHTMLAttributes, forwardRef } from 'react'

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: Array<{ value: string; label: string }>
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = '', label, error, options, id, ...props }, ref) => {
    const selectId = id || label?.toLowerCase().replace(/\s+/g, '-')

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5"
          >
            {label}
          </label>
        )}
        <select
          ref={ref}
          id={selectId}
          className={`
            w-full px-3 py-2.5 text-sm
            bg-white dark:bg-slate-800
            border border-slate-200 dark:border-slate-700 rounded-lg
            text-slate-900 dark:text-slate-100
            focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500
            disabled:opacity-50 disabled:cursor-not-allowed
            transition-colors duration-150
            ${error ? 'border-error-solid focus:ring-error-solid/20 focus:border-error-solid' : ''}
            ${className}
          `}
          {...props}
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        {error && (
          <p className="mt-1.5 text-xs text-error-solid">{error}</p>
        )}
      </div>
    )
  }
)

Select.displayName = 'Select'
