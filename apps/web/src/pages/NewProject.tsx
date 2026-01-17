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
  faPlay
} from '@fortawesome/free-solid-svg-icons'
import { faGithub as faGithubBrand } from '@fortawesome/free-brands-svg-icons'
import { Header } from '../components/layout/Header'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Button } from '../components/ui/Button'
import { Input } from '../components/ui/Input'
import { Select } from '../components/ui/Select'
import { Toggle } from '../components/ui/Toggle'
import { Slider } from '../components/ui/Slider'

const steps = [
  { id: 1, title: 'Source', icon: faCode },
  { id: 2, title: 'Agents', icon: faRobot },
  { id: 3, title: 'Benchmarks', icon: faFlask },
  { id: 4, title: 'Review', icon: faCheck }
]

export function NewProject() {
  const navigate = useNavigate()
  const [currentStep, setCurrentStep] = useState(1)
  const [formData, setFormData] = useState({
    name: '',
    description: '',
    sourceType: 'github' as 'github' | 'upload' | 'local',
    repository: '',
    branch: 'main',
    agentCount: 5,
    model: 'claude-sonnet',
    mutationRate: 'balanced' as 'conservative' | 'balanced' | 'aggressive',
    targetFitness: 0.9,
    autoGenerateBenchmarks: true,
    benchmarkTimeout: 30
  })

  const handleNext = () => {
    if (currentStep < 4) setCurrentStep(currentStep + 1)
  }

  const handleBack = () => {
    if (currentStep > 1) setCurrentStep(currentStep - 1)
  }

  const handleCreate = () => {
    // Create project logic would go here
    navigate('/projects')
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
                      { id: 'upload', icon: faUpload, title: 'Upload', description: 'Upload a ZIP file' },
                      { id: 'local', icon: faFolder, title: 'Local Path', description: 'From local filesystem' }
                    ].map((option) => (
                      <button
                        key={option.id}
                        onClick={() => setFormData({ ...formData, sourceType: option.id as typeof formData.sourceType })}
                        className={`p-4 rounded-xl border-2 text-left transition-all ${
                          formData.sourceType === option.id
                            ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                            : 'border-slate-200 dark:border-slate-700 hover:border-primary-300'
                        }`}
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
                <Select
                  label="Primary Model"
                  value={formData.model}
                  onChange={(e) => setFormData({ ...formData, model: e.target.value })}
                  options={[
                    { value: 'claude-sonnet', label: 'Claude Sonnet 4.5 (Recommended)' },
                    { value: 'gpt-4o', label: 'GPT-4o' },
                    { value: 'deepseek-coder', label: 'DeepSeek Coder (Budget)' }
                  ]}
                />

                <Slider
                  label="Agent Pool Size"
                  value={formData.agentCount}
                  onChange={(value) => setFormData({ ...formData, agentCount: value })}
                  min={1}
                  max={20}
                  valueSuffix=" agents"
                />

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

                <div className="p-4 rounded-lg bg-info-bg dark:bg-info-bg-dark border border-info-border dark:border-info-border-dark">
                  <p className="text-sm text-info-text dark:text-info-text-dark">
                    <strong>Estimated Cost:</strong> ~$0.50-2.00 per generation with current settings
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
                  label="Target Fitness Score"
                  value={formData.targetFitness * 100}
                  onChange={(value) => setFormData({ ...formData, targetFitness: value / 100 })}
                  min={50}
                  max={100}
                  valueSuffix="%"
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
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Model</p>
                    <p className="font-medium text-slate-900 dark:text-white">
                      {formData.model === 'claude-sonnet' ? 'Claude Sonnet 4.5' :
                       formData.model === 'gpt-4o' ? 'GPT-4o' : 'DeepSeek Coder'}
                    </p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Agent Pool</p>
                    <p className="font-medium text-slate-900 dark:text-white">{formData.agentCount} agents</p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Mutation Strategy</p>
                    <p className="font-medium text-slate-900 dark:text-white capitalize">{formData.mutationRate}</p>
                  </div>
                  <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <p className="text-xs text-slate-500 uppercase tracking-wider mb-1">Target Fitness</p>
                    <p className="font-medium text-slate-900 dark:text-white">{(formData.targetFitness * 100).toFixed(0)}%</p>
                  </div>
                </div>

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
              <Button variant="primary" icon={faArrowRight} iconPosition="right" onClick={handleNext}>
                Continue
              </Button>
            ) : (
              <Button variant="primary" icon={faPlay} onClick={handleCreate}>
                Create & Start Evolution
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
