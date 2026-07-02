import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { apiFetch, ApiError } from './client';

describe('apiFetch', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('should successfully fetch and return JSON data', async () => {
    const mockData = { result: 'success' };
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData),
    });

    const result = await apiFetch('/test-path', { param1: 'value1' });
    expect(result).toEqual(mockData);
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Check if the URL string passed to fetch contains the expected path and search params
    const fetchCallUrl = mockFetch.mock.calls[0][0];
    expect(fetchCallUrl).toContain('/test-path');
    expect(fetchCallUrl).toContain('param1=value1');
  });

  it('should throw ApiError with detail from JSON body when response is not ok', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 400,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Validation Error' })),
    });

    await expect(apiFetch('/test-path', {})).rejects.toThrowError(
      new ApiError(400, 'Validation Error')
    );
  });

  it('should throw ApiError with message from JSON body when detail is not present', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 403,
      text: () => Promise.resolve(JSON.stringify({ message: 'Forbidden access' })),
    });

    await expect(apiFetch('/test-path', {})).rejects.toThrowError(
      new ApiError(403, 'Forbidden access')
    );
  });

  it('should throw ApiError with entire body when JSON lacks detail/message', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 404,
      text: () => Promise.resolve(JSON.stringify({ someKey: 'someValue' })),
    });

    await expect(apiFetch('/test-path', {})).rejects.toThrowError(
      new ApiError(404, JSON.stringify({ someKey: 'someValue' }))
    );
  });

  it('should throw ApiError with entire text body when response is not JSON', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve('Internal Server Error text'),
    });

    await expect(apiFetch('/test-path', {})).rejects.toThrowError(
      new ApiError(500, 'Internal Server Error text')
    );
  });

  it('should throw ApiError with default HTTP {status} message when text body is empty or fails to read', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: () => Promise.reject(new Error('Failed to read')),
    });

    await expect(apiFetch('/test-path', {})).rejects.toThrowError(
      new ApiError(502, 'HTTP 502')
    );
  });
});
