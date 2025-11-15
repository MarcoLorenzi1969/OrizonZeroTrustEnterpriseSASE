import { SecretStore } from './SecretStore';

/**
 * Environment Variable Secret Store
 * Retrieves secrets from environment variables
 */
export class EnvSecretStore implements SecretStore {
  private readonly prefix: string;

  constructor(prefix: string = '') {
    this.prefix = prefix;
  }

  async getSecret(ref: string): Promise<string> {
    const key = this.prefix ? `${this.prefix}${ref}` : ref;
    const value = process.env[key];

    if (!value) {
      throw new Error(
        `Secret not found: ${ref}. ` +
          `Please set environment variable ${key} or update your .env file.`
      );
    }

    return value;
  }

  async hasSecret(ref: string): Promise<boolean> {
    const key = this.prefix ? `${this.prefix}${ref}` : ref;
    return process.env[key] !== undefined;
  }

  /**
   * Get all secrets matching a pattern
   * @param pattern - RegExp pattern to match against secret keys
   * @returns Map of matched secrets (key -> value)
   */
  async getSecretsMatching(pattern: RegExp): Promise<Map<string, string>> {
    const secrets = new Map<string, string>();

    for (const [key, value] of Object.entries(process.env)) {
      if (pattern.test(key) && value) {
        secrets.set(key, value);
      }
    }

    return secrets;
  }

  /**
   * List all available secret keys (for debugging)
   * WARNING: Use only in development/debugging
   */
  listSecretKeys(): string[] {
    return Object.keys(process.env).filter((key) => key.startsWith('SECRET__'));
  }
}
