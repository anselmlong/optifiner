/**
 * WebSocket client for real-time updates.
 */

type MessageHandler = (data: WebSocketMessage) => void

export interface WebSocketMessage {
  type: string
  workflow_id?: string
  data: Record<string, unknown>
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

export interface StatusUpdate {
  status: string
  baseline_score?: number
  final_score?: number
  improvement?: number
  improvement_percent?: number
  error?: string
}

export interface GraphNode {
  id: string
  type: string
  generation: number
  score: number
  agent_id?: string
  status: 'accepted' | 'rejected' | 'processing' | 'analyzing'
  label: string
  description: string
  commit_hash?: string
}

export interface GraphEdge {
  source: string
  target: string
}

export interface GraphUpdate {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

class WebSocketClient {
  private socket: WebSocket | null = null
  private url: string
  private handlers: Set<MessageHandler> = new Set()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5
  private reconnectDelay = 1000
  private pingInterval: number | null = null
  private isIntentionallyClosed = false

  constructor(url: string) {
    this.url = url
  }

  connect(): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      return
    }

    this.isIntentionallyClosed = false
    
    // Determine WebSocket URL based on current location
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const host = window.location.host
    const wsUrl = `${protocol}//${host}${this.url}`

    this.socket = new WebSocket(wsUrl)

    this.socket.onopen = () => {
      console.log(`WebSocket connected to ${this.url}`)
      this.reconnectAttempts = 0
      
      // Start ping interval
      this.pingInterval = window.setInterval(() => {
        if (this.socket?.readyState === WebSocket.OPEN) {
          this.socket.send('ping')
        }
      }, 30000)
    }

    this.socket.onmessage = (event) => {
      if (event.data === 'pong') {
        return // Ignore pong responses
      }
      
      try {
        const message = JSON.parse(event.data) as WebSocketMessage
        this.handlers.forEach(handler => handler(message))
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error)
      }
    }

    this.socket.onclose = () => {
      console.log(`WebSocket disconnected from ${this.url}`)
      
      if (this.pingInterval) {
        clearInterval(this.pingInterval)
        this.pingInterval = null
      }

      if (!this.isIntentionallyClosed && this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts++
        const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1)
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`)
        setTimeout(() => this.connect(), delay)
      }
    }

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }

  disconnect(): void {
    this.isIntentionallyClosed = true
    
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
    
    if (this.socket) {
      this.socket.close()
      this.socket = null
    }
  }

  subscribe(handler: MessageHandler): () => void {
    this.handlers.add(handler)
    return () => this.handlers.delete(handler)
  }

  isConnected(): boolean {
    return this.socket?.readyState === WebSocket.OPEN
  }
}

// Singleton instances
const workflowSockets: Map<string, WebSocketClient> = new Map()
let globalSocket: WebSocketClient | null = null

/**
 * Get or create a WebSocket connection for a specific workflow.
 */
export function getWorkflowSocket(workflowId: string): WebSocketClient {
  let socket = workflowSockets.get(workflowId)
  if (!socket) {
    socket = new WebSocketClient(`/ws/workflow/${workflowId}`)
    workflowSockets.set(workflowId, socket)
  }
  return socket
}

/**
 * Get or create the global WebSocket connection for dashboard updates.
 */
export function getGlobalSocket(): WebSocketClient {
  if (!globalSocket) {
    globalSocket = new WebSocketClient('/ws/global')
  }
  return globalSocket
}

/**
 * Disconnect and remove a workflow socket.
 */
export function disconnectWorkflowSocket(workflowId: string): void {
  const socket = workflowSockets.get(workflowId)
  if (socket) {
    socket.disconnect()
    workflowSockets.delete(workflowId)
  }
}

/**
 * Disconnect all sockets.
 */
export function disconnectAll(): void {
  workflowSockets.forEach(socket => socket.disconnect())
  workflowSockets.clear()
  
  if (globalSocket) {
    globalSocket.disconnect()
    globalSocket = null
  }
}
