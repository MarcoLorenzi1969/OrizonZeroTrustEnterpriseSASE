/**
 * Secret Store exports
 */

export { SecretStore, SecretRef } from './SecretStore';
export { EnvSecretStore } from './EnvSecretStore';
export { MockSecretStore } from './MockSecretStore';

/**
 * Default secret store factory
 */
import { EnvSecretStore } from './EnvSecretStore';
import { SecretStore } from './SecretStore';

export function createDefaultSecretStore(): SecretStore {
  return new EnvSecretStore();
}
