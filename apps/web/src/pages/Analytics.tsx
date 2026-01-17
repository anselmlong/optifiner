import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faDownload,
  faCalendar,
  faArrowUp
} from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Badge } from '../components/ui/Badge'
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

const fitnessData = [
  { day: 'Mon', fitness: 0.42, mutations: 24, cost: 12.5 },
  { day: 'Tue', fitness: 0.48, mutations: 31, cost: 15.2 },
  { day: 'Wed', fitness: 0.55, mutations: 28, cost: 14.8 },
  { day: 'Thu', fitness: 0.62, mutations: 35, cost: 18.3 },
  { day: 'Fri', fitness: 0.71, mutations: 42, cost: 22.1 },
  { day: 'Sat', fitness: 0.78, mutations: 38, cost: 19.5 },
  { day: 'Sun', fitness: 0.85, mutations: 45, cost: 24.6 }
]

const modelUsage = [
  { name: 'Claude Sonnet', value: 55, color: '#3B82F6' },
  { name: 'GPT-4o', value: 30, color: '#22C55E' },
  { name: 'DeepSeek', value: 15, color: '#F59E0B' }
]

const agentPerformance = [
  { name: 'Agent 01', accepted: 35, rejected: 7, pending: 2 },
  { name: 'Agent 02', accepted: 22, rejected: 6, pending: 0 },
  { name: 'Agent 03', accepted: 48, rejected: 8, pending: 3 },
  { name: 'Agent 04', accepted: 12, rejected: 3, pending: 1 },
  { name: 'Agent 05', accepted: 29, rejected: 4, pending: 2 }
]

export function Analytics() {
  return (
    <div className="min-h-screen">
      <Header title="Analytics" />

      <div className="p-6 space-y-6">
        {/* Period Selector & Export */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {['24h', '7d', '30d', '90d'].map((period) => (
              <button
                key={period}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                  period === '7d'
                    ? 'bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800'
                }`}
              >
                {period}
              </button>
            ))}
            <button className="px-4 py-2 text-sm font-medium rounded-lg text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 flex items-center gap-2">
              <FontAwesomeIcon icon={faCalendar} />
              Custom
            </button>
          </div>
          <Button variant="secondary" icon={faDownload}>
            Export Report
          </Button>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-4 gap-4">
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Avg. Fitness Gain</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">+43%</p>
              </div>
              <div className="flex items-center gap-1 text-success-solid">
                <FontAwesomeIcon icon={faArrowUp} className="text-xs" />
                <span className="text-sm">12%</span>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Total Mutations</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">243</p>
              </div>
              <Badge variant="success" size="sm" icon={faArrowUp}>+18%</Badge>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Acceptance Rate</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">84.2%</p>
              </div>
              <Badge variant="success" size="sm" icon={faArrowUp}>+5%</Badge>
            </div>
          </Card>
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Total Cost</p>
                <p className="text-3xl font-bold text-slate-900 dark:text-white">$127</p>
              </div>
              <Badge variant="warning" size="sm" icon={faArrowUp}>+8%</Badge>
            </div>
          </Card>
        </div>

        {/* Charts Row */}
        <div className="grid grid-cols-3 gap-6">
          {/* Fitness Over Time */}
          <Card className="col-span-2">
            <CardHeader>
              <CardTitle>Fitness Progress Over Time</CardTitle>
              <Badge variant="info" size="sm">Last 7 days</Badge>
            </CardHeader>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={fitnessData}>
                  <defs>
                    <linearGradient id="fitnessGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3B82F6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3B82F6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                  <YAxis tick={{ fontSize: 12 }} stroke="#94A3B8" domain={[0, 1]} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1E293B',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#F8FAFC'
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="fitness"
                    stroke="#3B82F6"
                    strokeWidth={2}
                    fill="url(#fitnessGradient)"
                    name="Fitness Score"
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Model Usage Pie */}
          <Card>
            <CardHeader>
              <CardTitle>Model Usage</CardTitle>
            </CardHeader>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modelUsage}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {modelUsage.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="flex items-center justify-center gap-4 mt-2">
              {modelUsage.map((model) => (
                <div key={model.name} className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full" style={{ backgroundColor: model.color }} />
                  <span className="text-xs text-slate-600 dark:text-slate-400">{model.name}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Second Charts Row */}
        <div className="grid grid-cols-2 gap-6">
          {/* Mutations & Cost */}
          <Card>
            <CardHeader>
              <CardTitle>Mutations vs Cost</CardTitle>
            </CardHeader>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={fitnessData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis dataKey="day" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                  <YAxis yAxisId="left" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                  <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1E293B',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#F8FAFC'
                    }}
                  />
                  <Legend />
                  <Bar yAxisId="left" dataKey="mutations" fill="#3B82F6" name="Mutations" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>

          {/* Agent Performance */}
          <Card>
            <CardHeader>
              <CardTitle>Agent Performance</CardTitle>
            </CardHeader>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={agentPerformance} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                  <XAxis type="number" tick={{ fontSize: 12 }} stroke="#94A3B8" />
                  <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} stroke="#94A3B8" width={80} />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1E293B',
                      border: 'none',
                      borderRadius: '8px',
                      fontSize: '12px',
                      color: '#F8FAFC'
                    }}
                  />
                  <Legend />
                  <Bar dataKey="accepted" stackId="a" fill="#22C55E" name="Accepted" />
                  <Bar dataKey="rejected" stackId="a" fill="#EF4444" name="Rejected" />
                  <Bar dataKey="pending" stackId="a" fill="#F59E0B" name="Pending" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </div>

        {/* Top Improvements Table */}
        <Card>
          <CardHeader>
            <CardTitle>Top Improvements This Week</CardTitle>
            <Button variant="ghost" size="sm">View All</Button>
          </CardHeader>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Mutation</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Agent</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">File</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Fitness Gain</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Latency</th>
                  <th className="text-left py-3 px-4 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                </tr>
              </thead>
              <tbody>
                {[
                  { id: 'MUT-8042', agent: 'Agent 03', file: 'data-sort-worker.js', fitnessGain: '+15.2%', latency: '-29%', status: 'merged' },
                  { id: 'MUT-8038', agent: 'Agent 01', file: 'auth-service.ts', fitnessGain: '+12.8%', latency: '-18%', status: 'merged' },
                  { id: 'MUT-8045', agent: 'Agent 05', file: 'cache-manager.py', fitnessGain: '+11.4%', latency: '-22%', status: 'pending' },
                  { id: 'MUT-8041', agent: 'Agent 02', file: 'api-router.go', fitnessGain: '+9.6%', latency: '-15%', status: 'merged' },
                  { id: 'MUT-8039', agent: 'Agent 04', file: 'query-optimizer.sql', fitnessGain: '+8.2%', latency: '-31%', status: 'merged' }
                ].map((row) => (
                  <tr key={row.id} className="border-b border-slate-100 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="py-3 px-4">
                      <span className="font-mono text-sm text-primary-600 dark:text-primary-400">{row.id}</span>
                    </td>
                    <td className="py-3 px-4 text-sm text-slate-700 dark:text-slate-300">{row.agent}</td>
                    <td className="py-3 px-4 font-mono text-sm text-slate-600 dark:text-slate-400">{row.file}</td>
                    <td className="py-3 px-4">
                      <span className="text-success-solid font-medium">{row.fitnessGain}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-success-solid">{row.latency}</span>
                    </td>
                    <td className="py-3 px-4">
                      <Badge variant={row.status === 'merged' ? 'success' : 'processing'} size="sm">
                        {row.status}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  )
}
