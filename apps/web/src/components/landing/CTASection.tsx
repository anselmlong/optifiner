import { motion } from 'framer-motion'
import { ArrowRight, Github, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { LandingButton } from '@/components/ui/Button'


const CTASection = () => {
  return (
    <section id="get-started" className="py-32 relative">
      {/* Background effects */}
      <div className="absolute inset-0 grid-pattern opacity-20" />
      <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-background" />

      <div className="container mx-auto px-6 relative">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="max-w-3xl mx-auto text-center"
        >
          {/* Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-primary/30 bg-primary/5 mb-8">
            <Sparkles className="h-4 w-4 text-primary" />
            <span className="text-sm font-medium text-primary">Open Source</span>
          </div>

          <h2 className="text-4xl md:text-6xl font-bold mb-6">
            Ready to <span className="text-gradient">evolve</span>?
          </h2>

          <p className="text-xl text-muted-foreground mb-12 leading-relaxed">
            Open source and free to use. Launch the dashboard to start evolving your codebase, or
            explore the source code on GitHub.
          </p>

          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.98 }}>
              <Link to="/dashboard">
                <LandingButton variant="hero" size="xl" className="text-lg px-12">
                  Launch Dashboard
                  <ArrowRight className="h-5 w-5" />
                </LandingButton>
              </Link>
            </motion.div>

            <a
              href="https://github.com/anselmlong/optifiner"
              target="_blank"
              rel="noopener noreferrer"
            >
              <LandingButton variant="heroOutline" size="xl">
                <Github className="h-5 w-5" />
                View on GitHub
              </LandingButton>
            </a>
          </div>
        </motion.div>
      </div>
    </section>
  )
}

export default CTASection
