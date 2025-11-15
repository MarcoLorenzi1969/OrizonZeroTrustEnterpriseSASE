/**
 * Secret Store Interface
 * Provides abstraction for retrieving secrets from various backends
 */

export interface SecretStore {
  /**
   * Retrieve a secret by reference
   * @param ref - Secret reference (e.g., "SECRET__SSH__EDGE_UBUNTU_USER")
   * @returns Promise resolving to the secret value
   * @throws Error if secret not found or retrieval fails
   */
  getSecret(ref: string): Promise<string>;

  /**
   * Check if a secret exists
   * @param ref - Secret reference
   * @returns Promise resolving to boolean
   */
  hasSecret(ref: string): Promise<boolean>;

  /**
   * Initialize the secret store (optional)
   * Called before first use
   */
  init?(): Promise<void>;

  /**
   * Cleanup resources (optional)
   * Called when store is no longer needed
   */
  cleanup?(): Promise<void>;
}

/**
 * Secret reference helper
 * Formats secret references in a consistent way
 */
export class SecretRef {
  static ssh(host: string, field: 'user' | 'pass' | 'key'): string {
    return `SECRET__SSH__${host.toUpperCase()}_${field.toUpperCase()}`;
  }

  static rdp(host: string, field: 'user' | 'pass'): string {
    return `SECRET__RDP__${host.toUpperCase()}_${field.toUpperCase()}`;
  }

  static custom(category: string, name: string, field?: string): string {
    const parts = ['SECRET', category.toUpperCase(), name.toUpperCase()];
    if (field) {
      parts.push(field.toUpperCase());
    }
    return parts.join('__');
  }
}
