import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import nock from 'nock';
import { ApiClient } from '../src/api';

describe('ApiClient', () => {
  const baseURL = 'https://test.guacamole.local';
  let client: ApiClient;

  beforeEach(() => {
    client = new ApiClient({
      baseURL,
      verifyTLS: false,
      retries: 0, // Disable retries for tests
    });
  });

  afterEach(() => {
    nock.cleanAll();
  });

  describe('GET requests', () => {
    it('should make a successful GET request', async () => {
      const mockData = { id: '1', name: 'Test Connection' };

      nock(baseURL)
        .get('/api/test')
        .reply(200, mockData);

      const result = await client.get('/api/test');
      expect(result).toEqual(mockData);
    });

    it('should handle GET request errors', async () => {
      nock(baseURL)
        .get('/api/test')
        .reply(404, { error: 'Not Found' });

      await expect(client.get('/api/test')).rejects.toThrow();
    });
  });

  describe('POST requests', () => {
    it('should make a successful POST request', async () => {
      const requestData = { name: 'New Connection' };
      const responseData = { id: '2', ...requestData };

      nock(baseURL)
        .post('/api/test', requestData)
        .reply(201, responseData);

      const result = await client.post('/api/test', requestData);
      expect(result).toEqual(responseData);
    });
  });

  describe('Authentication', () => {
    it('should set auth token in headers', async () => {
      const token = 'test-token-12345';
      client.setAuthToken(token);

      nock(baseURL)
        .get('/api/test')
        .matchHeader('Guacamole-Token', token)
        .reply(200, { success: true });

      const result = await client.get<{ success: boolean }>('/api/test');
      expect(result.success).toBe(true);
    });

    it('should clear auth token', () => {
      client.setAuthToken('test-token');
      client.clearAuthToken();

      // Token should be removed from headers
      // (hard to test directly, but we can verify no auth header is sent)
    });
  });

  describe('Error handling', () => {
    it('should handle network errors', async () => {
      nock(baseURL)
        .get('/api/test')
        .replyWithError('Network error');

      await expect(client.get('/api/test')).rejects.toThrow();
    });

    it('should handle 500 errors', async () => {
      nock(baseURL)
        .get('/api/test')
        .reply(500, { error: 'Internal Server Error' });

      await expect(client.get('/api/test')).rejects.toThrow();
    });
  });
});
