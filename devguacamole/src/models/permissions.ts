import { z } from 'zod';
import { PermissionOpSchema, PermissionTypeSchema } from './common';

/**
 * Permission models for Guacamole API
 */

export const UserPermissionsSchema = z.object({
  connectionPermissions: z.record(z.array(PermissionTypeSchema)).optional(),
  connectionGroupPermissions: z.record(z.array(PermissionTypeSchema)).optional(),
  sharingProfilePermissions: z.record(z.array(PermissionTypeSchema)).optional(),
  activeConnectionPermissions: z.record(z.array(PermissionTypeSchema)).optional(),
  userPermissions: z.record(z.array(PermissionTypeSchema)).optional(),
  userGroupPermissions: z.record(z.array(PermissionTypeSchema)).optional(),
  systemPermissions: z.array(z.string()).optional(),
});
export type UserPermissions = z.infer<typeof UserPermissionsSchema>;

export const PermissionPatchSchema = z.array(PermissionOpSchema);
export type PermissionPatch = z.infer<typeof PermissionPatchSchema>;

export const GrantPermissionRequestSchema = z.object({
  username: z.string().min(1),
  connectionId: z.string().min(1),
  permissions: z.array(PermissionTypeSchema),
});
export type GrantPermissionRequest = z.infer<typeof GrantPermissionRequestSchema>;

export { PermissionOpSchema, PermissionTypeSchema };
export type { PermissionOp, PermissionType } from './common';
