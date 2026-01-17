interface ToggleProps {
  checked: boolean
  onChange: (checked: boolean) => void
  label?: string
  description?: string
  disabled?: boolean
  className?: string
}

export function Toggle({ checked, onChange, label, description, disabled = false, className = '' }: ToggleProps) {
  return (
    <label className={`flex items-start gap-3 cursor-pointer ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
      <div className="relative mt-0.5">
        <input
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          disabled={disabled}
          className="sr-only"
        />
        <div className={`
          w-10 h-6 rounded-full transition-colors duration-200
          ${checked ? 'bg-primary-500' : 'bg-slate-300 dark:bg-slate-600'}
        `}>
          <div className={`
            absolute top-1 w-4 h-4 rounded-full bg-white shadow-sm transition-transform duration-200
            ${checked ? 'translate-x-5' : 'translate-x-1'}
          `} />
        </div>
      </div>
      {(label || description) && (
        <div>
          {label && (
            <span className="block text-sm font-medium text-slate-900 dark:text-slate-100">
              {label}
            </span>
          )}
          {description && (
            <span className="block text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              {description}
            </span>
          )}
        </div>
      )}
    </label>
  )
}
