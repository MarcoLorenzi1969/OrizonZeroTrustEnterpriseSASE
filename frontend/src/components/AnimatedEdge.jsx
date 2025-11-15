/**
 * Custom Animated Edge Component for ReactFlow
 * Shows animated particles moving along the edge to represent data flow
 * Animation speed and density based on bandwidth usage
 */

import { getBezierPath, EdgeLabelRenderer } from 'reactflow'
import { useEffect, useState } from 'react'

export default function AnimatedEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  style,
  markerEnd,
  markerStart,
  label
}) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  })

  // Extract bandwidth data
  const bandwidth = data?.bandwidth || { in: 0, out: 0, total: 0, usage_percent: 0 }
  const isActive = data?.status === 'active' || bandwidth.total > 0

  // Calculate animation parameters based on bandwidth
  // Higher bandwidth = more particles and faster animation
  const usagePercent = bandwidth.usage_percent || 0

  // Animation speed: 1s (fast) to 5s (slow) based on usage
  const animationDuration = isActive ? Math.max(1, 5 - (usagePercent / 25)) : 10

  // Number of particles: 2-8 based on bandwidth total
  const numParticles = isActive ? Math.max(2, Math.min(8, Math.ceil(bandwidth.total / 2))) : 0

  // Particle size based on bandwidth
  const particleSize = Math.max(4, Math.min(8, 4 + (usagePercent / 20)))

  // Generate particles for both directions
  const particles = []

  if (isActive) {
    // Particles flowing TO target (representing bandwidth_in)
    const incomingParticles = Math.ceil(numParticles * (bandwidth.in / bandwidth.total))
    for (let i = 0; i < incomingParticles; i++) {
      particles.push({
        id: `${id}-in-${i}`,
        direction: 'forward',
        delay: (animationDuration / incomingParticles) * i,
        color: style.stroke
      })
    }

    // Particles flowing FROM target (representing bandwidth_out)
    const outgoingParticles = Math.ceil(numParticles * (bandwidth.out / bandwidth.total))
    for (let i = 0; i < outgoingParticles; i++) {
      particles.push({
        id: `${id}-out-${i}`,
        direction: 'backward',
        delay: (animationDuration / outgoingParticles) * i,
        color: style.stroke
      })
    }
  }

  return (
    <>
      {/* Main edge path */}
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
        markerStart={markerStart}
      />

      {/* Animated particles */}
      {particles.map((particle) => (
        <circle
          key={particle.id}
          r={particleSize}
          fill={particle.color}
          style={{
            opacity: 0.8,
            filter: 'drop-shadow(0 0 2px rgba(255,255,255,0.8))'
          }}
        >
          <animateMotion
            dur={`${animationDuration}s`}
            repeatCount="indefinite"
            begin={`${particle.delay}s`}
            keyPoints={particle.direction === 'forward' ? '0;1' : '1;0'}
            keyTimes="0;1"
            calcMode="linear"
          >
            <mpath href={`#${id}`} />
          </animateMotion>
        </circle>
      ))}

      {/* Edge label with bandwidth info */}
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <div className="bg-slate-800/95 backdrop-blur-sm border border-slate-600 rounded px-2 py-1 text-xs">
            <div className="text-white font-semibold">{label}</div>
            {isActive && (
              <div className="text-slate-300 text-[10px] mt-0.5 space-y-0.5">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-green-400">↓ In:</span>
                  <span className="font-mono">{bandwidth.in} Mbps</span>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <span className="text-blue-400">↑ Out:</span>
                  <span className="font-mono">{bandwidth.out} Mbps</span>
                </div>
                <div className="flex items-center justify-between gap-3 pt-0.5 border-t border-slate-600">
                  <span className="text-slate-400">Total:</span>
                  <span className="font-mono font-semibold">{bandwidth.total} Mbps</span>
                </div>
                <div className="mt-1">
                  <div className="w-full h-1 bg-slate-700 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-green-500 to-blue-500 transition-all duration-500"
                      style={{ width: `${Math.min(100, usagePercent)}%` }}
                    ></div>
                  </div>
                  <div className="text-center text-[9px] text-slate-400 mt-0.5">
                    {usagePercent}% usage
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </EdgeLabelRenderer>
    </>
  )
}
