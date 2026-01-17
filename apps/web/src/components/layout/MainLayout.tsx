import { ReactNode } from 'react'
import { Sidebar } from './Sidebar'
import { useStore } from '../../store'

interface MainLayoutProps {
  children: ReactNode
  hideSidebar?: boolean
}

export function MainLayout({ children, hideSidebar = false }: MainLayoutProps) {
  const { sidebarCollapsed } = useStore()

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-900">
      {!hideSidebar && <Sidebar />}
      <main
        className={`
          transition-all duration-300 ease-in-out min-h-screen
          ${hideSidebar ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-60'}
        `}
      >
        {children}
      </main>
    </div>
  )
}
