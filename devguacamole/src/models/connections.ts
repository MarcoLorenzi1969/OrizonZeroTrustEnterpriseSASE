import { z } from 'zod';
import { ProtocolSchema, SecurityModeSchema } from './common';

/**
 * Connection models for Guacamole API
 */

// SSH Connection Parameters
export const SSHParametersSchema = z.object({
  hostname: z.string().min(1),
  port: z.string().default('22'),
  username: z.string().min(1),
  password: z.string().optional(),
  'private-key': z.string().optional(),
  passphrase: z.string().optional(),
  'enable-sftp': z.string().default('true'),
  'sftp-root-directory': z.string().optional(),
  'term-type': z.string().default('xterm-256color'),
  'color-scheme': z.string().default('gray-black'),
});
export type SSHParameters = z.infer<typeof SSHParametersSchema>;

// RDP Connection Parameters
export const RDPParametersSchema = z.object({
  hostname: z.string().min(1),
  port: z.string().default('3389'),
  username: z.string().min(1),
  password: z.string().min(1),
  domain: z.string().optional(),
  security: SecurityModeSchema.default('any'),
  'ignore-cert': z.string().default('true'),
  'enable-drive': z.string().default('false'),
  'enable-clipboard': z.string().default('false'),
  'enable-printing': z.string().default('false'),
  'console-audio': z.string().default('false'),
  'server-layout': z.string().default('en-us-qwerty'),
  width: z.string().optional(),
  height: z.string().optional(),
  dpi: z.string().optional(),
  'color-depth': z.string().default('32'),
});
export type RDPParameters = z.infer<typeof RDPParametersSchema>;

// Generic Connection Payload
export const ConnectionPayloadSchema = z.object({
  name: z.string().min(1),
  protocol: ProtocolSchema,
  parameters: z.union([SSHParametersSchema, RDPParametersSchema]),
  attributes: z
    .object({
      'max-connections': z.string().optional(),
      'max-connections-per-user': z.string().optional(),
    })
    .optional(),
  parentIdentifier: z.string().optional(),
});
export type ConnectionPayload = z.infer<typeof ConnectionPayloadSchema>;

// Connection Response
export const ConnectionSchema = z.object({
  identifier: z.string(),
  name: z.string(),
  protocol: ProtocolSchema,
  parameters: z.record(z.string()).optional(),
  attributes: z.record(z.string().nullable()).optional(),
  parentIdentifier: z.string().optional(),
  activeConnections: z.number().optional(),
});
export type Connection = z.infer<typeof ConnectionSchema>;

// Connection List Response
export const ConnectionListSchema = z.record(ConnectionSchema);
export type ConnectionList = z.infer<typeof ConnectionListSchema>;
