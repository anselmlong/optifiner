import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faRobot,
  faDna,
  faDollarSign,
  faChartLine,
  faPlus,
  faArrowRight,
  faPlay,
  faPause,
  faEllipsisV,
  faClock
} from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import { MetricCard } from '../components/ui/MetricCard'
import { ProgressBar } from '../components/ui/ProgressBar'
import { StatusDot } from '../components/ui/StatusDot'
import { useStore } from '../store'
import { XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart } from 'recharts'

export function Dashboard() {
  const { projects, metrics, agents } = useStore()

  const totalAgentsActive = agents.filter(a => a.status !== 'idle' && a.status !== 'waiting').length

  return (
    <div className="min-h-screen">
      <Header title="Evolution Dashboard" subtitle="Darwin-Alpha-9 • Online" />

      <div className="p-6 space-y-6">
        {/* Description */}
        <p className="text-slate-600 dark:text-slate-400 max-w-2xl">
          Manage Darwinian code evolution agents and monitor real-time fitness scores across your distributed repositories.
        </p>

        {/* Quick Actions */}
        <div className="flex items-center justify-between">
          <div />
          <Link to="/projects/new">
            <Button icon={faPlus} variant="primary">
              New Project
            </Button>
          </Link>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            label="Total Agents Active"
            value={124}
            change={12}
            changeLabel="vs last week"
            icon={faRobot}
            iconColor="text-primary-500"
          />
          <MetricCard
            label="Improvements Found"
            value="8,942"
            change={8}
            changeLabel="vs last week"
            icon={faDna}
            iconColor="text-success-solid"
          />
          <MetricCard
            label="Compute Cost (MTD)"
            value="124.50"
            prefix="$"
            change={-5}
            changeLabel="vs last month"
            icon={faDollarSign}
            iconColor="text-warning-solid"
          />
          <MetricCard
            label="Avg. Fitness Gain"
            value="18.4"
            suffix="%"
            change={3}
            icon={faChartLine}
            iconColor="text-info-solid"
          />
        </div>

        {/* Main Content Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Evolution Projects */}
          <div className="lg:col-span-2">
            <Card padding="none">
              <CardHeader className="px-5 pt-5 pb-0">
                <div className="flex items-center gap-2">
                  <FontAwesomeIcon icon={faDna} className="text-primary-500" />
                  <CardTitle>Active Evolution Projects</CardTitle>
                </div>
                <Link to="/projects" className="text-sm text-primary-500 hover:text-primary-600 flex items-center gap-1">
                  View all projects <FontAwesomeIcon icon={faArrowRight} className="text-xs" />
                </Link>
              </CardHeader>

              <div className="p-5 space-y-4">
                {projects.slice(0, 4).map((project) => (
                  <div
                    key={project.id}
                    className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <h4 className="font-semibold text-slate-900 dark:text-white">{project.name}</h4>
                          <Badge
                            variant={project.status === 'active' ? 'success' : project.status === 'paused' ? 'warning' : 'default'}
                            size="sm"
                            dot
                            pulse={project.status === 'active'}
                          >
                            {project.status === 'active' ? 'Running' : project.status === 'paused' ? 'Paused' : project.status}
                          </Badge>
                        </div>
                        <p className="text-sm text-slate-500 dark:text-slate-400">
                          GEN: {project.generation} • {project.activeAgents}/{project.totalAgents} agents
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500">
                          <FontAwesomeIcon icon={project.status === 'active' ? faPause : faPlay} />
                        </button>
                        <button className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-500">
                          <FontAwesomeIcon icon={faEllipsisV} />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs text-slate-500 dark:text-slate-400">BEST FITNESS</span>
                      <span className="text-sm font-semibold text-slate-900 dark:text-white">{project.fitness.toFixed(3)}</span>
                    </div>
                    <ProgressBar
                      value={project.fitness * 100}
                      variant={project.fitness > 0.8 ? 'success' : project.fitness > 0.5 ? 'default' : 'warning'}
                    />

                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                      <div className="flex items-center gap-4 text-xs text-slate-500 dark:text-slate-400">
                        <span className="flex items-center gap-1">
                          <FontAwesomeIcon icon={faClock} />
                          {new Date(project.updatedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                        <span className="flex items-center gap-1">
                          <FontAwesomeIcon icon={faDollarSign} />
                          ${project.costSpent.toFixed(2)}
                        </span>
                      </div>
                      <Badge variant="info" size="sm">
                        ROTATION: {Math.floor(Math.random() * 50) + 10}K
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* Right Sidebar */}
          <div className="space-y-6">
            {/* Fitness Trend */}
            <Card>
              <CardHeader>
                <CardTitle>Fitness Trend</CardTitle>
                <span className="text-xs text-slate-500">Last 24h</span>
              </CardHeader>
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={metrics}>
                    <defs>
                      <linearGradient id="fitnessGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#3B82F6" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                    <XAxis dataKey="generation" tick={{ fontSize: 10 }} stroke="#94A3B8" />
                    <YAxis tick={{ fontSize: 10 }} stroke="#94A3B8" domain={[0, 1]} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1E293B',
                        border: 'none',
                        borderRadius: '8px',
                        fontSize: '12px'
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="fitness"
                      stroke="#3B82F6"
                      strokeWidth={2}
                      fill="url(#fitnessGradient)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>

            {/* Agent Activity */}
            <Card>
              <CardHeader>
                <CardTitle>Agent Activity</CardTitle>
                <Badge variant="success" size="sm" dot pulse>{totalAgentsActive} Active</Badge>
              </CardHeader>
              <div className="space-y-3">
                {agents.slice(0, 4).map((agent) => (
                  <div key={agent.id} className="flex items-center gap-3">
                    <StatusDot status={agent.status} size="md" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{agent.name}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{agent.currentTask}</p>
                    </div>
                    <Badge
                      variant={
                        agent.status === 'analyzing' ? 'info' :
                        agent.status === 'mutating' ? 'mutating' :
                        agent.status === 'testing' ? 'processing' :
                        'default'
                      }
                      size="sm"
                    >
                      {agent.status}
                    </Badge>
                  </div>
                ))}
              </div>
              <Link to="/agents" className="mt-4 block text-center text-sm text-primary-500 hover:text-primary-600">
                View all agents
              </Link>
            </Card>

            {/* Cost Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle>Cost Breakdown</CardTitle>
              </CardHeader>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-chart-1" />
                    <span className="text-sm text-slate-600 dark:text-slate-400">Claude Sonnet</span>
                  </div>
                  <span className="text-sm font-medium text-slate-900 dark:text-white">$68.40</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-chart-2" />
                    <span className="text-sm text-slate-600 dark:text-slate-400">GPT-4o</span>
                  </div>
                  <span className="text-sm font-medium text-slate-900 dark:text-white">$42.15</span>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-chart-3" />
                    <span className="text-sm text-slate-600 dark:text-slate-400">DeepSeek</span>
                  </div>
                  <span className="text-sm font-medium text-slate-900 dark:text-white">$13.95</span>
                </div>
                <div className="pt-3 mt-3 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-900 dark:text-white">Total</span>
                  <span className="text-lg font-bold text-slate-900 dark:text-white">$124.50</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  )
}
