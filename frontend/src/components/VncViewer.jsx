/**
 * Orizon Zero Trust Connect - VNC Viewer Component
 * For: Marco @ Syneto/Orizon
 *
 * Remote Desktop viewer using noVNC (HTML5 VNC client)
 *
 * Features:
 * - Full VNC remote desktop in browser
 * - Zero Trust secure connection via WebSocket + JWT
 * - Quality settings (low/medium/high/lossless)
 * - Fullscreen support
 * - Connection status monitoring
 * - Auto-reconnect on disconnect
 */

import React, { useEffect, useRef, useState } from 'react';
import RFB from '@novnc/novnc/core/rfb';
import { AlertCircle, Monitor, Maximize, Minimize, Power, Settings } from 'lucide-react';

const VncViewer = ({
  sessionId,
  sessionToken,
  vncGatewayUrl = 'wss://46.101.189.126:6080',
  onDisconnect,
  quality = 'medium',
  viewOnly = false
}) => {
  const canvasRef = useRef(null);
  const rfbRef = useRef(null);

  const [status, setStatus] = useState('connecting'); // connecting, connected, disconnected, error
  const [error, setError] = useState(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [currentQuality, setCurrentQuality] = useState(quality);
  const [stats, setStats] = useState({
    bytesReceived: 0,
    framesSent: 0,
    latency: 0,
  });

  useEffect(() => {
    if (!sessionId || !sessionToken || !canvasRef.current) {
      return;
    }

    initializeVNC();

    return () => {
      disconnectVNC();
    };
  }, [sessionId, sessionToken]);

  const initializeVNC = () => {
    try {
      console.log('🔗 Initializing VNC connection...');
      console.log('Session ID:', sessionId);
      console.log('Gateway URL:', vncGatewayUrl);

      // Build WebSocket URL
      const wsUrl = `${vncGatewayUrl}/vnc/${sessionId}?token=${sessionToken}`;

      console.log('Connecting to:', wsUrl);

      // Create RFB instance
      const rfb = new RFB(canvasRef.current, wsUrl, {
        shared: true,
        credentials: {},
        repeaterID: '',
        wsProtocols: ['binary'],
      });

      // Apply quality settings
      applyQualitySettings(rfb, currentQuality);

      // View-only mode
      rfb.viewOnly = viewOnly;

      // Event handlers
      rfb.addEventListener('connect', handleConnect);
      rfb.addEventListener('disconnect', handleDisconnect);
      rfb.addEventListener('credentialsrequired', handleCredentials);
      rfb.addEventListener('securityfailure', handleSecurityFailure);
      rfb.addEventListener('desktopname', handleDesktopName);

      rfbRef.current = rfb;

      setStatus('connecting');

    } catch (error) {
      console.error('❌ Failed to initialize VNC:', error);
      setError(error.message);
      setStatus('error');
    }
  };

  const applyQualitySettings = (rfb, quality) => {
    switch (quality) {
      case 'low':
        // Low quality: 8-bit color, high compression
        rfb.compressionLevel = 9;
        rfb.qualityLevel = 1;
        console.log('📊 Quality: LOW (8-bit color, high compression)');
        break;

      case 'medium':
        // Medium quality: 16-bit color, medium compression
        rfb.compressionLevel = 6;
        rfb.qualityLevel = 6;
        console.log('📊 Quality: MEDIUM (16-bit color, medium compression)');
        break;

      case 'high':
        // High quality: 24-bit color, low compression
        rfb.compressionLevel = 2;
        rfb.qualityLevel = 9;
        console.log('📊 Quality: HIGH (24-bit color, low compression)');
        break;

      case 'lossless':
        // Lossless: 32-bit color, no compression
        rfb.compressionLevel = 0;
        rfb.qualityLevel = 10;
        console.log('📊 Quality: LOSSLESS (32-bit color, no compression)');
        break;
    }
  };

  const handleConnect = (e) => {
    console.log('✅ VNC connected:', e);
    setStatus('connected');
    setError(null);
  };

  const handleDisconnect = (e) => {
    console.log('🔌 VNC disconnected:', e);
    setStatus('disconnected');

    if (onDisconnect) {
      onDisconnect();
    }

    // Auto-reconnect after 5 seconds if not a clean disconnect
    if (e.detail.clean === false && status !== 'error') {
      console.log('🔄 Auto-reconnecting in 5s...');
      setTimeout(() => {
        if (canvasRef.current) {
          initializeVNC();
        }
      }, 5000);
    }
  };

  const handleCredentials = (e) => {
    console.log('🔐 Credentials required:', e);
    // For now, we don't support VNC password (Zero Trust handles auth via JWT)
    setError('VNC authentication not supported. Use JWT token authentication.');
    setStatus('error');
  };

  const handleSecurityFailure = (e) => {
    console.error('❌ Security failure:', e);
    setError(`Security failure: ${e.detail.status}`);
    setStatus('error');
  };

  const handleDesktopName = (e) => {
    console.log('🖥️ Desktop name:', e.detail.name);
  };

  const disconnectVNC = () => {
    if (rfbRef.current) {
      console.log('🛑 Disconnecting VNC...');
      rfbRef.current.disconnect();
      rfbRef.current = null;
    }
  };

  const toggleFullscreen = () => {
    const container = canvasRef.current?.parentElement;

    if (!document.fullscreenElement) {
      container?.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const changeQuality = (newQuality) => {
    setCurrentQuality(newQuality);

    if (rfbRef.current) {
      applyQualitySettings(rfbRef.current, newQuality);
    }

    setShowSettings(false);
  };

  const sendCtrlAltDel = () => {
    if (rfbRef.current) {
      rfbRef.current.sendCtrlAltDel();
      console.log('⌨️ Sent Ctrl+Alt+Del');
    }
  };

  // Status badge component
  const StatusBadge = () => {
    const statusConfig = {
      connecting: { color: 'bg-yellow-500', text: 'Connecting...', icon: Monitor },
      connected: { color: 'bg-green-500', text: 'Connected', icon: Monitor },
      disconnected: { color: 'bg-gray-500', text: 'Disconnected', icon: Monitor },
      error: { color: 'bg-red-500', text: 'Error', icon: AlertCircle },
    };

    const config = statusConfig[status] || statusConfig.disconnected;
    const Icon = config.icon;

    return (
      <div className="flex items-center gap-2 px-3 py-1.5 bg-gray-800 rounded-lg">
        <div className={`w-2 h-2 rounded-full ${config.color} animate-pulse`} />
        <Icon className="w-4 h-4 text-gray-300" />
        <span className="text-sm text-gray-300">{config.text}</span>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-gray-900">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <h2 className="text-lg font-semibold text-white">Remote Desktop</h2>
          <StatusBadge />
        </div>

        <div className="flex items-center gap-2">
          {/* Quality Settings */}
          <div className="relative">
            <button
              onClick={() => setShowSettings(!showSettings)}
              className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              title="Settings"
            >
              <Settings className="w-5 h-5" />
            </button>

            {showSettings && (
              <div className="absolute right-0 top-full mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-xl z-50">
                <div className="p-2">
                  <div className="text-xs font-semibold text-gray-400 px-2 py-1">Quality</div>
                  {['low', 'medium', 'high', 'lossless'].map((q) => (
                    <button
                      key={q}
                      onClick={() => changeQuality(q)}
                      className={`w-full text-left px-3 py-2 text-sm rounded ${
                        currentQuality === q
                          ? 'bg-blue-600 text-white'
                          : 'text-gray-300 hover:bg-gray-700'
                      }`}
                    >
                      {q.charAt(0).toUpperCase() + q.slice(1)}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Fullscreen */}
          <button
            onClick={toggleFullscreen}
            className="p-2 text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
            title={isFullscreen ? 'Exit Fullscreen' : 'Fullscreen'}
          >
            {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
          </button>

          {/* Ctrl+Alt+Del */}
          {!viewOnly && (
            <button
              onClick={sendCtrlAltDel}
              className="px-3 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              title="Send Ctrl+Alt+Del"
            >
              Ctrl+Alt+Del
            </button>
          )}

          {/* Disconnect */}
          <button
            onClick={disconnectVNC}
            className="p-2 text-red-400 hover:text-red-300 hover:bg-red-900/20 rounded-lg transition-colors"
            title="Disconnect"
          >
            <Power className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* VNC Canvas Container */}
      <div className="flex-1 relative overflow-auto bg-black">
        {error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/95 z-10">
            <div className="max-w-md p-6 bg-red-900/20 border border-red-500/50 rounded-lg">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
                <div>
                  <h3 className="text-lg font-semibold text-red-500 mb-2">Connection Error</h3>
                  <p className="text-sm text-gray-300">{error}</p>
                  <button
                    onClick={initializeVNC}
                    className="mt-4 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm font-medium transition-colors"
                  >
                    Retry Connection
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {status === 'connecting' && !error && (
          <div className="absolute inset-0 flex items-center justify-center bg-gray-900/95">
            <div className="text-center">
              <div className="w-16 h-16 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
              <p className="text-gray-300 text-lg">Connecting to remote desktop...</p>
              <p className="text-gray-500 text-sm mt-2">Session: {sessionId}</p>
            </div>
          </div>
        )}

        {/* noVNC Canvas */}
        <div
          ref={canvasRef}
          className="flex items-center justify-center min-h-full"
          style={{ touchAction: 'none' }}
        />
      </div>

      {/* Footer Info */}
      <div className="px-4 py-2 bg-gray-800 border-t border-gray-700 text-xs text-gray-400">
        <div className="flex items-center justify-between">
          <div>
            Session ID: <span className="font-mono text-gray-300">{sessionId}</span>
          </div>
          <div className="flex gap-4">
            <span>Quality: <span className="text-gray-300">{currentQuality}</span></span>
            {viewOnly && <span className="text-yellow-500">⚠️ View Only</span>}
          </div>
        </div>
      </div>
    </div>
  );
};

export default VncViewer;
