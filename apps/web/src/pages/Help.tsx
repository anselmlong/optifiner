import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import {
  faQuestionCircle,
  faRocket,
  faLightbulb,
  faCode,
  faRobot,
  faChartLine,
  faCog,
  faExternalLinkAlt,
  faSearch,
  faPlayCircle,
  faFileAlt,
  faComments
} from '@fortawesome/free-solid-svg-icons'
import { faGithub, faDiscord } from '@fortawesome/free-brands-svg-icons'
import { Header } from '../components/layout/Header'
import { Card, CardHeader, CardTitle } from '../components/ui/Card'
import { Input } from '../components/ui/Input'

const quickLinks = [
  { icon: faRocket, title: 'Getting Started', description: 'Learn the basics of Optifiner', href: '#' },
  { icon: faRobot, title: 'Agent Configuration', description: 'Configure and deploy agents', href: '#' },
  { icon: faChartLine, title: 'Understanding Fitness', description: 'How fitness scores work', href: '#' },
  { icon: faCog, title: 'Model Settings', description: 'Choose and configure LLM models', href: '#' },
  { icon: faCode, title: 'Writing Benchmarks', description: 'Create effective benchmarks', href: '#' },
  { icon: faLightbulb, title: 'Best Practices', description: 'Tips for better evolution', href: '#' }
]

const tutorials = [
  { icon: faPlayCircle, title: 'Your First Evolution Project', duration: '5 min', href: '#' },
  { icon: faPlayCircle, title: 'Understanding the Phylogenetic Tree', duration: '8 min', href: '#' },
  { icon: faPlayCircle, title: 'Optimizing Agent Performance', duration: '12 min', href: '#' },
  { icon: faPlayCircle, title: 'Cost Management Strategies', duration: '6 min', href: '#' }
]

const faqs = [
  {
    question: 'How does the Darwinian evolution process work?',
    answer: 'Optifiner spawns multiple AI agents that propose code improvements in parallel. Each mutation is tested against your benchmarks, and only changes that improve the fitness score are committed. This mimics natural selection, where the "fittest" code survives.'
  },
  {
    question: 'What models are supported?',
    answer: 'We currently support Claude Sonnet 4.5 (recommended for quality), GPT-4o (fast and reliable), and DeepSeek Coder (cost-effective for exploration). You can switch between models or use different models for different agent types.'
  },
  {
    question: 'How are fitness scores calculated?',
    answer: 'Fitness is a composite score based on your benchmarks. By default, it weights correctness (70%), latency (20%), and memory usage (10%). You can customize these weights in your project settings.'
  },
  {
    question: 'Is my code safe during evolution?',
    answer: 'Yes! All code mutations run in isolated Docker containers with resource limits. Only mutations that pass all existing tests can be merged. You can also enable manual review for significant changes.'
  },
  {
    question: 'How do I control costs?',
    answer: 'Set monthly cost limits in Settings. Use DeepSeek for exploration phases and Claude/GPT for refinement. Monitor the cost breakdown in Analytics to identify optimization opportunities.'
  }
]

export function Help() {
  return (
    <div className="min-h-screen">
      <Header title="Help & Documentation" />

      <div className="p-6">
        <div className="max-w-5xl mx-auto space-y-8">
          {/* Search */}
          <div className="text-center">
            <h2 className="text-2xl font-bold text-slate-900 dark:text-white mb-2">How can we help?</h2>
            <p className="text-slate-600 dark:text-slate-400 mb-6">Search our documentation or browse topics below</p>
          </div>

          {/* Quick Links */}
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">Quick Links</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {quickLinks.map((link) => (
                <a
                  key={link.title}
                  href={link.href}
                  className="p-4 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-primary-300 dark:hover:border-primary-700 hover:shadow-md transition-all group"
                >
                  <div className="w-10 h-10 rounded-lg bg-primary-100 dark:bg-primary-900/30 flex items-center justify-center mb-3 group-hover:bg-primary-200 dark:group-hover:bg-primary-900/50 transition-colors">
                    <FontAwesomeIcon icon={link.icon} className="text-primary-500" />
                  </div>
                  <h4 className="font-medium text-slate-900 dark:text-white mb-1">{link.title}</h4>
                  <p className="text-sm text-slate-500">{link.description}</p>
                </a>
              ))}
            </div>
          </div>

          {/* Video Tutorials */}
          <Card>
            <CardHeader>
              <CardTitle>Video Tutorials</CardTitle>
            </CardHeader>
            <div className="grid grid-cols-2 gap-4">
              {tutorials.map((tutorial) => (
                <a
                  key={tutorial.title}
                  href={tutorial.href}
                  className="flex items-center gap-4 p-3 rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group"
                >
                  <div className="w-16 h-12 rounded-lg bg-slate-200 dark:bg-slate-700 flex items-center justify-center group-hover:bg-primary-100 dark:group-hover:bg-primary-900/30 transition-colors">
                    <FontAwesomeIcon icon={tutorial.icon} className="text-slate-400 group-hover:text-primary-500 text-xl transition-colors" />
                  </div>
                  <div>
                    <h4 className="font-medium text-slate-900 dark:text-white">{tutorial.title}</h4>
                    <p className="text-sm text-slate-500">{tutorial.duration}</p>
                  </div>
                </a>
              ))}
            </div>
          </Card>

          {/* FAQs */}
          <Card>
            <CardHeader>
              <CardTitle>Frequently Asked Questions</CardTitle>
            </CardHeader>
            <div className="space-y-4">
              {faqs.map((faq, index) => (
                <div
                  key={index}
                  className="pb-4 border-b border-slate-100 dark:border-slate-700/50 last:border-0 last:pb-0"
                >
                  <h4 className="font-medium text-slate-900 dark:text-white mb-2 flex items-start gap-2">
                    <FontAwesomeIcon icon={faQuestionCircle} className="text-primary-500 mt-1 flex-shrink-0" />
                    {faq.question}
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400 ml-6">{faq.answer}</p>
                </div>
              ))}
            </div>
          </Card>

          {/* Resources */}
          <div className="grid grid-cols-3 gap-4">
            <Card className="text-center py-6 hover:border-primary-300 dark:hover:border-primary-700 transition-colors cursor-pointer">
              <FontAwesomeIcon icon={faFileAlt} className="text-3xl text-primary-500 mb-3" />
              <h4 className="font-medium text-slate-900 dark:text-white mb-1">API Documentation</h4>
              <p className="text-sm text-slate-500">Full API reference</p>
            </Card>
            <a href="https://github.com" className="block">
              <Card className="text-center py-6 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
                <FontAwesomeIcon icon={faGithub} className="text-3xl text-slate-700 dark:text-slate-300 mb-3" />
                <h4 className="font-medium text-slate-900 dark:text-white mb-1">GitHub Repository</h4>
                <p className="text-sm text-slate-500">View source code</p>
              </Card>
            </a>
            <a href="https://discord.com" className="block">
              <Card className="text-center py-6 hover:border-primary-300 dark:hover:border-primary-700 transition-colors">
                <FontAwesomeIcon icon={faDiscord} className="text-3xl text-[#5865F2] mb-3" />
                <h4 className="font-medium text-slate-900 dark:text-white mb-1">Discord Community</h4>
                <p className="text-sm text-slate-500">Get help from the community</p>
              </Card>
            </a>
          </div>

          {/* Contact Support */}
          <Card className="bg-gradient-to-r from-primary-500 to-primary-600 border-0">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-xl font-bold text-white mb-2">Need more help?</h3>
                <p className="text-primary-100">Our support team is here to help you get the most out of Optifiner.</p>
              </div>
              <a
                href="mailto:support@optifiner.dev"
                className="px-6 py-3 bg-white text-primary-600 font-medium rounded-lg hover:bg-primary-50 transition-colors flex items-center gap-2"
              >
                <FontAwesomeIcon icon={faComments} />
                Contact Support
              </a>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
