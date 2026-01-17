import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faSun,
  faMoon,
  faBell,
  faSearch,
  faPause,
  faPlay,
  faCog
} from '@fortawesome/free-solid-svg-icons'
import { useStore } from '../../store'
import { Button } from '../ui/Button'
import { Badge } from '../ui/Badge'

interface HeaderProps {
  title?: string
  subtitle?: string
  showEvolutionControls?: boolean
}

export function Header({ title, subtitle, showEvolutionControls = false }: HeaderProps) {
  const { theme, toggleTheme, isPaused, togglePause, currentGeneration, totalCost, efficiency } = useStore()

  return (
    <header className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 px-6 flex items-center justify-between">
      {/* Left side - Title */}
      <div className="flex items-center gap-4">
        {title && (
          <div>
            <h1 className="text-xl font-tech-header text-slate-900 dark:text-primary-400 flex items-center gap-2">
              {title}
              {subtitle && (
                <Badge variant="info" size="sm" dot pulse>
                  {subtitle}
                </Badge>
              )}
            </h1>
          </div>
        )}
      </div>

      {/* Center - Evolution Stats (when in evolution view) */}
      {showEvolutionControls && (
        <div className="flex items-center gap-8">
          <div className="text-center">
            <p className="stat-label">GENERATION</p>
            <p className="stat-value font-tech-value">{currentGeneration}</p>
          </div>
          <div className="text-center">
            <p className="stat-label">EST. COST</p>
            <p className="stat-value font-tech-value text-primary-400">${totalCost.toFixed(2)}</p>
          </div>
          <div className="text-center">
            <p className="stat-label">EFFICIENCY</p>
            <p className="stat-value font-tech-value text-primary-400">{efficiency}%</p>
          </div>
          <Button
            variant={isPaused ? 'primary' : 'secondary'}
            icon={isPaused ? faPlay : faPause}
            onClick={togglePause}
          >
            {isPaused ? 'Resume' : 'Pause'}
          </Button>
          <Button variant="ghost" icon={faCog} />
        </div>
      )}

      {/* Right side - Actions */}
      <div className="flex items-center gap-2">
        {/* Search */}
        <button className="p-2.5 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
          <FontAwesomeIcon icon={faSearch} />
        </button>

        {/* Notifications */}
        <button className="p-2.5 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors relative">
          <FontAwesomeIcon icon={faBell} />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-error-solid rounded-full" />
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2.5 rounded-lg text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <FontAwesomeIcon icon={theme === 'light' ? faMoon : faSun} />
        </button>
      </div>
    </header>
  )
}
