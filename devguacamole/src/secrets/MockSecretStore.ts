import { SecretStore } from './SecretStore';

/**
 * Mock Secret Store for testing
 * Stores secrets in memory
 */
export class MockSecretStore implements SecretStore {
  private secrets: Map<string, string> = new Map();

  constructor(initialSecrets?: Record<string, string>) {
    if (initialSecrets) {
      for (const [key, value] of Object.entries(initialSecrets)) {
        this.secrets.set(key, value);
      }
    }
  }

  async getSecret(ref: string): Promise<string> {
    const value = this.secrets.get(ref);
    if (!value) {
      throw new Error(`Secret not found: ${ref}`);
    }
    return value;
  }

  async hasSecret(ref: string): Promise<boolean> {
    return this.secrets.has(ref);
  }

  /**
   * Set a secret (for testing)
   */
  setSecret(ref: string, value: string): void {
    this.secrets.set(ref, value);
  }

  /**
   * Remove a secret (for testing)
   */
  deleteSecret(ref: string): boolean {
    return this.secrets.delete(ref);
  }

  /**
   * Clear all secrets (for testing)
   */
  clear(): void {
    this.secrets.clear();
  }

  /**
   * Get all secrets (for testing/debugging)
   */
  getAllSecrets(): Map<string, string> {
    return new Map(this.secrets);
  }
}
