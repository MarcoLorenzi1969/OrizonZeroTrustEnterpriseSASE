/**
 * Create Node Modal Component with Unique Link Provisioning
 * For: Marco @ Syneto/Orizon
 *
 * 3-Step Wizard:
 * 1. Basic node information
 * 2. Service selection
 * 3. Unique provision link and script download
 */

import { useState } from 'react'
import { FiX, FiChevronRight, FiChevronLeft, FiDownload, FiCheck, FiPlus, FiTrash2, FiCopy, FiExternalLink } from 'react-icons/fi'
import { FaLinux, FaApple, FaWindows } from 'react-icons/fa'
import api from '../../services/api'
import toast from 'react-hot-toast'

export default function CreateNodeModal({ onClose, onCreate }) {
  // Wizard step (1, 2, 3)
  const [currentStep, setCurrentStep] = useState(1)

  // Form data
  const [formData, setFormData] = useState({
    name: '',
    hostname: '',
    node_type: 'linux',
    public_ip: '',
    private_ip: '',
    location: '',
    tags: []
  })

  // Services
  const [services, setServices] = useState([])
  const [newService, setNewService] = useState({ name: '', port: '', protocol: 'tcp', enabled: true })

  // Provisioning data
  const [provisionData, setProvisionData] = useState(null)
  const [createdNodeId, setCreatedNodeId] = useState(null)

  const [loading, setLoading] = useState(false)

  // Node types
  const nodeTypes = [
    { value: 'linux', label: 'Linux', icon: <FaLinux className="w-8 h-8" />, description: 'Ubuntu, Debian, CentOS, RHEL' },
    { value: 'macos', label: 'macOS', icon: <FaApple className="w-8 h-8" />, description: 'macOS 10.15+' },
    { value: 'windows', label: 'Windows', icon: <FaWindows className="w-8 h-8" />, description: 'Windows 10/11, Server 2019+' },
  ]

  // Add service
  const handleAddService = () => {
    if (!newService.name || !newService.port) {
      toast.error('Service name and port are required')
      return
    }

    const port = parseInt(newService.port)
    if (isNaN(port) || port < 1 || port > 65535) {
      toast.error('Port must be between 1 and 65535')
      return
    }

    setServices([...services, { ...newService, port }])
    setNewService({ name: '', port: '', protocol: 'tcp', enabled: true })
  }

  // Remove service
  const handleRemoveService = (index) => {
    setServices(services.filter((_, i) => i !== index))
  }

  // Step 1: Create node
  const handleCreateNode = async () => {
    if (!formData.name || !formData.hostname) {
      toast.error('Name and hostname are required')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/nodes', {
        name: formData.name,
        hostname: formData.hostname,
        node_type: formData.node_type,
        public_ip: formData.public_ip || null,
        private_ip: formData.private_ip || null,
        location: formData.location || null,
        tags: formData.tags,
      })

      const nodeId = response.data.id
      setCreatedNodeId(nodeId)
      toast.success('Node created successfully')
      setCurrentStep(2)
    } catch (error) {
      console.error('Failed to create node:', error)
      toast.error(error.response?.data?.detail || 'Failed to create node')
    } finally {
      setLoading(false)
    }
  }

  // Step 2: Generate provision data
  const handleGenerateProvisionData = async () => {
    if (!createdNodeId) {
      toast.error('Node not created yet')
      return
    }

    setLoading(true)
    try {
      const response = await api.post(`/nodes/${createdNodeId}/provision`, services)
      setProvisionData(response.data)
      toast.success('Provision data generated!')
      setCurrentStep(3)
    } catch (error) {
      console.error('Failed to generate provision data:', error)
      toast.error(error.response?.data?.detail || 'Failed to generate provision data')
    } finally {
      setLoading(false)
    }
  }

  // Copy provision link to clipboard
  const handleCopyLink = async () => {
    if (!provisionData || !provisionData.provision_url) {
      toast.error('Provision URL not available')
      return
    }

    try {
      await navigator.clipboard.writeText(provisionData.provision_url)
      toast.success('Link copied to clipboard!')
    } catch (error) {
      // Fallback for older browsers
      const textArea = document.createElement('textarea')
      textArea.value = provisionData.provision_url
      document.body.appendChild(textArea)
      textArea.select()
      document.execCommand('copy')
      document.body.removeChild(textArea)
      toast.success('Link copied to clipboard!')
    }
  }

  // Open provision link in new tab
  const handleOpenLink = () => {
    if (!provisionData || !provisionData.provision_url) {
      toast.error('Provision URL not available')
      return
    }

    window.open(provisionData.provision_url, '_blank')
  }

  // Download script
  const handleDownloadScript = (osType) => {
    if (!provisionData || !provisionData.download_urls[osType]) {
      toast.error('Download URL not available')
      return
    }

    // Open download URL in new tab
    window.open(provisionData.download_urls[osType], '_blank')
    toast.success(`Downloading ${osType} script...`)
  }

  // Complete wizard
  const handleComplete = () => {
    if (onCreate) {
      onCreate(formData)
    }
    onClose()
  }

  // Step indicators
  const steps = [
    { number: 1, title: 'Node Info', description: 'Basic information' },
    { number: 2, title: 'Services', description: 'Configure services' },
    { number: 3, title: 'Provision', description: 'Link & scripts' },
  ]

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-6 border-b border-gray-700">
          <div>
            <h2 className="text-2xl font-bold text-white">Add New Node</h2>
            <p className="text-sm text-gray-400 mt-1">Step {currentStep} of 3</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition"
          >
            <FiX className="w-6 h-6" />
          </button>
        </div>

        {/* Step Indicators */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
          {steps.map((step, index) => (
            <div key={step.number} className="flex items-center flex-1">
              <div className="flex items-center">
                <div
                  className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition ${
                    currentStep >= step.number
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-400'
                  }`}
                >
                  {currentStep > step.number ? <FiCheck /> : step.number}
                </div>
                <div className="ml-3">
                  <div className="text-sm font-medium text-white">{step.title}</div>
                  <div className="text-xs text-gray-400">{step.description}</div>
                </div>
              </div>
              {index < steps.length - 1 && (
                <div className={`flex-1 h-1 mx-4 rounded ${
                  currentStep > step.number ? 'bg-blue-600' : 'bg-gray-700'
                }`} />
              )}
            </div>
          ))}
        </div>

        {/* Step Content */}
        <div className="p-6">
          {/* Step 1: Basic Info */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-4">Basic Node Information</h3>

              {/* Name */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Node Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Office-NYC-Node"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              {/* Hostname */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Hostname *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g., node-nyc-01"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.hostname}
                  onChange={(e) => setFormData({ ...formData, hostname: e.target.value })}
                />
              </div>

              {/* Node Type */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Platform *
                </label>
                <div className="grid grid-cols-3 gap-3">
                  {nodeTypes.map((type) => (
                    <button
                      key={type.value}
                      type="button"
                      onClick={() => setFormData({ ...formData, node_type: type.value })}
                      className={`p-4 rounded-lg border-2 text-center transition ${
                        formData.node_type === type.value
                          ? 'border-blue-500 bg-blue-500 bg-opacity-20'
                          : 'border-gray-600 hover:border-gray-500'
                      }`}
                    >
                      <div className="flex justify-center mb-2 text-white">{type.icon}</div>
                      <div className="text-white font-semibold">{type.label}</div>
                      <div className="text-xs text-gray-400 mt-1">{type.description}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* IP Addresses */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Public IP (optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., 203.0.113.1"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.public_ip}
                    onChange={(e) => setFormData({ ...formData, public_ip: e.target.value })}
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Private IP (optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., 192.168.1.10"
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={formData.private_ip}
                    onChange={(e) => setFormData({ ...formData, private_ip: e.target.value })}
                  />
                </div>
              </div>

              {/* Location */}
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Location (optional)
                </label>
                <input
                  type="text"
                  placeholder="e.g., New York, USA"
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  value={formData.location}
                  onChange={(e) => setFormData({ ...formData, location: e.target.value })}
                />
              </div>
            </div>
          )}

          {/* Step 2: Services */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-white mb-4">Configure Services</h3>
              <p className="text-sm text-gray-400 mb-4">
                Add services that will be accessible through this node
              </p>

              {/* Services List */}
              {services.length > 0 && (
                <div className="mb-4 space-y-2">
                  {services.map((service, index) => (
                    <div
                      key={index}
                      className="flex items-center justify-between p-3 bg-gray-700 rounded-lg"
                    >
                      <div className="flex items-center space-x-4">
                        <div className="text-white font-medium">{service.name}</div>
                        <div className="text-sm text-gray-400">
                          Port {service.port} • {service.protocol.toUpperCase()}
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveService(index)}
                        className="text-red-400 hover:text-red-300"
                      >
                        <FiTrash2 className="w-5 h-5" />
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Add Service Form */}
              <div className="p-4 bg-gray-700 rounded-lg space-y-3">
                <h4 className="text-sm font-medium text-white">Add Service</h4>
                <div className="grid grid-cols-12 gap-3">
                  <div className="col-span-5">
                    <input
                      type="text"
                      placeholder="Service name (e.g., SSH)"
                      className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={newService.name}
                      onChange={(e) => setNewService({ ...newService, name: e.target.value })}
                    />
                  </div>
                  <div className="col-span-3">
                    <input
                      type="number"
                      placeholder="Port"
                      min="1"
                      max="65535"
                      className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={newService.port}
                      onChange={(e) => setNewService({ ...newService, port: e.target.value })}
                    />
                  </div>
                  <div className="col-span-3">
                    <select
                      className="w-full px-3 py-2 bg-gray-600 border border-gray-500 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                      value={newService.protocol}
                      onChange={(e) => setNewService({ ...newService, protocol: e.target.value })}
                    >
                      <option value="tcp">TCP</option>
                      <option value="udp">UDP</option>
                    </select>
                  </div>
                  <div className="col-span-1">
                    <button
                      type="button"
                      onClick={handleAddService}
                      className="w-full h-full bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center justify-center transition"
                    >
                      <FiPlus className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              </div>

              {services.length === 0 && (
                <div className="text-center py-8 text-gray-400">
                  No services added yet. Add services to expose through this node.
                </div>
              )}
            </div>
          )}

          {/* Step 3: Provision Link & Scripts */}
          {currentStep === 3 && provisionData && (
            <div className="space-y-6">
              <h3 className="text-lg font-semibold text-white mb-4">Provision Your Node</h3>

              {/* Provision Link - Hero Section */}
              <div className="bg-gradient-to-br from-blue-600 to-purple-600 rounded-lg p-6">
                <div className="text-center mb-4">
                  <div className="inline-flex items-center justify-center w-16 h-16 bg-white bg-opacity-20 rounded-full mb-3">
                    <FiExternalLink className="w-8 h-8 text-white" />
                  </div>
                  <h4 className="text-white font-bold text-xl mb-2">Unique Provision Link</h4>
                  <p className="text-blue-100 text-sm">
                    Share this link to configure your edge device automatically
                  </p>
                </div>

                {/* Link Display */}
                <div className="bg-white bg-opacity-10 backdrop-blur-sm rounded-lg p-4 mb-4">
                  <div className="flex items-center gap-3">
                    <div className="flex-1 p-3 bg-gray-900 bg-opacity-50 rounded text-sm text-white font-mono break-all">
                      {provisionData.provision_url}
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={handleCopyLink}
                    className="flex items-center justify-center gap-2 px-6 py-3 bg-white text-blue-600 font-semibold rounded-lg hover:bg-gray-100 transition shadow-lg"
                  >
                    <FiCopy className="w-5 h-5" />
                    Copy Link
                  </button>
                  <button
                    onClick={handleOpenLink}
                    className="flex items-center justify-center gap-2 px-6 py-3 bg-gray-900 bg-opacity-50 text-white font-semibold rounded-lg hover:bg-gray-800 transition border border-white border-opacity-20"
                  >
                    <FiExternalLink className="w-5 h-5" />
                    Open Link
                  </button>
                </div>
              </div>

              {/* Download Scripts */}
              <div>
                <h4 className="text-white font-semibold mb-3">Or Download Script Directly</h4>
                <p className="text-sm text-gray-400 mb-4">
                  Skip the link and download the installation script for your platform
                </p>
                <div className="grid grid-cols-3 gap-4">
                  <button
                    onClick={() => handleDownloadScript('linux')}
                    className="p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition group"
                  >
                    <FaLinux className="w-12 h-12 text-white mx-auto mb-2" />
                    <div className="text-white font-semibold mb-1">Linux</div>
                    <div className="text-xs text-gray-400 mb-3">Ubuntu, Debian, CentOS, RHEL</div>
                    <div className="flex items-center justify-center text-blue-400 text-sm">
                      <FiDownload className="w-4 h-4 mr-1" />
                      Download
                    </div>
                  </button>

                  <button
                    onClick={() => handleDownloadScript('macos')}
                    className="p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition group"
                  >
                    <FaApple className="w-12 h-12 text-white mx-auto mb-2" />
                    <div className="text-white font-semibold mb-1">macOS</div>
                    <div className="text-xs text-gray-400 mb-3">macOS 10.15+</div>
                    <div className="flex items-center justify-center text-blue-400 text-sm">
                      <FiDownload className="w-4 h-4 mr-1" />
                      Download
                    </div>
                  </button>

                  <button
                    onClick={() => handleDownloadScript('windows')}
                    className="p-4 bg-gray-700 hover:bg-gray-600 rounded-lg transition group"
                  >
                    <FaWindows className="w-12 h-12 text-white mx-auto mb-2" />
                    <div className="text-white font-semibold mb-1">Windows</div>
                    <div className="text-xs text-gray-400 mb-3">Win 10/11, Server 2019+</div>
                    <div className="flex items-center justify-center text-blue-400 text-sm">
                      <FiDownload className="w-4 h-4 mr-1" />
                      Download
                    </div>
                  </button>
                </div>
              </div>

              {/* Instructions */}
              <div className="bg-blue-500 bg-opacity-10 border border-blue-500 rounded-lg p-4">
                <h4 className="text-blue-400 font-semibold mb-2">How to Use</h4>
                <ol className="text-sm text-gray-300 space-y-2 list-decimal list-inside">
                  <li><strong>Share the link</strong> with your device operator (email, chat, SMS)</li>
                  <li><strong>Open the link</strong> on the target device browser</li>
                  <li><strong>Download the script</strong> for your platform from the landing page</li>
                  <li><strong>Run the script</strong> with administrator privileges</li>
                  <li>The node will automatically connect to the hub</li>
                </ol>
              </div>

              {/* Token Expiration */}
              <div className="text-center text-sm text-gray-400">
                ⏰ Provision link expires: {new Date(provisionData.expires_at).toLocaleString()}
              </div>
            </div>
          )}
        </div>

        {/* Navigation Buttons */}
        <div className="flex justify-between items-center p-6 border-t border-gray-700">
          <div>
            {currentStep > 1 && currentStep < 3 && (
              <button
                type="button"
                onClick={() => setCurrentStep(currentStep - 1)}
                className="flex items-center px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
              >
                <FiChevronLeft className="w-5 h-5 mr-1" />
                Back
              </button>
            )}
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-6 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition"
            >
              {currentStep === 3 ? 'Close' : 'Cancel'}
            </button>

            {currentStep === 1 && (
              <button
                type="button"
                onClick={handleCreateNode}
                disabled={loading}
                className="flex items-center px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
              >
                {loading ? 'Creating...' : 'Next'}
                <FiChevronRight className="w-5 h-5 ml-1" />
              </button>
            )}

            {currentStep === 2 && (
              <button
                type="button"
                onClick={handleGenerateProvisionData}
                disabled={loading}
                className="flex items-center px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition disabled:opacity-50"
              >
                {loading ? 'Generating...' : 'Generate Provision Link'}
                <FiChevronRight className="w-5 h-5 ml-1" />
              </button>
            )}

            {currentStep === 3 && (
              <button
                type="button"
                onClick={handleComplete}
                className="flex items-center px-6 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition"
              >
                <FiCheck className="w-5 h-5 mr-1" />
                Complete
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
