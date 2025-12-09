import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import * as d3 from 'd3'

interface UseD3ZoomOptions {
  onZoom?: (transform: d3.ZoomTransform) => void
  scaleExtent?: [number, number]
  wheelDelta?: (event: WheelEvent) => number
}

export function useD3Zoom(options: UseD3ZoomOptions = {}) {
  const {
    onZoom,
    scaleExtent = [0.5, 5],
    wheelDelta = (event) => -event.deltaY * 0.002
  } = options

  const svgRef = useRef<SVGSVGElement>(null)
  const [transform, setTransform] = useState<d3.ZoomTransform>(d3.zoomIdentity)

  const handleZoom = useCallback(
    (event: d3.D3ZoomEvent<SVGSVGElement, unknown>) => {
      const t = event.transform
      setTransform(t)
      onZoom?.(t)

      // Synchronize zoom across all zoomable SVG elements
      d3.selectAll<SVGSVGElement, unknown>('.zoomable').each(function () {
        const svg = d3.select(this)
        const node = svg.node()

        // Skip the source element
        if (!node || node.contains(event.sourceEvent?.target as Element)) {
          return
        }

        svg.property('__zoom', t)
      })
    },
    [onZoom]
  )

  const zoomBehavior = useMemo(
    () =>
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent(scaleExtent)
        .on('zoom', handleZoom)
        .wheelDelta(wheelDelta)
        .touchable(() => true)
        .filter((event) => {
          if (event.type === 'dblclick') return false
          if (event.button && event.button !== 0) return false
          return true
        }),
    [handleZoom, scaleExtent, wheelDelta]
  )

  useEffect(() => {
    if (!svgRef.current) return

    const svg = d3.select(svgRef.current)
    const node = svg.node()

    if (node) {
      node.style.touchAction = 'none'
      node.style.webkitUserSelect = 'none'
      node.style.userSelect = 'none'
    }

    svg.call(zoomBehavior as any)
    svg.property('__zoom', transform)

    return () => {
      svg.on('.zoom', null)
    }
  }, [zoomBehavior, transform])

  return {
    svgRef,
    transform,
    zoomBehavior
  }
}
