import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiFetch, ApiError } from './client'

describe('apiFetch', () => {
  const mockFetch = vi.fn()

  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch)
    mockFetch.mockReset()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('should make a successful GET request', async () => {
    const mockData = { id: 1, name: 'Test' }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData)
    })

    const result = await apiFetch('/api/test', { param1: 'value1', param2: 2 })

    expect(mockFetch).toHaveBeenCalledWith('http://localhost:3000/api/test?param1=value1&param2=2')
    expect(result).toEqual(mockData)
  })

  it('should resolve base URL correctly for realestate API', async () => {
    const mockData = { success: true }
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockData)
    })

    const result = await apiFetch('/api/realestate/test', {})

    expect(mockFetch).toHaveBeenCalledWith('http://localhost:3000/api/realestate/test')
    expect(result).toEqual(mockData)
  })

  it('should handle API errors and parse JSON detail', async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Not found' }))
    })

    await expect(apiFetch('/api/test', {})).rejects.toThrow(ApiError)

    // reset for next assertion
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve(JSON.stringify({ detail: 'Not found' }))
    })

    await expect(apiFetch('/api/test', {})).rejects.toMatchObject({
      status: 404,
      message: 'Not found'
    })
  })

  it('should handle API errors and parse JSON message', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 500,
      text: () => Promise.resolve(JSON.stringify({ message: 'Internal Server Error' }))
    })

    await expect(apiFetch('/api/test', {})).rejects.toMatchObject({
      status: 500,
      message: 'Internal Server Error'
    })
  })

  it('should handle API errors with non-JSON response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 502,
      text: () => Promise.resolve('Bad Gateway')
    })

    await expect(apiFetch('/api/test', {})).rejects.toMatchObject({
      status: 502,
      message: 'Bad Gateway'
    })
  })

  it('should handle API errors with empty response text', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      status: 401,
      text: () => Promise.reject(new Error('no text'))
    })

    await expect(apiFetch('/api/test', {})).rejects.toMatchObject({
      status: 401,
      message: 'HTTP 401'
    })
  })
})
