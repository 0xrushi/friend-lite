import { useState, useEffect } from 'react'
import { motion, AnimatePresence, PanInfo } from 'framer-motion'
import { X, Check, Heart, HeartCrack } from 'lucide-react'
import { BACKEND_URL } from '../services/api'

interface AnomalyEvent {
  version_id: string
  conversation_id: string
  transcript: string
  timestamp: number
  audio_duration: number
  speaker_count: number
  word_count: number
}

export default function UserLoopModal() {
  const [isOpen, setIsOpen] = useState(false)
  const [events, setEvents] = useState<AnomalyEvent[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [direction, setDirection] = useState(0)
  const [isAnimating, setIsAnimating] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const [particles, setParticles] = useState<{ id: number; x: number; y: number; type: 'heart' | 'heart-break' }[]>([])

  // Algorithm to determine if popup should show (always true for now)
  useEffect(() => {
    const checkAnomaly = () => {
      // TODO: Replace with actual algorithm
      const shouldShow = true
      setIsOpen(shouldShow)
    }

    // Check on component mount
    checkAnomaly()

    // Poll every 30 seconds
    const interval = setInterval(checkAnomaly, 30000)
    return () => clearInterval(interval)
  }, [])

  // Load events when modal opens
  useEffect(() => {
    if (isOpen && !isLoading) {
      fetchEvents()
    }
  }, [isOpen, isLoading])

  // Clean up particles
  useEffect(() => {
    const timer = setTimeout(() => {
      setParticles([])
    }, 1000)
    return () => clearTimeout(timer)
  }, [particles])

  const fetchEvents = async () => {
    try {
      setIsLoading(true)
      console.log('Fetching events...')
      const response = await fetch(`${BACKEND_URL}/api/user-loop/events`)
      const data = await response.json()
      console.log('Events fetched:', data)
      console.log('Events array:', Array.isArray(data))
      console.log('Events length:', data.length)
      if (data.length > 0) {
        console.log('First event:', data[0])
        console.log('First event version_id:', data[0].version_id)
        console.log('First event transcript:', data[0].transcript)
      }
      setEvents(data)
      setCurrentIndex(0)
    } catch (error) {
      console.error('Failed to fetch events:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // Close modal when no events left and not loading
  useEffect(() => {
    if (!isLoading && events.length === 0 && isOpen) {
      console.log('No more events, closing modal')
      setIsOpen(false)
    }
  }, [events.length, isLoading, isOpen])

  const createParticles = (type: 'heart' | 'heart-break') => {
    const newParticles = Array.from({ length: 8 }, (_, i) => ({
      id: Date.now() + i,
      x: Math.random() * 400 - 200,
      y: Math.random() * 200 - 100,
      type
    }))
    setParticles(newParticles)
  }

  const onPanEnd = (_event: MouseEvent | TouchEvent | PointerEvent, info: PanInfo) => {
    if (isAnimating) return

    const threshold = 100
    if (info.offset.x > threshold) {
      handleAction('accept', 1)
      createParticles('heart')
    } else if (info.offset.x < -threshold) {
      handleAction('reject', -1)
      createParticles('heart-break')
    } else {
      // Snap back to center
      setDirection(0)
    }
  }

  const handleAction = async (action: 'accept' | 'reject', swipeDirection: number) => {
    const event = events[currentIndex]
    if (!event) return

    setIsAnimating(true)
    setDirection(swipeDirection)

    try {
      // Map AnomalyEvent fields to SwipeAction fields
      const swipeAction = {
        transcript_version_id: event.version_id,  // Backend expects transcript_version_id
        conversation_id: event.conversation_id,
        reason: null,
        timestamp: event.timestamp
      }

      console.log(`Sending ${action} action:`, swipeAction)

      if (action === 'reject') {
        const response = await fetch(`${BACKEND_URL}/api/user-loop/reject`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(swipeAction)
        })
        const result = await response.json()
        console.log('Reject result:', result)
      } else {
        // Accept action: Call /accept endpoint
        const response = await fetch(`${BACKEND_URL}/api/user-loop/accept`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(swipeAction)
        })
        const result = await response.json()
        console.log('Accept result:', result)
      }
    } catch (error) {
      console.error(`Failed to handle ${action}:`, error)
    }

    // Wait for animation to complete, then move to next card
    setTimeout(() => {
      if (currentIndex < events.length - 1) {
        setCurrentIndex(prev => prev + 1)
        setIsAnimating(false)
        setDirection(0)
      } else {
        // No more events, close modal
        setIsOpen(false)
        setEvents([])
        setIsAnimating(false)
        setDirection(0)
      }
    }, 400)
  }

  if (!isOpen) {
    return null
  }

  if (events.length === 0) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <motion.div
          className="bg-white dark:bg-gray-800 rounded-3xl shadow-2xl p-8"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
        >
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-700 dark:text-gray-300">Loading transcripts...</p>
          </div>
        </motion.div>
      </div>
    )
  }

  const currentEvent = events[currentIndex]

  const cardVariants = {
    enter: (direction: number) => ({
      x: direction > 0 ? 1000 : -1000,
      opacity: 0,
      scale: 0.8,
      rotate: 0
    }),
    center: {
      zIndex: 1,
      x: 0,
      opacity: 1,
      scale: 1,
      rotate: 0
    },
    exit: (direction: number) => ({
      zIndex: 0,
      x: direction > 0 ? 1000 : -1000,
      opacity: 0,
      scale: 0.8,
      rotate: direction * 0.2
    })
  }

  return (
    <AnimatePresence mode="wait">
      {isOpen && (
        <motion.div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="relative w-full max-w-md mx-4 perspective-1000">
            {/* Particles */}
            <AnimatePresence mode="popLayout">
              {particles.map(particle => (
                <motion.div
                  key={particle.id}
                  className="absolute top-1/2 left-1/2 pointer-events-none"
                  initial={{ x: particle.x, y: particle.y, scale: 0, opacity: 1 }}
                  animate={{ y: particle.y - 200, scale: [0, 1.5, 1], opacity: [1, 1, 0] }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.8, ease: "easeOut" }}
                >
                  {particle.type === 'heart' ? (
                    <motion.div
                      animate={{ scale: [1, 1.2, 1], rotate: [0, 360] }}
                      transition={{ duration: 0.8, repeat: 0 }}
                    >
                      <Heart className="h-16 w-16 text-pink-500 fill-pink-500" />
                    </motion.div>
                  ) : (
                    <motion.div
                      animate={{ scale: [1, 1.2, 1], rotate: [0, -360] }}
                      transition={{ duration: 0.8, repeat: 0 }}
                    >
                      <HeartCrack className="h-16 w-16 text-red-500" />
                    </motion.div>
                  )}
                </motion.div>
              ))}
            </AnimatePresence>

            {/* Card */}
            <motion.div
              className="relative bg-white dark:bg-gray-800 rounded-3xl shadow-2xl p-6 cursor-grab active:cursor-grabbing"
              custom={direction}
              variants={cardVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{
                x: { type: "spring", stiffness: 300, damping: 30 },
                opacity: { duration: 0.2 },
                scale: { duration: 0.2 },
                rotate: { type: "spring", stiffness: 200, damping: 20 }
              }}
              drag="x"
              dragConstraints={{ left: 0, right: 0 }}
              dragElastic={0.1}
              onDragEnd={onPanEnd}
              whileDrag={{ scale: 1.05, rotate: 0, transition: { duration: 0 } }}
            >
              {/* Status Overlays */}
              <AnimatePresence mode="popLayout">
                {direction > 0 && (
                  <motion.div
                    className="absolute top-6 right-8 text-5xl font-bold text-green-500 border-4 border-green-500 rounded-2xl px-4 py-2"
                    initial={{ scale: 0, opacity: 0, rotate: -15 }}
                    animate={{ scale: 1, opacity: 1, rotate: -15 }}
                    exit={{ scale: 1.2, opacity: 0, rotate: -15 }}
                    transition={{ duration: 0.3 }}
                  >
                    GOOD
                  </motion.div>
                )}
                {direction < 0 && (
                  <motion.div
                    className="absolute top-6 left-8 text-5xl font-bold text-red-500 border-4 border-red-500 rounded-2xl px-4 py-2"
                    initial={{ scale: 0, opacity: 0, rotate: 15 }}
                    animate={{ scale: 1, opacity: 1, rotate: 15 }}
                    exit={{ scale: 1.2, opacity: 0, rotate: 15 }}
                    transition={{ duration: 0.3 }}
                  >
                    NOPE
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Content */}
              <motion.div
                className="text-center"
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1, duration: 0.4 }}
              >
                <motion.div
                  className="mb-4 text-2xl font-semibold text-gray-900 dark:text-gray-100"
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.15, duration: 0.4 }}
                >
                  Review Transcript
                </motion.div>

                <motion.p
                  className="mb-6 text-lg text-gray-700 dark:text-gray-300 leading-relaxed"
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.2, duration: 0.4 }}
                >
                  {currentEvent?.transcript || "Loading transcript..."}
                </motion.p>

                {/* Audio Player */}
                <motion.div
                  className="mb-6"
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.25, duration: 0.4 }}
                  onPointerDown={(e) => e.stopPropagation()}
                  onPointerMove={(e) => e.stopPropagation()}
                  onPointerUp={(e) => e.stopPropagation()}
                >
                  {/* Only render audio when we have a valid version_id */}
                  {currentEvent?.version_id ? (
                    <>
                      {console.log('Rendering audio with version_id:', currentEvent.version_id)}
                      <audio
                        key={currentEvent.version_id}
                        controls
                        preload="auto"
                        autoPlay={false}
                        className="w-full"
                        src={`${BACKEND_URL}/api/user-loop/audio/${currentEvent.version_id}`}
                        onError={(e) => {
                          console.error('Audio load error:', e)
                          console.error('Audio src:', (e.target as HTMLAudioElement).src)
                        }}
                        onLoadStart={() => console.log('Audio load started')}
                        onCanPlay={() => console.log('Audio can play')}
                        onLoadedData={() => console.log('Audio loaded data')}
                      />
                    </>
                  ) : (
                    <div className="text-gray-400 text-sm">Loading audio...</div>
                  )}
                </motion.div>

                {/* Counter */}
                <motion.div
                  className="text-sm text-gray-500 dark:text-gray-400 mb-4"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.3, duration: 0.4 }}
                >
                  {currentIndex + 1} / {events.length}
                </motion.div>

                {/* Instructions */}
                <motion.div
                  className="text-sm text-gray-500 dark:text-gray-400 flex items-center justify-center gap-2"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: 0.35, duration: 0.4 }}
                >
                  <motion.div
                    animate={{ x: [0, 10, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                  >
                    →
                  </motion.div>
                  Swipe right to accept
                  <motion.div
                    animate={{ x: [0, -10, 0] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: "easeInOut" }}
                  >
                    ←
                  </motion.div>
                  Swipe left to reject
                </motion.div>
              </motion.div>

              {/* Close Button */}
              <motion.button
                onClick={() => setIsOpen(false)}
                className="absolute top-4 right-4 p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
                whileHover={{ scale: 1.1, rotate: 90 }}
                whileTap={{ scale: 0.9 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <X className="h-6 w-6" />
              </motion.button>
            </motion.div>

            {/* Control Buttons */}
            <motion.div
              className="flex justify-center items-center gap-8 mt-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.4, duration: 0.4 }}
            >
              <motion.button
                onClick={() => handleAction('reject', -1)}
                className="w-16 h-16 rounded-full bg-white dark:bg-gray-800 border-2 border-red-500 text-red-500 flex items-center justify-center shadow-lg hover:shadow-xl"
                whileHover={{ scale: 1.1, boxShadow: "0 10px 30px rgba(239, 68, 68, 0.3)" }}
                whileTap={{ scale: 0.9 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <motion.div
                  animate={{ rotate: [0, -5, 0] }}
                  transition={{ duration: 0.3 }}
                >
                  <X className="h-8 w-8" />
                </motion.div>
              </motion.button>
              <motion.button
                onClick={() => handleAction('accept', 1)}
                className="w-16 h-16 rounded-full bg-white dark:bg-gray-800 border-2 border-green-500 text-green-500 flex items-center justify-center shadow-lg hover:shadow-xl"
                whileHover={{ scale: 1.1, boxShadow: "0 10px 30px rgba(34, 197, 94, 0.3)" }}
                whileTap={{ scale: 0.9 }}
                transition={{ type: "spring", stiffness: 400, damping: 17 }}
              >
                <motion.div
                  animate={{ rotate: [0, 5, 0] }}
                  transition={{ duration: 0.3 }}
                >
                  <Check className="h-8 w-8" />
                </motion.div>
              </motion.button>
            </motion.div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  )
}
