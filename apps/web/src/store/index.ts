import { create } from 'zustand'
import type { Project, Agent, EvolutionNode, LogEntry, Settings, Metric } from '../types'

interface AppState {
  // Theme
  theme: 'light' | 'dark'
  setTheme: (theme: 'light' | 'dark') => void
  toggleTheme: () => void

  // Sidebar
  sidebarCollapsed: boolean
  setSidebarCollapsed: (collapsed: boolean) => void

  // Projects
  projects: Project[]
  currentProject: Project | null
  setCurrentProject: (project: Project | null) => void

  // Agents
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

  // Settings
  settings: Settings
  updateSettings: (settings: Partial<Settings>) => void
}

export const useStore = create<AppState>((set) => ({
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

  // Projects - mock data
  projects: [
    {
      id: '1',
      name: 'Legacy Refactor Agent',
      description: 'Refactoring legacy payment processing module',
      status: 'active',
      generation: 12,
      fitness: 0.892,
      totalAgents: 5,
      activeAgents: 3,
      costSpent: 24.50,
      createdAt: '2024-01-15T10:00:00Z',
      updatedAt: '2024-01-17T14:30:00Z',
      repository: 'github.com/acme/payments',
      targetFitness: 0.95
    },
    {
      id: '2',
      name: 'Sorting Algo Evolution',
      description: 'Optimizing custom sorting algorithms',
      status: 'active',
      generation: 28,
      fitness: 0.998,
      totalAgents: 8,
      activeAgents: 6,
      costSpent: 45.20,
      createdAt: '2024-01-10T08:00:00Z',
      updatedAt: '2024-01-17T14:25:00Z',
      targetFitness: 0.999
    },
    {
      id: '3',
      name: 'React Component Opt',
      description: 'Performance optimization for dashboard components',
      status: 'paused',
      generation: 7,
      fitness: 0.450,
      totalAgents: 4,
      activeAgents: 0,
      costSpent: 12.80,
      createdAt: '2024-01-12T14:00:00Z',
      updatedAt: '2024-01-16T09:15:00Z'
    },
    {
      id: '4',
      name: 'Go Microservice Mesh',
      description: 'Service mesh optimization',
      status: 'active',
      generation: 3,
      fitness: 0.324,
      totalAgents: 6,
      activeAgents: 4,
      costSpent: 8.90,
      createdAt: '2024-01-16T11:00:00Z',
      updatedAt: '2024-01-17T14:20:00Z'
    }
  ],
  currentProject: null,
  setCurrentProject: (project) => set({ currentProject: project }),

  // Agents - mock data
  agents: [
    { id: 'a1', name: 'Agent 01', type: 'refactor', status: 'analyzing', currentTask: 'Refactoring controller.py', currentFile: 'src/controller.py', mutationsProposed: 42, mutationsAccepted: 35, successRate: 0.833 },
    { id: 'a2', name: 'Agent 02', type: 'analyzer', status: 'idle', currentTask: 'Unit testing utilities.ts', currentFile: 'lib/utilities.ts', mutationsProposed: 28, mutationsAccepted: 22, successRate: 0.786 },
    { id: 'a3', name: 'Agent 03', type: 'optimizer', status: 'mutating', currentTask: 'Optimizing mutation_engine.py', currentFile: 'core/mutation_engine.py', mutationsProposed: 56, mutationsAccepted: 48, successRate: 0.857 },
    { id: 'a4', name: 'Agent 04', type: 'feature', status: 'waiting', currentTask: 'Waiting for branch', mutationsProposed: 15, mutationsAccepted: 12, successRate: 0.800 },
    { id: 'a5', name: 'Agent 05', type: 'analyzer', status: 'analyzing', currentTask: 'Analyzing fitness delta', currentFile: 'metrics/fitness.py', mutationsProposed: 33, mutationsAccepted: 29, successRate: 0.879 }
  ],

  // Evolution - mock data
  evolutionTree: null,
  currentGeneration: 42,
  isPaused: false,
  togglePause: () => set((state) => ({ isPaused: !state.isPaused })),

  // Metrics
  metrics: Array.from({ length: 20 }, (_, i) => ({
    timestamp: new Date(Date.now() - (20 - i) * 3600000).toISOString(),
    generation: i + 23,
    fitness: 0.4 + (i * 0.025) + Math.random() * 0.02,
    latency: 200 - i * 5 + Math.random() * 10,
    memory: 128 + Math.random() * 20,
    cost: i * 0.65
  })),
  totalCost: 12.84,
  efficiency: 18.4,

  // Logs - mock data
  logs: [
    { id: '1', timestamp: '14:22:01', level: 'success', agentId: 'a3', agentName: 'Agent 03', message: 'submitted PR for mutation #482', details: 'Fitness score improved to 0.42. Re-distributing tasks...' },
    { id: '2', timestamp: '14:21:45', level: 'info', agentId: 'a1', agentName: 'Agent 01', message: 'analyzing code complexity in module auth', details: undefined },
    { id: '3', timestamp: '14:21:30', level: 'warning', agentId: 'a5', agentName: 'Agent 05', message: 'benchmark timeout exceeded, retrying...', details: undefined },
    { id: '4', timestamp: '14:21:15', level: 'error', agentId: 'a2', agentName: 'Agent 02', message: 'mutation rejected: test failure in utils.test.ts', details: undefined }
  ],
  addLog: (log) => set((state) => ({
    logs: [{ ...log, id: Date.now().toString() }, ...state.logs].slice(0, 100)
  })),

  // Settings
  settings: {
    model: 'claude-sonnet',
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
