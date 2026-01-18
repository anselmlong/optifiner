import { useState, useEffect, useMemo } from 'react'
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
  faChevronRight,
  faSpinner
} from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { Input } from '../components/ui/Input'
import { useStore } from '../store'

interface HistoryGeneration {
  id: string
  generation: number
  timestamp: string
  mutations: Array<{
    id: string
    agent: string
    file: string
    status: 'accepted' | 'rejected'
    fitnessChange: number
    description: string
  }>
  totalFitness: number
  fitnessGain: number
}

export function History() {
  const { workflows, workflowsLoading, workflowsError, fetchWorkflows } = useStore()
  const [searchQuery, setSearchQuery] = useState('')
  const [expandedGen, setExpandedGen] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'accepted' | 'rejected'>('all')

  // Fetch workflows on mount
  useEffect(() => {
    fetchWorkflows()
  }, [fetchWorkflows])

  // Transform workflows into history data format
  const historyData = useMemo<HistoryGeneration[]>(() => {
    const generations: HistoryGeneration[] = []

    workflows.forEach(workflow => {
      // Group steps by generation
      const stepsByGeneration = new Map<number, typeof workflow.steps>()

      workflow.steps?.forEach(step => {
        if (!stepsByGeneration.has(step.generation)) {
          stepsByGeneration.set(step.generation, [])
        }
        stepsByGeneration.get(step.generation)!.push(step)
      })

      // Convert each generation into history format
      stepsByGeneration.forEach((steps, generation) => {
        const mutations = steps.map(step => ({
          id: step.id,
          agent: step.agent_id || 'Unknown Agent',
          file: step.commit_hash || 'Unknown file',
          status: (step.improvement > 0 ? 'accepted' : 'rejected') as 'accepted' | 'rejected',
          fitnessChange: step.improvement_percent / 100,
          description: step.is_initial
            ? 'Initial baseline measurement'
            : `Score: ${step.baseline_score.toFixed(2)} → ${step.final_score.toFixed(2)}`,
        }))

        const lastStep = steps[steps.length - 1]
        const firstStep = steps[0]
        const fitnessGain = lastStep ? (lastStep.final_score - firstStep.baseline_score) : 0

        generations.push({
          id: `${workflow.workflow_id}-gen-${generation}`,
          generation,
          timestamp: lastStep?.timestamp || workflow.created_at || new Date().toISOString(),
          mutations,
          totalFitness: lastStep?.final_score || 0,
          fitnessGain,
        })
      })
    })

    // Sort by generation descending
    return generations.sort((a, b) => b.generation - a.generation)
  }, [workflows])

  // Set first generation expanded by default when data loads
  useEffect(() => {
    if (historyData.length > 0 && !expandedGen) {
      setExpandedGen(historyData[0].id)
    }
  }, [historyData, expandedGen])

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

        {/* Loading State */}
        {workflowsLoading && (
          <Card className="py-12 text-center">
            <FontAwesomeIcon icon={faSpinner} className="text-4xl text-primary-500 mb-4 animate-spin" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">Loading history...</h3>
          </Card>
        )}

        {/* Error State */}
        {workflowsError && !workflowsLoading && (
          <Card className="py-12 text-center">
            <h3 className="text-lg font-semibold text-red-500 mb-2">Error loading history</h3>
            <p className="text-slate-500 mb-4">{workflowsError}</p>
            <Button variant="primary" onClick={() => fetchWorkflows()}>
              Retry
            </Button>
          </Card>
        )}

        {/* Empty State */}
        {!workflowsLoading && !workflowsError && historyData.length === 0 && (
          <Card className="py-12 text-center">
            <FontAwesomeIcon icon={faHistory} className="text-4xl text-slate-300 dark:text-slate-600 mb-4" />
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">No history yet</h3>
            <p className="text-slate-500 mb-4">
              Run your first optimization to see evolution history here.
            </p>
          </Card>
        )}

        {/* Load More - only shown when there's data and more to load */}
        {historyData.length > 0 && (
          <div className="text-center">
            <Button variant="secondary" onClick={() => fetchWorkflows({ limit: 50 })}>
              Load More Generations
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
