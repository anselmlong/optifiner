import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faArrowLeft,
  faArrowRight,
  faFolder,
  faUpload,
  faCheck,
  faCode,
  faRobot,
  faFlask,
  faPlay,
  faPlus,
  faTrash
} from '@fortawesome/free-solid-svg-icons'
import { faGithub as faGithubBrand } from '@fortawesome/free-brands-svg-icons'
import { Header } from '../components/layout/Header'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Toggle } from '../components/ui/Toggle'
import { Slider } from '../components/ui/Slider'
import { useStore } from '../store'

const steps = [
  { id: 1, title: 'Source', icon: faCode },
  { id: 2, title: 'Agents', icon: faRobot },
  { id: 3, title: 'Benchmarks', icon: faFlask },
  { id: 4, title: 'Review', icon: faCheck }
]

export function NewProject() {
  const navigate = useNavigate()
  const { startWorkflow, connectWorkflowWs } = useStore()
  const [currentStep, setCurrentStep] = useState(1)
  const [isCreating, setIsCreating] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Model configuration type
  type ModelConfigItem = {
    id: string
    model: string
    apiKey: string
    agentCount: number
  }

  const [modelConfigs, setModelConfigs] = useState<ModelConfigItem[]>([
    { id: '1', model: 'claude-sonnet-4.5', apiKey: '', agentCount: 5 }
  ])

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    sourceType: 'github' as 'github' | 'upload' | 'local',
    repository: '',
    branch: 'main',
    mutationRate: 'balanced' as 'conservative' | 'balanced' | 'aggressive',
    targetFitness: 0.9,
    maxCost: 10,
    autoGenerateBenchmarks: true,
    benchmarkTimeout: 30,
    parallelAgents: 5,  // Run 5 agents in parallel
    generations: 5,     // Run 5 generations
  })

  const totalAgents = modelConfigs.reduce((sum, config) => sum + config.agentCount, 0)

  const addModelConfig = () => {
    setModelConfigs([...modelConfigs, {
      id: Date.now().toString(),
      model: 'gpt-5.2-codex',
      apiKey: '',
      agentCount: 3
    }])
  }

  const removeModelConfig = (id: string) => {
    if (modelConfigs.length > 1) {
      setModelConfigs(modelConfigs.filter(c => c.id !== id))
    }
  }

  const updateModelConfig = (id: string, updates: Partial<ModelConfigItem>) => {
    setModelConfigs(modelConfigs.map(c => c.id === id ? { ...c, ...updates } : c))
  }

  // Validation for each step
  const canProceed = () => {
    switch (currentStep) {
      case 1: // Source step - need name and repository
        return formData.name.trim() !== '' && 
               (formData.sourceType !== 'github' || formData.repository.trim() !== '')
      case 2: // Agents step - need at least one model with API key and agents
        return modelConfigs.every(c => c.apiKey.trim() !== '' && c.agentCount > 0)
      case 3: // Benchmarks step - no required fields
        return true
      default:
        return true
    }
  }

  const handleNext = () => {
    if (currentStep < 4 && canProceed()) setCurrentStep(currentStep + 1)
  }

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1)
  }

  const handleCreate = async () => {
    setIsCreating(true)
    setError(null)

    // Map model selection to provider/model_name (using actual Anthropic API model names)
    const modelMapping: Record<string, { provider: string; model_name: string }> = {
      'claude-opus-4.5': { provider: 'anthropic', model_name: 'claude-opus-4-20250514' },
      'claude-sonnet-4.5': { provider: 'anthropic', model_name: 'claude-sonnet-4-5-20250514' },
      'claude-haiku-4.5': { provider: 'anthropic', model_name: 'claude-haiku-4-20250514' },
      'gpt-5.2-codex': { provider: 'openai', model_name: 'gpt-5.2-codex' },
      'gpt-5.2': { provider: 'openai', model_name: 'gpt-5.2' },
      'gemini-3-flash-preview': { provider: 'google', model_name: 'gemini-3-flash-preview' },
      'gemini-3-pro-preview': { provider: 'google', model_name: 'gemini-3-pro-preview' }
    }

    // Build models array from all configurations
    const models = modelConfigs.map(config => {
      const mapping = modelMapping[config.model] || modelMapping['claude-sonnet-4.5']
      return {
        provider: mapping.provider,
        model_name: mapping.model_name,
        api_key: config.apiKey,
        instances: config.agentCount
      }
    })

    try {
      // Use store method instead of direct fetch
      const result = await startWorkflow({
        repo_url: formData.repository,
        branch: formData.branch || 'main',
        total_cost_limit: formData.maxCost,
        user_prompt: formData.description || `Optimize ${formData.name}`,
        models,
        parallel: formData.parallelAgents,
        generations: formData.generations,
        early_stop: false,  // Wait for all agents to complete and pick the best
      })

      if (!result) {
        throw new Error('Failed to start workflow')
      }

      // Connect WebSocket for real-time updates
      connectWorkflowWs(result.workflow_id)

      // Navigate to the evolution monitor for this workflow
      navigate(`/projects/${result.workflow_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create project')
      setIsCreating(false)
    }
  }

  return (
    <div className="min-h-screen">
      <Header title="Create New Project" />

      <div className="p-6">
        <div className="max-w-3xl mx-auto">
          {/* Progress Steps */}
          <div className="flex items-center justify-between mb-8">
            {steps.map((step, index) => (
              <div key={step.id} className="flex items-center">
                <div className={`flex items-center gap-3 ${
                  step.id === currentStep ? 'text-primary-500' :
                  step.id < currentStep ? 'text-success-solid' :
                  'text-slate-400'
                }`}>
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center border-2 ${
                    step.id === currentStep ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20' :
                    step.id < currentStep ? 'border-success-solid bg-success-bg dark:bg-success-bg-dark' :
                    'border-slate-300 dark:border-slate-600'
                  }`}>
                    {step.id < currentStep ? (
                      <FontAwesomeIcon icon={faCheck} />
                    ) : (
                      <FontAwesomeIcon icon={step.icon} />
                    )}
                  </div>
                  <span className="font-medium hidden sm:block">{step.title}</span>
                </div>
                {index < steps.length - 1 && (
                  <div className={`w-16 h-0.5 mx-4 ${
                    step.id < currentStep ? 'bg-success-solid' : 'bg-slate-200 dark:bg-slate-700'
                  }`} />
                )}
              </div>
            ))}
          </div>

          {/* Step 1: Source */}
          {currentStep === 1 && (
            <Card>
              <CardHeader>
                <CardTitle>Project Source</CardTitle>
              </CardHeader>
              <div className="space-y-6">
                <Input
                  label="Project Name"
                  placeholder="My Evolution Project"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
                <Input
                  label="Description (optional)"
                  placeholder="Describe what you want to optimize..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                    Source Type
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: 'github', icon: faGithubBrand, title: 'GitHub', description: 'Import from repository' },
                      { id: 'upload', icon: faUpload, title: 'Upload', description: 'Upload a ZIP file', disabled: true },
                      { id: 'local', icon: faFolder, title: 'Local Path', description: 'From local filesystem', disabled: true }
                    ].map((option) => (
                      <button
                        key={option.id}
                        onClick={() => !option.disabled && setFormData({ ...formData, sourceType: option.id as typeof formData.sourceType })}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${
                          formData.sourceType === option.id
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : option.disabled
                            ? 'border-slate-200 dark:border-slate-700 opacity-50 cursor-not-allowed'
                            : 'border-slate-200 dark:border-slate-700 hover:border-primary-300'
                        }`}
                        disabled={option.disabled}
                      >
                        <FontAwesomeIcon icon={option.icon} className={`text-2xl mb-2 ${
                          formData.sourceType === option.id ? 'text-primary-500' : 'text-slate-400'
                        }`} />
                        <h4 className="font-medium text-slate-900 dark:text-white">{option.title}</h4>
                        <p className="text-xs text-slate-500">{option.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                {formData.sourceType === 'github' && (
                  <div className="grid grid-cols-3 gap-4">
                    <div className="col-span-2">
                      <Input
                        label="Repository URL"
                        placeholder="https://github.com/user/repo"
                        value={formData.repository}
                        onChange={(e) => setFormData({ ...formData, repository: e.target.value })}
                      />
                    </div>
                    <Select
                      label="Branch"
                      value={formData.branch}
                      onChange={(e) => setFormData({ ...formData, branch: e.target.value })}
                      options={[
                        { value: 'main', label: 'main' },
                        { value: 'master', label: 'master' },
                        { value: 'develop', label: 'develop' }
                      ]}
                    />
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Step 2: Agents */}
          {currentStep === 2 && (
            <Card>
              <CardHeader>
                <CardTitle>Agent Configuration</CardTitle>
              </CardHeader>
              <div className="space-y-6">
                {/* Total agents summary */}
                <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 flex items-center justify-between">
                  <div>
                    <p className="text-sm text-slate-500">Total Agents</p>
                    <p className="text-2xl font-bold text-slate-900 dark:text-white">{totalAgents}</p>
                  </div>
                  <div className="text-sm text-slate-500">
                    {modelConfigs.map((c, i) => (
                      <span key={c.id}>
                        {i > 0 && ' + '}
                        {c.agentCount}
                      </span>
                    ))}
                    {modelConfigs.length > 1 && ` = ${totalAgents}`}
                  </div>
                </div>

                {/* Model configurations */}
                <div className="space-y-4">
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300">
                    Model Configurations
                  </label>
                  
                  {modelConfigs.map((config, index) => (
                    <div key={config.id} className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium text-slate-600 dark:text-slate-400">
                          Model {index + 1}
                        </span>
                        {modelConfigs.length > 1 && (
                          <button
                            onClick={() => removeModelConfig(config.id)}
                            className="p-1.5 text-slate-400 hover:text-error-solid transition-colors"
                          >
                            <FontAwesomeIcon icon={faTrash} />
                          </button>
                        )}
                      </div>
                      
                      <div className="grid grid-cols-2 gap-4">
                        <Select
                          label="Model"
                          value={config.model}
                          onChange={(e) => updateModelConfig(config.id, { model: e.target.value })}
                          options={[
                            { value: 'claude-opus-4.5', label: 'Claude Opus 4.5' },
                            { value: 'claude-sonnet-4.5', label: 'Claude Sonnet 4.5' },
                            { value: 'claude-haiku-4.5', label: 'Claude Haiku 4.5' },
                            { value: 'gpt-5.2-codex', label: 'GPT-5.2 Codex' },
                            { value: 'gpt-5.2', label: 'GPT-5.2' },
                            { value: 'gemini-3-flash-preview', label: 'Gemini 3 Flash Preview' },
                            { value: 'gemini-3-pro-preview', label: 'Gemini 3 Pro Preview' }
                          ]}
                        />
                        <div>
                          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                            Agents
                          </label>
                          <input
                            type="number"
                            min={1}
                            max={20}
                            value={config.agentCount}
                            onChange={(e) => updateModelConfig(config.id, { agentCount: Math.max(1, parseInt(e.target.value) || 1) })}
                            className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                          />
                        </div>
                      </div>
                      
                      <Input
                        label="API Key"
                        type="password"
                        placeholder={`Enter ${config.model.startsWith('claude') ? 'Anthropic' : config.model.startsWith('gpt') ? 'OpenAI' : 'Google'} API key`}
                        value={config.apiKey}
                        onChange={(e) => updateModelConfig(config.id, { apiKey: e.target.value })}
                      />
                    </div>
                  ))}

                  <Button
                    variant="secondary"
                    icon={faPlus}
                    onClick={addModelConfig}
                    className="w-full"
                  >
                    Add Another Model
                  </Button>
                </div>

                <div>
                  <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
                    Mutation Strategy
                  </label>
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { id: 'conservative', title: 'Conservative', description: 'Small, safe changes. Lower risk.' },
                      { id: 'balanced', title: 'Balanced', description: 'Moderate improvements. Recommended.' },
                      { id: 'aggressive', title: 'Aggressive', description: 'Large refactors. Higher potential.' }
                    ].map((option) => (
                      <button
                        key={option.id}
                        onClick={() => setFormData({ ...formData, mutationRate: option.id as typeof formData.mutationRate })}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${
                          formData.mutationRate === option.id
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-primary-300'
                        }`}
                      >
                        <h4 className="font-medium text-slate-900 dark:text-white">{option.title}</h4>
                        <p className="text-xs text-slate-500 mt-1">{option.description}</p>
                      </button>
                    ))}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Parallel Agents
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={10}
                      value={formData.parallelAgents}
                      onChange={(e) => setFormData({ ...formData, parallelAgents: Math.max(1, parseInt(e.target.value) || 1) })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">Number of agents running at same time</p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
                      Generations
                    </label>
                    <input
                      type="number"
                      min={1}
                      max={20}
                      value={formData.generations}
                      onChange={(e) => setFormData({ ...formData, generations: Math.max(1, parseInt(e.target.value) || 1) })}
                      className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-primary-500"
                    />
                    <p className="text-xs text-slate-500 mt-1">Evolution cycles to run</p>
                  </div>
                </div>

                <Slider
                  label="Maximum Cost Limit"
                  value={formData.maxCost}
                  onChange={(value) => setFormData({ ...formData, maxCost: value })}
                  min={1}
                  max={100}
                  valuePrefix="$"
                />

                <div className="p-4 rounded-lg bg-info-bg dark:bg-info-bg-dark border border-info-border dark:border-info-border-dark">
                  <p className="text-sm text-info-text dark:text-info-text-dark">
                    <strong>Estimated Cost:</strong> ~$0.50-2.00 per generation with current settings. 
                    Total budget: ${formData.maxCost}
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Step 3: Benchmarks */}
          {currentStep === 3 && (
            <Card>
              <CardHeader>
                <CardTitle>Benchmark Configuration</CardTitle>
              </CardHeader>
              <div className="space-y-6">
                <Toggle
                  checked={formData.autoGenerateBenchmarks}
                  onChange={(checked) => setFormData({ ...formData, autoGenerateBenchmarks: checked })}
                  label="Auto-generate Benchmarks"
                  description="Let Optifiner analyze your code and create appropriate benchmarks automatically"
                />

                <Slider
                  label="Maximum Budget"
                  value={formData.maxCost}
                  onChange={(value) => setFormData({ ...formData, maxCost: value })}
                  min={1}
                  max={100}
                  valuePrefix="$"
                />

                <Slider
                  label="Benchmark Timeout"
                  value={formData.benchmarkTimeout}
                  onChange={(value) => setFormData({ ...formData, benchmarkTimeout: value })}
                  min={10}
                  max={120}
                  valueSuffix=" seconds"
                />

                {!formData.autoGenerateBenchmarks && (
                  <div className="p-4 rounded-lg border-2 border-dashed border-slate-300 dark:border-slate-600 text-center">
                    <FontAwesomeIcon icon={faUpload} className="text-2xl text-slate-400 mb-2" />
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      Drop your benchmark files here or click to upload
                    </p>
                    <p className="text-xs text-slate-400 mt-1">
                      Supports pytest, jest, go test, and custom scripts
                    </p>
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Step 4: Review */}
          {currentStep === 4 && (
            <Card>
              <CardHeader>
                <CardTitle>Review & Create</CardTitle>
              </CardHeader>
              <div className="space-y-6">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Project Name</p>
                    <p className="font-medium text-slate-900 dark:text-white">{formData.name || 'Untitled Project'}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Source</p>
                    <p className="font-medium text-slate-900 dark:text-white capitalize">{formData.sourceType}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 col-span-2">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-2">Models & Agents</p>
                    <div className="space-y-2">
                      {modelConfigs.map((config) => {
                        const modelLabels: Record<string, string> = {
                          'claude-opus-4.5': 'Claude Opus 4.5',
                          'claude-sonnet-4.5': 'Claude Sonnet 4.5',
                          'claude-haiku-4.5': 'Claude Haiku 4.5',
                          'gpt-5.2-codex': 'GPT-5.2 Codex',
                          'gpt-5.2': 'GPT-5.2',
                          'gemini-3-flash-preview': 'Gemini 3 Flash Preview',
                          'gemini-3-pro-preview': 'Gemini 3 Pro Preview'
                        }
                        return (
                          <div key={config.id} className="flex items-center justify-between text-sm">
                            <span className="text-slate-600 dark:text-slate-400">
                              {modelLabels[config.model] || config.model}
                            </span>
                            <span className="font-medium text-slate-900 dark:text-white">
                              {config.agentCount} agent{config.agentCount !== 1 ? 's' : ''}
                            </span>
                          </div>
                        )
                      })}
                      <div className="pt-2 border-t border-slate-200 dark:border-slate-700 flex items-center justify-between">
                        <span className="font-medium text-slate-700 dark:text-slate-300">Total</span>
                        <span className="font-bold text-slate-900 dark:text-white">{totalAgents} agents</span>
                      </div>
                    </div>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Mutation Strategy</p>
                    <p className="font-medium text-slate-900 dark:text-white capitalize">{formData.mutationRate}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Target Fitness</p>
                    <p className="font-medium text-slate-900 dark:text-white">{(formData.targetFitness * 100).toFixed(0)}%</p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Cost Limit</p>
                    <p className="font-medium text-slate-900 dark:text-white">${formData.maxCost}</p>
                  </div>
                </div>

                {error && (
                  <div className="p-4 rounded-lg bg-error-bg dark:bg-error-bg-dark border border-error-border dark:border-error-border-dark">
                    <p className="text-sm text-error-text dark:text-error-text-dark">
                      <strong>Error:</strong> {error}
                    </p>
                  </div>
                )}

                <div className="p-4 rounded-lg bg-success-bg dark:bg-success-bg-dark border border-success-border dark:border-success-border-dark">
                  <div className="flex items-center gap-2 mb-2">
                    <FontAwesomeIcon icon={faCheck} className="text-success-solid" />
                    <span className="font-medium text-success-text dark:text-success-text-dark">Ready to create</span>
                  </div>
                  <p className="text-sm text-success-text dark:text-success-text-dark">
                    Your project will be created and evolution will begin automatically. You can monitor progress in real-time from the Evolution Monitor.
                  </p>
                </div>
              </div>
            </Card>
          )}

          {/* Navigation */}
          <div className="flex items-center justify-between mt-6">
            <Button
              variant="ghost"
              icon={faArrowLeft}
              onClick={currentStep === 1 ? () => navigate('/projects') : handleBack}
            >
              {currentStep === 1 ? 'Cancel' : 'Back'}
            </Button>
            {currentStep < 4 ? (
              <Button 
                variant="primary" 
                icon={faArrowRight} 
                iconPosition="right" 
                onClick={handleNext}
                disabled={!canProceed()}
              >
                Continue
              </Button>
            ) : (
              <Button 
                variant="primary" 
                icon={faPlay} 
                onClick={handleCreate}
                loading={isCreating}
                disabled={!formData.repository || !modelConfigs.every(c => c.apiKey.trim() !== '')}
              >
                Create & Start Evolution
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
