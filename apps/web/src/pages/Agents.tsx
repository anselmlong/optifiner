import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faRobot,
  faPlus,
  faSearch,
  faCog,
  faPlay,
  faPause,
  faEllipsisV,
  faBrain,
  faCode,
  faWrench,
  faRocket,
  faChartLine,
  faCheckCircle
} from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { ProgressBar } from '../components/ui/ProgressBar'
import { StatusDot } from '../components/ui/StatusDot'
import { useStore } from '../store'

const agentTypeInfo = {
  analyzer: { icon: faBrain, color: 'text-info-solid', bgColor: 'bg-info-bg dark:bg-info-bg-dark', label: 'Analyzer' },
  refactor: { icon: faCode, color: 'text-purple-500', bgColor: 'bg-purple-100 dark:bg-purple-900/30', label: 'Refactor' },
  feature: { icon: faRocket, color: 'text-success-solid', bgColor: 'bg-success-bg dark:bg-success-bg-dark', label: 'Feature' },
  optimizer: { icon: faWrench, color: 'text-warning-solid', bgColor: 'bg-warning-bg dark:bg-warning-bg-dark', label: 'Optimizer' }
}

export function Agents() {
  const { agents } = useStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [typeFilter, setTypeFilter] = useState<'all' | 'analyzer' | 'refactor' | 'feature' | 'optimizer'>('all')

  const filteredAgents = agents.filter(agent => {
    const matchesSearch = agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          agent.currentTask?.toLowerCase().includes(searchQuery.toLowerCase())
    const matchesType = typeFilter === 'all' || agent.type === typeFilter
    return matchesSearch && matchesType
  })

  const stats = {
    total: agents.length,
    active: agents.filter(a => !['idle', 'waiting'].includes(a.status)).length,
    totalMutations: agents.reduce((sum, a) => sum + a.mutationsProposed, 0),
    acceptedMutations: agents.reduce((sum, a) => sum + a.mutationsAccepted, 0)
  }

  return (
    <div className="min-h-screen">
      <Header title="Agent Fleet" />

      <div className="p-6 space-y-6">
        {/* Stats Row */}
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center">
                <FontAwesomeIcon icon={faRobot} className="text-primary-500" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.total}</p>
                <p className="text-sm text-slate-500">Total Agents</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-success-bg dark:bg-success-bg-dark flex items-center justify-center">
                <FontAwesomeIcon icon={faPlay} className="text-success-solid" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.active}</p>
                <p className="text-sm text-slate-500">Active Now</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-info-bg dark:bg-info-bg-dark flex items-center justify-center">
                <FontAwesomeIcon icon={faCode} className="text-info-solid" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.totalMutations}</p>
                <p className="text-sm text-slate-500">Mutations Proposed</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-success-bg dark:bg-success-bg-dark flex items-center justify-center">
                <FontAwesomeIcon icon={faCheckCircle} className="text-success-solid" />
              </div>
              <div>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">{stats.acceptedMutations}</p>
                <p className="text-sm text-slate-500">Accepted</p>
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
                placeholder="Search agents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setTypeFilter('all')}
                className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                  typeFilter === 'all'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                All Types
              </button>
              {Object.entries(agentTypeInfo).map(([type, info]) => (
                <button
                  key={type}
                  onClick={() => setTypeFilter(type as typeof typeFilter)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors flex items-center gap-2 ${
                    typeFilter === type
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  <FontAwesomeIcon icon={info.icon} className={info.color} />
                  {info.label}
                </button>
              ))}
            </div>
          </div>
          <Button icon={faPlus} variant="primary">
            Deploy Agent
          </Button>
        </div>

        {/* Agents Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAgents.map((agent) => {
            const typeInfo = agentTypeInfo[agent.type]
            return (
              <Card key={agent.id} className="hover:border-primary-300 dark:hover:border-primary-700 transition-all">
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-3">
                    <div className={`w-12 h-12 rounded-xl ${typeInfo.bgColor} flex items-center justify-center`}>
                      <FontAwesomeIcon icon={typeInfo.icon} className={typeInfo.color} />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-slate-900 dark:text-white">{agent.name}</h3>
                        <StatusDot status={agent.status} />
                      </div>
                      <p className="text-xs text-slate-500">{typeInfo.label} Agent</p>
                    </div>
                  </div>
                  <button className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500">
                    <FontAwesomeIcon icon={faEllipsisV} />
                  </button>
                </div>

                {/* Current Task */}
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 mb-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Badge
                      variant={
                        agent.status === 'analyzing' ? 'info' :
                        agent.status === 'mutating' ? 'mutating' :
                        agent.status === 'testing' ? 'processing' :
                        'default'
                      }
                      size="sm"
                    >
                      {agent.status.toUpperCase()}
                    </Badge>
                  </div>
                  <p className="text-sm text-slate-700 dark:text-slate-300">{agent.currentTask}</p>
                  {agent.currentFile && (
                    <p className="text-xs text-slate-500 mt-1 font-mono">{agent.currentFile}</p>
                  )}
                </div>

                {/* Stats */}
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-lg font-semibold text-slate-900 dark:text-white">{agent.mutationsProposed}</p>
                    <p className="text-xs text-slate-500">Proposed</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-lg font-semibold text-success-solid">{agent.mutationsAccepted}</p>
                    <p className="text-xs text-slate-500">Accepted</p>
                  </div>
                  <div className="text-center p-2 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-lg font-semibold text-slate-900 dark:text-white">{(agent.successRate * 100).toFixed(0)}%</p>
                    <p className="text-xs text-slate-500">Success</p>
                  </div>
                </div>

                {/* Success Rate Bar */}
                <div className="mb-4">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs text-slate-500">Success Rate</span>
                    <span className="text-xs font-medium text-slate-700 dark:text-slate-300">{(agent.successRate * 100).toFixed(1)}%</span>
                  </div>
                  <ProgressBar
                    value={agent.successRate * 100}
                    variant={agent.successRate > 0.8 ? 'success' : agent.successRate > 0.6 ? 'default' : 'warning'}
                  />
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 pt-3 border-t border-slate-100 dark:border-slate-700">
                  <Button variant="secondary" size="sm" className="flex-1" icon={faChartLine}>
                    View Logs
                  </Button>
                  <Button variant="ghost" size="sm" icon={faCog} />
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={agent.status === 'idle' || agent.status === 'waiting' ? faPlay : faPause}
                  />
                </div>
              </Card>
            )
          })}
        </div>

        {/* Empty State */}
        {filteredAgents.length === 0 && (
          <Card className="py-12 text-center">
            <FontAwesomeIcon icon={faRobot} className="text-4xl text-slate-300 dark:text-slate-600 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No agents found</h3>
            <p className="text-slate-500 mb-4">
              {searchQuery ? 'Try adjusting your search or filters' : 'Deploy your first agent to get started'}
            </p>
            <Button icon={faPlus} variant="primary">
              Deploy Agent
            </Button>
          </Card>
        )}
      </div>
    </div>
  )
}
