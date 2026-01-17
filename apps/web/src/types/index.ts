export interface Project {
  id: string;
  name: string;
  description?: string;
  status: 'active' | 'paused' | 'completed' | 'error';
  generation: number;
  fitness: number;
  totalAgents: number;
  activeAgents: number;
  costSpent: number;
  createdAt: string;
  updatedAt: string;
  repository?: string;
  targetFitness?: number;
}

export interface Agent {
  id: string;
  name: string;
  type: 'analyzer' | 'refactor' | 'feature' | 'optimizer';
  status: 'idle' | 'analyzing' | 'mutating' | 'testing' | 'waiting';
  currentTask?: string;
  currentFile?: string;
  mutationsProposed: number;
  mutationsAccepted: number;
  successRate: number;
}

export interface EvolutionNode {
  id: string;
  generation: number;
  agentId: string;
  agentName: string;
  status: 'accepted' | 'rejected' | 'processing' | 'analyzing' | 'testing';
  fitness: number;
  fitnessChange?: number;
  description: string;
  commitHash?: string;
  parentId?: string;
  children: EvolutionNode[];
  timestamp: string;
  metrics?: {
    latency?: number;
    latencyChange?: number;
    memory?: number;
    memoryChange?: number;
    complexity?: number;
    complexityChange?: number;
  };
}

export interface Metric {
  timestamp: string;
  generation: number;
  fitness: number;
  latency: number;
  memory: number;
  cost: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: 'info' | 'success' | 'warning' | 'error';
  agentId?: string;
  agentName?: string;
  message: string;
  details?: string;
}

export interface Settings {
  model: 'claude-opus-4.5' | 'claude-sonnet-4.5' | 'claude-haiku-4.5' | 'gpt-5.2-codex' | 'gpt-5.2' | 'gemini-3-flash-preview' | 'gemini-3-pro-preview';
  agentCount: number;
  mutationRate: 'conservative' | 'balanced' | 'aggressive';
  benchmarkTimeout: number;
  targetFitness: number;
  autoStop: boolean;
  parallelExecution: boolean;
  costLimit: number;
}

export interface MutationAnalysis {
  id: string;
  fileName: string;
  candidate: string;
  agentId: string;
  agentName: string;
  agentVersion: string;
  status: 'pending' | 'approved' | 'rejected';
  metrics: {
    executionLatency: { value: number; change: number; unit: string };
    memoryUsage: { value: number; change: number; unit: string };
    complexity: { value: number; change: number; unit: string };
  };
  reasoning: string;
  safetyCheck: {
    unitTestsPassed: number;
    unitTestsTotal: number;
    regressionRisk: 'Low' | 'Medium' | 'High';
  };
  related: Array<{ id: string; title: string }>;
  baseCode: string;
  mutatedCode: string;
}
