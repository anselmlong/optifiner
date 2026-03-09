/**
 * API client for Optifiner backend.
 */

const API_BASE = '/api/v1'

export interface ApiResponse<T> {
  data?: T
  error?: string
}

// =============================================================================
// Health Check API
// =============================================================================

export interface HealthStatus {
  status: string
  version?: string
}

export async function checkHealth(): Promise<ApiResponse<HealthStatus>> {
  try {
    const response = await fetch('/api/v1/health') // Changed from /health
    const text = await response.text()
    
    try {
      const data = JSON.parse(text)
      if (!response.ok) {
        return { error: data.detail || 'Health check failed' }
      }
      return { data }
    } catch (e) {
      return { error: `Invalid JSON response: ${text.slice(0, 50)}...` }
    }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'API not reachable' }
  }
}

export async function getApiInfo(): Promise<ApiResponse<{ name: string; version: string }>> {
  try {
    const response = await fetch('/api/v1/') // Changed from /
    const text = await response.text()
    
    try {
      const data = JSON.parse(text)
      if (!response.ok) {
        return { error: data.detail || 'Failed to get API info' }
      }
      return { data }
    } catch (e) {
      return { error: `Invalid JSON response: ${text.slice(0, 50)}...` }
    }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'API not reachable' }
  }
}

async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<ApiResponse<T>> {
  try {
    const response = await fetch(`${API_BASE}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    })

    const text = await response.text()
    let data;
    try {
      data = JSON.parse(text)
    } catch (e) {
      return { error: `Invalid JSON response from ${endpoint}: ${text.slice(0, 50)}...` }
    }

    if (!response.ok) {
      // Handle FastAPI/Pydantic validation errors (array of error objects)
      if (Array.isArray(data.detail)) {
        const errors = data.detail.map((err: { loc?: string[]; msg?: string }) => {
          const field = err.loc?.slice(1).join('.') || 'unknown'
          return `${field}: ${err.msg}`
        }).join('; ')
        return { error: errors || 'Validation failed' }
      }
      // Handle string error messages
      return { error: data.detail || data.error || data.message || 'Request failed' }
    }

    return { data }
  } catch (error) {
    return { error: error instanceof Error ? error.message : 'Network error' }
  }
}

// =============================================================================
// Project API
// =============================================================================

export interface Project {
  id: string
  name: string
  description: string | null
  repository_url: string | null
  repository_branch: string | null
  target_fitness: number
  cost_limit: number
  status: string
  current_fitness: number
  total_cost_spent: number
  current_generation: number
  created_at: string | null
  updated_at: string | null
}

export interface ProjectsResponse {
  projects: Project[]
  total: number
}

export async function getProjects(params?: {
  status?: string
  skip?: number
  limit?: number
}): Promise<ApiResponse<ProjectsResponse>> {
  const query = new URLSearchParams()
  if (params?.status) query.append('status', params.status)
  if (params?.skip) query.append('skip', params.skip.toString())
  if (params?.limit) query.append('limit', params.limit.toString())
  
  const queryString = query.toString()
  return fetchApi<ProjectsResponse>(`/projects${queryString ? `?${queryString}` : ''}`)
}

export interface LocalProject {
  id: string
  name: string
  description: string
  directory: string
  path: string
  has_benchmark: boolean
  status: 'local'
  repository_url: string | null
  repository_branch: string | null
  target_fitness: number
  cost_limit: number
  current_fitness: number
  total_cost_spent: number
  current_generation: number
  created_at: string | null
  updated_at: string | null
}

export interface LocalProjectsResponse {
  projects: LocalProject[]
  total: number
}

export async function getLocalProjects(): Promise<ApiResponse<LocalProjectsResponse>> {
  return fetchApi<LocalProjectsResponse>('/projects/local')
}

export async function getProject(projectId: string): Promise<ApiResponse<Project>> {
  return fetchApi<Project>(`/projects/${projectId}`)
}

export async function createProject(data: {
  name: string
  description?: string
  repository_url?: string
  repository_branch?: string
  target_fitness?: number
  cost_limit?: number
}): Promise<ApiResponse<Project>> {
  const query = new URLSearchParams()
  query.append('name', data.name)
  if (data.description) query.append('description', data.description)
  if (data.repository_url) query.append('repository_url', data.repository_url)
  if (data.repository_branch) query.append('repository_branch', data.repository_branch)
  if (data.target_fitness) query.append('target_fitness', data.target_fitness.toString())
  if (data.cost_limit) query.append('cost_limit', data.cost_limit.toString())
  
  return fetchApi<Project>(`/projects?${query.toString()}`, { method: 'POST' })
}

export async function updateProject(
  projectId: string,
  data: Partial<Project>
): Promise<ApiResponse<Project>> {
  const query = new URLSearchParams()
  if (data.name) query.append('name', data.name)
  if (data.description) query.append('description', data.description)
  if (data.status) query.append('status', data.status)
  if (data.target_fitness) query.append('target_fitness', data.target_fitness.toString())
  if (data.cost_limit) query.append('cost_limit', data.cost_limit.toString())
  
  return fetchApi<Project>(`/projects/${projectId}?${query.toString()}`, { method: 'PUT' })
}

export async function deleteProject(projectId: string): Promise<ApiResponse<{ success: boolean }>> {
  return fetchApi<{ success: boolean }>(`/projects/${projectId}`, { method: 'DELETE' })
}

export async function getProjectWorkflows(
  projectId: string,
  params?: { skip?: number; limit?: number }
): Promise<ApiResponse<WorkflowsResponse>> {
  const query = new URLSearchParams()
  if (params?.skip) query.append('skip', params.skip.toString())
  if (params?.limit) query.append('limit', params.limit.toString())

  const queryString = query.toString()
  return fetchApi<WorkflowsResponse>(`/projects/${projectId}/workflows${queryString ? `?${queryString}` : ''}`)
}

// =============================================================================
// Workflow API
// =============================================================================

export interface WorkflowStep {
  id: string
  step: number
  generation: number
  agent_id: string | null
  baseline_score: number
  final_score: number
  improvement: number
  improvement_percent: number
  is_initial: boolean
  commit_hash: string | null
  timestamp: string | null
}

export interface Workflow {
  workflow_id: string
  project_id: string | null
  status: string
  repo_url: string
  repo_dir: string | null
  branch: string | null
  original_branch: string | null
  baseline_score: number | null
  current_best_score: number | null
  baseline_data: Record<string, unknown> | null
  user_prompt: string | null
  models: Array<{
    provider: string
    model_name: string
    instances: number
  }> | null
  agents_per_generation: number
  parallel: number
  max_generations: number
  max_iterations_per_agent: number
  agent_types: string[] | null
  min_improvement_pct: number
  early_stop: boolean
  evaluator_path: string | null
  verbosity: number
  log_dir: string | null
  total_cost_limit: number
  time_limit_seconds: number
  generation: number
  total_improvements: number
  total_attempts: number
  step_count: number
  total_cost: number
  improvement: number | null
  improvement_percent: number | null
  error: string | null
  graph_data: {
    nodes: Array<{
      id: string
      type: string
      generation: number
      score: number
    }>
    edges: Array<{
      source: string
      target: string
    }>
  } | null
  started_at: string | null
  completed_at: string | null
  paused_at: string | null
  created_at: string | null
  steps: WorkflowStep[]
}

export interface WorkflowsResponse {
  workflows: Workflow[]
  total: number
}

export interface StartWorkflowRequest {
  repo_url: string
  branch?: string
  total_cost_limit: number
  models: Array<{
    provider: string
    model_name: string
    api_key: string
    instances?: number
  }>
  user_prompt?: string
  agents_per_generation?: number
  parallel?: number
  generations?: number
  max_iterations_per_agent?: number
  agent_types?: string[]
  min_improvement_pct?: number
  early_stop?: boolean
  evaluator_path?: string
  build_benchmark?: boolean
  verbosity?: number
  log_dir?: string
  time_limit_seconds?: number
}

export interface StartWorkflowResponse {
  success: boolean
  workflow_id: string
  baseline_score: number
  repo_dir: string
  branch: string
  status: string
  error?: string
}

export async function startWorkflow(
  data: StartWorkflowRequest
): Promise<ApiResponse<StartWorkflowResponse>> {
  return fetchApi<StartWorkflowResponse>('/optimization/start', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function getWorkflows(params?: {
  project_id?: string
  status?: string
  skip?: number
  limit?: number
}): Promise<ApiResponse<WorkflowsResponse>> {
  const query = new URLSearchParams()
  if (params?.project_id) query.append('project_id', params.project_id)
  if (params?.status) query.append('status', params.status)
  if (params?.skip) query.append('skip', params.skip.toString())
  if (params?.limit) query.append('limit', params.limit.toString())
  
  const queryString = query.toString()
  return fetchApi<WorkflowsResponse>(`/optimization/workflows${queryString ? `?${queryString}` : ''}`)
}

export async function getWorkflowStatus(workflowId: string): Promise<ApiResponse<Workflow>> {
  return fetchApi<Workflow>(`/optimization/${workflowId}/status`)
}

export interface LogEntry {
  id: string
  workflow_id: string
  level: string
  message: string
  details: string | null
  agent_name: string | null
  timestamp: string
}

export async function getWorkflowLogs(
  workflowId: string,
  limit = 100
): Promise<ApiResponse<{ logs: LogEntry[] }>> {
  return fetchApi<{ logs: LogEntry[] }>(`/optimization/${workflowId}/logs?limit=${limit}`)
}

export async function pauseWorkflow(
  workflowId: string
): Promise<ApiResponse<{ success: boolean; status: string }>> {
  return fetchApi<{ success: boolean; status: string }>(`/optimization/${workflowId}/pause`, {
    method: 'POST',
  })
}

export async function resumeWorkflow(
  workflowId: string
): Promise<ApiResponse<{ success: boolean; status: string }>> {
  return fetchApi<{ success: boolean; status: string }>(`/optimization/${workflowId}/resume`, {
    method: 'POST',
  })
}

export async function stopWorkflow(
  workflowId: string
): Promise<ApiResponse<{ success: boolean; status: string; final_score: number | null }>> {
  return fetchApi<{ success: boolean; status: string; final_score: number | null }>(
    `/optimization/${workflowId}/stop`,
    { method: 'POST' }
  )
}

// =============================================================================
// Dashboard API
// =============================================================================

export interface DashboardStats {
  projects: {
    total: number
    active: number
    paused: number
    completed: number
  }
  workflows: {
    running: number
  }
  cost: {
    total_spent: number
  }
}

export async function getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
  return fetchApi<DashboardStats>('/stats/dashboard')
}

// =============================================================================
// WebSocket Message Types (used by websocket.ts and store)
// =============================================================================

export interface StatusUpdate {
  status: string
  baseline_score?: number
  final_score?: number
  improvement?: number
  improvement_percent?: number
  error?: string
}

export interface AgentUpdate {
  instance_id: string
  status: string
  agent_type?: string
  score?: number
  success?: boolean
  error?: string
}

export interface StepUpdate {
  step: number
  generation: number
  agent_id: string
  baseline_score: number
  final_score: number
  improvement_percent: number
}

export interface LogUpdate {
  level: string
  message: string
  agent_name?: string
  details?: string
  timestamp: string
}
