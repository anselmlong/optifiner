import { Github } from 'lucide-react'

const Footer = () => {
  return (
    <footer className="border-t border-border py-12">
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-6">
          <div className="flex items-center gap-3">
            <img src="/optifiner-logo.png" alt="Optifiner" className="h-8 w-8 rounded-lg" />
            <span className="font-bold">Optifiner</span>
          </div>

          <div className="flex items-center gap-6">
            <a
              href="https://github.com/anselmlong/optifiner"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors text-sm"
            >
              <Github className="h-4 w-4" />
              GitHub
            </a>
            <a
              href="https://devpost.com/software/optifiner"
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground transition-colors text-sm"
            >
              Devpost
            </a>
          </div>

          <p className="text-sm text-muted-foreground">
            © {new Date().getFullYear()} Optifiner. MIT License.
          </p>
        </div>
      </div>
    </footer>
  )
}

export default Footer
