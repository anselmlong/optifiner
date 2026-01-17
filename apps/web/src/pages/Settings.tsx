import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faRobot,
  faBrain,
  faDollarSign,
  faFlask,
  faShieldAlt,
  faBell,
  faSave,
  faUndo
} from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Toggle } from '../components/ui/Toggle'
import { Slider } from '../components/ui/Slider'
import { useStore } from '../store'

export function Settings() {
  const { settings, updateSettings } = useStore()

  return (
    <div className="min-h-screen">
      <Header title="Settings" />

      <div className="p-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Model Configuration */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FontAwesomeIcon icon={faBrain} className="text-primary-500" />
                <CardTitle>Model Configuration</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-6">
                <Select
                  label="Primary Model"
                  value={settings.model}
                  onChange={(e) => updateSettings({ model: e.target.value as typeof settings.model })}
                  options={[
                    { value: 'claude-opus-4.5', label: 'Claude Opus 4.5' },
                    { value: 'claude-sonnet-4.5', label: 'Claude Sonnet 4.5 (Recommended)' },
                    { value: 'claude-haiku-4.5', label: 'Claude Haiku 4.5' },
                    { value: 'gpt-5.2-codex', label: 'GPT-5.2 Codex' },
                    { value: 'gpt-5.2', label: 'GPT-5.2' },
                    { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash Preview' },
                    { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro Preview' }
                  ]}
                />
                <Input
                  label="API Key"
                  type="password"
                  placeholder="sk-ant-..."
                  defaultValue="••••••••••••••••"
                />
              </div>

              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <h4 className="text-sm font-medium text-slate-900 dark:text-white mb-3">Model Comparison</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-slate-500 mb-1">Claude 4.5 Series</p>
                    <p className="text-slate-900 dark:text-white">Best quality, recommended</p>
                    <p className="text-xs text-slate-400">Opus / Sonnet / Haiku</p>
                  </div>
                  <div>
                    <p className="text-slate-500 mb-1">GPT-5.2 Series</p>
                    <p className="text-slate-900 dark:text-white">Fast, excellent for code</p>
                    <p className="text-xs text-slate-400">Codex / Standard</p>
                  </div>
                  <div>
                    <p className="text-slate-500 mb-1">Gemini 3 Series</p>
                    <p className="text-slate-900 dark:text-white">Cost-effective, fast</p>
                    <p className="text-xs text-slate-400">Flash / Pro Preview</p>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {/* Agent Settings */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FontAwesomeIcon icon={faRobot} className="text-primary-500" />
                <CardTitle>Agent Configuration</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-6">
              <Slider
                label="Agent Pool Size"
                value={settings.agentCount}
                onChange={(value) => updateSettings({ agentCount: value })}
                min={1}
                max={20}
                valueSuffix=" agents"
              />

              <div>
                <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                  Mutation Strategy
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {(['conservative', 'balanced', 'aggressive'] as const).map((rate) => (
                    <button
                      key={rate}
                      onClick={() => updateSettings({ mutationRate: rate })}
                      className={`p-4 rounded-lg border-2 transition-all ${
                        settings.mutationRate === rate
                          ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                          : 'border-slate-200 dark:border-slate-700 hover:border-primary-300'
                      }`}
                    >
                      <h4 className="font-medium text-slate-900 dark:text-white capitalize">{rate}</h4>
                      <p className="text-xs text-slate-500 mt-1">
                        {rate === 'conservative' && 'Small, safe changes'}
                        {rate === 'balanced' && 'Moderate improvements'}
                        {rate === 'aggressive' && 'Large refactors'}
                      </p>
                    </button>
                  ))}
                </div>
              </div>

              <Toggle
                checked={settings.parallelExecution}
                onChange={(checked) => updateSettings({ parallelExecution: checked })}
                label="Parallel Execution"
                description="Run multiple agents simultaneously for faster evolution"
              />
            </div>
          </Card>

          {/* Benchmark Settings */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FontAwesomeIcon icon={faFlask} className="text-primary-500" />
                <CardTitle>Benchmark Settings</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-6">
              <Slider
                label="Benchmark Timeout"
                value={settings.benchmarkTimeout}
                onChange={(value) => updateSettings({ benchmarkTimeout: value })}
                min={10}
                max={120}
                valueSuffix=" seconds"
              />

              <Slider
                label="Target Fitness Score"
                value={settings.targetFitness * 100}
                onChange={(value) => updateSettings({ targetFitness: value / 100 })}
                min={50}
                max={100}
                valueSuffix="%"
              />

              <Toggle
                checked={settings.autoStop}
                onChange={(checked) => updateSettings({ autoStop: checked })}
                label="Auto-stop on Target"
                description="Automatically stop evolution when target fitness is reached"
              />
            </div>
          </Card>

          {/* Cost Controls */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FontAwesomeIcon icon={faDollarSign} className="text-primary-500" />
                <CardTitle>Cost Controls</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-6">
              <Slider
                label="Monthly Cost Limit"
                value={settings.costLimit}
                onChange={(value) => updateSettings({ costLimit: value })}
                min={10}
                max={500}
                valuePrefix="$"
              />

              <div className="grid grid-cols-2 gap-6">
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Current Month Spend</p>
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">$124.50</p>
                  <p className="text-xs text-slate-500 mt-1">75% of limit</p>
                </div>
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                  <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Projected Monthly</p>
                  <p className="text-2xl font-bold text-warning-solid">$186.75</p>
                  <p className="text-xs text-slate-500 mt-1">Based on current usage</p>
                </div>
              </div>

              <Toggle
                checked={true}
                onChange={() => {}}
                label="Cost Alerts"
                description="Get notified when approaching cost limits"
              />
            </div>
          </Card>

          {/* Safety & Security */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FontAwesomeIcon icon={faShieldAlt} className="text-primary-500" />
                <CardTitle>Safety & Security</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-4">
              <Toggle
                checked={true}
                onChange={() => {}}
                label="Require Test Pass"
                description="Only accept mutations that pass all existing tests"
              />
              <Toggle
                checked={true}
                onChange={() => {}}
                label="Sandbox Execution"
                description="Run all code in isolated Docker containers"
              />
              <Toggle
                checked={false}
                onChange={() => {}}
                label="Allow Breaking Changes"
                description="Permit mutations that modify public APIs"
              />
              <Toggle
                checked={true}
                onChange={() => {}}
                label="Code Review Required"
                description="Flag significant changes for manual review"
              />
            </div>
          </Card>

          {/* Notifications */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <FontAwesomeIcon icon={faBell} className="text-primary-500" />
                <CardTitle>Notifications</CardTitle>
              </div>
            </CardHeader>

            <div className="space-y-4">
              <Toggle
                checked={true}
                onChange={() => {}}
                label="Evolution Milestones"
                description="Notify on significant fitness improvements"
              />
              <Toggle
                checked={true}
                onChange={() => {}}
                label="Agent Errors"
                description="Alert when agents encounter failures"
              />
              <Toggle
                checked={false}
                onChange={() => {}}
                label="Daily Summary"
                description="Receive daily progress reports via email"
              />
            </div>
          </Card>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-3">
            <Button variant="ghost" icon={faUndo}>
              Reset to Defaults
            </Button>
            <Button variant="primary" icon={faSave}>
              Save Changes
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
