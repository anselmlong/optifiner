import { Routes, Route, useLocation } from 'react-router-dom'
import { MainLayout } from './components/layout'
import {
  Landing,
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
    <Routes>
      {/* Landing page - standalone, no layout */}
      <Route path="/" element={<Landing />} />

      {/* All other routes wrapped in MainLayout */}
      <Route
        path="*"
        element={
          <MainLayout hideSidebar={hideSidebar}>
            <Routes>
              <Route path="/dashboard" element={<Dashboard />} />
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
        }
      />
    </Routes>
  )
}

export default App
