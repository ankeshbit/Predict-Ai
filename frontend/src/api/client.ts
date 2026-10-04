/**
 * Predict-Ai API Client
 * Centralized fetch client with JWT authentication, error handling, and type safety.
 * Captures the HTTP Date header from responses for "Last updated" display.
 */

const API_BASE = '/api/v1';

/** Configurable polling interval (ms). Set VITE_POLL_INTERVAL_MS in .env to override. */
export const POLL_INTERVAL_MS: number = Number(
  (import.meta as any).env?.VITE_POLL_INTERVAL_MS ?? 7000
);

export interface ApiErrorResponse {
  error: {
    code: string;
    message: string;
    details?: any;
  };
}

export class ApiError extends Error {
  code: string;
  details?: any;
  statusCode: number;

  constructor(statusCode: number, code: string, message: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export function getAuthToken(): string | null {
  return localStorage.getItem('predicore_auth_token');
}

export function setAuthToken(token: string | null): void {
  if (token) {
    localStorage.setItem('predicore_auth_token', token);
  } else {
    localStorage.removeItem('predicore_auth_token');
  }
}

/** Formatted hh:mm:ss from the HTTP Date response header (server time, not client clock). */
let _lastServerUpdateTime: string | null = null;
export function getLastServerUpdateTime(): string | null {
  return _lastServerUpdateTime;
}

function _formatServerDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  try {
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return null;
    return d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return null;
  }
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const token = getAuthToken();

  const headers: Record<string, string> = {
    Accept: 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Capture server time from Date header (GET requests only, not mutations)
  if (!options.method || options.method === 'GET') {
    const serverDate = response.headers.get('Date');
    const formatted = _formatServerDate(serverDate);
    if (formatted) {
      _lastServerUpdateTime = formatted;
    }
  }

  if (response.status === 204) {
    return {} as T;
  }

  const responseText = await response.text();
  let data: any = null;
  if (responseText) {
    try {
      data = JSON.parse(responseText);
    } catch {
      data = responseText;
    }
  }

  if (!response.ok) {
    const errorDetails = data?.error || data?.detail;
    const code = errorDetails?.code || `HTTP_${response.status}`;
    const message =
      typeof errorDetails === 'string'
        ? errorDetails
        : errorDetails?.message || response.statusText || 'An unexpected error occurred';
    throw new ApiError(response.status, code, message, errorDetails?.details);
  }

  return data as T;
}
