import { motion } from 'framer-motion'
import { Dna, Bot, Zap, GitBranch, Target, Shield } from 'lucide-react'

const features = [
  {
    icon: Dna,
    title: 'Darwinian Evolution',
    description:
      'Code variations compete and evolve through natural selection, keeping only the fittest optimizations.',
  },
  {
    icon: Bot,
    title: 'Multi-Agent System',
    description:
      'Specialized AI agents collaborate to analyze, mutate, and test code improvements in parallel.',
  },
  {
    icon: Zap,
    title: 'Autonomous Optimization',
    description:
      'Set it and forget it. Optifiner continuously improves your codebase without manual intervention.',
  },
  {
    icon: GitBranch,
    title: 'Git Integration',
    description:
      'Seamlessly integrates with your existing workflow. Optimizations are proposed as pull requests.',
  },
  {
    icon: Target,
    title: 'Performance Metrics',
    description:
      'Track improvements with detailed benchmarks. Every optimization is measured and validated.',
  },
  {
    icon: Shield,
    title: 'Safe Mutations',
    description:
      'Comprehensive testing ensures no regressions. Only verified improvements make it through.',
  },
]

const FeaturesSection = () => {
  return (
    <section id="features" className="py-32 relative">
      {/* Background accent */}
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary/5 to-transparent" />

      <div className="container mx-auto px-6 relative">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-20"
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            Built for the <span className="text-gradient">future</span>
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Leveraging evolutionary algorithms and multi-agent AI to revolutionize code optimization
          </p>
        </motion.div>

        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((feature, index) => (
            <motion.div
              key={feature.title}
              initial={{ opacity: 0, y: 40 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.6, delay: index * 0.1 }}
              whileHover={{ y: -4, transition: { duration: 0.2 } }}
              className="group relative p-8 rounded-2xl border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-all duration-300"
            >
              {/* Icon */}
              <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center mb-6 group-hover:bg-primary/20 transition-colors duration-300">
                <feature.icon className="h-7 w-7 text-primary" />
              </div>

              {/* Content */}
              <h3 className="text-xl font-bold mb-3">{feature.title}</h3>
              <p className="text-muted-foreground leading-relaxed">{feature.description}</p>

              {/* Hover glow */}
              <div className="absolute inset-0 rounded-2xl opacity-0 group-hover:opacity-100 transition-opacity duration-300 -z-10 blur-xl bg-primary/10" />
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}

export default FeaturesSection
