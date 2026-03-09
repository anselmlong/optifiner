import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import { LandingButton } from '@/components/ui/Button'


const Header = () => {
  return (
    <motion.header
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="fixed top-0 left-0 right-0 z-50 border-b border-border/50 bg-background/80 backdrop-blur-xl"
    >
      <div className="container mx-auto px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <img src="/optifiner-logo.png" alt="Optifiner" className="h-10 w-10 rounded-lg" />
          <span className="text-xl font-bold tracking-tight">Optifiner</span>
        </div>

        <nav className="hidden md:flex items-center gap-8">
          <a href="#demo" className="text-muted-foreground hover:text-foreground transition-colors">
            Demo
          </a>
          <a href="#features" className="text-muted-foreground hover:text-foreground transition-colors">
            Features
          </a>
          <a
            href="https://github.com/anselmlong/optifiner"
            target="_blank"
            rel="noopener noreferrer"
            className="text-muted-foreground hover:text-foreground transition-colors"
          >
            GitHub
          </a>
        </nav>

        <div className="flex items-center gap-4">
          <Link to="/dashboard">
            <LandingButton variant="hero" size="sm">
              Launch Dashboard
            </LandingButton>
          </Link>
        </div>
      </div>
    </motion.header>
  )
}

export default Header
