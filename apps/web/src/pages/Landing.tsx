import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faGithub } from '@fortawesome/free-brands-svg-icons'

export const Landing = () => {
  const [isVisible, setIsVisible] = useState({
    hero: false,
    section1: false,
    section2: false,
    cta: false,
  })
  const observerRefs = {
    hero: useRef<HTMLDivElement>(null),
    section1: useRef<HTMLDivElement>(null),
    section2: useRef<HTMLDivElement>(null),
    cta: useRef<HTMLDivElement>(null),
  }

  useEffect(() => {
    // Set hero to visible immediately
    setIsVisible((prev) => ({ ...prev, hero: true }))

    // Set up intersection observer for scroll animations
    const observerOptions = {
      threshold: 0.3,
      rootMargin: '0px 0px -100px 0px',
    }

    const observerCallback = (entries: IntersectionObserverEntry[]) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          const element = entry.target as HTMLElement
          const sectionKey = element.id as keyof typeof isVisible
          setIsVisible((prev) => ({ ...prev, [sectionKey]: true }))
        }
      })
    }

    const observer = new IntersectionObserver(observerCallback, observerOptions)

    Object.values(observerRefs).forEach((ref) => {
      if (ref.current) {
        observer.observe(ref.current)
      }
    })

    return () => observer.disconnect()
  }, [])

  return (
    <div className="min-h-screen bg-black text-green-500 font-mono overflow-hidden scroll-smooth">
      {/* Global Styles */}
      <style>{`
        @keyframes blink-cursor {
          0%, 49% { opacity: 1; }
          50%, 100% { opacity: 0; }
        }

        @keyframes fade-in-up {
          from {
            opacity: 0;
            transform: translateY(30px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }

        @keyframes glow-pulse {
          0%, 100% {
            text-shadow: 0 0 10px rgba(34, 197, 94, 0.5);
          }
          50% {
            text-shadow: 0 0 20px rgba(34, 197, 94, 0.8);
          }
        }

        .cursor {
          animation: blink-cursor 1s infinite;
        }

        .fade-in-up {
          animation: fade-in-up 0.8s ease-out forwards;
        }

        .glow-text {
          animation: glow-pulse 2s ease-in-out infinite;
        }

        .terminal-prompt::before {
          content: '$ ';
          color: #4ade80;
        }

        .scroll-smooth {
          scroll-behavior: smooth;
        }

        /* Reduce motion for accessibility */
        @media (prefers-reduced-motion: reduce) {
          * {
            animation-duration: 0.01ms !important;
            animation-iteration-count: 1 !important;
            transition-duration: 0.01ms !important;
          }
        }
      `}</style>

      {/* Hero Section */}
      <section
        ref={observerRefs.hero}
        id="hero"
        className="relative min-h-screen flex flex-col items-center justify-center px-6"
      >
        {/* Grid background effect */}
        <div className="absolute inset-0 opacity-5">
          <div
            className="h-full w-full"
            style={{
              backgroundImage:
                'linear-gradient(0deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent)',
              backgroundSize: '50px 50px',
            }}
          />
        </div>

        <div className="relative z-10 text-center max-w-4xl">
          {/* Main Title with Cursor */}
          <h1
            className={`text-5xl md:text-7xl font-bold mb-2 glow-text ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0s' : '0s' }}
          >
            optifiner
          </h1>

          {/* Cursor */}
          <div className="h-12 md:h-16 flex items-center justify-center">
            <span className={`text-4xl md:text-6xl cursor ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`} style={{ animationDelay: isVisible.hero ? '0.2s' : '0s' }}>
              _
            </span>
          </div>

          {/* Tagline */}
          <p
            className={`text-lg md:text-2xl text-green-400 mb-4 ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0.4s' : '0s' }}
          >
            Agents meet evolution.
          </p>

          {/* Subtitle */}
          <p
            className={`text-sm md:text-base text-green-600 mb-12 ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0.6s' : '0s' }}
          >
            Built for Hack n Roll 2026
          </p>

          {/* Navigation Links */}
          <div
            className={`flex flex-col md:flex-row gap-4 justify-center items-center mb-8 ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0.8s' : '0s' }}
          >
            <a
              href="https://github.com/anselmlong/optifiner"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 border border-green-500/50 rounded hover:bg-green-500/10 transition-colors"
            >
              <FontAwesomeIcon icon={faGithub} />
              <span>GitHub</span>
            </a>
            <a
              href="https://devpost.com/software/optifiner"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 border border-green-500/50 rounded hover:bg-green-500/10 transition-colors"
            >
              <span>Devpost</span>
            </a>
          </div>

          {/* Horizontal Line */}
          <div className="w-32 h-px bg-gradient-to-r from-transparent via-green-500/50 to-transparent my-8" />

          {/* Scroll Indicator */}
          <div
            className={`text-green-600 text-sm mt-4 animate-bounce ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '1s' : '0s' }}
          >
            <div>↓ scroll to learn more ↓</div>
          </div>
        </div>
      </section>

      {/* Section 1: Full Automation */}
      <section
        ref={observerRefs.section1}
        id="section1"
        className="relative min-h-screen flex flex-col items-center justify-center px-6 py-20 border-b border-green-900/30"
      >
        <div className="absolute inset-0 opacity-5">
          <div
            className="h-full w-full"
            style={{
              backgroundImage:
                'linear-gradient(0deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent)',
              backgroundSize: '50px 50px',
            }}
          />
        </div>

        <div className="relative z-10 max-w-2xl">
          <div className={`${isVisible.section1 ? 'fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-green-400">full automation</h2>
            <p className="text-base md:text-lg text-green-300 leading-relaxed">
              optifiner finds and defines benchmarks for you, and evolves agents until it works. Watch as your code gets better, faster, and smarter with every generation.
            </p>
            <div className="mt-8 text-sm text-green-600">
              <pre className="overflow-x-auto">
                {`> ./optifiner --target=benchmark.json
> discovering benchmarks...
> initializing agent population...
> running generation 1... ✓
> running generation 2... ✓
> fitness improved 23.4%`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* Section 2: Git Integration */}
      <section
        ref={observerRefs.section2}
        id="section2"
        className="relative min-h-screen flex flex-col items-center justify-center px-6 py-20 border-b border-green-900/30"
      >
        <div className="absolute inset-0 opacity-5">
          <div
            className="h-full w-full"
            style={{
              backgroundImage:
                'linear-gradient(0deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent)',
              backgroundSize: '50px 50px',
            }}
          />
        </div>

        <div className="relative z-10 max-w-2xl">
          <div className={`${isVisible.section2 ? 'fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-4xl md:text-5xl font-bold mb-6 text-green-400">git integration</h2>
            <p className="text-base md:text-lg text-green-300 leading-relaxed">
              Agents clone, stage, commit, and push autonomously. Wake up with the right changes in your code, automatically tested and ready to merge.
            </p>
            <div className="mt-8 text-sm text-green-600">
              <pre className="overflow-x-auto">
                {`> git clone https://github.com/user/project
> agent-1: Implementing optimization...
> git add src/algorithm.ts
> git commit -m "feat: reduce time complexity"
> git push origin evolution-branch
> All tests passed ✓`}
              </pre>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section
        ref={observerRefs.cta}
        id="cta"
        className="relative min-h-screen flex flex-col items-center justify-center px-6 py-20"
      >
        <div className="absolute inset-0 opacity-5">
          <div
            className="h-full w-full"
            style={{
              backgroundImage:
                'linear-gradient(0deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent), linear-gradient(90deg, transparent 24%, rgba(34, 197, 94, 0.05) 25%, rgba(34, 197, 94, 0.05) 26%, transparent 27%, transparent 74%, rgba(34, 197, 94, 0.05) 75%, rgba(34, 197, 94, 0.05) 76%, transparent 77%, transparent)',
              backgroundSize: '50px 50px',
            }}
          />
        </div>

        <div className="relative z-10 text-center max-w-2xl">
          <div className={`${isVisible.cta ? 'fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-green-400">Ready to evolve?</h2>

            <Link
              to="/dashboard"
              className="inline-block px-8 py-4 border-2 border-green-500 text-green-500 font-bold text-lg hover:bg-green-500/10 transition-all duration-300 hover:shadow-lg hover:shadow-green-500/30 rounded"
            >
              try it now →
            </Link>

            <div className="mt-12 text-green-600 text-sm">
              <p className="terminal-prompt">optifiner helps you create better code through evolution</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-green-900/30 bg-black/50 py-8 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-8 text-sm">
            <div>
              <h3 className="text-green-400 font-bold mb-4">optifiner</h3>
              <p className="text-green-600">Autonomous evolution for your code</p>
            </div>
            <div>
              <h3 className="text-green-400 font-bold mb-4">links</h3>
              <ul className="space-y-2 text-green-600">
                <li>
                  <a href="https://github.com/anselmlong/optifiner" target="_blank" rel="noopener noreferrer" className="hover:text-green-400 transition-colors">
                    GitHub
                  </a>
                </li>
                <li>
                  <a href="#" className="opacity-50 cursor-not-allowed">
                    Devpost
                  </a>
                </li>
              </ul>
            </div>
            <div>
              <h3 className="text-green-400 font-bold mb-4">navigate</h3>
              <ul className="space-y-2 text-green-600">
                <li>
                  <Link to="/dashboard" className="hover:text-green-400 transition-colors">
                    Dashboard
                  </Link>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-green-900/30 pt-6 text-center text-green-700 text-xs">
            <p>© 2026 optifiner | Hack n Roll 2026</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
