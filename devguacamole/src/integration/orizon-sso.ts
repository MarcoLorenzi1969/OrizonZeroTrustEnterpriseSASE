import axios, { AxiosInstance } from 'axios';
import { OrizonToken, OrizonTokenSchema, OrizonLoginRequest } from '../models/auth';
import winston from 'winston';

/**
 * Orizon SSO Integration
 * Handles authentication with Orizon hub and token management
 */

export interface OrizonConfig {
  apiUrl: string;
  verifyTLS?: boolean;
  logger?: winston.Logger;
}

export class OrizonSSO {
  private api: AxiosInstance;
  private logger: winston.Logger;
  private currentToken?: OrizonToken;

  constructor(config: OrizonConfig) {
    this.logger =
      config.logger ||
      winston.createLogger({
        level: process.env.LOG_LEVEL || 'info',
        format: winston.format.combine(
          winston.format.timestamp(),
          winston.format.errors({ stack: true }),
          winston.format.json()
        ),
        transports: [new winston.transports.Console()],
      });

    this.api = axios.create({
      baseURL: config.apiUrl,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      httpsAgent: config.verifyTLS === false ? { rejectUnauthorized: false } : undefined,
    });

    if (config.verifyTLS === false) {
      this.logger.warn('⚠️  TLS verification is DISABLED for Orizon API');
    }
  }

  /**
   * Authenticate with Orizon
   */
  async login(email: string, password: string): Promise<OrizonToken> {
    try {
      const response = await this.api.post<OrizonToken>('/auth/login', {
        email,
        password,
      });

      this.currentToken = OrizonTokenSchema.parse(response.data);
      this.logger.info('Successfully authenticated with Orizon', {
        email,
        role: this.currentToken.user?.role,
      });

      // Set token for future requests
      this.api.defaults.headers.common['Authorization'] =
        `Bearer ${this.currentToken.access_token}`;

      return this.currentToken;
    } catch (error: any) {
      this.logger.error('Orizon authentication failed', {
        error: error.message,
        status: error.response?.status,
      });
      throw new Error(`Orizon authentication failed: ${error.message}`);
    }
  }

  /**
   * Get current Orizon user info
   */
  async getCurrentUser(): Promise<any> {
    if (!this.currentToken) {
      throw new Error('Not authenticated with Orizon. Call login() first.');
    }

    try {
      const response = await this.api.get('/auth/me');
      return response.data;
    } catch (error: any) {
      this.logger.error('Failed to get current user', { error: error.message });
      throw error;
    }
  }

  /**
   * Check if user has admin role
   */
  isAdmin(): boolean {
    return this.currentToken?.user?.role === 'superuser' ||
           this.currentToken?.user?.role === 'admin';
  }

  /**
   * Get Guacamole credentials for the authenticated user
   * This maps Orizon user to Guacamole credentials
   */
  async getGuacamoleCredentials(): Promise<{
    username: string;
    password: string;
  }> {
    if (!this.currentToken) {
      throw new Error('Not authenticated with Orizon. Call login() first.');
    }

    // For admin users, use admin credentials
    if (this.isAdmin()) {
      return {
        username: process.env.GUAC_ADMIN_USER || 'guacadmin',
        password: process.env.GUAC_ADMIN_PASS || 'guacadmin',
      };
    }

    // For regular users, we could map to Guacamole users
    // For now, use a read-only guest account or create user-specific accounts
    // This would be enhanced with proper user provisioning in Guacamole

    throw new Error(
      'Non-admin SSO not yet implemented. Admin users can access Guacamole with full permissions.'
    );
  }

  /**
   * Create or sync Guacamole user from Orizon user
   * This would be called when a user first accesses Guacamole via SSO
   */
  async syncGuacamoleUser(guacamoleClient: any): Promise<void> {
    if (!this.currentToken) {
      throw new Error('Not authenticated with Orizon');
    }

    // TODO: Implement user provisioning in Guacamole
    // 1. Check if user exists in Guacamole
    // 2. Create user if needed
    // 3. Sync permissions based on Orizon role
    // 4. Grant access to appropriate connections

    this.logger.info('Guacamole user sync not yet implemented');
  }

  /**
   * Get current token
   */
  getToken(): OrizonToken | undefined {
    return this.currentToken;
  }

  /**
   * Check if authenticated
   */
  isAuthenticated(): boolean {
    return !!this.currentToken;
  }

  /**
   * Logout from Orizon
   */
  async logout(): Promise<void> {
    if (this.currentToken) {
      try {
        await this.api.post('/auth/logout');
      } catch (error: any) {
        this.logger.warn('Logout request failed', { error: error.message });
      } finally {
        this.currentToken = undefined;
        delete this.api.defaults.headers.common['Authorization'];
      }
    }
  }
}

/**
 * Create Orizon SSO client from environment
 */
export function createOrizonSSO(config?: Partial<OrizonConfig>): OrizonSSO {
  return new OrizonSSO({
    apiUrl: config?.apiUrl || process.env.ORIZON_API_URL || 'https://46.101.189.126/api/v1',
    verifyTLS: config?.verifyTLS ?? process.env.GUAC_VERIFY_TLS !== 'false',
    logger: config?.logger,
  });
}
