import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchRankings } from './rankings';
import { apiFetch } from './client';

vi.mock('./client', () => ({
  apiFetch: vi.fn(),
}));

describe('fetchRankings', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls apiFetch with default parameters', async () => {
    const mockResponse = { items: [] };
    vi.mocked(apiFetch).mockResolvedValueOnce(mockResponse as any);

    const result = await fetchRankings('kospi', '30d');

    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(apiFetch).toHaveBeenCalledWith('/api/stock/rankings', {
      market: 'kospi',
      period: '30d',
      cap_tier: 'all',
      top: 20,
      order: 'desc'
    });
    expect(result).toBe(mockResponse);
  });

  it('calls apiFetch with custom parameters', async () => {
    const mockResponse = { items: [] };
    vi.mocked(apiFetch).mockResolvedValueOnce(mockResponse as any);

    const result = await fetchRankings('nasdaq', '365d', 'large', 50, 'asc');

    expect(apiFetch).toHaveBeenCalledTimes(1);
    expect(apiFetch).toHaveBeenCalledWith('/api/stock/rankings', {
      market: 'nasdaq',
      period: '365d',
      cap_tier: 'large',
      top: 50,
      order: 'asc'
    });
    expect(result).toBe(mockResponse);
  });

  it('propagates errors from apiFetch', async () => {
    const error = new Error('Network error');
    vi.mocked(apiFetch).mockRejectedValueOnce(error);

    await expect(fetchRankings('kospi', '30d')).rejects.toThrow('Network error');
  });
});
