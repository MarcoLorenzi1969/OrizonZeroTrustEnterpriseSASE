import { z } from 'zod';

/**
 * Authentication models for Guacamole API
 */

export const AuthTokenSchema = z.object({
  authToken: z.string(),
  username: z.string(),
  dataSource: z.string(),
  availableDataSources: z.array(z.string()),
});
export type AuthToken = z.infer<typeof AuthTokenSchema>;

export const LoginRequestSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1),
});
export type LoginRequest = z.infer<typeof LoginRequestSchema>;

export const OrizonTokenSchema = z.object({
  access_token: z.string(),
  token_type: z.string().default('bearer'),
  expires_in: z.number().optional(),
  user: z
    .object({
      email: z.string().email(),
      role: z.string(),
      id: z.string().uuid().optional(),
    })
    .optional(),
});
export type OrizonToken = z.infer<typeof OrizonTokenSchema>;

export const OrizonLoginRequestSchema = z.object({
  email: z.string().email(),
  password: z.string().min(1),
});
export type OrizonLoginRequest = z.infer<typeof OrizonLoginRequestSchema>;
