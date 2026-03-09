import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faPlus,
  faSearch,
  faPlay,
  faPause,
  faTrash,
  faEllipsisV,
  faChartLine,
  faFolder,
  faSpinner,
  faHdd,
  faCheck,
  faExclamationTriangle
} from '@fortawesome/free-solid-svg-icons'
import { faGithub as faGithubBrand } from '@fortawesome/free-brands-svg-icons'
import { Header } from '../components/layout/Header'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { ProgressBar } from '../components/ui/ProgressBar'
import { ConfirmDialog } from '../components/ui/ConfirmDialog'
import { useStore } from '../store'

export function Projects() {
  const {
    projects,
    projectsLoading,
    projectsError,
    fetchProjects,
    deleteProject,
    deleteProjectLoading,
    pauseWorkflow,
    resumeWorkflow,
    pauseLoading,
    resumeLoading,
    fetchProjectWorkflows,
    updateProject,
  } = useStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [filter, setFilter] = useState<'all' | 'active' | 'paused' | 'completed' | 'local'>('all')
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [projectToDelete, setProjectToDelete] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Fetch projects on mount
  useEffect(() => {
    fetchProjects()
  }, [fetchProjects])

  const filteredProjects = projects.filter(project => {
    const matchesSearch = project.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          project.description?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesFilter = filter === 'all' || 
                          (filter === 'local' && project.isLocal) ||
                          (!project.isLocal && project.status === filter)
    return matchesSearch && matchesFilter
  })

  const stats = {
    total: projects.length,
    active: projects.filter(p => p.status === 'active' && !p.isLocal).length,
    paused: projects.filter(p => p.status === 'paused').length,
    completed: projects.filter(p => p.status === 'completed').length,
    local: projects.filter(p => p.isLocal).length,
  }

  const handleDeleteClick = (projectId: string) => {
    setProjectToDelete(projectId)
    setDeleteConfirmOpen(true)
  }

  const handleDeleteConfirm = async () => {
    if (projectToDelete) {
      const success = await deleteProject(projectToDelete)
      if (success) {
        setDeleteConfirmOpen(false)
        setProjectToDelete(null)
      }
    }
  }

  const handlePauseResume = async (projectId: string, currentStatus: string) => {
    setActionLoading(projectId)
    try {
      // Fetch workflows for this project to find the active one
      const workflows = await fetchProjectWorkflows(projectId)

      // Find the running or paused workflow
      const activeWorkflow = workflows.find(w => w.status === 'running' || w.status === 'paused')

      if (!activeWorkflow) {
        // No active workflow, just update project status directly
        await updateProject(projectId, {
          status: currentStatus === 'active' ? 'paused' : 'active'
        })
      } else {
        // Use workflow ID to pause/resume
        if (currentStatus === 'active') {
          await pauseWorkflow(activeWorkflow.workflow_id)
        } else if (currentStatus === 'paused') {
          await resumeWorkflow(activeWorkflow.workflow_id)
        }
      }

      // Refresh projects to get updated status
      fetchProjects()
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="min-h-screen">
      <Header title="Projects" />

      <div className="p-6 space-y-6">
        {/* Stats */}
        <div className="grid grid-cols-5 gap-4">
          <Card className="cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors" onClick={() => setFilter('all')}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
                <FontAwesomeIcon icon={faFolder} className="text-slate-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.total}</p>
                <p className="text-sm text-slate-500">Total</p>
              </div>
            </div>
          </Card>
          <Card className="cursor-pointer hover:border-amber-300 dark:hover:border-amber-700 transition-colors" onClick={() => setFilter('local')}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-100 dark:bg-amber-900/30 flex items-center justify-center">
                <FontAwesomeIcon icon={faHdd} className="text-amber-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.local}</p>
                <p className="text-sm text-slate-500">Local</p>
              </div>
            </div>
          </Card>
          <Card className="cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors" onClick={() => setFilter('active')}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-success-bg dark:bg-success-bg-dark flex items-center justify-center">
                <FontAwesomeIcon icon={faPlay} className="text-success-solid" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.active}</p>
                <p className="text-sm text-slate-500">Active</p>
              </div>
            </div>
          </Card>
          <Card className="cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors" onClick={() => setFilter('paused')}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-warning-bg dark:bg-warning-bg-dark flex items-center justify-center">
                <FontAwesomeIcon icon={faPause} className="text-warning-solid" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.paused}</p>
                <p className="text-sm text-slate-500">Paused</p>
              </div>
            </div>
          </Card>
          <Card className="cursor-pointer hover:border-primary-300 dark:hover:border-primary-700 transition-colors" onClick={() => setFilter('completed')}>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-info-bg dark:bg-info-bg-dark flex items-center justify-center">
                <FontAwesomeIcon icon={faChartLine} className="text-info-solid" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.completed}</p>
                <p className="text-sm text-slate-500">Completed</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Search and Filters */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1">
            <div className="w-80">
              <Input
                icon={faSearch}
                placeholder="Search projects..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              {(['all', 'local', 'active', 'paused', 'completed'] as const).map((f) => (
                <button
                  key={f}
                  onClick={() => setFilter(f)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                    filter === f
                      ? f === 'local' 
                        ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400'
                        : 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {f.charAt(0).toUpperCase() + f.slice(1)}
                </button>
              ))}
            </div>
          </div>
          <Link to="/projects/new">
            <Button icon={faPlus} variant="primary">
              New Project
            </Button>
          </Link>
        </div>

        {/* Projects Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {filteredProjects.map((project) => (
            <Card key={project.id} className="hover:border-primary-300 dark:hover:border-primary-700 transition-all hover:shadow-md">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-start gap-3">
                  <div className={`w-12 h-12 rounded-xl flex items-center justify-center text-white font-bold ${
                    project.isLocal 
                      ? 'bg-gradient-to-br from-amber-400 to-amber-600' 
                      : 'bg-gradient-to-br from-primary-400 to-primary-600'
                  }`}>
                    {project.isLocal ? (
                      <FontAwesomeIcon icon={faHdd} className="text-lg" />
                    ) : (
                      project.name.split(' ').map(w => w[0]).join('').slice(0, 2)
                    )}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-semibold text-slate-900 dark:text-white">{project.name}</h3>
                      {project.isLocal && (
                        <span className="text-xs px-1.5 py-0.5 rounded bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400">
                          Local
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-slate-500">{project.description}</p>
                    {project.isLocal && (
                      <div className="flex items-center gap-1 mt-1 text-xs">
                        {project.hasBenchmark ? (
                          <span className="text-green-600 dark:text-green-400 flex items-center gap-1">
                            <FontAwesomeIcon icon={faCheck} className="text-[10px]" />
                            Benchmark ready
                          </span>
                        ) : (
                          <span className="text-amber-600 dark:text-amber-400 flex items-center gap-1">
                            <FontAwesomeIcon icon={faExclamationTriangle} className="text-[10px]" />
                            No benchmark
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Badge
                    variant={project.isLocal ? 'warning' : project.status === 'active' ? 'success' : project.status === 'paused' ? 'warning' : 'default'}
                    dot
                    pulse={!project.isLocal && project.status === 'active'}
                  >
                    {project.isLocal ? 'ready' : project.status}
                  </Badge>
                  <button className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500">
                    <FontAwesomeIcon icon={faEllipsisV} />
                  </button>
                </div>
              </div>

              {/* Fitness Progress */}
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-slate-500 uppercase tracking-wider">FITNESS SCORE</span>
                  <span className="text-sm font-semibold text-slate-900 dark:text-white">
                    {(project.fitness * 100).toFixed(1)}%
                    {project.targetFitness && (
                      <span className="text-slate-400 font-normal"> / {(project.targetFitness * 100).toFixed(0)}%</span>
                    )}
                  </span>
                </div>
                <ProgressBar
                  value={project.fitness * 100}
                  max={project.targetFitness ? project.targetFitness * 100 : 100}
                  variant={project.fitness > 0.8 ? 'success' : project.fitness > 0.5 ? 'default' : 'warning'}
                />
              </div>

              {/* Stats Row */}
              <div className="grid grid-cols-4 gap-4 py-3 border-t border-slate-100 dark:border-slate-700">
                <div className="text-center">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">{project.generation}</p>
                  <p className="text-xs text-slate-500">Generation</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">
                    {project.activeAgents}/{project.totalAgents}
                  </p>
                  <p className="text-xs text-slate-500">Agents</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">${project.costSpent.toFixed(0)}</p>
                  <p className="text-xs text-slate-500">Cost</p>
                </div>
                <div className="text-center">
                  <p className="text-lg font-semibold text-slate-900 dark:text-white">
                    {Math.floor((Date.now() - new Date(project.updatedAt).getTime()) / 60000)}m
                  </p>
                  <p className="text-xs text-slate-500">Last Update</p>
                </div>
              </div>

              {/* Repository / Local Path */}
              {(project.repository || project.localPath) && (
                <div className="flex items-center gap-2 pt-3 border-t border-slate-100 dark:border-slate-700">
                  <FontAwesomeIcon icon={project.isLocal ? faFolder : faGithubBrand} className="text-slate-400" />
                  <span className="text-sm text-slate-500 truncate">
                    {project.isLocal ? project.localPath : project.repository}
                  </span>
                </div>
              )}

              {/* Actions */}
              <div className="flex items-center gap-2 mt-4 pt-3 border-t border-slate-100 dark:border-slate-700">
                {project.isLocal ? (
                  <>
                    <Link to={`/projects/${project.id}`} className="flex-1">
                      <Button variant="primary" size="sm" className="w-full" icon={faPlay}>
                        Run Optimization
                      </Button>
                    </Link>
                  </>
                ) : (
                  <>
                    <Link to={`/projects/${project.id}`} className="flex-1">
                      <Button variant="secondary" size="sm" className="w-full" icon={faChartLine}>
                        Monitor
                      </Button>
                    </Link>
                    {project.status !== 'completed' && (
                      <Button
                        variant="ghost"
                        size="sm"
                        icon={project.status === 'active' ? faPause : faPlay}
                        onClick={() => handlePauseResume(project.id, project.status)}
                        disabled={actionLoading !== null || pauseLoading || resumeLoading}
                        loading={actionLoading === project.id || ((pauseLoading || resumeLoading) && actionLoading === project.id)}
                      >
                        {project.status === 'active' ? 'Pause' : 'Resume'}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      icon={faTrash}
                      onClick={() => handleDeleteClick(project.id)}
                      className="text-error-solid hover:bg-error-bg dark:hover:bg-error-bg-dark"
                    />
                  </>
                )}
              </div>
            </Card>
          ))}
        </div>

        {/* Loading State */}
        {projectsLoading && (
          <Card className="py-12 text-center">
            <FontAwesomeIcon icon={faSpinner} className="text-4xl text-primary-500 mb-4 animate-spin" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Loading projects...</h3>
          </Card>
        )}

        {/* Error State */}
        {projectsError && !projectsLoading && (
          <Card className="py-12 text-center">
            <h3 className="text-lg font-semibold text-red-500 mb-2">Error loading projects</h3>
            <p className="text-slate-500 mb-4">{projectsError}</p>
            <Button variant="primary" onClick={() => fetchProjects()}>
              Retry
            </Button>
          </Card>
        )}

        {/* Empty State */}
        {!projectsLoading && !projectsError && filteredProjects.length === 0 && (
          <Card className="py-12 text-center">
            <FontAwesomeIcon icon={faFolder} className="text-4xl text-slate-300 dark:text-slate-600 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No projects found</h3>
            <p className="text-slate-500 mb-4">
              {searchQuery ? 'Try adjusting your search or filters' : 'Create your first evolution project to get started'}
            </p>
            <Link to="/projects/new">
              <Button icon={faPlus} variant="primary">
                Create New Project
              </Button>
            </Link>
          </Card>
        )}
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={deleteConfirmOpen}
        onConfirm={handleDeleteConfirm}
        onCancel={() => {
          setDeleteConfirmOpen(false)
          setProjectToDelete(null)
        }}
        title="Delete Project"
        message="Are you sure you want to delete this project? This action cannot be undone."
        confirmLabel="Delete"
        isLoading={deleteProjectLoading}
        variant="danger"
      />
    </div>
  )
}
