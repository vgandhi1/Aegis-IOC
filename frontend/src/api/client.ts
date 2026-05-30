export interface Session {
  access_token: string;
  expires_in: number;
  role: string;
  full_name: string;
  scopes: string[];
  tabs: string[];
}

export interface Identity {
  username: string;
  full_name: string;
  role: string;
  scopes: string[];
  tabs: string[];
  actions: string[];
}

const BASE = "/api/v1";

class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...options, headers: { ...headers, ...(options.headers || {}) } });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  login: (username: string, password: string) =>
    request<Session>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) }),
  me: (token: string) => request<Identity>("/auth/me", {}, token),

  list: <T>(domainPath: string, token: string) => request<T[]>(domainPath, {}, token),

  post: <T>(path: string, body: unknown, token: string) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }, token),
};

export { ApiError };
