import { useState } from 'react'
import { FontAwesomeIcon } from '@fortawesome/react-fontawesome'
import { faTimes, faCheck, faEnvelope } from '@fortawesome/free-solid-svg-icons'

interface EarlyAccessModalProps {
  isOpen: boolean
  onClose: () => void
}

export function EarlyAccessModal({ isOpen, onClose }: EarlyAccessModalProps) {
  const [email, setEmail] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const validateEmail = (email: string): boolean => {
    const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/
    return emailPattern.test(email.trim())
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    if (!email.trim()) {
      setError('Email is required')
      return
    }

    if (!validateEmail(email)) {
      setError('Please enter a valid email address')
      return
    }

    setIsSubmitting(true)

    try {
      const response = await fetch('/api/v1/early-access/signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email: email.trim(),
          source: 'landing_page',
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to sign up')
      }

      setSuccess(true)

      setTimeout(() => {
        onClose()
        setTimeout(() => {
          setEmail('')
          setSuccess(false)
        }, 300)
      }, 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred. Please try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleClose = () => {
    if (!isSubmitting) {
      onClose()
      setTimeout(() => {
        setEmail('')
        setError(null)
        setSuccess(false)
      }, 300)
    }
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        onClick={handleClose}
      />

      <div className="relative w-full max-w-md mx-4 bg-black border-2 border-green-500/50 rounded-lg shadow-2xl shadow-green-500/20 animate-in fade-in zoom-in-95 duration-200 font-mono">
        <div className="flex items-center justify-between px-4 py-3 border-b border-green-500/30 bg-green-900/10">
          <div className="flex items-center gap-2">
            <div className="size-3 rounded-full bg-red-500/80" />
            <div className="size-3 rounded-full bg-yellow-500/80" />
            <div className="size-3 rounded-full bg-green-500/80" />
            <span className="ml-2 text-sm text-green-400">optifiner/early-access</span>
          </div>
          <button
            onClick={handleClose}
            disabled={isSubmitting}
            aria-label="Close early access modal"
            className="p-1 text-green-400 hover:text-green-300 transition-all duration-150 disabled:opacity-50 hover:scale-110 active:scale-95"
          >
            <FontAwesomeIcon icon={faTimes} />
          </button>
        </div>

        <div className="p-6">
          {success ? (
            <div className="text-center py-4">
              <div className="inline-flex items-center justify-center size-16 rounded-full bg-green-500/20 mb-4 animate-in zoom-in duration-300">
                <FontAwesomeIcon icon={faCheck} className="text-3xl text-green-400" />
              </div>
              <h3 className="text-xl font-bold text-green-400 mb-2 text-balance">
                Success!
              </h3>
              <p className="text-green-500 text-sm text-pretty">
                We'll notify you when Optifiner is ready.
              </p>
              <p className="text-green-700 text-xs mt-2">
                Closing in 3 seconds...
              </p>
            </div>
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-2xl font-bold text-green-400 mb-2 text-balance">
                  Join Early Access
                </h2>
                <p className="text-green-500 text-sm text-pretty">
                  Be the first to know when Optifiner launches. We'll send you an invitation to start evolving your code.
                </p>
              </div>

              <form onSubmit={handleSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm text-green-400 mb-2">
                    $ enter_email --notify-on-launch
                  </label>
                  <div className="relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <FontAwesomeIcon icon={faEnvelope} className="text-green-600" />
                    </div>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => {
                        setEmail(e.target.value)
                        setError(null)
                      }}
                      placeholder="you@example.com"
                      disabled={isSubmitting}
                      className="w-full pl-10 pr-4 py-3 bg-black border-2 border-green-500/50 rounded text-green-400 placeholder-green-800 focus:outline-none focus:border-green-500 focus:shadow-lg focus:shadow-green-500/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                      autoFocus
                    />
                  </div>
                  {error && (
                    <p className="mt-2 text-sm text-red-400 flex items-center gap-2">
                      <span>✗</span> {error}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting || !email.trim()}
                  className="w-full py-3 border-2 border-green-500 bg-green-500/10 text-green-400 font-bold rounded hover:bg-green-500/20 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:bg-green-500/10 active:scale-95"
                >
                  {isSubmitting ? (
                    <span className="flex items-center justify-center gap-2">
                      <span className="animate-spin">⟳</span>
                      Processing...
                    </span>
                  ) : (
                    'Sign Up for Early Access'
                  )}
                </button>
              </form>

              <p className="mt-4 text-xs text-green-700 text-center">
                No spam. Just a notification when we launch.
              </p>
            </>
          )}
        </div>

        <div className="px-4 py-2 border-t border-green-500/30 bg-green-900/10">
          <p className="text-xs text-green-700">
            <span className="text-green-500">~/optifiner</span> <span className="text-green-400 animate-pulse">_</span>
          </p>
        </div>
      </div>
    </div>
  )
}
