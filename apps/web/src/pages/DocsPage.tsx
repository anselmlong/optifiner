import { useParams, useNavigate } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faArrowLeft, faExternalLinkAlt } from '@fortawesome/free-solid-svg-icons'
import { Header } from '../components/layout/Header'
import { Card } from '../components/ui/Card'
import { useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'

interface DocSection {
  id: string
  title: string
  description: string
}

// Mapping to in-app documentation files (docs/in-app/)
const docSections: DocSection[] = [
  { id: 'getting-started', title: 'Getting Started', description: 'Learn the basics and set up Optifiner' },
  { id: 'agent-configuration', title: 'Agent Configuration', description: 'Configure and deploy agents' },
  { id: 'understanding-fitness', title: 'Understanding Fitness', description: 'How fitness scores work' },
  { id: 'model-settings', title: 'Model Settings', description: 'Choose and configure LLM models' },
  { id: 'writing-benchmarks', title: 'Writing Benchmarks', description: 'Create effective benchmarks' },
  { id: 'best-practices', title: 'Best Practices', description: 'Tips for better evolution' },
  { id: 'first-evolution-project', title: 'Your First Evolution Project', description: 'Step-by-step tutorial for beginners' },
  { id: 'phylogenetic-tree', title: 'Understanding the Phylogenetic Tree', description: 'How to read the tree visualization' },
  { id: 'optimizing-agents', title: 'Optimizing Agent Performance', description: 'Advanced agent tuning' },
  { id: 'cost-management', title: 'Cost Management Strategies', description: 'Budget planning and optimization' }
]

// File mapping to in-app docs location
const getDocFileName = (docId: string): string => {
  const fileMap: Record<string, string> = {
    'getting-started': 'GETTING_STARTED.md',
    'agent-configuration': 'AGENT_CONFIGURATION.md',
    'understanding-fitness': 'UNDERSTANDING_FITNESS.md',
    'model-settings': 'MODEL_SETTINGS.md',
    'writing-benchmarks': 'WRITING_BENCHMARKS.md',
    'best-practices': 'BEST_PRACTICES.md',
    'first-evolution-project': 'FIRST_EVOLUTION_PROJECT.md',
    'phylogenetic-tree': 'PHYLOGENETIC_TREE.md',
    'optimizing-agents': 'OPTIMIZING_AGENTS.md',
    'cost-management': 'COST_MANAGEMENT.md'
  }
  return fileMap[docId] || 'INDEX.md'
}

export function DocsPage() {
  const { docId } = useParams<{ docId?: string }>()
  const navigate = useNavigate()

  // Overview page - show all available docs
  if (!docId) {
    return (
      <div className="min-h-screen">
        <Header title="Documentation" />
        <div className="p-6">
          <div className="max-w-5xl mx-auto">
            <div className="mb-8">
              <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-2">Documentation</h1>
              <p className="text-slate-600 dark:text-slate-400">Browse our documentation and tutorials</p>
            </div>

            {/* Quick Links Section */}
            <div className="mb-12">
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Quick References</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {docSections.slice(0, 6).map((section) => (
                  <button
                    key={section.id}
                    onClick={() => navigate(`/docs/${section.id}`)}
                    className="text-left p-6 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all hover:bg-slate-50 dark:hover:bg-slate-900/50"
                  >
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">{section.title}</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{section.description}</p>
                  </button>
                ))}
              </div>
            </div>

            {/* Tutorials Section */}
            <div>
              <h2 className="text-xl font-semibold text-slate-900 dark:text-white mb-4">Tutorials</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {docSections.slice(6).map((section) => (
                  <button
                    key={section.id}
                    onClick={() => navigate(`/docs/${section.id}`)}
                    className="text-left p-6 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all hover:bg-slate-50 dark:hover:bg-slate-900/50"
                  >
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-2">{section.title}</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">{section.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  // Individual doc page
  const doc = docSections.find((d) => d.id === docId)
  if (!doc) {
    return (
      <div className="min-h-screen">
        <Header title="Documentation" />
        <div className="p-6">
          <div className="max-w-4xl mx-auto">
            <button
              onClick={() => navigate('/docs')}
              className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium mb-6"
            >
              <FontAwesomeIcon icon={faArrowLeft} />
              Back to Documentation
            </button>
            <div className="text-center py-12">
              <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-4">Documentation not found</h2>
              <p className="text-slate-600 dark:text-slate-400 mb-6">The page you're looking for doesn't exist.</p>
              <button
                onClick={() => navigate('/docs')}
                className="px-6 py-2 rounded-lg bg-primary-600 hover:bg-primary-700 text-white font-medium transition-colors"
              >
                Go to Documentation
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return <DocPageContent doc={doc} docId={docId} navigate={navigate} />
}

function DocPageContent({ docId, navigate }: { doc: DocSection; docId: string; navigate: any }) {
  const [content, setContent] = useState<string>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fileName = getDocFileName(docId)

  useEffect(() => {
    const loadDocumentation = async () => {
      try {
        setLoading(true)
        const response = await fetch(`/docs/in-app/${fileName}`)
        if (!response.ok) {
          throw new Error(`Failed to load documentation: ${response.statusText}`)
        }
        const text = await response.text()
        setContent(text)
        setError(null)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load documentation')
        setContent('')
      } finally {
        setLoading(false)
      }
    }

    loadDocumentation()
  }, [docId, fileName])

  return (
    <div className="min-h-screen">
      <Header title="Documentation" />
      <div className="p-6">
        <div className="max-w-4xl mx-auto">
          <button
            onClick={() => navigate('/docs')}
            className="flex items-center gap-2 text-primary-600 hover:text-primary-700 font-medium mb-8"
          >
            <FontAwesomeIcon icon={faArrowLeft} />
            Back to Documentation
          </button>

          <Card className="p-8">
            <div className="prose dark:prose-invert max-w-none">
              {loading ? (
                <div className="text-center py-12">
                  <p className="text-slate-600 dark:text-slate-400">Loading documentation...</p>
                </div>
              ) : error ? (
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-900 rounded-lg p-6 mb-8">
                  <p className="text-red-900 dark:text-red-200">
                    <strong>⚠️ Error loading documentation</strong>
                    <br />
                    {error}
                  </p>
                </div>
              ) : (
                <ReactMarkdown
                  components={{
                    h1: ({ children }) => <h1 className="text-3xl font-bold text-slate-900 dark:text-white mb-4">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-3 mt-6">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2 mt-4">{children}</h3>,
                    p: ({ children }) => <p className="text-slate-700 dark:text-slate-300 mb-4 leading-relaxed">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc list-inside text-slate-700 dark:text-slate-300 mb-4 space-y-2">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal list-inside text-slate-700 dark:text-slate-300 mb-4 space-y-2">{children}</ol>,
                    li: ({ children }) => <li className="text-slate-700 dark:text-slate-300">{children}</li>,
                    code: ({ children }) => <code className="bg-slate-100 dark:bg-slate-800 px-2 py-1 rounded text-slate-900 dark:text-slate-100 font-mono text-sm">{children}</code>,
                    pre: ({ children }) => <pre className="bg-slate-900 dark:bg-slate-950 text-slate-100 p-4 rounded-lg overflow-x-auto mb-4">{children}</pre>,
                    blockquote: ({ children }) => <blockquote className="border-l-4 border-primary-500 pl-4 italic text-slate-700 dark:text-slate-300 mb-4">{children}</blockquote>,
                    a: ({ href, children }) => <a href={href} className="text-primary-600 dark:text-primary-400 hover:underline" target="_blank" rel="noopener noreferrer">{children}</a>,
                    hr: () => <hr className="my-6 border-slate-200 dark:border-slate-700" />,
                    table: ({ children }) => <table className="w-full border-collapse mb-4">{children}</table>,
                    thead: ({ children }) => <thead className="bg-slate-100 dark:bg-slate-800">{children}</thead>,
                    tbody: ({ children }) => <tbody>{children}</tbody>,
                    tr: ({ children }) => <tr className="border-b border-slate-200 dark:border-slate-700">{children}</tr>,
                    th: ({ children }) => <th className="border border-slate-200 dark:border-slate-700 px-3 py-2 text-left text-slate-900 dark:text-white font-semibold">{children}</th>,
                    td: ({ children }) => <td className="border border-slate-200 dark:border-slate-700 px-3 py-2 text-slate-700 dark:text-slate-300">{children}</td>,
                  }}
                >
                  {content}
                </ReactMarkdown>
              )}
            </div>
          </Card>

          <div className="mt-8 flex justify-start">
            <button
              onClick={() => navigate('/docs')}
              className="px-6 py-2 rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-900 transition-colors text-slate-700 dark:text-slate-300 font-medium"
            >
              All Documentation
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
