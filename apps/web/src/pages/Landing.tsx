import { useEffect, useRef, useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faGithub } from '@fortawesome/free-brands-svg-icons'

export const Landing = () => {
  const [isVisible, setIsVisible] = useState({
    hero: false,
    section1: false,
    section2: false,
    section3: false,
    cta: false,
  })
  const observerRefs = {
    hero: useRef<HTMLDivElement>(null),
    section1: useRef<HTMLDivElement>(null),
    section2: useRef<HTMLDivElement>(null),
    section3: useRef<HTMLDivElement>(null),
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
            opacity: 1;
          }
          50% {
            opacity: 0.8;
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

        <div className="relative z-10 text-center max-w-4xl">
          {/* Main Title with Cursor */}
          <h1
            className={`text-5xl md:text-7xl font-bold mb-6 glow-text text-balance ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0s' : '0s' }}
          >
            optifiner
          </h1>

          {/* Tagline */}
          <p
            className={`text-lg md:text-2xl text-green-400 mb-8 text-pretty ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0.4s' : '0s' }}
          >
            Optimize everything.
          </p>

          {/* Subtitle */}
          <p
            className={`text-sm md:text-base text-green-600 mb-12 text-pretty ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '0.6s' : '0s' }}
          >
            A Darwinian, multi-agent framework that autonomously improves codebase performance.
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
              className="flex items-center gap-2 px-4 py-2 border border-green-500/50 rounded hover:bg-green-500/10 transition-all duration-150 hover:scale-105 hover:border-green-500"
            >
              <FontAwesomeIcon icon={faGithub} />
              <span>GitHub</span>
            </a>
            <a
              href="https://devpost.com/software/optifiner"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 px-4 py-2 border border-green-500/50 rounded hover:bg-green-500/10 transition-all duration-150 hover:scale-105 hover:border-green-500"
            >
              <span>Devpost</span>
            </a>
          </div>


          {/* Scroll Indicator */}
          <div
            className={`text-green-600 text-sm mt-12 animate-bounce ${isVisible.hero ? 'fade-in-up' : 'opacity-0'}`}
            style={{ animationDelay: isVisible.hero ? '1s' : '0s' }}
          >
            <div>↓ scroll to learn more ↓</div>
          </div>
        </div>
      </section>

      {/* Section 1: Real Results - Video */}
      <section
        ref={observerRefs.section1}
        id="section1"
        className="relative flex flex-col items-center justify-center px-6 py-20 border-b border-green-900/30"
      >
        <div className="relative z-10 w-full max-w-4xl">
          <div className={`${isVisible.section1 ? 'fade-in-up' : 'opacity-0'}`}>
            <div className="mb-8 rounded-lg overflow-hidden border border-green-500/30">
              <video
                className="w-full h-auto bg-black"
                controls
                autoPlay
                muted
                loop
              >
                <source src="/videos/optifiner-demo-vid.mp4" type="video/mp4" />
                Your browser does not support the video tag.
              </video>
            </div>

            <p className="text-center text-green-300 text-lg font-semibold">
              go from 2 to 60 FPS in just 8 minutes.
            </p>
          </div>
        </div>
      </section>

      {/* Section 2: Full Automation */}
      <section
        ref={observerRefs.section2}
        id="section2"
        className="relative min-h-screen flex flex-col items-center justify-center px-6 py-20 border-b border-green-900/30"
      >
        <div className="relative z-10 w-full max-w-6xl">
          <div className={`${isVisible.section2 ? 'fade-in-up' : 'opacity-0'}`}>
            <div className="text-left">
              <h2 className="text-4xl md:text-5xl font-bold mb-6 text-green-400 text-balance">full automation</h2>
              <p className="text-base md:text-lg text-green-300 leading-relaxed text-pretty mb-8">
                optifiner finds and defines benchmarks for you, and evolves agents until it works. Watch as your code gets better, faster, and smarter with every generation.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Section 3: Git Integration */}
      <section
        ref={observerRefs.section3}
        id="section3"
        className="relative min-h-screen flex flex-col items-center justify-center px-6 py-20 border-b border-green-900/30"
      >
        <div className="relative z-10 w-full max-w-6xl">
          <div className={`${isVisible.section3 ? 'fade-in-up' : 'opacity-0'}`}>
            <div className="text-left">
              <h2 className="text-4xl md:text-5xl font-bold mb-6 text-green-400 text-balance">git integration</h2>

              <p className="text-base md:text-lg text-green-300 leading-relaxed text-pretty">
                Agents clone, stage, commit, and push autonomously. Wake up with the right changes in your code, automatically tested and ready to merge.
              </p>
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

        <div className="relative z-10 text-center max-w-2xl">
          <div className={`${isVisible.cta ? 'fade-in-up' : 'opacity-0'}`}>
            <h2 className="text-4xl md:text-5xl font-bold mb-8 text-green-400 text-balance">Ready to evolve?</h2>

            <a
              href="https://github.com/anselmlong/optifiner"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-block px-8 py-4 border-2 border-green-500 text-green-500 font-bold text-lg hover:bg-green-500/10 transition-all duration-150 rounded hover:scale-105"
            >
              View on GitHub →
            </a>

            <div className="mt-12 text-green-600 text-sm">
              <p className="terminal-prompt text-pretty">optifiner helps you create better code through evolution</p>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-green-900/30 bg-black/50 py-8 px-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col items-center justify-center mb-8 text-sm text-center">
            <div className="mb-6">
              <h3 className="text-green-400 font-bold mb-2 text-balance">optifiner</h3>
              <p className="text-green-600 text-pretty">Autonomous evolution for your code</p>
            </div>
            <div>
              <h3 className="text-green-400 font-bold mb-3 text-balance">links</h3>
              <ul className="space-y-2 text-green-600">
                <li>
                  <a href="https://github.com/anselmlong/optifiner" target="_blank" rel="noopener noreferrer" className="hover:text-green-400 transition-colors">
                    GitHub
                  </a>
                </li>
                <li>
                  <a href="https://devpost.com/software/optifiner" target="_blank" rel="noopener noreferrer" className="hover:text-green-400 transition-colors">
                    Devpost
                  </a>
                </li>
              </ul>
            </div>
          </div>

          <div className="border-t border-green-900/30 pt-6 text-center text-green-700 text-xs">
            <p>© 2026 optifiner | Hack & Roll 2026</p>
          </div>
        </div>
      </footer>
    </div>
  )
}
