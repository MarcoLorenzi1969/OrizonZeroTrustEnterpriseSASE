import axios, { AxiosInstance, AxiosError, AxiosRequestConfig } from 'axios';
import axiosRetry from 'axios-retry';
import winston from 'winston';
import https from 'https';

/**
 * Low-level HTTP client for Guacamole API
 */

export interface ApiClientConfig {
  baseURL: string;
  verifyTLS?: boolean;
  timeout?: number;
  retries?: number;
  logger?: winston.Logger;
}

export class ApiClient {
  private client: AxiosInstance;
  private logger: winston.Logger;

  constructor(config: ApiClientConfig) {
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

    // Create axios instance
    this.client = axios.create({
      baseURL: config.baseURL,
      timeout: config.timeout || 30000,
      headers: {
        'Content-Type': 'application/json',
      },
      httpsAgent: config.verifyTLS === false
        ? new https.Agent({ rejectUnauthorized: false })
        : undefined,
    });

    // Configure retries with exponential backoff
    axiosRetry(this.client, {
      retries: config.retries || 3,
      retryDelay: axiosRetry.exponentialDelay,
      retryCondition: (error: AxiosError) => {
        return (
          axiosRetry.isNetworkOrIdempotentRequestError(error) ||
          (error.response?.status ?? 0) >= 500
        );
      },
      onRetry: (retryCount, error) => {
        this.logger.warn(`Retry attempt ${retryCount} for ${error.config?.url}`, {
          error: error.message,
        });
      },
    });

    // Request interceptor for logging (with secret redaction)
    this.client.interceptors.request.use(
      (config) => {
        this.logger.debug('API Request', {
          method: config.method?.toUpperCase(),
          url: config.url,
          headers: this.redactSecrets(config.headers || {}),
        });
        return config;
      },
      (error) => {
        this.logger.error('Request Error', { error: error.message });
        return Promise.reject(error);
      }
    );

    // Response interceptor for logging
    this.client.interceptors.response.use(
      (response) => {
        this.logger.debug('API Response', {
          status: response.status,
          url: response.config.url,
        });
        return response;
      },
      (error: AxiosError) => {
        if (error.response) {
          this.logger.error('API Error Response', {
            status: error.response.status,
            url: error.config?.url,
            data: error.response.data,
          });
        } else if (error.request) {
          this.logger.error('API No Response', {
            url: error.config?.url,
            message: error.message,
          });
        } else {
          this.logger.error('API Request Setup Error', {
            message: error.message,
          });
        }
        return Promise.reject(error);
      }
    );

    if (config.verifyTLS === false) {
      this.logger.warn('⚠️  TLS verification is DISABLED. This is insecure for production!');
    }
  }

  /**
   * Make a GET request
   */
  async get<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.get<T>(url, config);
    return response.data;
  }

  /**
   * Make a POST request
   */
  async post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.post<T>(url, data, config);
    return response.data;
  }

  /**
   * Make a PATCH request
   */
  async patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.patch<T>(url, data, config);
    return response.data;
  }

  /**
   * Make a DELETE request
   */
  async delete<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.delete<T>(url, config);
    return response.data;
  }

  /**
   * Make a PUT request
   */
  async put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    const response = await this.client.put<T>(url, data, config);
    return response.data;
  }

  /**
   * Set authorization token
   */
  setAuthToken(token: string): void {
    this.client.defaults.headers.common['Guacamole-Token'] = token;
  }

  /**
   * Clear authorization token
   */
  clearAuthToken(): void {
    delete this.client.defaults.headers.common['Guacamole-Token'];
  }

  /**
   * Redact sensitive information from objects
   */
  private redactSecrets(obj: Record<string, unknown>): Record<string, unknown> {
    const redacted: Record<string, unknown> = {};
    const sensitiveKeys = ['password', 'token', 'authorization', 'guacamole-token'];

    for (const [key, value] of Object.entries(obj)) {
      if (sensitiveKeys.some((k) => key.toLowerCase().includes(k))) {
        redacted[key] = '[REDACTED]';
      } else {
        redacted[key] = value;
      }
    }

    return redacted;
  }
}
