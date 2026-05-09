const STORAGE_KEY = "shopguard.token";

/** Same-tab auth UI sync (Header, etc.) */
export const AUTH_CHANGE_EVENT = "shopguard:auth-change";

export function notifyAuthChange(): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event(AUTH_CHANGE_EVENT));
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(STORAGE_KEY);
}

export function setToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, token);
  notifyAuthChange();
}

export function clearToken(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
  notifyAuthChange();
}

/** Subscribe for React useSyncExternalStore (Header login state, etc.) */
export function subscribeAuth(onChange: () => void): () => void {
  if (typeof window === "undefined") return () => {};
  const run = () => onChange();
  window.addEventListener(AUTH_CHANGE_EVENT, run);
  window.addEventListener("storage", run);
  return () => {
    window.removeEventListener(AUTH_CHANGE_EVENT, run);
    window.removeEventListener("storage", run);
  };
}

export function getLoggedInSnapshot(): boolean {
  if (typeof window === "undefined") return false;
  return !!getToken();
}

function decodeJwtPayload(token: string): Record<string, unknown> | null {
  try {
    const [, payload] = token.split(".");
    if (!payload) return null;
    const normalized = payload.replace(/-/g, "+").replace(/_/g, "/");
    const json = atob(normalized);
    return JSON.parse(json) as Record<string, unknown>;
  } catch {
    return null;
  }
}

export function getRoleSnapshot(): string | null {
  const token = getToken();
  if (!token) return null;
  const payload = decodeJwtPayload(token);
  const role = payload?.role;
  return typeof role === "string" ? role : null;
}
