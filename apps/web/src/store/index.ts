import { create } from 'zustand'
import type { Project, Agent, EvolutionNode, LogEntry, Settings, Metric } from '../types'
import * as api from '../api'
import { getWorkflowSocket, getGlobalSocket, disconnectWorkflowSocket, type WebSocketMessage, type GraphUpdate } from '../api/websocket'

// Helper function to convert flat graph data to nested tree structure
function graphToTree(graphData: GraphUpdate): EvolutionNode | null {
  if (!graphData.nodes || graphData.nodes.length === 0) return null
  
  // Build a map of nodes by id
  const nodeMap = new Map<string, EvolutionNode>()
  
  for (const node of graphData.nodes) {
    nodeMap.set(node.id, {
      id: node.id,
      generation: node.generation,
      agentId: node.agent_id || 'system',
      agentName: node.agent_id || 'System',
      status: node.status,
      fitness: node.score,
      fitnessChange: 0,
      description: node.description,
      commitHash: node.commit_hash,
      children: [],
      timestamp: new Date().toISOString(),
    })
  }
  
  // Build tree by connecting edges
  let rootNode: EvolutionNode | null = null
  
  for (const edge of graphData.edges) {
    const parent = nodeMap.get(edge.source)
    const child = nodeMap.get(edge.target)
    if (parent && child) {
      parent.children.push(child)
    }
  }
  
  // Find root node (node with no incoming edges)
  const childIds = new Set(graphData.edges.map(e => e.target))
  for (const node of graphData.nodes) {
    if (!childIds.has(node.id)) {
      rootNode = nodeMap.get(node.id) || null
      break
    }
  }
  
  return rootNode
}

interface AppState {
  // API Status
  apiHealthy: boolean
  apiError: string | null
  checkApiHealth: () => Promise<boolean>
  // Theme
  theme: 'light' | 'dark'
  setTheme: (theme: 'light' | 'dark') => void
  toggleTheme: () => void

  // Sidebar
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void

  // Projects (from API)
  projects: Project[]
  currentProject: Project | null
  projectsLoading: boolean
  projectsError: string | null
  deleteProjectLoading: boolean
  fetchProjects: () => Promise<void>
  setCurrentProject: (project: Project | null) => void
  createProject: (data: { name: string; description?: string; repository_url?: string }) => Promise<Project | null>
  updateProject: (id: string, data: Partial<api.Project>) => Promise<boolean>
  deleteProject: (id: string) => Promise<boolean>

  // Workflows
  currentWorkflow: api.Workflow | null
  workflowLoading: boolean
  workflowError: string | null
  fetchWorkflow: (workflowId: string) => Promise<void>
  connectWorkflowWs: (workflowId: string) => void
  disconnectWorkflowWs: (workflowId: string) => void

  // Workflows list (for History page)
  workflows: api.Workflow[]
  workflowsLoading: boolean
  workflowsError: string | null
  fetchWorkflows: (params?: { project_id?: string; status?: string; skip?: number; limit?: number }) => Promise<void>

  // Project workflows (workflows for a specific project)
  projectWorkflows: Map<string, api.Workflow[]>
  projectWorkflowsLoading: boolean
  fetchProjectWorkflows: (projectId: string) => Promise<api.Workflow[]>

  // Workflow control
  pauseLoading: boolean
  resumeLoading: boolean
  stopLoading: boolean
  startWorkflow: (data: api.StartWorkflowRequest) => Promise<api.StartWorkflowResponse | null>
  pauseWorkflow: (workflowId: string) => Promise<boolean>
  resumeWorkflow: (workflowId: string) => Promise<boolean>
  stopWorkflow: (workflowId: string) => Promise<boolean>

  // Workflow logs
  workflowLogs: api.LogEntry[]
  workflowLogsLoading: boolean
  fetchWorkflowLogs: (workflowId: string, limit?: number) => Promise<void>

  // Agents (from workflow)
  agents: Agent[]
  activeAgentCount: number
  clearAgents: () => void

  // Evolution
  evolutionTree: EvolutionNode | null
  graphData: GraphUpdate | null
  currentGeneration: number
  isPaused: boolean
  togglePause: () => void

  // Metrics
  metrics: Metric[]
  totalCost: number
  efficiency: number

  // Logs
  logs: LogEntry[]
  addLog: (log: Omit<LogEntry, 'id'>) => void
  clearLogs: () => void

  // Dashboard stats
  dashboardStats: api.DashboardStats | null
  fetchDashboardStats: () => Promise<void>

  // Settings
  settings: Settings
  updateSettings: (settings: Partial<Settings>) => void

  // Global WebSocket
  connectGlobalWs: () => void
  disconnectGlobalWs: () => void
}

export const useStore = create<AppState>((set, get) => ({
  // API Status
  apiHealthy: false,
  apiError: null,
  checkApiHealth: async () => {
    const response = await api.checkHealth()
    if (response.error) {
      set({ apiHealthy: false, apiError: response.error })
      return false
    }
    set({ apiHealthy: true, apiError: null })
    return true
  },

  // Theme
  theme: 'light',
  setTheme: (theme) => {
    set({ theme })
    if (theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  },
  toggleTheme: () => set((state) => {
    const newTheme = state.theme === 'light' ? 'dark' : 'light'
    if (newTheme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    return { theme: newTheme }
  }),

  // Sidebar
  sidebarCollapsed: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  // Projects - fetched from API
  projects: [],
  currentProject: null,
  projectsLoading: false,
  projectsError: null,
  deleteProjectLoading: false,

  fetchProjects: async () => {
    set({ projectsLoading: true, projectsError: null })
    
    // Fetch both database projects and local workspace projects in parallel
    const [dbResponse, localResponse] = await Promise.all([
      api.getProjects(),
      api.getLocalProjects(),
    ])
    
    if (dbResponse.error && localResponse.error) {
      set({ projectsError: dbResponse.error, projectsLoading: false })
      return
    }
    
    // Transform API projects to store format
    const dbProjects: Project[] = (dbResponse.data?.projects || []).map(p => ({
      id: p.id,
      name: p.name,
      description: p.description || '',
      status: p.status as 'active' | 'paused' | 'completed',
      generation: p.current_generation,
      fitness: p.current_fitness,
      totalAgents: 0, // Will be updated from workflows
      activeAgents: 0,
      costSpent: p.total_cost_spent,
      createdAt: p.created_at || new Date().toISOString(),
      updatedAt: p.updated_at || new Date().toISOString(),
      repository: p.repository_url || undefined,
      targetFitness: p.target_fitness,
    }))
    
    // Transform local projects to store format
    const localProjects: Project[] = (localResponse.data?.projects || []).map(p => ({
      id: p.id,
      name: p.name,
      description: p.description || '',
      status: 'active' as const, // Local projects are always ready to run
      generation: 0,
      fitness: 0,
      totalAgents: 0,
      activeAgents: 0,
      costSpent: 0,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      repository: p.path, // Use local path as repository
      targetFitness: p.target_fitness,
      isLocal: true, // Mark as local project
      localPath: p.path,
      hasBenchmark: p.has_benchmark,
    }))
    
    // Merge both lists (database projects first, then local)
    const allProjects = [...dbProjects, ...localProjects]
    
    set({ projects: allProjects, projectsLoading: false })
  },
  
  setCurrentProject: (project) => set({ currentProject: project }),
  
  createProject: async (data) => {
    const response = await api.createProject({
      name: data.name,
      description: data.description,
      repository_url: data.repository_url,
    })
    
    if (response.error || !response.data) {
      return null
    }
    
    // Refresh projects list
    get().fetchProjects()
    
    return {
      id: response.data.id,
      name: response.data.name,
      description: response.data.description || '',
      status: response.data.status as 'active' | 'paused' | 'completed',
      generation: response.data.current_generation,
      fitness: response.data.current_fitness,
      totalAgents: 0,
      activeAgents: 0,
      costSpent: response.data.total_cost_spent,
      createdAt: response.data.created_at || new Date().toISOString(),
      updatedAt: response.data.updated_at || new Date().toISOString(),
      repository: response.data.repository_url || undefined,
      targetFitness: response.data.target_fitness,
    }
  },

  updateProject: async (id: string, data: Partial<api.Project>) => {
    const response = await api.updateProject(id, data)

    if (response.error || !response.data) {
      return false
    }

    // Refresh projects list
    get().fetchProjects()
    return true
  },

  deleteProject: async (id: string) => {
    set({ deleteProjectLoading: true })
    const response = await api.deleteProject(id)
    set({ deleteProjectLoading: false })

    if (response.error || !response.data?.success) {
      return false
    }

    // Refresh projects list
    get().fetchProjects()
    return true
  },

  // Workflows
  currentWorkflow: null,
  workflowLoading: false,
  workflowError: null,
  
  fetchWorkflow: async (workflowId: string) => {
    set({ workflowLoading: true, workflowError: null })
    const response = await api.getWorkflowStatus(workflowId)
    
    if (response.error) {
      set({ workflowError: response.error, workflowLoading: false })
      return
    }
    
    set({ 
      currentWorkflow: response.data || null, 
      workflowLoading: false,
      currentGeneration: response.data?.generation || 0,
      isPaused: response.data?.status === 'paused',
    })
    
    // Update agents from workflow
    // Note: agents would come from agent instances in the workflow
  },
  
  connectWorkflowWs: (workflowId: string) => {
    const socket = getWorkflowSocket(workflowId)
    socket.connect()
    
    socket.subscribe((message: WebSocketMessage) => {
      const state = get()
      
      switch (message.type) {
        case 'status':
          const statusData = message.data as unknown as api.StatusUpdate
          // Clear agents when workflow completes or stops
          const shouldClearAgents = ['completed', 'stopped', 'failed'].includes(statusData.status)
          set({
            isPaused: statusData.status === 'paused',
            currentWorkflow: state.currentWorkflow ? {
              ...state.currentWorkflow,
              status: statusData.status,
              current_best_score: statusData.final_score ?? state.currentWorkflow.current_best_score,
              improvement: statusData.improvement ?? state.currentWorkflow.improvement,
              improvement_percent: statusData.improvement_percent ?? state.currentWorkflow.improvement_percent,
            } : null,
            ...(shouldClearAgents ? { agents: [], activeAgentCount: 0 } : {}),
          })
          break
          
        case 'agent_update':
          const agentData = message.data as unknown as api.AgentUpdate
          // Check if agent exists in list
          const existingAgent = state.agents.find(a => a.id === agentData.instance_id)
          
          let newAgentsList: Agent[]
          if (existingAgent) {
            // Update existing agent
            newAgentsList = state.agents.map(agent => 
              agent.id === agentData.instance_id 
                ? { ...agent, status: agentData.status as Agent['status'] }
                : agent
            )
          } else {
            // Add new agent
            const newAgent: Agent = {
              id: agentData.instance_id,
              name: agentData.instance_id,
              type: (agentData.agent_type as Agent['type']) || 'optimizer',
              status: agentData.status as Agent['status'],
              currentTask: agentData.status === 'running' ? 'Optimizing...' : undefined,
              mutationsProposed: 0,
              mutationsAccepted: 0,
              successRate: 0,
            }
            newAgentsList = [...state.agents, newAgent]
          }
          
          // Calculate active count (pending or running agents)
          const activeCount = newAgentsList.filter(
            a => a.status === 'analyzing' || a.status === 'mutating' || 
                 (a.status as string) === 'pending' || (a.status as string) === 'running'
          ).length
          
          set({ agents: newAgentsList, activeAgentCount: activeCount })
          break
          
        case 'step':
          const stepData = message.data as unknown as api.StepUpdate
          // Add to logs
          state.addLog({
            timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
            level: 'success',
            agentId: stepData.agent_id,
            agentName: stepData.agent_id,
            message: `Improved: ${stepData.baseline_score.toFixed(2)} → ${stepData.final_score.toFixed(2)} (+${stepData.improvement_percent.toFixed(1)}%)`,
          })
          
          // Update workflow state
          if (state.currentWorkflow) {
            set({
              currentWorkflow: {
                ...state.currentWorkflow,
                current_best_score: stepData.final_score,
                step_count: stepData.step,
                generation: stepData.generation,
              },
              currentGeneration: stepData.generation,
            })
          }
          break
          
        case 'log':
          const logData = message.data as unknown as api.LogUpdate
          state.addLog({
            timestamp: logData.timestamp,
            level: logData.level as LogEntry['level'],
            agentId: logData.agent_name || 'system',
            agentName: logData.agent_name || 'System',
            message: logData.message,
            details: logData.details || undefined,
          })
          break
          
        case 'generation_start':
          const genData = message.data as { generation: number; best_score: number }
          set({ currentGeneration: genData.generation })
          state.addLog({
            timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
            level: 'info',
            agentId: 'system',
            agentName: 'System',
            message: `Starting generation ${genData.generation}`,
          })
          break
          
        case 'graph_update':
          const graphUpdateData = message.data as unknown as GraphUpdate
          const tree = graphToTree(graphUpdateData)
          set({ 
            graphData: graphUpdateData,
            evolutionTree: tree,
          })
          break
      }
    })
  },
  
  disconnectWorkflowWs: (workflowId: string) => {
    disconnectWorkflowSocket(workflowId)
  },

  // Workflows list (for History page)
  workflows: [],
  workflowsLoading: false,
  workflowsError: null,

  fetchWorkflows: async (params) => {
    set({ workflowsLoading: true, workflowsError: null })
    const response = await api.getWorkflows(params)

    if (response.error) {
      set({ workflowsError: response.error, workflowsLoading: false })
      return
    }

    set({
      workflows: response.data?.workflows || [],
      workflowsLoading: false,
    })
  },

  // Project workflows
  projectWorkflows: new Map(),
  projectWorkflowsLoading: false,

  fetchProjectWorkflows: async (projectId: string) => {
    set({ projectWorkflowsLoading: true })
    const response = await api.getProjectWorkflows(projectId)
    set({ projectWorkflowsLoading: false })

    if (response.error || !response.data) {
      return []
    }

    const workflows = response.data.workflows || []
    set(state => {
      const newMap = new Map(state.projectWorkflows)
      newMap.set(projectId, workflows)
      return { projectWorkflows: newMap }
    })
    return workflows
  },

  // Workflow control
  pauseLoading: false,
  resumeLoading: false,
  stopLoading: false,

  startWorkflow: async (data: api.StartWorkflowRequest) => {
    const response = await api.startWorkflow(data)

    if (response.error || !response.data) {
      return null
    }

    return response.data
  },

  pauseWorkflow: async (workflowId: string) => {
    set({ pauseLoading: true })
    const response = await api.pauseWorkflow(workflowId)
    set({ pauseLoading: false })

    if (response.error || !response.data?.success) {
      return false
    }

    // Update local state
    set({ isPaused: true })

    // Update currentWorkflow if it matches
    const state = get()
    if (state.currentWorkflow?.workflow_id === workflowId) {
      set({
        currentWorkflow: {
          ...state.currentWorkflow,
          status: 'paused',
        },
      })
    }

    return true
  },

  resumeWorkflow: async (workflowId: string) => {
    set({ resumeLoading: true })
    const response = await api.resumeWorkflow(workflowId)
    set({ resumeLoading: false })

    if (response.error || !response.data?.success) {
      return false
    }

    // Update local state
    set({ isPaused: false })

    // Update currentWorkflow if it matches
    const state = get()
    if (state.currentWorkflow?.workflow_id === workflowId) {
      set({
        currentWorkflow: {
          ...state.currentWorkflow,
          status: 'running',
        },
      })
    }

    return true
  },

  stopWorkflow: async (workflowId: string) => {
    set({ stopLoading: true })
    const response = await api.stopWorkflow(workflowId)
    set({ stopLoading: false })

    if (response.error || !response.data?.success) {
      return false
    }

    // Update currentWorkflow if it matches
    const state = get()
    if (state.currentWorkflow?.workflow_id === workflowId) {
      set({
        currentWorkflow: {
          ...state.currentWorkflow,
          status: 'stopped',
        },
      })
    }

    return true
  },

  // Workflow logs
  workflowLogs: [],
  workflowLogsLoading: false,

  fetchWorkflowLogs: async (workflowId: string, limit = 100) => {
    set({ workflowLogsLoading: true })
    const response = await api.getWorkflowLogs(workflowId, limit)
    set({ workflowLogsLoading: false })

    if (response.data) {
      set({ workflowLogs: response.data.logs })
    }
  },

  // Agents - populated from workflow data
  agents: [],
  activeAgentCount: 0,
  clearAgents: () => set({ agents: [], activeAgentCount: 0 }),

  // Evolution
  evolutionTree: null,
  graphData: null,
  currentGeneration: 0,
  isPaused: false,
  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),

  // Metrics
  metrics: [],
  totalCost: 0,
  efficiency: 0,

  // Logs
  logs: [],
  addLog: (log) => set((state) => ({
    logs: [{ ...log, id: Date.now().toString() }, ...state.logs].slice(0, 100)
  })),
  clearLogs: () => set({ logs: [] }),

  // Dashboard stats
  dashboardStats: null,
  fetchDashboardStats: async () => {
    const response = await api.getDashboardStats()
    if (response.data) {
      set({ 
        dashboardStats: response.data,
        totalCost: response.data.cost.total_spent,
      })
    }
  },

  // Global WebSocket
  connectGlobalWs: () => {
    const socket = getGlobalSocket()
    socket.connect()
    
    socket.subscribe((message: WebSocketMessage) => {
      // Handle global updates (for dashboard)
      if (message.type === 'status' || message.type === 'step') {
        // Refresh dashboard stats when workflows change
        get().fetchDashboardStats()
        get().fetchProjects()
      }
    })
  },
  
  disconnectGlobalWs: () => {
    // The global socket is managed by the websocket module
  },

  // Settings
  settings: {
    model: 'claude-sonnet-4.5',
    agentCount: 10,
    mutationRate: 'balanced',
    benchmarkTimeout: 30,
    targetFitness: 0.95,
    autoStop: true,
    parallelExecution: true,
    costLimit: 50
  },
  updateSettings: (newSettings) => set((state) => ({
    settings: { ...state.settings, ...newSettings }
  }))
}))
