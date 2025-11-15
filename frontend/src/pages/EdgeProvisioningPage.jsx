/**
 * Edge Node Provisioning Page
 * Dedicated page for generating provision links for new edge nodes
 * For: Marco @ Syneto/Orizon
 */

import { useState } from 'react'
import {
  FiLink,
  FiCopy,
  FiExternalLink,
  FiServer,
  FiCheckCircle,
  FiClock,
  FiShield
} from 'react-icons/fi'
import api from '../services/api'
import { toast } from 'react-toastify'

export default function EdgeProvisioningPage() {
  const [formData, setFormData] = useState({
    name: '',
    location: '',
    description: ''
  })

  const [services, setServices] = useState([
    { name: 'SSH', port: 22, protocol: 'tcp', enabled: true },
    { name: 'HTTP', port: 80, protocol: 'tcp', enabled: false },
    { name: 'HTTPS', port: 443, protocol: 'tcp', enabled: false },
    { name: 'RDP', port: 3389, protocol: 'tcp', enabled: false },
    { name: 'VNC', port: 5900, protocol: 'tcp', enabled: false }
  ])

  const [provisionData, setProvisionData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [copied, setCopied] = useState(false)

  const handleServiceToggle = (index) => {
    const updatedServices = [...services]
    updatedServices[index].enabled = !updatedServices[index].enabled
    setServices(updatedServices)
  }

  const handleGenerateLink = async () => {
    // Validation
    if (!formData.name.trim()) {
      toast.error('Node name is required')
      return
    }

    const enabledServices = services.filter(s => s.enabled)
    if (enabledServices.length === 0) {
      toast.error('Please enable at least one service')
      return
    }

    setLoading(true)

    try {
      const response = await api.post('/nodes/provision', {
        name: formData.name.trim(),
        location: formData.location.trim() || 'Unknown',
        description: formData.description.trim(),
        type: 'edge',
        services: enabledServices.map(s => ({
          name: s.name,
          port: s.port,
          protocol: s.protocol
        }))
      })

      setProvisionData(response.data)
      toast.success('Provision link generated successfully!')
    } catch (error) {
      console.error('Failed to generate provision link:', error)
      toast.error(error.response?.data?.detail || 'Failed to generate provision link')
    } finally {
      setLoading(false)
    }
  }

  const handleCopyLink = () => {
    if (provisionData?.provision_url) {
      navigator.clipboard.writeText(provisionData.provision_url)
      setCopied(true)
      toast.success('Link copied to clipboard!')
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleOpenLink = () => {
    if (provisionData?.provision_url) {
      window.open(provisionData.provision_url, '_blank')
    }
  }

  const handleReset = () => {
    setProvisionData(null)
    setFormData({
      name: '',
      location: '',
      description: ''
    })
    setServices([
      { name: 'SSH', port: 22, protocol: 'tcp', enabled: true },
      { name: 'HTTP', port: 80, protocol: 'tcp', enabled: false },
      { name: 'HTTPS', port: 443, protocol: 'tcp', enabled: false },
      { name: 'RDP', port: 3389, protocol: 'tcp', enabled: false },
      { name: 'VNC', port: 5900, protocol: 'tcp', enabled: false }
    ])
    setCopied(false)
  }

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg flex items-center justify-center">
            <FiLink className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Edge Node Provisioning</h1>
            <p className="text-gray-400 text-sm mt-1">Generate unique provision links for new edge devices</p>
          </div>
        </div>
      </div>

      {!provisionData ? (
        /* Configuration Form */
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
          <div className="p-6 border-b border-gray-700 bg-gradient-to-r from-blue-900/20 to-purple-900/20">
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <FiServer className="w-5 h-5" />
              Node Configuration
            </h2>
            <p className="text-gray-400 text-sm mt-1">Configure your edge node details and services</p>
          </div>

          <div className="p-6 space-y-6">
            {/* Node Information */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white">Node Information</h3>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Node Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="e.g., edge-server-01"
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Location
                </label>
                <input
                  type="text"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                  placeholder="e.g., London Data Center"
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Description
                </label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  placeholder="e.g., Production web server"
                  rows={3}
                  className="w-full px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>
            </div>

            {/* Services Configuration */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium text-white flex items-center gap-2">
                <FiShield className="w-5 h-5 text-blue-400" />
                Services to Enable <span className="text-red-400 text-sm">*</span>
              </h3>
              <p className="text-sm text-gray-400">Select which services should be exposed through the Zero Trust tunnel</p>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {services.map((service, index) => (
                  <ServiceCard
                    key={index}
                    service={service}
                    onToggle={() => handleServiceToggle(index)}
                  />
                ))}
              </div>
            </div>

            {/* Generate Button */}
            <div className="pt-4">
              <button
                onClick={handleGenerateLink}
                disabled={loading}
                className="w-full py-4 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white font-semibold rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                    Generating...
                  </>
                ) : (
                  <>
                    <FiLink className="w-5 h-5" />
                    Generate Provision Link
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      ) : (
        /* Provision Link Display */
        <div className="space-y-6">
          {/* Success Card */}
          <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-700/50 rounded-xl p-6">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center">
                <FiCheckCircle className="w-6 h-6 text-green-400" />
              </div>
              <div>
                <h3 className="text-xl font-semibold text-white">Provision Link Generated!</h3>
                <p className="text-green-400 text-sm">Share this link to configure the edge device</p>
              </div>
            </div>
          </div>

          {/* Node Details */}
          <div className="bg-gray-800 rounded-xl border border-gray-700 p-6">
            <h3 className="text-lg font-semibold text-white mb-4">Node Details</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <p className="text-sm text-gray-400">Name</p>
                <p className="text-white font-medium">{provisionData.node.name}</p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Type</p>
                <p className="text-white font-medium capitalize">{provisionData.node.type}</p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Location</p>
                <p className="text-white font-medium">{provisionData.node.location}</p>
              </div>
              <div>
                <p className="text-sm text-gray-400">Status</p>
                <span className="inline-flex items-center gap-1 px-2 py-1 bg-yellow-900/30 border border-yellow-700/50 rounded text-yellow-400 text-sm">
                  <FiClock className="w-3 h-3" />
                  Pending Provisioning
                </span>
              </div>
            </div>

            {provisionData.node.description && (
              <div className="mt-4">
                <p className="text-sm text-gray-400">Description</p>
                <p className="text-white">{provisionData.node.description}</p>
              </div>
            )}
          </div>

          {/* Provision Link Hero Section */}
          <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-xl p-6">
            <div className="text-center mb-4">
              <div className="inline-flex items-center justify-center w-16 h-16 bg-white bg-opacity-20 rounded-full mb-3">
                <FiExternalLink className="w-8 h-8 text-white" />
              </div>
              <h4 className="text-white font-bold text-xl mb-2">Unique Provision Link</h4>
              <p className="text-blue-100 text-sm">
                Share this link to configure your edge device automatically
              </p>
            </div>

            <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4 mb-4">
              <div className="flex items-center gap-3">
                <div className="flex-1 p-3 bg-gray-900 bg-opacity-50 rounded text-sm text-white font-mono break-all">
                  {provisionData.provision_url}
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={handleCopyLink}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-white bg-opacity-20 hover:bg-opacity-30 text-white font-medium rounded-lg transition-all"
              >
                {copied ? (
                  <>
                    <FiCheckCircle className="w-5 h-5" />
                    Copied!
                  </>
                ) : (
                  <>
                    <FiCopy className="w-5 h-5" />
                    Copy Link
                  </>
                )}
              </button>
              <button
                onClick={handleOpenLink}
                className="flex items-center justify-center gap-2 px-4 py-3 bg-white text-blue-600 font-medium rounded-lg hover:bg-gray-100 transition-all"
              >
                <FiExternalLink className="w-5 h-5" />
                Open Link
              </button>
            </div>
          </div>

          {/* Token Expiration Info */}
          <div className="bg-yellow-900/20 border border-yellow-700/50 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <FiClock className="w-5 h-5 text-yellow-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-yellow-400 font-medium mb-1">Link Expiration</h4>
                <p className="text-yellow-200 text-sm">
                  This provision link will expire in 24 hours. The edge device must be configured before expiration.
                </p>
              </div>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex gap-3">
            <button
              onClick={handleReset}
              className="flex-1 px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-medium rounded-lg transition-colors"
            >
              Generate Another Link
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ServiceCard({ service, onToggle }) {
  return (
    <button
      onClick={onToggle}
      className={`p-4 rounded-lg border-2 transition-all text-left ${
        service.enabled
          ? 'border-blue-500 bg-blue-500/10'
          : 'border-gray-600 bg-gray-900 hover:border-gray-500'
      }`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className={`font-semibold ${service.enabled ? 'text-white' : 'text-gray-400'}`}>
          {service.name}
        </span>
        <div className={`w-5 h-5 rounded border-2 flex items-center justify-center ${
          service.enabled
            ? 'bg-blue-500 border-blue-500'
            : 'border-gray-600'
        }`}>
          {service.enabled && (
            <FiCheckCircle className="w-4 h-4 text-white" />
          )}
        </div>
      </div>
      <div className="text-sm text-gray-400">
        Port: <span className="font-mono">{service.port}</span> / {service.protocol.toUpperCase()}
      </div>
    </button>
  )
}
