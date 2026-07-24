import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchBacktest, fetchBacktestDetail } from './backtest';
import { client } from './client';

vi.mock('./client', () => ({
  client: {
    get: vi.fn(),
  },
}));

describe('fetchBacktest', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls client.get with default top parameter', async () => {
    const mockResponse = { items: [] };
    vi.mocked(client.get).mockResolvedValueOnce(mockResponse as any);

    const result = await fetchBacktest('kospi', '2023-01-01', '30d');

    expect(client.get).toHaveBeenCalledTimes(1);
    expect(client.get).toHaveBeenCalledWith('/api/stock/backtest', {
      market: 'kospi',
      as_of: '2023-01-01',
      period: '30d',
      top: '20',
    });
    expect(result).toBe(mockResponse);
  });

  it('calls client.get with custom top parameter', async () => {
    const mockResponse = { items: [] };
    vi.mocked(client.get).mockResolvedValueOnce(mockResponse as any);

    const result = await fetchBacktest('nasdaq', '2023-12-31', '365d', 50);

    expect(client.get).toHaveBeenCalledTimes(1);
    expect(client.get).toHaveBeenCalledWith('/api/stock/backtest', {
      market: 'nasdaq',
      as_of: '2023-12-31',
      period: '365d',
      top: '50',
    });
    expect(result).toBe(mockResponse);
  });

  it('propagates errors from client.get', async () => {
    const error = new Error('Network error');
    vi.mocked(client.get).mockRejectedValueOnce(error);

    await expect(fetchBacktest('kospi', '2023-01-01', '30d')).rejects.toThrow('Network error');
  });
});

describe('fetchBacktestDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls client.get with correct arguments', async () => {
    const mockResponse = { detail: {} };
    vi.mocked(client.get).mockResolvedValueOnce(mockResponse as any);

    const result = await fetchBacktestDetail('kospi', '005930', '2023-01-01', '30d');

    expect(client.get).toHaveBeenCalledTimes(1);
    expect(client.get).toHaveBeenCalledWith('/api/stock/backtest/detail', {
      market: 'kospi',
      ticker: '005930',
      as_of: '2023-01-01',
      period: '30d',
    });
    expect(result).toBe(mockResponse);
  });

  it('propagates errors from client.get', async () => {
    const error = new Error('Not found');
    vi.mocked(client.get).mockRejectedValueOnce(error);

    await expect(fetchBacktestDetail('kospi', '005930', '2023-01-01', '30d')).rejects.toThrow('Not found');
  });
});
