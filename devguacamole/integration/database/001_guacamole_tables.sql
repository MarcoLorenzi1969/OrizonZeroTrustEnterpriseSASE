-- Orizon Guacamole Integration - Database Schema
-- Add Guacamole-related tables to existing Orizon database

-- Table: guacamole_servers
-- Stores Guacamole server instances
CREATE TABLE IF NOT EXISTS guacamole_servers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    url VARCHAR(500) NOT NULL,
    datasource VARCHAR(50) NOT NULL DEFAULT 'mysql',
    admin_username VARCHAR(255) NOT NULL,
    admin_password_encrypted TEXT NOT NULL,
    verify_tls BOOLEAN DEFAULT TRUE,
    status VARCHAR(50) DEFAULT 'offline',
    last_health_check TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: guacamole_connections
-- Maps Orizon nodes to Guacamole connections
CREATE TABLE IF NOT EXISTS guacamole_connections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    node_id UUID NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    guacamole_server_id UUID NOT NULL REFERENCES guacamole_servers(id) ON DELETE CASCADE,
    connection_id VARCHAR(255) NOT NULL, -- Guacamole connection ID
    connection_name VARCHAR(255) NOT NULL,
    protocol VARCHAR(50) NOT NULL, -- ssh, rdp, vnc
    status VARCHAR(50) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(node_id, protocol),
    UNIQUE(guacamole_server_id, connection_id)
);

-- Table: guacamole_user_mappings
-- Maps Orizon users to Guacamole users (for SSO)
CREATE TABLE IF NOT EXISTS guacamole_user_mappings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    guacamole_server_id UUID NOT NULL REFERENCES guacamole_servers(id) ON DELETE CASCADE,
    guacamole_username VARCHAR(255) NOT NULL,
    auto_provision BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, guacamole_server_id)
);

-- Table: guacamole_sessions
-- Track active Guacamole sessions for SSO
CREATE TABLE IF NOT EXISTS guacamole_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    guacamole_server_id UUID NOT NULL REFERENCES guacamole_servers(id) ON DELETE CASCADE,
    guacamole_token TEXT NOT NULL,
    connection_id VARCHAR(255),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Table: guacamole_access_logs
-- Audit log for Guacamole access
CREATE TABLE IF NOT EXISTS guacamole_access_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    connection_id UUID REFERENCES guacamole_connections(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL, -- login, access_connection, logout
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_guac_connections_node_id ON guacamole_connections(node_id);
CREATE INDEX IF NOT EXISTS idx_guac_connections_server_id ON guacamole_connections(guacamole_server_id);
CREATE INDEX IF NOT EXISTS idx_guac_user_mappings_user_id ON guacamole_user_mappings(user_id);
CREATE INDEX IF NOT EXISTS idx_guac_sessions_user_id ON guacamole_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_guac_sessions_expires_at ON guacamole_sessions(expires_at);
CREATE INDEX IF NOT EXISTS idx_guac_access_logs_user_id ON guacamole_access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_guac_access_logs_created_at ON guacamole_access_logs(created_at);

-- Insert default Guacamole server
INSERT INTO guacamole_servers (
    name,
    url,
    datasource,
    admin_username,
    admin_password_encrypted,
    verify_tls,
    status
) VALUES (
    'Primary Guacamole Hub',
    'https://167.71.33.70/guacamole',
    'mysql',
    'orizonzerotrust',
    'ripper-FfFIlBelloccio.1969F-web', -- TODO: Encrypt in production
    FALSE,
    'online'
) ON CONFLICT (name) DO NOTHING;

-- Grant permissions (adjust user as needed)
-- GRANT ALL PRIVILEGES ON guacamole_servers TO orizonuser;
-- GRANT ALL PRIVILEGES ON guacamole_connections TO orizonuser;
-- GRANT ALL PRIVILEGES ON guacamole_user_mappings TO orizonuser;
-- GRANT ALL PRIVILEGES ON guacamole_sessions TO orizonuser;
-- GRANT ALL PRIVILEGES ON guacamole_access_logs TO orizonuser;

COMMENT ON TABLE guacamole_servers IS 'Guacamole server instances for remote access';
COMMENT ON TABLE guacamole_connections IS 'Maps Orizon nodes to Guacamole connections';
COMMENT ON TABLE guacamole_user_mappings IS 'SSO user mapping between Orizon and Guacamole';
COMMENT ON TABLE guacamole_sessions IS 'Active Guacamole SSO sessions';
COMMENT ON TABLE guacamole_access_logs IS 'Audit log for Guacamole access';
