import { describe, it, expect, beforeEach } from 'vitest';
import { MockSecretStore, EnvSecretStore, SecretRef } from '../src/secrets';

describe('SecretStore', () => {
  describe('MockSecretStore', () => {
    let store: MockSecretStore;

    beforeEach(() => {
      store = new MockSecretStore({
        'SECRET__SSH__TEST_USER': 'testuser',
        'SECRET__SSH__TEST_PASS': 'testpass',
      });
    });

    it('should retrieve existing secrets', async () => {
      const secret = await store.getSecret('SECRET__SSH__TEST_USER');
      expect(secret).toBe('testuser');
    });

    it('should throw error for non-existent secrets', async () => {
      await expect(store.getSecret('SECRET__NONEXISTENT')).rejects.toThrow(
        'Secret not found: SECRET__NONEXISTENT'
      );
    });

    it('should check if secret exists', async () => {
      const exists = await store.hasSecret('SECRET__SSH__TEST_USER');
      const notExists = await store.hasSecret('SECRET__NONEXISTENT');

      expect(exists).toBe(true);
      expect(notExists).toBe(false);
    });

    it('should set new secrets', () => {
      store.setSecret('SECRET__NEW', 'newvalue');
      expect(store.hasSecret('SECRET__NEW')).resolves.toBe(true);
    });

    it('should delete secrets', () => {
      const deleted = store.deleteSecret('SECRET__SSH__TEST_USER');
      expect(deleted).toBe(true);
      expect(store.hasSecret('SECRET__SSH__TEST_USER')).resolves.toBe(false);
    });

    it('should clear all secrets', () => {
      store.clear();
      expect(store.getAllSecrets().size).toBe(0);
    });
  });

  describe('EnvSecretStore', () => {
    let store: EnvSecretStore;

    beforeEach(() => {
      process.env.SECRET__SSH__ENV_TEST = 'envvalue';
      store = new EnvSecretStore();
    });

    it('should retrieve secrets from environment', async () => {
      const secret = await store.getSecret('SECRET__SSH__ENV_TEST');
      expect(secret).toBe('envvalue');
    });

    it('should throw error for undefined env vars', async () => {
      await expect(store.getSecret('SECRET__UNDEFINED')).rejects.toThrow(
        'Secret not found'
      );
    });

    it('should list secret keys', () => {
      const keys = store.listSecretKeys();
      expect(keys).toContain('SECRET__SSH__ENV_TEST');
    });
  });

  describe('SecretRef', () => {
    it('should generate SSH secret refs', () => {
      const userRef = SecretRef.ssh('edge_ubuntu', 'user');
      const passRef = SecretRef.ssh('edge_ubuntu', 'pass');

      expect(userRef).toBe('SECRET__SSH__EDGE_UBUNTU_USER');
      expect(passRef).toBe('SECRET__SSH__EDGE_UBUNTU_PASS');
    });

    it('should generate RDP secret refs', () => {
      const userRef = SecretRef.rdp('windows_srv', 'user');
      const passRef = SecretRef.rdp('windows_srv', 'pass');

      expect(userRef).toBe('SECRET__RDP__WINDOWS_SRV_USER');
      expect(passRef).toBe('SECRET__RDP__WINDOWS_SRV_PASS');
    });

    it('should generate custom secret refs', () => {
      const ref = SecretRef.custom('api', 'github', 'token');
      expect(ref).toBe('SECRET__API__GITHUB__TOKEN');
    });
  });
});
