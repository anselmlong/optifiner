import { NavLink } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faChartLine,
  faFolderOpen,
  faCog,
  faChartPie,
  faHistory,
  faQuestionCircle,
  faChevronLeft,
  faChevronRight,
  faDna
} from '@fortawesome/free-solid-svg-icons'
import { useStore } from '../../store'

const mainNavItems = [
  { to: '/', icon: faChartLine, label: 'Dashboard' },
  { to: '/projects', icon: faFolderOpen, label: 'Projects' },
  { to: '/analytics', icon: faChartPie, label: 'Analytics' },
  { to: '/history', icon: faHistory, label: 'History' },
]

const bottomNavItems = [
  { to: '/settings', icon: faCog, label: 'Model Settings' },
  { to: '/help', icon: faQuestionCircle, label: 'Help & Docs' },
]

export function Sidebar() {
  const { sidebarCollapsed, setSidebarCollapsed } = useStore()

  return (
    <aside
      className={`
        fixed top-0 left-0 h-screen z-30
        sidebar-gradient border-r border-slate-200/50 dark:border-slate-700
        transition-all duration-300 ease-in-out
        flex flex-col
        ${sidebarCollapsed ? 'w-16' : 'w-60'}
      `}
    >
      {/* Logo */}
      <div className={`flex items-center h-16 px-4 border-b border-slate-200/50 dark:border-slate-700 ${sidebarCollapsed ? 'justify-center' : 'gap-3'}`}>
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-500 to-primary-700 flex items-center justify-center shadow-md">
          <FontAwesomeIcon icon={faDna} className="text-white text-sm" />
        </div>
        {!sidebarCollapsed && (
          <div>
            <h1 className="text-lg font-bold text-slate-900 dark:text-white">Optifiner</h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 -mt-0.5">Self-Evolving Framework</p>
          </div>
        )}
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {mainNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
              transition-all duration-150
              ${isActive
                ? 'bg-primary-500/10 text-primary-600 dark:text-primary-400'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-100'
              }
              ${sidebarCollapsed ? 'justify-center' : ''}
            `}
          >
            <FontAwesomeIcon icon={item.icon} className={`text-base ${sidebarCollapsed ? '' : 'w-5'}`} />
            {!sidebarCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* Bottom Navigation */}
      <div className="px-3 py-4 space-y-1 border-t border-slate-200/50 dark:border-slate-700">
        {bottomNavItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) => `
              flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
              transition-all duration-150
              ${isActive
                ? 'bg-primary-500/10 text-primary-600 dark:text-primary-400'
                : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-100'
              }
              ${sidebarCollapsed ? 'justify-center' : ''}
            `}
          >
            <FontAwesomeIcon icon={item.icon} className={`text-base ${sidebarCollapsed ? '' : 'w-5'}`} />
            {!sidebarCollapsed && <span>{item.label}</span>}
          </NavLink>
        ))}

        {/* Collapse Button */}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className={`
            flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium w-full
            text-slate-600 dark:text-slate-400 hover:bg-slate-100/50 dark:hover:bg-slate-800/50 hover:text-slate-900 dark:hover:text-slate-100
            transition-all duration-150
            ${sidebarCollapsed ? 'justify-center' : ''}
          `}
        >
          <FontAwesomeIcon icon={sidebarCollapsed ? faChevronRight : faChevronLeft} className={`text-base ${sidebarCollapsed ? '' : 'w-5'}`} />
          {!sidebarCollapsed && <span>Collapse</span>}
        </button>
      </div>

      {/* User Profile */}
      {!sidebarCollapsed && (
        <div className="px-3 py-4 border-t border-slate-200/50 dark:border-slate-700">
          <div className="flex items-center gap-3 px-3 py-2">
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white text-sm font-medium">
              AT
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 dark:text-white truncate">Alex Thomas</p>
              <p className="text-xs text-slate-500 dark:text-slate-400">Lead Developer</p>
            </div>
          </div>
        </div>
      )}
    </aside>
  )
}
