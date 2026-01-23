import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import * as d3 from 'd3'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faExpand,
  faSearch,
  faCodeBranch,
  faMemory,
  faGaugeHigh,
  faArrowLeft,
  faPlay,
  faPause,
  faSpinner,
  faChevronRight,
  faStop
} from '@fortawesome/free-solid-svg-icons'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { StatusDot } from '../components/ui/StatusDot'
import { RunConfigModal } from '../components/ui/RunConfigModal'
import { useStore } from '../store'
import { BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip } from 'recharts'
import * as api from '../api'
import type { EvolutionNode } from '../types'

// Helper to convert EvolutionNode from store to TreeNodeData for rendering
function evolutionNodeToTreeNode(node: EvolutionNode): TreeNodeData {
  return {
    id: node.id,
    label: node.generation === 0 ? 'Baseline' : `Gen ${node.generation}`,
    description: node.description,
    status: node.status as TreeNodeData['status'],
    fitness: node.fitness,
    agentName: node.agentName !== 'System' ? node.agentName : undefined,
    children: node.children.map(evolutionNodeToTreeNode),
  }
}

interface TreeNodeData {
  id: string
  label: string
  description: string
  status: 'accepted' | 'rejected' | 'analyzing' | 'processing'
  fitness: number
  agentName?: string
  children: TreeNodeData[]
}

// Default placeholder tree when no data is available
const defaultTreeData: TreeNodeData = {
  id: 'placeholder',
  label: 'Waiting...',
  description: 'Start an optimization to see the evolution tree',
  status: 'processing',
  fitness: 0,
  children: []
}

function EvolutionTree({ data, onNodeClick }: { data: TreeNodeData, onNodeClick: (node: TreeNodeData) => void }) {
  const svgRef = useRef<SVGSVGElement>(null)
  
  useEffect(() => {
    if (!data || !svgRef.current) return

    const width = 1200
    const height = 800
    const nodeWidth = 220
    const nodeHeight = 140
    
    // Clear previous render
    d3.select(svgRef.current).selectAll("*").remove()
    
    const svg = d3.select(svgRef.current)
      .attr("viewBox", [0, 0, width, height])
      .call(d3.zoom<SVGSVGElement, unknown>().on("zoom", (event) => {
        g.attr("transform", event.transform)
      }))
    
    const g = svg.append("g")
      .attr("transform", `translate(${width/2}, 50)`)
    
    const root = d3.hierarchy<TreeNodeData>(data)
    
    const treeLayout = d3.tree<TreeNodeData>()
      .nodeSize([nodeWidth + 40, nodeHeight + 80])
      
    // @ts-ignore
    treeLayout(root)
    
    // Links
    g.selectAll(".link")
      .data(root.links())
      .join("path")
      .attr("className", "link")
      .attr("fill", "none")
      .attr("stroke", "#94a3b8")
      .attr("stroke-width", 2)
      .attr("stroke-opacity", 0.4)
      .attr("d", d3.linkVertical()
        .x((d: any) => d.x!)
        .y((d: any) => d.y!) as any
      )
      
    // Nodes
    const node = g.selectAll(".node")
      .data(root.descendants())
      .join("g")
      .attr("className", "node")
      .attr("transform", (d: any) => `translate(${d.x},${d.y})`)
      // Add click handler for nodes
      .on("click", (_event, d) => {
        if (d.data.status === 'accepted' || d.data.status === 'rejected') {
          onNodeClick(d.data)
        }
      })
      .style("cursor", d => (d.data.status === 'accepted' || d.data.status === 'rejected') ? "pointer" : "default")
      
    // Node Content using foreignObject for HTML styling
    const fo = node.append("foreignObject")
      .attr("width", nodeWidth)
      .attr("height", nodeHeight)
      .attr("x", -nodeWidth / 2)
      .attr("y", -nodeHeight / 2)
      
    fo.append("xhtml:div")
      .style("width", "100%")
      .style("height", "100%")
      .html(d => {
        const statusColors: Record<string, string> = {
          accepted: 'border-green-500 bg-green-50 dark:bg-green-900/20',
          rejected: 'border-red-500 bg-red-50 dark:bg-red-900/20',
          analyzing: 'border-cyan-500 bg-cyan-50 dark:bg-cyan-900/20',
          processing: 'border-yellow-500 bg-yellow-50 dark:bg-yellow-900/20'
        }
        
        const statusBadge: Record<string, string> = {
          accepted: '<span class="px-2 py-0.5 rounded text-xs font-bold bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300">ACCEPTED</span>',
          rejected: '<span class="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300">REJECTED</span>',
          analyzing: '<span class="px-2 py-0.5 rounded text-xs font-bold bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300">ANALYZING</span>',
          processing: '<span class="px-2 py-0.5 rounded text-xs font-bold bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300">PROCESSING</span>'
        }

        const borderColor = statusColors[d.data.status] || 'border-slate-300'
        const badge = statusBadge[d.data.status]
        
        return `
          <div class="h-full w-full p-3 rounded-lg border-2 ${borderColor} bg-white dark:bg-slate-800 shadow-sm flex flex-col justify-between overflow-hidden hover:shadow-md transition-all">
            <div class="flex items-center justify-between mb-1">
              ${badge}
              <span class="text-xs text-slate-400 font-mono">F:${d.data.fitness.toFixed(2)}</span>
            </div>
            <div>
              <h4 class="font-semibold text-sm text-slate-900 dark:text-white mb-1 line-clamp-1" title="${d.data.label}">${d.data.label}</h4>
              <p class="text-xs text-slate-600 dark:text-slate-400 line-clamp-2">${d.data.description || 'No description'}</p>
            </div>
            ${d.data.agentName ? `
              <div class="mt-2 flex items-center gap-1 text-xs text-slate-500">
                <span class="w-2 h-2 rounded-full bg-cyan-500 animate-pulse"></span>
                <span>${d.data.agentName}</span>
              </div>
            ` : ''}
          </div>
        `
      })

  }, [data, onNodeClick])

  return (
    <div className="w-full h-full overflow-hidden bg-slate-50 dark:bg-slate-900/50 rounded-lg">
      <svg ref={svgRef} className="w-full h-full cursor-grab active:cursor-grabbing text-slate-500" />
    </div>
  )
}

export function EvolutionMonitor() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const {
    agents,
    activeAgentCount,
    logs,
    projects,
    isPaused,
    currentWorkflow,
    evolutionTree,
    fetchWorkflow,
    connectWorkflowWs,
    disconnectWorkflowWs,
    clearLogs,
    clearAgents,
    // Workflow control from store
    pauseWorkflow,
    resumeWorkflow,
    stopWorkflow,
    pauseLoading,
    resumeLoading,
    stopLoading,
  } = useStore()

  // Console resize state
  const [consoleHeight, setConsoleHeight] = useState(200)
  const [isDragging, setIsDragging] = useState(false)

  // Run configuration modal state
  const [isRunModalOpen, setIsRunModalOpen] = useState(false)
  const [isRunning, setIsRunning] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [workflowId, setWorkflowId] = useState<string | null>(null)
  
  // Right sidebar state
  const [activeTab, setActiveTab] = useState<'fitness' | 'agents' | null>('fitness')
  const isSidebarOpen = activeTab !== null

  // Check if projectId is a workflow ID (UUID format)
  const isWorkflowId = projectId && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(projectId)

  // Fetch workflow data if we have a workflow ID
  useEffect(() => {
    if (isWorkflowId && projectId) {
      setWorkflowId(projectId)
      fetchWorkflow(projectId)
      connectWorkflowWs(projectId)
      setIsRunning(true)
      
      return () => {
        disconnectWorkflowWs(projectId)
      }
    }
  }, [projectId, isWorkflowId, fetchWorkflow, connectWorkflowWs, disconnectWorkflowWs])

  // Update running state based on workflow status
  useEffect(() => {
    if (currentWorkflow) {
      setIsRunning(['running', 'paused'].includes(currentWorkflow.status))
    }
  }, [currentWorkflow])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsDragging(true)
    document.body.style.cursor = 'row-resize'
  }, [])

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging) return
      const newHeight = window.innerHeight - e.clientY
      if (newHeight > 36 && newHeight < window.innerHeight - 100) {
        setConsoleHeight(newHeight)
      }
    }

    const handleMouseUp = () => {
      setIsDragging(false)
      document.body.style.cursor = 'default'
    }

    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove)
      window.addEventListener('mouseup', handleMouseUp)
    }

    return () => {
      window.removeEventListener('mousemove', handleMouseMove)
      window.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isDragging])

  const project = projects.find(p => p.id === projectId)

  // Convert evolution tree from store to tree node data for rendering
  const treeData = useMemo(() => {
    if (evolutionTree) {
      return evolutionNodeToTreeNode(evolutionTree)
    }
    return defaultTreeData
  }, [evolutionTree])

  const handleNodeClick = (node: TreeNodeData) => {
    // Navigate to code analysis for completed nodes
    navigate(`/projects/${projectId}/analysis/${node.id}`)
  }

  // Handle starting the optimization
  const handleStartOptimization = async (config: { 
    models: Array<{ id: string; provider: string; modelName: string; apiKey: string; instances: number }>; 
    maxCost: number; 
    userPrompt: string 
  }) => {
    setIsStarting(true)
    clearLogs()
    clearAgents()
    
    // Map display model names to actual Anthropic API model names
    const modelNameMapping: Record<string, string> = {
      'claude-opus-4.5': 'claude-opus-4-20250514',
      'claude-sonnet-4.5': 'claude-sonnet-4-5-20250514',
      'claude-haiku-4.5': 'claude-haiku-4-20250514',
    }
    
    try {
      const response = await api.startWorkflow({
        repo_url: project?.repository || '',
        total_cost_limit: config.maxCost,
        user_prompt: config.userPrompt,
        models: config.models.map(m => ({
          provider: m.provider,
          model_name: modelNameMapping[m.modelName] || m.modelName,
          api_key: m.apiKey,
          instances: m.instances,
        })),
      })

      if (response.data?.success) {
        const newWorkflowId = response.data.workflow_id
        setWorkflowId(newWorkflowId)
        setIsRunning(true)
        setIsRunModalOpen(false)
        
        // Connect WebSocket for real-time updates
        connectWorkflowWs(newWorkflowId)
        
        // Navigate to the workflow page
        navigate(`/projects/${newWorkflowId}`)
      } else {
        console.error('Failed to start optimization:', response.error)
        alert(`Failed to start: ${response.error || 'Unknown error'}`)
      }
    } catch (error) {
      console.error('Error starting optimization:', error)
      alert('Failed to connect to the server. Make sure the API is running.')
    } finally {
      setIsStarting(false)
    }
  }

  // Handle pause/resume using store methods
  const handlePauseResume = async () => {
    if (!workflowId) return

    if (isPaused) {
      const success = await resumeWorkflow(workflowId)
      if (!success) {
        console.error('Failed to resume workflow')
      }
    } else {
      const success = await pauseWorkflow(workflowId)
      if (!success) {
        console.error('Failed to pause workflow')
      }
    }
  }

  // Handle stop using store method
  const handleStop = async () => {
    if (!workflowId) return

    const success = await stopWorkflow(workflowId)
    if (success) {
      setIsRunning(false)
      // Refresh workflow data
      fetchWorkflow(workflowId)
    } else {
      console.error('Failed to stop workflow')
    }
  }

  // Build fitness data from workflow steps
  const fitnessData = currentWorkflow?.steps?.map(step => ({
    label: `Gen ${step.generation}`,
    value: step.final_score,
  })) || [
    { label: 'Gen 0', value: currentWorkflow?.baseline_score || 0 },
  ]

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
      {/* Back Button Header - Fixed Height */}
      <div className="flex-none flex items-center gap-4 px-6 py-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 z-10">
        <Button variant="ghost" size="sm" icon={faArrowLeft} onClick={() => navigate('/projects')}>
          Back to Projects
        </Button>
        <div className="flex-1">
          <h1 className="text-lg font-semibold text-slate-900 dark:text-white">
            {project?.name || currentWorkflow?.repo_url?.split('/').pop() || 'Evolution Monitor'}
          </h1>
          <p className="text-sm text-slate-500">
            {isRunning ? (
              <span className="flex items-center gap-2">
                <span className={`w-2 h-2 rounded-full ${isPaused ? 'bg-yellow-500' : 'bg-green-500 animate-pulse'}`} />
                {currentWorkflow?.status || (isPaused ? 'Paused' : 'Running')}
                {workflowId && <span className="text-xs text-slate-400">• {workflowId.slice(0, 8)}</span>}
                {currentWorkflow && (
                  <span className="text-xs text-slate-400">
                    • Gen {currentWorkflow.generation}/{currentWorkflow.max_generations}
                    • Score: {currentWorkflow.current_best_score?.toFixed(2) || 'N/A'}
                  </span>
                )}
              </span>
            ) : currentWorkflow?.status === 'completed' ? (
              <span className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                Completed
                <span className="text-xs text-slate-400">
                  • Final: {currentWorkflow.current_best_score?.toFixed(2)}
                  {currentWorkflow.improvement_percent && ` (+${currentWorkflow.improvement_percent.toFixed(1)}%)`}
                </span>
              </span>
            ) : (
              'Not started'
            )}
          </p>
        </div>

        {/* Run/Pause/Stop Buttons */}
        <div className="flex items-center gap-3">
          {isRunning ? (
            <>
              <Button
                variant={isPaused ? 'primary' : 'secondary'}
                icon={isPaused ? faPlay : faPause}
                onClick={handlePauseResume}
                disabled={pauseLoading || resumeLoading}
                loading={pauseLoading || resumeLoading}
              >
                {isPaused ? 'Resume' : 'Pause'}
              </Button>
              <Button
                variant="ghost"
                icon={faStop}
                onClick={handleStop}
                disabled={stopLoading}
                loading={stopLoading}
                className="text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20"
              >
                Stop
              </Button>
            </>
          ) : currentWorkflow?.status === 'completed' || currentWorkflow?.status === 'stopped' ? (
            <Button 
              variant="primary" 
              icon={faPlay}
              onClick={() => setIsRunModalOpen(true)}
            >
              Run New Optimization
            </Button>
          ) : (
            <Button 
              variant="primary" 
              icon={isStarting ? faSpinner : faPlay}
              onClick={() => setIsRunModalOpen(true)}
              disabled={isStarting}
              className={isStarting ? 'animate-pulse' : ''}
            >
              {isStarting ? 'Starting...' : 'Run Optimization'}
            </Button>
          )}
        </div>
      </div>

      {/* Run Configuration Modal */}
      <RunConfigModal
        isOpen={isRunModalOpen}
        onClose={() => setIsRunModalOpen(false)}
        onStart={handleStartOptimization}
        projectName={project?.name}
      />

      {/* Main Content Area - Flex 1 */}
      <div className="flex-1 min-h-0 relative">
        <div className="absolute inset-0 overflow-hidden flex">
          {/* Main Content - Phylogenetic Tree */}
          <div className="flex-1 h-full flex flex-col min-h-0 min-w-0 p-6">
            <Card padding="none" className="h-full flex flex-col border-slate-200 dark:border-slate-700 shadow-sm relative overflow-hidden">
              <div className="flex-none flex items-center justify-between p-4 border-b border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 z-10">
                <div>
                  <h3 className="text-lg font-semibold text-slate-900 dark:text-white">Phylogenetic Tree</h3>
                  <p className="text-sm text-slate-500">Visualizing code mutations across 42 generations</p>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="ghost" size="sm" icon={faExpand} />
                  <Button variant="ghost" size="sm" icon={faSearch} />
                </div>
              </div>

              {/* Tree Visualization */}
              <div className="flex-1 w-full relative min-h-0 bg-slate-50 dark:bg-slate-900/50">
                <EvolutionTree 
                  data={treeData} 
                  onNodeClick={handleNodeClick}
                />
              </div>

              {/* Legend */}
              <div className="flex-none flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 z-10">
                <div className="flex items-center gap-6 text-xs">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-status-accepted" />
                    <span className="text-slate-600 dark:text-slate-400">Accepted (14)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-status-rejected" />
                    <span className="text-slate-600 dark:text-slate-400">Rejected (28)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-status-processing" />
                    <span className="text-slate-600 dark:text-slate-400">Processing (1)</span>
                  </div>
                </div>
                <Button variant="ghost" size="sm" icon={faSearch}>
                  ZOOM TO ACTIVE
                </Button>
              </div>
            </Card>
          </div>

          {/* Right Sidebar - Activity Bar Style */}
          <div className="flex-none flex h-full border-l border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 transition-all duration-300">
             
             {/* Collapsible Content Panel */}
            <div className={`${isSidebarOpen ? 'w-80 opacity-100' : 'w-0 opacity-0'} overflow-hidden transition-all duration-300 bg-slate-50 dark:bg-slate-900 flex flex-col border-r border-slate-200 dark:border-slate-700`}>
                <div className="p-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-700">
                    <h3 className="font-semibold text-slate-900 dark:text-white">
                      {activeTab === 'fitness' ? 'Fitness Overview' : 'Agent Fleet'}
                    </h3>
                    <Button variant="ghost" size="sm" icon={faChevronRight} onClick={() => setActiveTab(null)} />
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 flex flex-col gap-4 custom-scrollbar">
                  {activeTab === 'fitness' && (
                    <>
                      <Card>
                        <div className="flex items-center gap-2 mb-4">
                          <FontAwesomeIcon icon={faGaugeHigh} className="text-primary-500" />
                          <span className="text-sm font-semibold text-slate-900 dark:text-white">METRICS</span>
                        </div>

                        <div className="space-y-4">
                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-slate-500">Code Complexity</span>
                              <span className="text-xs text-success-solid">+12% vs G1</span>
                            </div>
                            <p className="text-2xl font-bold text-slate-900 dark:text-white">0.42</p>
                          </div>

                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-slate-500">Test Coverage</span>
                              <span className="text-xs text-success-solid">+8.4%</span>
                            </div>
                            <p className="text-2xl font-bold text-slate-900 dark:text-white">98.2%</p>
                          </div>

                          <div>
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-xs text-slate-500">Execution Speed</span>
                              <span className="text-xs text-error-solid">-2ms</span>
                            </div>
                            <p className="text-2xl font-bold text-slate-900 dark:text-white">142ms</p>
                          </div>
                        </div>
                      </Card>

                      <Card>
                        <div className="flex items-center justify-between mb-4">
                          <span className="text-sm font-semibold text-slate-900 dark:text-white">FITNESS TREND</span>
                        </div>
                        <div className="h-32">
                          <ResponsiveContainer width="100%" height="100%">
                            <BarChart data={fitnessData}>
                              <XAxis dataKey="label" tick={{ fontSize: 8 }} />
                              <YAxis tick={{ fontSize: 8 }} domain={[0, 1]} />
                              <Tooltip />
                              <Bar dataKey="value" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                            </BarChart>
                          </ResponsiveContainer>
                        </div>
                      </Card>
                    </>
                  )}

                  {activeTab === 'agents' && (
                    <Card>
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <FontAwesomeIcon icon={faCodeBranch} className="text-primary-500" />
                          <span className="text-sm font-semibold text-slate-900 dark:text-white">ACTIVE AGENTS</span>
                        </div>
                        <Badge variant={activeAgentCount > 0 ? "success" : "default"} size="sm">
                          {activeAgentCount} ACTIVE
                        </Badge>
                      </div>

                      <div className="space-y-3">
                        {agents.length === 0 ? (
                          <div className="text-center py-8 text-slate-400">
                            <p className="text-sm">No agents running</p>
                            <p className="text-xs mt-1">Start an optimization to see agents</p>
                          </div>
                        ) : (
                          agents.map((agent, index) => (
                            <div key={agent.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50">
                              <StatusDot status={agent.status} size="md" />
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="text-sm font-medium text-slate-900 dark:text-white">{agent.name}</span>
                                  <Badge
                                    variant={
                                      agent.status === 'mutating' ? 'mutating' :
                                      agent.status === 'analyzing' ? 'info' :
                                      (agent.status as string) === 'running' ? 'success' :
                                      (agent.status as string) === 'pending' ? 'warning' :
                                      'default'
                                    }
                                    size="sm"
                                  >
                                    {agent.status === 'mutating' ? 'MUTATING' : agent.status.toUpperCase()}
                                  </Badge>
                                </div>
                                <p className="text-xs text-slate-500 truncate">{agent.currentFile || agent.currentTask}</p>
                              </div>
                              <span className="text-xs text-slate-400">#{index + 1}</span>
                            </div>
                          ))
                        )}
                      </div>
                    </Card>
                  )}
                </div>
            </div>

            {/* Icon Strip (Always Visible) */}
            <div className="w-12 bg-slate-50 dark:bg-slate-800 flex flex-col items-center py-4 gap-4 z-10 border-l border-slate-200 dark:border-slate-700">
               <button 
                onClick={() => setActiveTab(activeTab === 'fitness' ? null : 'fitness')} 
                className={`p-2 rounded-lg transition-all ${activeTab === 'fitness' ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'}`}
                title="Fitness Overview"
               >
                 <FontAwesomeIcon icon={faGaugeHigh} className="text-xl" />
               </button>
               <button 
                onClick={() => setActiveTab(activeTab === 'agents' ? null : 'agents')} 
                className={`p-2 rounded-lg transition-all ${activeTab === 'agents' ? 'bg-primary-100 text-primary-600 dark:bg-primary-900/30 dark:text-primary-400' : 'text-slate-400 hover:text-slate-600 dark:hover:text-slate-200'}`}
                title="Agent Fleet"
               >
                 <FontAwesomeIcon icon={faCodeBranch} className="text-xl" />
               </button>
            </div>
          </div>
        </div>
      </div>

      {/* Resize Handle */}
      <div 
        className="h-1 flex-none bg-slate-200 dark:bg-slate-700 hover:bg-primary-500 cursor-row-resize transition-colors z-20"
        onMouseDown={handleMouseDown}
      />

      {/* Console Area - Resizable */}
      <div 
        style={{ height: consoleHeight }} 
        className="flex-none flex flex-col bg-slate-900 border-t border-slate-700 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.1)] overflow-hidden transition-[height] duration-0 ease-linear"
      >
        <div className="flex-none flex items-center justify-between px-4 py-2 bg-slate-900 border-b border-slate-700 select-none">
          <div className="flex items-center gap-4 text-xs font-mono text-slate-400">
            <span className="text-slate-300 font-bold">CONSOLE</span>
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
              Connected to Darwin-Alpha-9
            </span>
          </div>
          <div className="flex items-center gap-4 text-xs font-mono text-slate-500">
            <span className="flex items-center gap-2 hover:text-slate-300 cursor-pointer transition-colors">
              <FontAwesomeIcon icon={faMemory} />
              12.4GB
            </span>
            <span className="hover:text-slate-300 cursor-pointer transition-colors">OPS: 420/s</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 font-mono text-xs space-y-1">
          {logs.map((log) => (
            <div key={log.id} className="flex items-start gap-3 hover:bg-slate-800/50 p-0.5 rounded px-2 transition-colors">
              <span className="text-slate-500 shrink-0 w-20">[{log.timestamp}]</span>
              <span className={`shrink-0 w-32 font-bold ${
                log.level === 'success' ? 'text-green-400' :
                log.level === 'error' ? 'text-red-400' :
                log.level === 'warning' ? 'text-yellow-400' :
                'text-blue-400'
              }`}>
                {log.agentName}
              </span>
              <span className="text-slate-300 flex-1">{log.message}</span>
              {log.level === 'success' && (
                <span className="text-green-500 text-[10px] border border-green-500/30 px-1 rounded bg-green-500/10">SUCCESS</span>
              )}
              {log.details && <span className="text-slate-500">{log.details}</span>}
            </div>
          ))}
          <div className="text-slate-600 italic pl-2 pt-2 animate-pulse">
            Waiting for next evolution cycle...
          </div>
        </div>
      </div>
    </div>
  )
}
