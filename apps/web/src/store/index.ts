import { create } from 'zustand'
import type { Project, Agent, EvolutionNode, LogEntry, Settings, Metric } from '../types'
import * as api from '../api'
import { getWorkflowSocket, getGlobalSocket, disconnectWorkflowSocket, type WebSocketMessage } from '../api/websocket'

interface AppState {
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
  fetchProjects: () => Promise<void>
  setCurrentProject: (project: Project | null) => void
  createProject: (data: { name: string; description?: string; repository_url?: string }) => Promise<Project | null>

  // Workflows
  currentWorkflow: api.Workflow | null
  workflowLoading: boolean
  workflowError: string | null
  fetchWorkflow: (workflowId: string) => Promise<void>
  connectWorkflowWs: (workflowId: string) => void
  disconnectWorkflowWs: (workflowId: string) => void

  // Agents (from workflow)
  agents: Agent[]

  // Evolution
  evolutionTree: EvolutionNode | null
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
  
  fetchProjects: async () => {
    set({ projectsLoading: true, projectsError: null })
    const response = await api.getProjects()
    
    if (response.error) {
      set({ projectsError: response.error, projectsLoading: false })
      return
    }
    
    // Transform API projects to store format
    const projects: Project[] = (response.data?.projects || []).map(p => ({
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
    
    set({ projects, projectsLoading: false })
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
          set({
            isPaused: statusData.status === 'paused',
            currentWorkflow: state.currentWorkflow ? {
              ...state.currentWorkflow,
              status: statusData.status,
              current_best_score: statusData.final_score ?? state.currentWorkflow.current_best_score,
              improvement: statusData.improvement ?? state.currentWorkflow.improvement,
              improvement_percent: statusData.improvement_percent ?? state.currentWorkflow.improvement_percent,
            } : null,
          })
          break
          
        case 'agent_update':
          const agentData = message.data as unknown as api.AgentUpdate
          // Update agents list
          const updatedAgents = state.agents.map(agent => 
            agent.id === agentData.instance_id 
              ? { ...agent, status: agentData.status as Agent['status'] }
              : agent
          )
          set({ agents: updatedAgents })
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
      }
    })
  },
  
  disconnectWorkflowWs: (workflowId: string) => {
    disconnectWorkflowSocket(workflowId)
  },

  // Agents - populated from workflow data
  agents: [],

  // Evolution
  evolutionTree: null,
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
