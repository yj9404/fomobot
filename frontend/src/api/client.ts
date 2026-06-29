const BASE_STOCK = import.meta.env.VITE_API_BASE_URL ?? ''
const BASE_RE    = import.meta.env.VITE_RE_API_BASE_URL ?? ''

function resolveBase(path: string): string {
  return path.startsWith('/api/realestate') ? BASE_RE : BASE_STOCK
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

export async function apiFetch<T>(path: string, params: Record<string, string | number>): Promise<T> {
  const url = new URL(resolveBase(path) + path, window.location.href)
  for (const [k, v] of Object.entries(params)) {
    url.searchParams.set(k, String(v))
  }
  const res = await fetch(url.toString())
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    let message = `HTTP ${res.status}`
    if (body) {
      try {
        const parsed = JSON.parse(body)
        message = parsed.detail ?? parsed.message ?? body
      } catch {
        message = body
      }
    }
    throw new ApiError(res.status, message)
  }
  return res.json() as Promise<T>
}
