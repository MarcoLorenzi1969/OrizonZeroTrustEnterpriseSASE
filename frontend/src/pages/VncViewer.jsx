/**
 * Orizon Zero Trust Connect - VNC Viewer Page
 * For: Marco @ Syneto/Orizon
 *
 * Full-screen VNC viewer page
 */

import React, { useEffect, useState } from 'react';
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import axios from 'axios';
import VncViewer from '../components/VncViewer';

const VncViewerPage = () => {
  const { sessionId } = useParams();
  const location = useLocation();
  const navigate = useNavigate();

  const [session, setSession] = useState(location.state?.session || null);
  const [loading, setLoading] = useState(!session);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!session) {
      fetchSession();
    }
  }, [sessionId]);

  const fetchSession = async () => {
    try {
      const response = await axios.get(`/api/v1/vnc/sessions/${sessionId}`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        },
      });

      setSession(response.data);
      setError(null);
    } catch (err) {
      console.error('Error fetching VNC session:', err);
      setError(err.response?.data?.detail || 'Failed to fetch VNC session');
    } finally {
      setLoading(false);
    }
  };

  const handleDisconnect = () => {
    navigate('/vnc');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-300">Loading VNC session...</p>
        </div>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-900">
        <div className="text-center max-w-md">
          <div className="text-red-500 text-6xl mb-4">⚠️</div>
          <h2 className="text-2xl font-bold text-white mb-2">Session Not Found</h2>
          <p className="text-gray-400 mb-6">{error || 'VNC session does not exist or has been terminated'}</p>
          <button
            onClick={() => navigate('/vnc')}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
            Back to Sessions
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <button
          onClick={() => navigate('/vnc')}
          className="flex items-center gap-2 px-3 py-1.5 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          <span className="text-sm">Back to Sessions</span>
        </button>

        <div className="text-sm text-gray-400">
          <span className="font-medium text-gray-300">{session.name}</span>
          {session.description && (
            <span className="ml-2">• {session.description}</span>
          )}
        </div>
      </div>

      {/* VNC Viewer */}
      <div className="flex-1">
        <VncViewer
          sessionId={session.id}
          sessionToken={session.session_token}
          vncGatewayUrl={import.meta.env.VITE_VNC_GATEWAY_URL || 'wss://46.101.189.126:6080'}
          onDisconnect={handleDisconnect}
          quality={session.quality}
          viewOnly={session.view_only}
        />
      </div>
    </div>
  );
};

export default VncViewerPage;
