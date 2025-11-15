import { z } from 'zod';

/**
 * Common types and schemas for Guacamole API
 */

export const ProtocolSchema = z.enum(['ssh', 'rdp', 'vnc', 'telnet']);
export type Protocol = z.infer<typeof ProtocolSchema>;

export const SecurityModeSchema = z.enum(['any', 'nla', 'tls', 'rdp']);
export type SecurityMode = z.infer<typeof SecurityModeSchema>;

export const PermissionTypeSchema = z.enum([
  'READ',
  'UPDATE',
  'DELETE',
  'ADMINISTER',
]);
export type PermissionType = z.infer<typeof PermissionTypeSchema>;

export const PermissionOpSchema = z.object({
  op: z.enum(['add', 'remove']),
  path: z.string(),
  value: PermissionTypeSchema,
});
export type PermissionOp = z.infer<typeof PermissionOpSchema>;

export const ErrorResponseSchema = z.object({
  message: z.string().optional(),
  error: z.string().optional(),
  statusCode: z.number().optional(),
});
export type ErrorResponse = z.infer<typeof ErrorResponseSchema>;
