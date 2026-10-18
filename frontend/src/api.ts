import type { Watch, WatchInput, WatchStatus } from './types';

export const API_BASE = (import.meta.env.VITE_API_BASE_URL?.trim() || '/api').replace(/\/+$/, '');
export const API_DOCS = API_BASE === '/api' ? 'http://127.0.0.1:8000/docs' : `${API_BASE}/docs`;

export class ApiError extends Error {
  constructor(message: string, public readonly status: number) { super(message); }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const timeout = AbortSignal.timeout(20_000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: options.body ? { 'Content-Type': 'application/json' } : undefined,
      signal: options.signal ? AbortSignal.any([options.signal, timeout]) : timeout,
    });
    if (!response.ok) {
      let message = `Request failed (HTTP ${response.status}). Please try again.`;
      try {
        const { detail } = await response.json();
        if (typeof detail === 'string') message = detail;
        else if (Array.isArray(detail)) message = detail.map((item: { loc?: (string | number)[]; msg?: string }) => `${item.loc?.slice(1).join('.') || 'Input'}: ${item.msg || 'Invalid value'}`).join(' ');
      } catch { /* An upstream proxy can return HTML instead of FastAPI JSON. */ }
      throw new ApiError(message, response.status);
    }
    if (response.status === 204) return undefined as T;
    return await response.json() as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (options.signal?.aborted) throw error;
    if (timeout.aborted) throw new Error('The server took too long to respond. Please try again.');
    throw new Error('Could not connect to the API. Check your connection and try again.');
  }
}

export const listWatches = () => request<Watch[]>('/watches');
export const createWatch = (input: WatchInput) => request<Watch>('/watches', { method: 'POST', body: JSON.stringify(input) });
export const setWatchActive = (id: number, active: boolean) => request<Watch>(`/watches/${id}`, { method: 'PATCH', body: JSON.stringify({ active }) });
export const deleteWatch = (id: number) => request<void>(`/watches/${id}`, { method: 'DELETE' });
export const getWatchStatus = (id: number, signal?: AbortSignal) => request<WatchStatus>(`/watches/${id}/status`, { signal });
export const getHealth = () => request<{ status: string }>('/health');
