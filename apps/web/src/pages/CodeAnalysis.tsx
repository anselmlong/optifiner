import { useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faCodeBranch,
  faCheck,
  faTimes,
  faArrowDown,
  faArrowUp,
  faRobot,
  faLightbulb,
  faShieldAlt,
  faLink,
  faCodeCompare,
  faCopy,
  faArrowLeft
} from '@fortawesome/free-solid-svg-icons'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { ProgressBar } from '../components/ui/ProgressBar'

// Mock mutation data
const mockMutation = {
  fileName: 'optimization/data-sort-worker.js',
  candidate: 'MUT-8042x',
  metrics: {
    executionLatency: { value: 85, change: -29, unit: 'ms' },
    memoryUsage: { value: 46, change: -2.2, unit: 'MB' },
    complexity: { value: 4.0, change: -66, unit: 'cyc' }
  },
  agent: {
    name: 'Refactor-Agent-09',
    version: 'v3.4.1',
    mode: 'Expert Mode'
  },
  reasoning: `Detected a nested loop structure O(n²) in the processLargeDataSet function which causes significant latency spikes on datasets >10k items.

I have refactored this to use a Map for frequency counting, reducing complexity to O(n). This trades a small amount of memory for a 66% improvement in time complexity.`,
  safetyCheck: {
    unitTestsPassed: 94,
    unitTestsTotal: 94,
    regressionRisk: 'Low' as const
  },
  related: [
    { id: 'issue-405', title: 'Worker thread timeout on large import' }
  ],
  baseCode: `function processLargeDataSet(items) {
  let result = [];
  for (let i = 0; i < items.length; i++) {
    let count = 0;
    for (let j = 0; j < items.length; j++) {
      if (items[i] === items[j]) count++;
    }
    result.push({ item: items[i], count });
  }
  return result;
}`,
  mutatedCode: `function processLargeDataSet(items) {
  let result = [];

  // Optimized with frequency map O(n)
  const counts = new Map();
  for (const item of items) {
    counts.set(item, (counts.get(item) ||
      0) + 1);
  }

  result = items.map(item => ({ item,
    count: counts.get(item) }));

  return result;
}`
}

export function CodeAnalysis() {
  const { projectId, nodeId } = useParams<{ projectId: string; nodeId: string }>()
  const navigate = useNavigate()
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const [activeTab, setActiveTab] = useState<'base' | 'mutation'>('mutation')

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-slate-50 dark:bg-slate-900">
      {/* App Header */}
      <header className="h-14 bg-white dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 flex items-center px-4 shrink-0">
        <Button variant="ghost" size="sm" icon={faArrowLeft} onClick={() => navigate(`/projects/${projectId}`)}>
          Back to Tree
        </Button>
        <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 mx-4" />
        <div className="flex items-center gap-2">
          <span className="text-slate-500 text-sm">Analyzing Node:</span>
          <Badge variant="blue" size="sm" icon={faCodeBranch}>{nodeId}</Badge>
        </div>
      </header>

      {/* Main Content Area */}
      <div className="flex-1 flex min-h-0">
        
        {/* Left Column: Code Viewer (Flexible) */}
        <div className="flex-1 flex flex-col min-w-0 border-r border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900">
          
          {/* Toolbar */}
          <div className="h-16 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between px-6 shrink-0 bg-slate-50/50 dark:bg-slate-800/20 backdrop-blur-sm">
            <div className="flex items-center gap-4">
              <div className="flex flex-col">
                <div className="flex items-center gap-2 mb-1">
                  <h1 className="text-lg font-bold text-slate-900 dark:text-white font-mono">{mockMutation.fileName}</h1>
                  <Badge variant="processing" size="sm">Candidate {mockMutation.candidate}</Badge>
                </div>
                <div className="flex text-xs text-slate-500 gap-4">
                  <span className="flex items-center gap-1"><FontAwesomeIcon icon={faCodeBranch} /> master</span>
                  <span className="text-slate-300 dark:text-slate-600">→</span>
                  <span className="flex items-center gap-1 text-primary-500 font-medium"><FontAwesomeIcon icon={faCodeCompare} /> {mockMutation.candidate}</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <div className="flex bg-slate-100 dark:bg-slate-800 rounded-lg p-1 mr-4">
                <button
                  onClick={() => setActiveTab('mutation')} // Currently tied to side-by-side view, can be enhanced
                  className="px-3 py-1.5 text-xs font-medium rounded-md bg-white dark:bg-slate-700 shadow-sm text-slate-900 dark:text-white"
                >
                  Split View
                </button>
                <button
                  className="px-3 py-1.5 text-xs font-medium rounded-md text-slate-500 hover:text-slate-700 dark:hover:text-slate-300"
                >
                  Unified
                </button>
              </div>
              <Button variant="secondary" icon={faTimes}>Discard</Button>
              <Button variant="primary" icon={faCheck}>Merge</Button>
            </div>
          </div>

          {/* Code Area - Scrollable */}
          <div className="flex-1 overflow-auto custom-scrollbar">
            <div className="min-h-full grid grid-cols-2 divide-x divide-slate-200 dark:divide-slate-700">
              {/* Base Code Pane */}
              <div className="flex flex-col">
                <div className="sticky top-0 z-10 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-700 px-4 py-2 text-xs font-medium text-slate-500 uppercase tracking-wider flex justify-between items-center">
                  <span>Base (HEAD)</span>
                  <span className="font-mono opacity-50">63 lines</span>
                </div>
                <div className="p-0">
                  <pre className="text-sm font-mono text-slate-700 dark:text-slate-300 leading-6">
                    <code>
                      {mockMutation.baseCode.split('\n').map((line, i) => (
                        <div key={i} className="flex hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <span className="w-12 text-right pr-4 text-slate-400 select-none bg-slate-50 dark:bg-slate-800/30 border-r border-slate-100 dark:border-slate-700/50 py-0.5">{i + 1}</span>
                          <span className={`flex-1 pl-4 py-0.5 ${line.includes('for (let j') ? 'bg-error-bg/30 dark:bg-error-bg-dark/30' : ''}`}>
                            {line || ' '}
                          </span>
                        </div>
                      ))}
                    </code>
                  </pre>
                </div>
              </div>

              {/* Mutation Pane */}
              <div className="flex flex-col">
                <div className="sticky top-0 z-10 bg-primary-50/30 dark:bg-primary-900/10 border-b border-primary-100 dark:border-primary-900/30 px-4 py-2 text-xs font-medium text-primary-600 dark:text-primary-400 uppercase tracking-wider flex justify-between items-center">
                  <span>Mutation (Candidate)</span>
                  <span className="font-mono opacity-50">58 lines</span>
                </div>
                <div className="p-0">
                   <pre className="text-sm font-mono text-slate-700 dark:text-slate-300 leading-6">
                    <code>
                      {mockMutation.mutatedCode.split('\n').map((line, i) => (
                        <div key={i} className="flex hover:bg-slate-50 dark:hover:bg-slate-800/50">
                          <span className="w-12 text-right pr-4 text-slate-400 select-none bg-slate-50 dark:bg-slate-800/30 border-r border-slate-100 dark:border-slate-700/50 py-0.5">{i + 1}</span>
                          <span className={`flex-1 pl-4 py-0.5 ${
                            line.includes('// Optimized') || line.includes('const counts') || line.includes('counts.set')
                              ? 'bg-success-bg/30 dark:bg-success-bg-dark/30 relative after:content-[""] after:absolute after:left-0 after:top-0 after:bottom-0 after:w-1 after:bg-success-solid'
                              : ''
                          }`}>
                            {line || ' '}
                          </span>
                        </div>
                      ))}
                    </code>
                  </pre>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Analysis Sidebar */}
        <aside className="w-96 flex-shrink-0 bg-white dark:bg-slate-800 border-l border-slate-200 dark:border-slate-700 flex flex-col overflow-y-auto custom-scrollbar">
          <div className="p-6 space-y-8">
            
            {/* Impact Metrics - Vertical Stack */}
            <div>
              <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Impact Analysis</h3>
              <div className="space-y-3">
                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Latency</span>
                    <Badge variant="success" size="sm" icon={faArrowDown}>{mockMutation.metrics.executionLatency.change}%</Badge>
                  </div>
                  <div className="flex items-baseline gap-1">
                     <span className="text-2xl font-bold text-slate-900 dark:text-white">{mockMutation.metrics.executionLatency.value}</span>
                     <span className="text-sm text-slate-500">{mockMutation.metrics.executionLatency.unit}</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Memory</span>
                    <Badge variant="warning" size="sm" icon={faArrowUp}>+{Math.abs(mockMutation.metrics.memoryUsage.change)}%</Badge>
                  </div>
                  <div className="flex items-baseline gap-1">
                     <span className="text-2xl font-bold text-slate-900 dark:text-white">{mockMutation.metrics.memoryUsage.value}</span>
                     <span className="text-sm text-slate-500">{mockMutation.metrics.memoryUsage.unit}</span>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-100 dark:border-slate-700/50">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-slate-600 dark:text-slate-400">Complexity</span>
                    <Badge variant="success" size="sm" icon={faArrowDown}>{mockMutation.metrics.complexity.change}%</Badge>
                  </div>
                  <div className="flex items-baseline gap-1">
                     <span className="text-2xl font-bold text-slate-900 dark:text-white">{mockMutation.metrics.complexity.value}</span>
                     <span className="text-sm text-slate-500">{mockMutation.metrics.complexity.unit}</span>
                  </div>
                </div>
              </div>
            </div>

            <hr className="border-slate-100 dark:border-slate-700" />

            {/* Agent Insights */}
            <div>
              <div className="flex items-center gap-3 mb-4">
                <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center shadow-sm">
                  <FontAwesomeIcon icon={faRobot} className="text-white text-xs" />
                </div>
                <div>
                   <h4 className="text-sm font-bold text-slate-900 dark:text-white">{mockMutation.agent.name}</h4>
                   <p className="text-[10px] text-slate-500 uppercase tracking-wide">{mockMutation.agent.mode}</p>
                </div>
              </div>

              <div className="bg-primary-50 dark:bg-primary-900/20 border border-primary-100 dark:border-primary-900/30 rounded-lg p-4">
                <div className="flex items-start gap-2">
                  <FontAwesomeIcon icon={faLightbulb} className="text-primary-500 mt-0.5 text-sm" />
                  <p className="text-sm text-slate-700 dark:text-slate-300 leading-relaxed italic">
                    "{mockMutation.reasoning}"
                  </p>
                </div>
              </div>
            </div>
            
            <hr className="border-slate-100 dark:border-slate-700" />

            {/* Safety Verification */}
            <div>
               <div className="flex items-center gap-2 mb-4">
                <FontAwesomeIcon icon={faShieldAlt} className="text-slate-400" />
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Safety Verification</h3>
              </div>
              
              <div className="space-y-4">
                 <div className="space-y-2">
                   <div className="flex justify-between text-sm">
                     <span className="text-slate-600 dark:text-slate-400">Test Coverage</span>
                     <span className="font-medium text-slate-900 dark:text-white">100%</span>
                   </div>
                   <ProgressBar value={100} max={100} variant="success" size="sm" />
                 </div>

                 <div className="space-y-2">
                   <div className="flex justify-between text-sm">
                     <span className="text-slate-600 dark:text-slate-400">Pass Rate</span>
                     <span className="font-medium text-slate-900 dark:text-white">{mockMutation.safetyCheck.unitTestsPassed}/{mockMutation.safetyCheck.unitTestsTotal}</span>
                   </div>
                   <ProgressBar value={mockMutation.safetyCheck.unitTestsPassed} max={mockMutation.safetyCheck.unitTestsTotal} variant="success" size="sm" />
                 </div>
              </div>
            </div>

            {/* Related Issues */}
            <div>
              <div className="flex items-center gap-2 mb-4">
                <FontAwesomeIcon icon={faLink} className="text-slate-400" />
                <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Related Context</h3>
              </div>
              <div className="space-y-2">
                {mockMutation.related.map((item) => (
                  <a
                    key={item.id}
                    href="#"
                    className="flex items-start gap-3 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-700/50 border border-transparent hover:border-slate-200 dark:hover:border-slate-600 transition-all group"
                  >
                    <FontAwesomeIcon icon={faLink} className="text-slate-300 group-hover:text-primary-400 mt-1" />
                    <div>
                      <span className="text-xs font-mono text-slate-500 block mb-0.5">{item.id}</span>
                      <span className="text-sm text-slate-700 dark:text-slate-300 group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors leading-tight block">
                        {item.title}
                      </span>
                    </div>
                  </a>
                ))}
              </div>
            </div>

          </div>
        </aside>
      </div>
    </div>
  )
}
