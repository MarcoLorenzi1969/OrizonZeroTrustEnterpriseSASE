import { ApiClient } from './api';
import { SecretStore } from './secrets';
import {
  AuthToken,
  AuthTokenSchema,
  Connection,
  ConnectionSchema,
  ConnectionPayload,
  ConnectionList,
  ConnectionListSchema,
  UserPermissions,
  UserPermissionsSchema,
  PermissionOp,
} from './models';

/**
 * High-level Guacamole API functions
 */

export interface GuacamoleConfig {
  url: string;
  datasource: string;
  verifyTLS?: boolean;
  secretStore?: SecretStore;
}

export class GuacamoleClient {
  private api: ApiClient;
  private datasource: string;
  private secretStore?: SecretStore;
  private currentToken?: string;

  constructor(config: GuacamoleConfig) {
    this.api = new ApiClient({
      baseURL: config.url,
      verifyTLS: config.verifyTLS !== false,
    });
    this.datasource = config.datasource;
    this.secretStore = config.secretStore;
  }

  /**
   * Authenticate and get token
   */
  async getToken(username: string, password: string): Promise<AuthToken> {
    // Guacamole expects form data for login
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    const response = await this.api.post<AuthToken>('/api/tokens', formData.toString(), {
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });

    const authToken = AuthTokenSchema.parse(response);
    this.currentToken = authToken.authToken;
    this.api.setAuthToken(authToken.authToken);

    return authToken;
  }

  /**
   * Create a new connection
   */
  async createConnection(payload: ConnectionPayload): Promise<Connection> {
    if (!this.currentToken) {
      throw new Error('Not authenticated. Call getToken() first.');
    }

    // Resolve secret references in parameters if secret store is available
    const resolvedPayload = await this.resolveSecrets(payload);

    const response = await this.api.post<Connection>(
      `/api/session/data/${this.datasource}/connections`,
      resolvedPayload
    );

    return ConnectionSchema.parse(response);
  }

  /**
   * Get all connections
   */
  async getConnections(): Promise<ConnectionList> {
    if (!this.currentToken) {
      throw new Error('Not authenticated. Call getToken() first.');
    }

    const response = await this.api.get<ConnectionList>(
      `/api/session/data/${this.datasource}/connections`
    );

    return ConnectionListSchema.parse(response);
  }

  /**
   * Get a specific connection
   */
  async getConnection(connectionId: string): Promise<Connection> {
    if (!this.currentToken) {
      throw new Error('Not authenticated. Call getToken() first.');
    }

    const response = await this.api.get<Connection>(
      `/api/session/data/${this.datasource}/connections/${connectionId}`
    );

    return ConnectionSchema.parse(response);
  }

  /**
   * Delete a connection
   */
  async deleteConnection(connectionId: string): Promise<void> {
    if (!this.currentToken) {
      throw new Error('Not authenticated. Call getToken() first.');
    }

    await this.api.delete(`/api/session/data/${this.datasource}/connections/${connectionId}`);
  }

  /**
   * Get user permissions
   */
  async getUserPermissions(username: string): Promise<UserPermissions> {
    if (!this.currentToken) {
      throw new Error('Not authenticated. Call getToken() first.');
    }

    const response = await this.api.get<UserPermissions>(
      `/api/session/data/${this.datasource}/users/${username}/permissions`
    );

    return UserPermissionsSchema.parse(response);
  }

  /**
   * Set user permissions (PATCH operation)
   */
  async setUserPermissions(username: string, ops: PermissionOp[]): Promise<void> {
    if (!this.currentToken) {
      throw new Error('Not authenticated. Call getToken() first.');
    }

    await this.api.patch(
      `/api/session/data/${this.datasource}/users/${username}/permissions`,
      ops
    );
  }

  /**
   * Grant READ permission on a connection to a user
   */
  async grantConnectionAccess(
    username: string,
    connectionId: string,
    permissions: string[] = ['READ']
  ): Promise<void> {
    const ops: PermissionOp[] = permissions.map((perm) => ({
      op: 'add',
      path: `/connectionPermissions/${connectionId}`,
      value: perm as any,
    }));

    await this.setUserPermissions(username, ops);
  }

  /**
   * Revoke connection access from a user
   */
  async revokeConnectionAccess(username: string, connectionId: string): Promise<void> {
    const ops: PermissionOp[] = [
      {
        op: 'remove',
        path: `/connectionPermissions/${connectionId}`,
        value: 'READ',
      },
    ];

    await this.setUserPermissions(username, ops);
  }

  /**
   * Create SSH connection with defaults
   */
  async createSSHConnection(params: {
    name: string;
    hostname: string;
    port?: string;
    username: string;
    password?: string;
    privateKey?: string;
    enableSFTP?: boolean;
  }): Promise<Connection> {
    const payload: ConnectionPayload = {
      name: params.name,
      protocol: 'ssh',
      parameters: {
        hostname: params.hostname,
        port: params.port || '22',
        username: params.username,
        password: params.password,
        'private-key': params.privateKey,
        'enable-sftp': params.enableSFTP !== false ? 'true' : 'false',
        'term-type': 'xterm-256color',
        'color-scheme': 'gray-black',
      },
      attributes: {
        'max-connections': '2',
        'max-connections-per-user': '1',
      },
    };

    return this.createConnection(payload);
  }

  /**
   * Create RDP connection with secure defaults
   */
  async createRDPConnection(params: {
    name: string;
    hostname: string;
    port?: string;
    username: string;
    password: string;
    domain?: string;
    security?: 'any' | 'nla' | 'tls' | 'rdp';
    enableDrive?: boolean;
    enableClipboard?: boolean;
  }): Promise<Connection> {
    const payload: ConnectionPayload = {
      name: params.name,
      protocol: 'rdp',
      parameters: {
        hostname: params.hostname,
        port: params.port || '3389',
        username: params.username,
        password: params.password,
        domain: params.domain,
        security: params.security || 'any',
        'ignore-cert': 'true',
        'enable-drive': params.enableDrive ? 'true' : 'false',
        'enable-clipboard': params.enableClipboard ? 'true' : 'false',
        'enable-printing': 'false',
        'console-audio': 'false',
        'server-layout': 'en-us-qwerty',
        'color-depth': '32',
      },
      attributes: {
        'max-connections': '2',
        'max-connections-per-user': '1',
      },
    };

    return this.createConnection(payload);
  }

  /**
   * Resolve secret references in connection payload
   */
  private async resolveSecrets(payload: ConnectionPayload): Promise<ConnectionPayload> {
    if (!this.secretStore) {
      return payload;
    }

    const resolvedParams: Record<string, string> = {};

    for (const [key, value] of Object.entries(payload.parameters)) {
      if (typeof value === 'string' && value.startsWith('SECRET__')) {
        try {
          resolvedParams[key] = await this.secretStore.getSecret(value);
        } catch (error) {
          throw new Error(`Failed to resolve secret ${value}: ${(error as Error).message}`);
        }
      } else {
        resolvedParams[key] = value as string;
      }
    }

    return {
      ...payload,
      parameters: resolvedParams as any,
    };
  }

  /**
   * Logout and clear token
   */
  async logout(): Promise<void> {
    if (this.currentToken) {
      try {
        await this.api.delete(`/api/tokens/${this.currentToken}`);
      } finally {
        this.currentToken = undefined;
        this.api.clearAuthToken();
      }
    }
  }

  /**
   * Check if client is authenticated
   */
  isAuthenticated(): boolean {
    return !!this.currentToken;
  }

  /**
   * Get current token
   */
  getAuthToken(): string | undefined {
    return this.currentToken;
  }
}

/**
 * Convenience function to create a Guacamole client from environment
 */
export function createGuacamoleClient(config?: Partial<GuacamoleConfig>): GuacamoleClient {
  return new GuacamoleClient({
    url: config?.url || process.env.GUAC_URL || 'https://167.71.33.70/guacamole',
    datasource: config?.datasource || process.env.GUAC_DATASOURCE || 'mysql',
    verifyTLS: config?.verifyTLS ?? process.env.GUAC_VERIFY_TLS !== 'false',
    secretStore: config?.secretStore,
  });
}
