/**
 * Orizon Zero Trust Connect - Guacamole Integration
 * Main entry point for the library
 */

// Core API
export { ApiClient } from './api';
export type { ApiClientConfig } from './api';

// Guacamole Client
export { GuacamoleClient, createGuacamoleClient } from './guac';
export type { GuacamoleConfig } from './guac';

// Secret Store
export { SecretStore, SecretRef, EnvSecretStore, MockSecretStore, createDefaultSecretStore } from './secrets';

// Models
export * from './models/common';
export * from './models/auth';
export * from './models/connections';
export * from './models/permissions';

// Orizon Integration
export { OrizonSSO, createOrizonSSO } from './integration/orizon-sso';
export type { OrizonConfig } from './integration/orizon-sso';

export { NodeSync } from './integration/node-sync';
export type { OrizonNode, NodeSyncConfig } from './integration/node-sync';
