import { motion } from 'framer-motion'
import { Play } from 'lucide-react'
import { useRef, useState } from 'react'

const DemoSection = () => {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [isPlaying, setIsPlaying] = useState(false)

  const handlePlayPause = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause()
      } else {
        videoRef.current.play()
      }
      setIsPlaying(!isPlaying)
    }
  }

  return (
    <section id="demo" className="py-32 relative">
      <div className="container mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 40 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="text-center mb-16"
        >
          <h2 className="text-4xl md:text-5xl font-bold mb-6">
            See <span className="text-gradient">Optifiner</span> in action
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
            Watch how our multi-agent system analyzes, evolves, and optimizes your code autonomously
          </p>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
          className="relative max-w-5xl mx-auto"
        >
          {/* Video container with glow effect */}
          <div className="relative rounded-2xl overflow-hidden border border-border bg-card glow-box">
            {/* Terminal-style header */}
            <div className="flex items-center gap-2 px-4 py-3 bg-secondary/50 border-b border-border">
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-destructive/80" />
                <div className="w-3 h-3 rounded-full bg-accent/80" />
                <div className="w-3 h-3 rounded-full bg-primary/80" />
              </div>
              <span className="font-mono text-xs text-muted-foreground ml-4">optifiner-demo.mp4</span>
            </div>

            {/* Video player */}
            <div className="relative aspect-video bg-background">
              <video
                ref={videoRef}
                src="/videos/optifiner-demo-vid.mp4"
                className="w-full h-full object-cover"
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onClick={handlePlayPause}
                controls
                playsInline
              />

              {/* Play button overlay (hidden when playing) */}
              {!isPlaying && (
                <motion.button
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  onClick={handlePlayPause}
                  className="absolute inset-0 flex items-center justify-center bg-background/40 backdrop-blur-sm group cursor-pointer"
                >
                  <div className="w-20 h-20 rounded-full bg-primary flex items-center justify-center glow-box group-hover:glow-box-strong transition-all duration-300 group-hover:scale-110">
                    <Play className="h-8 w-8 text-primary-foreground ml-1" />
                  </div>
                </motion.button>
              )}
            </div>
          </div>

          {/* Decorative elements */}
          <div className="absolute -z-10 -inset-8 bg-gradient-to-r from-primary/10 via-transparent to-primary/10 blur-3xl opacity-50" />
        </motion.div>
      </div>
    </section>
  )
}

export default DemoSection
