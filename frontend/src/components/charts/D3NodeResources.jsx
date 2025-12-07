/**
 * D3NodeResources - Animated Bar Chart Race for Node Metrics
 * Shows CPU, Memory, Disk usage with smooth animations
 *
 * @version 1.0.0
 * @date 2024-12-07
 */

import { useEffect, useRef, useState, useMemo, memo } from 'react'
import * as d3 from 'd3'
import { Cpu, HardDrive, MemoryStick, Play, Pause, RotateCcw } from 'lucide-react'

// Metric colors
const METRIC_COLORS = {
  cpu: '#3b82f6',      // Blue
  memory: '#8b5cf6',   // Purple
  disk: '#06b6d4',     // Cyan
}

// Metric icons
const METRIC_ICONS = {
  cpu: Cpu,
  memory: MemoryStick,
  disk: HardDrive,
}

// Format percentage
const formatValue = (v) => `${Math.round(v)}%`

// Main Component
function D3NodeResources({ nodes = [], title = "Node Resources" }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const animationRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 400, height: 300 })
  const [currentMetric, setCurrentMetric] = useState('cpu')
  const [isPlaying, setIsPlaying] = useState(true)
  const [metricIndex, setMetricIndex] = useState(0)

  const metrics = ['cpu', 'memory', 'disk']
  const metricLabels = { cpu: 'CPU', memory: 'Memory', disk: 'Disk' }

  // Process node data for the chart
  const chartData = useMemo(() => {
    if (!nodes || nodes.length === 0) return []

    return nodes.map(node => ({
      id: node.id,
      name: node.name?.length > 15 ? node.name.substring(0, 13) + '...' : node.name || 'Unknown',
      fullName: node.name || 'Unknown',
      cpu: node.cpu_usage ?? Math.floor(Math.random() * 60) + 10,
      memory: node.memory_usage ?? Math.floor(Math.random() * 70) + 20,
      disk: node.disk_usage ?? Math.floor(Math.random() * 80) + 10,
      status: node.status,
      isHub: node.is_hub || node.node_type === 'hub',
    })).sort((a, b) => b[currentMetric] - a[currentMetric])
  }, [nodes, currentMetric])

  // Handle resize
  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect()
        setDimensions({ width: Math.max(300, width), height: Math.max(200, height) })
      }
    }
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  // Auto-cycle metrics
  useEffect(() => {
    if (!isPlaying) return

    const interval = setInterval(() => {
      setMetricIndex(prev => {
        const next = (prev + 1) % metrics.length
        setCurrentMetric(metrics[next])
        return next
      })
    }, 3000)

    return () => clearInterval(interval)
  }, [isPlaying])

  // D3 Rendering
  useEffect(() => {
    if (!svgRef.current || chartData.length === 0) return

    const svg = d3.select(svgRef.current)
    const { width, height } = dimensions
    const margin = { top: 30, right: 60, left: 100, bottom: 10 }
    const innerWidth = width - margin.left - margin.right
    const innerHeight = height - margin.top - margin.bottom

    const n = Math.min(chartData.length, 8) // Max 8 bars
    const barSize = Math.min(32, (innerHeight - 20) / n)
    const barPadding = 0.2

    // Get top N nodes by current metric
    const topNodes = [...chartData]
      .sort((a, b) => b[currentMetric] - a[currentMetric])
      .slice(0, n)

    // Scales
    const x = d3.scaleLinear()
      .domain([0, 100])
      .range([0, innerWidth])

    const y = d3.scaleBand()
      .domain(topNodes.map(d => d.id))
      .range([0, n * barSize])
      .padding(barPadding)

    // Clear previous
    svg.selectAll('*').remove()

    // Container group
    const g = svg.append('g')
      .attr('transform', `translate(${margin.left},${margin.top})`)

    // Background grid
    g.append('g')
      .attr('class', 'grid')
      .selectAll('line')
      .data([25, 50, 75, 100])
      .join('line')
      .attr('x1', d => x(d))
      .attr('x2', d => x(d))
      .attr('y1', 0)
      .attr('y2', n * barSize)
      .attr('stroke', '#334155')
      .attr('stroke-dasharray', '2,2')

    // Grid labels
    g.append('g')
      .attr('class', 'grid-labels')
      .selectAll('text')
      .data([0, 25, 50, 75, 100])
      .join('text')
      .attr('x', d => x(d))
      .attr('y', -10)
      .attr('text-anchor', 'middle')
      .attr('fill', '#64748b')
      .attr('font-size', '10px')
      .text(d => `${d}%`)

    // Bars group
    const barsGroup = g.append('g').attr('class', 'bars')

    // Create bars with animation
    const bars = barsGroup.selectAll('g')
      .data(topNodes, d => d.id)
      .join(
        enter => {
          const g = enter.append('g')
            .attr('transform', (d, i) => `translate(0,${y(d.id)})`)

          // Bar background
          g.append('rect')
            .attr('class', 'bar-bg')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', innerWidth)
            .attr('height', y.bandwidth())
            .attr('fill', '#1e293b')
            .attr('rx', 4)

          // Bar fill
          g.append('rect')
            .attr('class', 'bar-fill')
            .attr('x', 0)
            .attr('y', 0)
            .attr('width', 0)
            .attr('height', y.bandwidth())
            .attr('fill', METRIC_COLORS[currentMetric])
            .attr('rx', 4)
            .transition()
            .duration(800)
            .ease(d3.easeCubicOut)
            .attr('width', d => x(d[currentMetric]))

          // Node name label
          g.append('text')
            .attr('class', 'label-name')
            .attr('x', -8)
            .attr('y', y.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('text-anchor', 'end')
            .attr('fill', d => d.isHub ? '#22d3ee' : '#94a3b8')
            .attr('font-size', '11px')
            .attr('font-weight', d => d.isHub ? '600' : '400')
            .text(d => d.name)

          // Hub indicator
          g.filter(d => d.isHub)
            .append('text')
            .attr('class', 'hub-indicator')
            .attr('x', -margin.left + 10)
            .attr('y', y.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('fill', '#06b6d4')
            .attr('font-size', '9px')
            .attr('font-weight', 'bold')
            .text('H')

          // Value label
          g.append('text')
            .attr('class', 'label-value')
            .attr('x', d => x(d[currentMetric]) + 8)
            .attr('y', y.bandwidth() / 2)
            .attr('dy', '0.35em')
            .attr('fill', '#fff')
            .attr('font-size', '11px')
            .attr('font-weight', '600')
            .attr('opacity', 0)
            .text(d => formatValue(d[currentMetric]))
            .transition()
            .delay(400)
            .duration(400)
            .attr('opacity', 1)

          return g
        },
        update => {
          update.transition()
            .duration(800)
            .ease(d3.easeCubicOut)
            .attr('transform', (d, i) => `translate(0,${y(d.id)})`)

          update.select('.bar-fill')
            .transition()
            .duration(800)
            .ease(d3.easeCubicOut)
            .attr('width', d => x(d[currentMetric]))
            .attr('fill', METRIC_COLORS[currentMetric])

          update.select('.label-value')
            .transition()
            .duration(800)
            .attr('x', d => x(d[currentMetric]) + 8)
            .tween('text', function(d) {
              const node = this
              const current = parseFloat(node.textContent) || 0
              const target = d[currentMetric]
              const i = d3.interpolateNumber(current, target)
              return t => { node.textContent = formatValue(i(t)) }
            })

          return update
        }
      )

    // Metric indicator in top right
    const metricLabel = svg.append('g')
      .attr('transform', `translate(${width - 20}, 20)`)

    metricLabel.append('text')
      .attr('text-anchor', 'end')
      .attr('fill', METRIC_COLORS[currentMetric])
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text(metricLabels[currentMetric])

  }, [chartData, dimensions, currentMetric])

  // Empty state
  if (nodes.length === 0) {
    return (
      <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-blue-400" />
          {title}
        </h2>
        <div className="h-[250px] flex items-center justify-center text-slate-500">
          <div className="text-center">
            <Cpu className="w-12 h-12 mx-auto mb-2 opacity-50" />
            <p>No node data available</p>
          </div>
        </div>
      </div>
    )
  }

  const MetricIcon = METRIC_ICONS[currentMetric]

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <MetricIcon className="w-5 h-5" style={{ color: METRIC_COLORS[currentMetric] }} />
          {title}
          <span className="text-sm font-normal text-slate-400">
            ({nodes.length} nodes)
          </span>
        </h2>

        {/* Controls */}
        <div className="flex items-center gap-2">
          {/* Metric selector */}
          <div className="flex items-center gap-1 bg-slate-700/50 rounded-lg p-1">
            {metrics.map((metric, idx) => {
              const Icon = METRIC_ICONS[metric]
              return (
                <button
                  key={metric}
                  onClick={() => {
                    setCurrentMetric(metric)
                    setMetricIndex(idx)
                  }}
                  className={`p-1.5 rounded transition-colors ${
                    currentMetric === metric
                      ? 'bg-slate-600'
                      : 'hover:bg-slate-600/50'
                  }`}
                  title={metricLabels[metric]}
                >
                  <Icon
                    className="w-4 h-4"
                    style={{ color: currentMetric === metric ? METRIC_COLORS[metric] : '#94a3b8' }}
                  />
                </button>
              )
            })}
          </div>

          {/* Play/Pause */}
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-1.5 bg-slate-700/50 hover:bg-slate-600 rounded-lg transition-colors"
            title={isPlaying ? 'Pause' : 'Play'}
          >
            {isPlaying ? (
              <Pause className="w-4 h-4 text-slate-300" />
            ) : (
              <Play className="w-4 h-4 text-slate-300" />
            )}
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 mb-3 text-xs">
        {metrics.map(metric => {
          const Icon = METRIC_ICONS[metric]
          return (
            <div
              key={metric}
              className={`flex items-center gap-1.5 cursor-pointer transition-opacity ${
                currentMetric === metric ? 'opacity-100' : 'opacity-50'
              }`}
              onClick={() => {
                setCurrentMetric(metric)
                setMetricIndex(metrics.indexOf(metric))
              }}
            >
              <span
                className="w-3 h-3 rounded"
                style={{ backgroundColor: METRIC_COLORS[metric] }}
              ></span>
              <span className="text-slate-400">{metricLabels[metric]}</span>
            </div>
          )
        })}
        <div className="flex items-center gap-1.5 ml-2 pl-2 border-l border-slate-600">
          <span className="text-cyan-400 font-bold text-[10px]">H</span>
          <span className="text-slate-400">Hub</span>
        </div>
      </div>

      {/* Chart */}
      <div
        ref={containerRef}
        className="relative overflow-hidden rounded-lg bg-slate-900/30"
        style={{ height: Math.min(300, Math.max(180, nodes.length * 40 + 50)) }}
      >
        <svg
          ref={svgRef}
          width={dimensions.width}
          height={dimensions.height}
        />
      </div>

      {/* Progress indicator */}
      <div className="flex items-center justify-center gap-2 mt-3">
        {metrics.map((metric, idx) => (
          <div
            key={metric}
            className={`w-2 h-2 rounded-full transition-all ${
              idx === metricIndex
                ? 'scale-125'
                : 'opacity-40'
            }`}
            style={{ backgroundColor: METRIC_COLORS[metric] }}
          ></div>
        ))}
        {isPlaying && (
          <span className="text-[10px] text-slate-500 ml-2">Auto-cycling</span>
        )}
      </div>
    </div>
  )
}

export default memo(D3NodeResources)
