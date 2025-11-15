/**
 * Orizon Zero Trust Connect - VNC Sessions Management Page
 * For: Marco @ Syneto/Orizon
 *
 * Manage VNC remote desktop sessions
 */

import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Monitor,
  Plus,
  Trash2,
  Eye,
  Clock,
  Activity,
  AlertCircle,
  CheckCircle,
  XCircle,
} from 'lucide-react';
import axios from 'axios';

const VncSessions = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [creating, setCreating] = useState(false);

  // Form state
  const [formData, setFormData] = useState({
    node_id: '',
    name: '',
    description: '',
    quality: 'medium',
    screen_width: 1920,
    screen_height: 1080,
    view_only: false,
    max_duration_seconds: 300,
  });

  useEffect(() => {
    fetchSessions();
    fetchNodes();

    // Auto-refresh every 10 seconds
    const interval = setInterval(fetchSessions, 10000);
    return () => clearInterval(interval);
  }, []);

  const fetchSessions = async () => {
    try {
      const response = await axios.get('/api/v1/vnc/sessions', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      setSessions(response.data.sessions || []);
      setError(null);
    } catch (err) {
      console.error('Error fetching VNC sessions:', err);
      setError(err.response?.data?.detail || 'Failed to fetch VNC sessions');
    } finally {
      setLoading(false);
    }
  };

  const fetchNodes = async () => {
    try {
      const response = await axios.get('/api/v1/nodes', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      setNodes(response.data.nodes || []);
    } catch (err) {
      console.error('Error fetching nodes:', err);
    }
  };

  const createSession = async (e) => {
    e.preventDefault();
    setCreating(true);

    try {
      const response = await axios.post(
        '/api/v1/vnc/sessions',
        formData,
        {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('token')}`,
          },
        }
      );

      const newSession = response.data;

      // Navigate to viewer
      navigate(`/vnc/viewer/${newSession.id}`, {
        state: { session: newSession },
      });

      setShowCreateModal(false);
      setFormData({
        node_id: '',
        name: '',
        description: '',
        quality: 'medium',
        screen_width: 1920,
        screen_height: 1080,
        view_only: false,
        max_duration_seconds: 300,
      });
    } catch (err) {
      console.error('Error creating VNC session:', err);
      setError(err.response?.data?.detail || 'Failed to create VNC session');
    } finally {
      setCreating(false);
    }
  };

  const terminateSession = async (sessionId) => {
    if (!confirm('Are you sure you want to terminate this VNC session?')) {
      return;
    }

    try {
      await axios.delete(`/api/v1/vnc/sessions/${sessionId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      fetchSessions();
    } catch (err) {
      console.error('Error terminating session:', err);
      setError(err.response?.data?.detail || 'Failed to terminate session');
    }
  };

  const openSession = (session) => {
    navigate(`/vnc/viewer/${session.id}`, {
      state: { session },
    });
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { color: 'bg-yellow-500', text: 'Pending', icon: Clock },
      connecting: { color: 'bg-blue-500', text: 'Connecting', icon: Activity },
      active: { color: 'bg-green-500', text: 'Active', icon: CheckCircle },
      disconnected: { color: 'bg-gray-500', text: 'Disconnected', icon: XCircle },
      expired: { color: 'bg-orange-500', text: 'Expired', icon: Clock },
      error: { color: 'bg-red-500', text: 'Error', icon: AlertCircle },
      terminated: { color: 'bg-gray-500', text: 'Terminated', icon: XCircle },
    };

    const config = statusConfig[status] || statusConfig.disconnected;
    const Icon = config.icon;

    return (
      <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium text-white ${config.color}`}>
        <Icon className="w-3.5 h-3.5" />
        {config.text}
      </span>
    );
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-300">Loading VNC sessions...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-3xl font-bold text-white mb-2">VNC Remote Desktop</h1>
            <p className="text-gray-400">Secure remote desktop sessions via Zero Trust</p>
          </div>

          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            <Plus className="w-5 h-5" />
            New Session
          </button>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 bg-red-900/20 border border-red-500/50 rounded-lg flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="text-red-500 font-semibold">Error</h3>
              <p className="text-gray-300 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Sessions Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {sessions.map((session) => (
            <div key={session.id} className="bg-gray-800 rounded-lg border border-gray-700 p-5">
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-blue-600 rounded-lg">
                    <Monitor className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold">{session.name}</h3>
                    <p className="text-sm text-gray-400">{session.description || 'No description'}</p>
                  </div>
                </div>
              </div>

              <div className="space-y-2 mb-4 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Status</span>
                  {getStatusBadge(session.status)}
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Quality</span>
                  <span className="text-white capitalize">{session.quality}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-gray-400">Resolution</span>
                  <span className="text-white">{session.screen_width}×{session.screen_height}</span>
                </div>

                {session.remaining_seconds > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Expires in</span>
                    <span className="text-yellow-500">{formatDuration(session.remaining_seconds)}</span>
                  </div>
                )}

                {session.uptime_seconds > 0 && (
                  <div className="flex items-center justify-between">
                    <span className="text-gray-400">Uptime</span>
                    <span className="text-green-500">{formatDuration(session.uptime_seconds)}</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2">
                {(session.status === 'active' || session.status === 'connecting') && (
                  <button
                    onClick={() => openSession(session)}
                    className="flex-1 flex items-center justify-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    <Eye className="w-4 h-4" />
                    Open
                  </button>
                )}

                <button
                  onClick={() => terminateSession(session.id)}
                  className="flex items-center justify-center gap-2 px-3 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}

          {sessions.length === 0 && (
            <div className="col-span-full text-center py-12">
              <Monitor className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-semibold text-gray-400 mb-2">No VNC Sessions</h3>
              <p className="text-gray-500 mb-4">Create your first remote desktop session</p>
              <button
                onClick={() => setShowCreateModal(true)}
                className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                <Plus className="w-5 h-5" />
                New Session
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Create Session Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-800 rounded-lg max-w-2xl w-full p-6">
            <h2 className="text-2xl font-bold text-white mb-6">Create VNC Session</h2>

            <form onSubmit={createSession} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Node</label>
                <select
                  value={formData.node_id}
                  onChange={(e) => setFormData({ ...formData, node_id: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  required
                >
                  <option value="">Select a node...</option>
                  {nodes.filter(n => n.status === 'online').map((node) => (
                    <option key={node.id} value={node.id}>
                      {node.name} ({node.hostname})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Session Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., Production Server Desktop"
                  required
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Description (optional)</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="What's this session for?"
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Quality</label>
                  <select
                    value={formData.quality}
                    onChange={(e) => setFormData({ ...formData, quality: e.target.value })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="low">Low (Slow network)</option>
                    <option value="medium">Medium (Default)</option>
                    <option value="high">High (LAN)</option>
                    <option value="lossless">Lossless (Very fast network)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Duration (seconds)</label>
                  <input
                    type="number"
                    value={formData.max_duration_seconds}
                    onChange={(e) => setFormData({ ...formData, max_duration_seconds: parseInt(e.target.value) })}
                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                    min={60}
                    max={3600}
                  />
                </div>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="view_only"
                  checked={formData.view_only}
                  onChange={(e) => setFormData({ ...formData, view_only: e.target.checked })}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-700 text-blue-600 focus:ring-2 focus:ring-blue-500"
                />
                <label htmlFor="view_only" className="text-sm text-gray-300">
                  View Only Mode (no keyboard/mouse input)
                </label>
              </div>

              <div className="flex gap-3 pt-4">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 text-white rounded-lg font-medium transition-colors"
                >
                  {creating ? 'Creating...' : 'Create Session'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default VncSessions;
