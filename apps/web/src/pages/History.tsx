import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faHistory,
  faSearch,
  faCheck,
  faTimes,
  faEye,
  faUndo,
  faCalendar,
  faClock,
  faRobot,
  faChevronDown,
  faChevronRight
} from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'

const historyData = [
  {
    id: 'gen-42',
    generation: 42,
    timestamp: '2024-01-17T14:30:00Z',
    mutations: [
      { id: 'MUT-8042', agent: 'Agent 03', file: 'data-sort-worker.js', status: 'accepted', fitnessChange: +0.15, description: 'Optimized nested loop with Map' },
      { id: 'MUT-8043', agent: 'Agent 01', file: 'cache-layer.ts', status: 'rejected', fitnessChange: -0.02, description: 'Attempted LRU cache implementation' },
      { id: 'MUT-8044', agent: 'Agent 05', file: 'utils.py', status: 'accepted', fitnessChange: +0.08, description: 'Vectorized array operations' }
    ],
    totalFitness: 0.89,
    fitnessGain: +0.04
  },
  {
    id: 'gen-41',
    generation: 41,
    timestamp: '2024-01-17T14:15:00Z',
    mutations: [
      { id: 'MUT-8039', agent: 'Agent 02', file: 'api-router.go', status: 'accepted', fitnessChange: +0.06, description: 'Reduced middleware overhead' },
      { id: 'MUT-8040', agent: 'Agent 04', file: 'db-pool.rs', status: 'rejected', fitnessChange: -0.01, description: 'Connection pooling refactor' },
      { id: 'MUT-8041', agent: 'Agent 03', file: 'serializer.js', status: 'accepted', fitnessChange: +0.05, description: 'JSON streaming implementation' }
    ],
    totalFitness: 0.85,
    fitnessGain: +0.03
  },
  {
    id: 'gen-40',
    generation: 40,
    timestamp: '2024-01-17T14:00:00Z',
    mutations: [
      { id: 'MUT-8035', agent: 'Agent 01', file: 'auth-service.ts', status: 'accepted', fitnessChange: +0.12, description: 'JWT validation optimization' },
      { id: 'MUT-8036', agent: 'Agent 05', file: 'logger.py', status: 'accepted', fitnessChange: +0.02, description: 'Async logging implementation' },
      { id: 'MUT-8037', agent: 'Agent 02', file: 'middleware.go', status: 'rejected', fitnessChange: 0, description: 'Request batching attempt' },
      { id: 'MUT-8038', agent: 'Agent 03', file: 'parser.js', status: 'accepted', fitnessChange: +0.04, description: 'Lazy parsing for large files' }
    ],
    totalFitness: 0.82,
    fitnessGain: +0.06
  },
  {
    id: 'gen-39',
    generation: 39,
    timestamp: '2024-01-17T13:45:00Z',
    mutations: [
      { id: 'MUT-8031', agent: 'Agent 04', file: 'query-optimizer.sql', status: 'accepted', fitnessChange: +0.08, description: 'Index usage optimization' },
      { id: 'MUT-8032', agent: 'Agent 01', file: 'caching.ts', status: 'rejected', fitnessChange: -0.03, description: 'Redis integration attempt' }
    ],
    totalFitness: 0.76,
    fitnessGain: +0.02
  }
]

export function History() {
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedGen, setExpandedGen] = useState<string | null>('gen-42')
  const [statusFilter, setStatusFilter] = useState<'all' | 'accepted' | 'rejected'>('all')

  return (
    <div className="min-h-screen">
      <Header title="Evolution History" />

      <div className="p-6 space-y-6">
        {/* Filters */}
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-4 flex-1">
            <div className="w-80">
              <Input
                icon={faSearch}
                placeholder="Search mutations, files, agents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>
            <div className="flex items-center gap-2">
              {(['all', 'accepted', 'rejected'] as const).map((status) => (
                <button
                  key={status}
                  onClick={() => setStatusFilter(status)}
                  className={`px-3 py-1.5 text-sm font-medium rounded-lg transition-colors ${
                    statusFilter === status
                      ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                      : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                  }`}
                >
                  {status.charAt(0).toUpperCase() + status.slice(1)}
                </button>
              ))}
            </div>
            <button className="px-3 py-1.5 text-sm font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2">
              <FontAwesomeIcon icon={faCalendar} />
              Date Range
            </button>
          </div>
          <Button variant="secondary" icon={faHistory}>
            Export History
          </Button>
        </div>

        {/* Timeline */}
        <div className="space-y-4">
          {historyData.map((gen) => (
            <Card key={gen.id} padding="none">
              {/* Generation Header */}
              <button
                onClick={() => setExpandedGen(expandedGen === gen.id ? null : gen.id)}
                className="w-full px-5 py-4 flex items-center justify-between hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <div className="flex items-center gap-4">
                  <FontAwesomeIcon
                    icon={expandedGen === gen.id ? faChevronDown : faChevronRight}
                    className="text-slate-400"
                  />
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-400 to-primary-600 flex items-center justify-center text-white font-bold">
                    G{gen.generation}
                  </div>
                  <div className="text-left">
                    <h3 className="font-semibold text-slate-900 dark:text-white">
                      Generation {gen.generation}
                    </h3>
                    <div className="flex items-center gap-3 text-sm text-slate-500">
                      <span className="flex items-center gap-1">
                        <FontAwesomeIcon icon={faClock} className="text-xs" />
                        {new Date(gen.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      <span>{gen.mutations.length} mutations</span>
                      <span>{gen.mutations.filter(m => m.status === 'accepted').length} accepted</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right">
                    <p className="text-sm text-slate-500">Fitness</p>
                    <p className="text-lg font-bold text-slate-900 dark:text-white">{gen.totalFitness.toFixed(2)}</p>
                  </div>
                  <Badge
                    variant={gen.fitnessGain > 0 ? 'success' : 'error'}
                    size="sm"
                  >
                    {gen.fitnessGain > 0 ? '+' : ''}{(gen.fitnessGain * 100).toFixed(1)}%
                  </Badge>
                </div>
              </button>

              {/* Expanded Mutations */}
              {expandedGen === gen.id && (
                <div className="border-t border-slate-200 dark:border-slate-700">
                  {gen.mutations.map((mutation, index) => (
                    <div
                      key={mutation.id}
                      className={`px-5 py-4 flex items-center justify-between ${
                        index !== gen.mutations.length - 1 ? 'border-b border-slate-100 dark:border-slate-700/50' : ''
                      } hover:bg-slate-50 dark:hover:bg-slate-800/30`}
                    >
                      <div className="flex items-center gap-4">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                          mutation.status === 'accepted'
                            ? 'bg-success-bg dark:bg-success-bg-dark text-success-solid'
                            : 'bg-error-bg dark:bg-error-bg-dark text-error-solid'
                        }`}>
                          <FontAwesomeIcon icon={mutation.status === 'accepted' ? faCheck : faTimes} className="text-sm" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-sm text-primary-600 dark:text-primary-400">{mutation.id}</span>
                            <Badge variant="default" size="sm">
                              <FontAwesomeIcon icon={faRobot} className="mr-1" />
                              {mutation.agent}
                            </Badge>
                          </div>
                          <p className="text-sm text-slate-700 dark:text-slate-300 mt-0.5">{mutation.description}</p>
                          <p className="text-xs text-slate-500 font-mono mt-1">{mutation.file}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-4">
                        <div className="text-right">
                          <p className="text-xs text-slate-500">Fitness Impact</p>
                          <p className={`text-sm font-medium ${
                            mutation.fitnessChange > 0 ? 'text-success-solid' :
                            mutation.fitnessChange < 0 ? 'text-error-solid' :
                            'text-slate-500'
                          }`}>
                            {mutation.fitnessChange > 0 ? '+' : ''}{(mutation.fitnessChange * 100).toFixed(1)}%
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button variant="ghost" size="sm" icon={faEye}>
                            View
                          </Button>
                          {mutation.status === 'accepted' && (
                            <Button variant="ghost" size="sm" icon={faUndo} className="text-slate-500">
                              Revert
                            </Button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          ))}
        </div>

        {/* Load More */}
        <div className="text-center">
          <Button variant="secondary">
            Load More Generations
          </Button>
        </div>
      </div>
    </div>
  )
}
