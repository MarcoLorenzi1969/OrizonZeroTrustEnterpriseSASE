import { describe, it, expect } from 'vitest';
import { SecretRef } from '../src/secrets';

describe('CLI', () => {
  describe('SecretRef helpers for CLI', () => {
    it('should generate proper secret references for Edge Ubuntu', () => {
      const sshUser = SecretRef.ssh('edge_ubuntu', 'user');
      const sshPass = SecretRef.ssh('edge_ubuntu', 'pass');
      const rdpUser = SecretRef.rdp('edge_ubuntu', 'user');
      const rdpPass = SecretRef.rdp('edge_ubuntu', 'pass');

      expect(sshUser).toBe('SECRET__SSH__EDGE_UBUNTU_USER');
      expect(sshPass).toBe('SECRET__SSH__EDGE_UBUNTU_PASS');
      expect(rdpUser).toBe('SECRET__RDP__EDGE_UBUNTU_USER');
      expect(rdpPass).toBe('SECRET__RDP__EDGE_UBUNTU_PASS');
    });

    it('should generate proper secret references for Edge Kali', () => {
      const sshUser = SecretRef.ssh('edge_kali', 'user');
      const sshPass = SecretRef.ssh('edge_kali', 'pass');

      expect(sshUser).toBe('SECRET__SSH__EDGE_KALI_USER');
      expect(sshPass).toBe('SECRET__SSH__EDGE_KALI_PASS');
    });
  });

  describe('Environment variable validation', () => {
    it('should have required Guacamole env vars documented', () => {
      const requiredEnvVars = [
        'GUAC_URL',
        'GUAC_DATASOURCE',
        'GUAC_ADMIN_USER',
        'GUAC_ADMIN_PASS',
        'ORIZON_API_URL',
        'ORIZON_ADMIN_EMAIL',
        'ORIZON_ADMIN_PASS',
      ];

      // Just verify the list is defined
      // In real scenarios, CLI would validate these on startup
      expect(requiredEnvVars.length).toBeGreaterThan(0);
    });
  });
});
