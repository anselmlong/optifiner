import { Routes, Route, useLocation } from 'react-router-dom'
import { MainLayout } from './components/layout'
import {
  Dashboard,
  EvolutionMonitor,
  CodeAnalysis,
  Projects,
  Settings,
  Analytics,
  History,
  Help,
  NewProject,
  DocsPage
} from './pages'

function App() {
  const location = useLocation()
  
  // Routes that should not have a sidebar (project-specific views)
  const noSidebarRoutes = ['/projects/', '/evolution/']
  const hideSidebar = noSidebarRoutes.some(route => location.pathname.startsWith(route) && location.pathname !== '/projects/new')

  return (
    <MainLayout hideSidebar={hideSidebar}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/projects/new" element={<NewProject />} />
        <Route path="/projects/:projectId" element={<EvolutionMonitor />} />
        <Route path="/projects/:projectId/analysis/:nodeId" element={<CodeAnalysis />} />
        <Route path="/analytics" element={<Analytics />} />
        <Route path="/history" element={<History />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/help" element={<Help />} />
        <Route path="/docs" element={<DocsPage />} />
        <Route path="/docs/:docId" element={<DocsPage />} />
      </Routes>
    </MainLayout>
  )
}

export default App
