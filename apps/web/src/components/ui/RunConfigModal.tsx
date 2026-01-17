import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { 
  faPlay, 
  faPlus, 
  faTrash, 
  faDollarSign,
  faRobot,
  faKey
} from '@fortawesome/free-solid-svg-icons'
import { Modal } from './Modal'
import { Button } from './Button'
import { Input } from './Input'
import { Select } from './Select'

interface ModelConfig {
  id: string
  provider: string
  modelName: string
  apiKey: string
  instances: number
}

interface RunConfigModalProps {
  isOpen: boolean
  onClose: () => void
  onStart: (config: { models: ModelConfig[]; maxCost: number; userPrompt: string }) => void
  projectName?: string
}

const MODEL_OPTIONS = [
  { provider: 'anthropic', models: ['claude-sonnet-4-20250514', 'claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'] },
  { provider: 'openai', models: ['gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo'] },
  { provider: 'google', models: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'] },
  { provider: 'deepseek', models: ['deepseek-chat', 'deepseek-coder'] },
]

const PROVIDER_OPTIONS = MODEL_OPTIONS.map(p => ({ value: p.provider, label: p.provider.charAt(0).toUpperCase() + p.provider.slice(1) }))

export function RunConfigModal({ isOpen, onClose, onStart, projectName }: RunConfigModalProps) {
  const [models, setModels] = useState<ModelConfig[]>([
    { id: '1', provider: 'anthropic', modelName: 'claude-sonnet-4-20250514', apiKey: '', instances: 1 }
  ])
  const [maxCost, setMaxCost] = useState<number>(10)
  const [userPrompt, setUserPrompt] = useState<string>('Optimize the code for better performance while maintaining correctness.')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const addModel = () => {
    const newId = (Math.max(0, ...models.map(m => parseInt(m.id))) + 1).toString()
    setModels([...models, { 
      id: newId, 
      provider: 'anthropic', 
      modelName: 'claude-sonnet-4-20250514', 
      apiKey: '', 
      instances: 1 
    }])
  }

  const removeModel = (id: string) => {
    if (models.length > 1) {
      setModels(models.filter(m => m.id !== id))
    }
  }

  const updateModel = (id: string, field: keyof ModelConfig, value: string | number) => {
    setModels(models.map(m => {
      if (m.id !== id) return m
      
      // If changing provider, reset modelName to first model of that provider
      if (field === 'provider') {
        const providerModels = MODEL_OPTIONS.find(p => p.provider === value)?.models || []
        return { ...m, provider: value as string, modelName: providerModels[0] || '' }
      }
      
      return { ...m, [field]: value }
    }))
  }

  const getModelsForProvider = (provider: string) => {
    return MODEL_OPTIONS.find(p => p.provider === provider)?.models.map(m => ({ value: m, label: m })) || []
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}
    
    models.forEach((model) => {
      if (!model.apiKey.trim()) {
        newErrors[`apiKey-${model.id}`] = 'API key is required'
      }
      if (model.instances < 1) {
        newErrors[`instances-${model.id}`] = 'At least 1 instance required'
      }
    })

    if (maxCost <= 0) {
      newErrors['maxCost'] = 'Cost limit must be greater than 0'
    }

    if (!userPrompt.trim()) {
      newErrors['userPrompt'] = 'Optimization goal is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleStart = () => {
    if (validate()) {
      onStart({ models, maxCost, userPrompt })
    }
  }

  const totalInstances = models.reduce((sum, m) => sum + m.instances, 0)

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Configure Optimization Run" size="lg">
      <div className="space-y-6">
        {/* Project Info */}
        {projectName && (
          <div className="p-3 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700">
            <p className="text-sm text-slate-500">Running optimization for:</p>
            <p className="font-semibold text-slate-900 dark:text-white">{projectName}</p>
          </div>
        )}

        {/* Optimization Goal */}
        <div>
          <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">
            Optimization Goal
          </label>
          <textarea
            value={userPrompt}
            onChange={(e) => setUserPrompt(e.target.value)}
            placeholder="Describe what you want to optimize..."
            rows={2}
            className={`
              w-full px-3 py-2.5 text-sm
              bg-white dark:bg-slate-800
              border border-slate-200 dark:border-slate-700 rounded-lg
              text-slate-900 dark:text-slate-100
              placeholder:text-slate-400 dark:placeholder:text-slate-500
              focus:outline-none focus:ring-2 focus:ring-primary-500/20 focus:border-primary-500
              resize-none
              ${errors['userPrompt'] ? 'border-error-solid' : ''}
            `}
          />
          {errors['userPrompt'] && (
            <p className="mt-1 text-xs text-error-solid">{errors['userPrompt']}</p>
          )}
        </div>

        {/* Models Section */}
        <div>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <FontAwesomeIcon icon={faRobot} className="text-primary-500" />
              <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Models ({models.length})
              </span>
              <span className="text-xs text-slate-500">
                • {totalInstances} total instance{totalInstances !== 1 ? 's' : ''}
              </span>
            </div>
            <Button variant="ghost" size="sm" icon={faPlus} onClick={addModel}>
              Add Model
            </Button>
          </div>

          <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
            {models.map((model, index) => (
              <div 
                key={model.id} 
                className="p-4 bg-slate-50 dark:bg-slate-900 rounded-lg border border-slate-200 dark:border-slate-700 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
                    Model {index + 1}
                  </span>
                  {models.length > 1 && (
                    <button
                      onClick={() => removeModel(model.id)}
                      className="p-1 text-slate-400 hover:text-error-solid transition-colors"
                    >
                      <FontAwesomeIcon icon={faTrash} className="text-xs" />
                    </button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <Select
                    label="Provider"
                    value={model.provider}
                    onChange={(e) => updateModel(model.id, 'provider', e.target.value)}
                    options={PROVIDER_OPTIONS}
                  />
                  <Select
                    label="Model"
                    value={model.modelName}
                    onChange={(e) => updateModel(model.id, 'modelName', e.target.value)}
                    options={getModelsForProvider(model.provider)}
                  />
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <Input
                      label="API Key"
                      type="password"
                      icon={faKey}
                      value={model.apiKey}
                      onChange={(e) => updateModel(model.id, 'apiKey', e.target.value)}
                      placeholder="sk-..."
                      error={errors[`apiKey-${model.id}`]}
                    />
                  </div>
                  <Input
                    label="Instances"
                    type="number"
                    min={1}
                    max={10}
                    value={model.instances}
                    onChange={(e) => updateModel(model.id, 'instances', parseInt(e.target.value) || 1)}
                    error={errors[`instances-${model.id}`]}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Cost Limit */}
        <div>
          <div className="flex items-center gap-2 mb-1.5">
            <FontAwesomeIcon icon={faDollarSign} className="text-primary-500" />
            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Maximum Cost Limit
            </label>
          </div>
          <div className="flex items-center gap-3">
            <Input
              type="number"
              min={0.01}
              step={0.01}
              value={maxCost}
              onChange={(e) => setMaxCost(parseFloat(e.target.value) || 0)}
              className="flex-1"
              error={errors['maxCost']}
            />
            <span className="text-sm text-slate-500">USD</span>
          </div>
          <p className="mt-1.5 text-xs text-slate-500">
            The optimization will automatically stop when this cost limit is reached.
          </p>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" icon={faPlay} onClick={handleStart}>
            Start Optimization
          </Button>
        </div>
      </div>
    </Modal>
  )
}
