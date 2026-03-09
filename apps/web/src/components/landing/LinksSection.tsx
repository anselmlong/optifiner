import { motion } from 'framer-motion'
import { ExternalLink, Github } from 'lucide-react'

const LinksSection = () => {
  return (
    <section className="py-24 relative">
      <div className="container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="flex flex-col md:flex-row items-center justify-center gap-6"
        >
          <a
            href="https://github.com/anselmlong/optifiner"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full md:w-auto"
          >
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-4 p-6 rounded-2xl border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-all duration-300 cursor-pointer"
            >
              <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center">
                <Github className="h-7 w-7 text-primary" />
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold">GitHub</h3>
                <p className="text-sm text-muted-foreground">View source code</p>
              </div>
              <ExternalLink className="h-5 w-5 text-muted-foreground" />
            </motion.div>
          </a>

          <a
            href="https://devpost.com/software/optifiner"
            target="_blank"
            rel="noopener noreferrer"
            className="w-full md:w-auto"
          >
            <motion.div
              whileHover={{ scale: 1.02 }}
              className="flex items-center gap-4 p-6 rounded-2xl border border-border bg-card/50 backdrop-blur-sm hover:border-primary/50 transition-all duration-300 cursor-pointer"
            >
              <div className="w-14 h-14 rounded-xl bg-primary/10 flex items-center justify-center">
                <span className="text-2xl font-bold text-primary">D</span>
              </div>
              <div className="flex-1">
                <h3 className="text-lg font-bold">Devpost</h3>
                <p className="text-sm text-muted-foreground">See project details</p>
              </div>
              <ExternalLink className="h-5 w-5 text-muted-foreground" />
            </motion.div>
          </a>
        </motion.div>
      </div>
    </section>
  )
}

export default LinksSection
