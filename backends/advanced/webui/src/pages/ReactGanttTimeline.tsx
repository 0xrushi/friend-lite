import { useState, useEffect } from 'react'
import { Calendar, RefreshCw, AlertCircle, ZoomIn, ZoomOut } from 'lucide-react'
import Timeline from 'react-gantt-timeline'
import { memoriesApi } from '../services/api'
import { useAuth } from '../contexts/AuthContext'

interface TimeRange {
  start: string
  end: string
  name?: string
}

interface MemoryWithTimeRange {
  id: string
  content: string
  created_at: string
  metadata?: {
    name?: string
    timeRanges?: TimeRange[]
    isPerson?: boolean
    isEvent?: boolean
    isPlace?: boolean
  }
}

interface ReactGanttTask {
  id: string
  name: string
  start: Date
  end: Date
  color?: string
}

export default function ReactGanttTimeline() {
  const [memories, setMemories] = useState<MemoryWithTimeRange[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [useDemoData, setUseDemoData] = useState(false)
  const [zoomLevel, setZoomLevel] = useState(1) // 0.5 = 50%, 1 = 100%, 2 = 200%
  const { user } = useAuth()

  const handleZoomIn = () => {
    setZoomLevel(prev => Math.min(prev + 0.25, 3)) // Max 300%
  }

  const handleZoomOut = () => {
    setZoomLevel(prev => Math.max(prev - 0.25, 0.5)) // Min 50%
  }

  // Demo data for testing the Timeline visualization - spans multiple years
  const getDemoMemories = (): MemoryWithTimeRange[] => {
    return [
      {
        id: 'demo-graduation',
        content: 'College graduation ceremony and celebration dinner with family.',
        created_at: '2024-05-20T14:00:00',
        metadata: {
          name: 'College Graduation',
          isEvent: true,
          timeRanges: [
            {
              name: 'Graduation Ceremony',
              start: '2024-05-20T14:00:00',
              end: '2024-05-20T17:00:00'
            },
            {
              name: 'Celebration Dinner',
              start: '2024-05-20T18:00:00',
              end: '2024-05-20T21:00:00'
            }
          ]
        }
      },
      {
        id: 'demo-vacation',
        content: 'Summer vacation in Hawaii with family. Visited beaches, hiked Diamond Head, attended a luau.',
        created_at: '2024-07-10T08:00:00',
        metadata: {
          name: 'Hawaii Vacation',
          isEvent: true,
          timeRanges: [
            {
              name: 'Hawaii Trip',
              start: '2024-07-10T08:00:00',
              end: '2024-07-17T20:00:00'
            }
          ]
        }
      },
      {
        id: 'demo-marathon',
        content: 'Completed first marathon in Boston. Training started 6 months ago.',
        created_at: '2025-04-15T06:00:00',
        metadata: {
          name: 'Boston Marathon',
          isEvent: true,
          timeRanges: [
            {
              name: 'Marathon Race',
              start: '2025-04-15T06:00:00',
              end: '2025-04-15T11:30:00'
            }
          ]
        }
      },
      {
        id: 'demo-wedding',
        content: "Sarah and Tom's wedding was a beautiful celebration. The ceremony started at 3 PM, followed by a reception.",
        created_at: '2025-06-15T15:00:00',
        metadata: {
          name: "Sarah & Tom's Wedding",
          isEvent: true,
          timeRanges: [
            {
              name: 'Wedding Ceremony',
              start: '2025-06-15T15:00:00',
              end: '2025-06-15T16:30:00'
            },
            {
              name: 'Reception',
              start: '2025-06-15T18:00:00',
              end: '2025-06-16T00:00:00'
            }
          ]
        }
      },
      {
        id: 'demo-conference',
        content: 'Tech conference in San Francisco. Attended keynotes, workshops, and networking events.',
        created_at: '2026-03-10T09:00:00',
        metadata: {
          name: 'Tech Conference 2026',
          isEvent: true,
          timeRanges: [
            {
              name: 'Conference',
              start: '2026-03-10T09:00:00',
              end: '2026-03-13T18:00:00'
            }
          ]
        }
      }
    ]
  }

  const fetchMemoriesWithTimeRanges = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await memoriesApi.getAll()

      // Extract memories from response
      const memoriesData = response.data.memories || response.data || []

      const memoriesWithTimeRanges = memoriesData.filter(
        (memory: MemoryWithTimeRange) =>
          memory.metadata?.timeRanges &&
          memory.metadata.timeRanges.length > 0
      )

      if (memoriesWithTimeRanges.length === 0) {
        setUseDemoData(true)
        setMemories(getDemoMemories())
        setError('No memories with time ranges found. Showing demo data.')
      } else {
        setMemories(memoriesWithTimeRanges)
        setUseDemoData(false)
      }
    } catch (err) {
      console.error('Failed to fetch memories:', err)
      setError('Failed to load memories. Showing demo data.')
      setUseDemoData(true)
      setMemories(getDemoMemories())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (user) {
      fetchMemoriesWithTimeRanges()
    }
  }, [user])

  const handleRefresh = () => {
    fetchMemoriesWithTimeRanges()
  }

  const handleToggleDemoData = () => {
    if (useDemoData) {
      fetchMemoriesWithTimeRanges()
    } else {
      setMemories(getDemoMemories())
      setUseDemoData(true)
    }
  }

  // Convert memories to react-gantt-timeline format
  const convertToReactGanttFormat = (memories: MemoryWithTimeRange[]): ReactGanttTask[] => {
    const tasks: ReactGanttTask[] = []

    memories.forEach((memory) => {
      const timeRanges = memory.metadata?.timeRanges || []
      const isEvent = memory.metadata?.isEvent
      const isPerson = memory.metadata?.isPerson
      const isPlace = memory.metadata?.isPlace

      let color = '#3b82f6' // default blue
      if (isEvent) color = '#3b82f6' // blue
      else if (isPerson) color = '#10b981' // green
      else if (isPlace) color = '#f59e0b' // amber

      timeRanges.forEach((range, index) => {
        tasks.push({
          id: `${memory.id}-${index}`,
          name: range.name || memory.metadata?.name || memory.content.substring(0, 30),
          start: new Date(range.start),
          end: new Date(range.end),
          color: color
        })
      })
    })

    return tasks
  }

  const tasks = convertToReactGanttFormat(memories)

  const data = tasks.map((task) => ({
    id: task.id,
    name: task.name,
    start: task.start,
    end: task.end,
    color: task.color
  }))

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold flex items-center gap-2">
            <Calendar className="w-8 h-8" />
            Timeline (React Gantt)
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Visualize your memories on an interactive timeline using react-gantt-timeline
          </p>
        </div>
        <div className="flex gap-2">
          {/* Zoom controls */}
          <div className="flex items-center border border-gray-300 dark:border-gray-600 rounded-lg overflow-hidden">
            <button
              onClick={handleZoomIn}
              disabled={zoomLevel >= 3}
              className="px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
            <div className="px-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 text-sm font-medium">
              {Math.round(zoomLevel * 100)}%
            </div>
            <button
              onClick={handleZoomOut}
              disabled={zoomLevel <= 0.5}
              className="px-3 py-2 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 hover:bg-gray-100 dark:hover:bg-gray-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>
          </div>
          <button
            onClick={handleToggleDemoData}
            className="flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition"
          >
            {useDemoData ? 'Load Real Data' : 'Show Demo Data'}
          </button>
          <button
            onClick={handleRefresh}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
          <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
          <span className="text-yellow-800 dark:text-yellow-200">{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
        </div>
      ) : memories.length === 0 ? (
        <div className="text-center py-12 bg-gray-50 dark:bg-gray-800 rounded-lg">
          <Calendar className="w-16 h-16 mx-auto text-gray-400 mb-4" />
          <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            No Timeline Data
          </h3>
          <p className="text-gray-600 dark:text-gray-400 mb-4">
            No memories with time ranges found. Try the demo data to see the timeline in action.
          </p>
          <button
            onClick={handleToggleDemoData}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Load Demo Data
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {/* Timeline Container - Expands with zoom */}
          <div className="bg-white dark:bg-gray-800 rounded-lg border p-4 overflow-auto" style={{
            minHeight: `${Math.min(300 * zoomLevel, 500)}px`,
            maxHeight: '600px'
          }}>
            <div style={{
              transform: `scale(${zoomLevel})`,
              transformOrigin: 'top left',
              transition: 'transform 0.2s ease-out'
            }}>
              <Timeline
                data={data}
              />
            </div>
          </div>

          {/* Legend */}
          <div className="flex items-center justify-center space-x-6 text-sm">
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-blue-500 rounded"></div>
              <span>Event</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-green-500 rounded"></div>
              <span>Person</span>
            </div>
            <div className="flex items-center space-x-2">
              <div className="w-4 h-4 bg-amber-500 rounded"></div>
              <span>Place</span>
            </div>
          </div>

          {useDemoData && (
            <div className="text-center text-sm text-gray-500 dark:text-gray-400">
              Showing demo data with events spanning 2024-2026
            </div>
          )}
        </div>
      )}
    </div>
  )
}
