import { getToken, clearToken } from "./auth";
import type { Report, UrlAnalysisResult, User, FraudType, PlatformStats } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * FastAPI returns `detail` as a string for HTTPException, but as an array of
 * error objects for 422 validation errors. Flatten both into a readable string
 * so the UI never shows "[object Object]".
 */
function normalizeDetail(detail: unknown): string | null {
  if (detail == null) return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    const msgs = detail
      .map((e) => (e && typeof e === "object" && "msg" in e ? String((e as { msg: unknown }).msg) : String(e)))
      .filter(Boolean);
    return msgs.length ? msgs.join("; ") : null;
  }
  try {
    return JSON.stringify(detail);
  } catch {
    return null;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (!(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (res.status === 401) {
    clearToken();
    throw new Error("Unauthorized");
  }
  if (res.status === 403) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = normalizeDetail(body.detail) ?? detail;
    } catch { /* noop */ }
    if (detail.toLowerCase().includes("suspended")) {
      clearToken();
    }
    throw new Error(detail);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = normalizeDetail(body.detail) ?? detail;
    } catch { /* noop */ }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  requestPasswordReset: (email: string) =>
    request<{ detail: string }>("/auth/password-reset/request", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  confirmPasswordReset: (token: string, newPassword: string) =>
    request<void>("/auth/password-reset/confirm", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    }),

  me: () => request<User>("/users/me"),
  myReports: () => request<Report[]>("/users/me/reports"),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>("/users/me/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

  createReport: (
    data: {
      url: string;
      fraud_type: FraudType;
      description: string;
      legal_consent: boolean;
    },
    evidenceFile?: File
  ) => {
    const form = new FormData();
    const normalizedUrl = data.url.trim().match(/^https?:\/\//i)
      ? data.url.trim()
      : `https://${data.url.trim()}`;
    form.append("url", normalizedUrl);
    form.append("fraud_type", data.fraud_type);
    form.append("description", data.description.trim());
    form.append("legal_consent", data.legal_consent ? "true" : "false");
    if (evidenceFile && evidenceFile.size > 0) {
      form.append("evidence", evidenceFile, evidenceFile.name);
    }
    return request<Report>("/reports", { method: "POST", body: form });
  },

  fetchReportEvidence: async (reportId: string): Promise<Blob> => {
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const res = await fetch(`${BASE_URL}/reports/${reportId}/evidence`, { headers });
    if (res.status === 401) {
      clearToken();
      throw new Error("Unauthorized");
    }
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        detail = normalizeDetail(body.detail) ?? detail;
      } catch { /* noop */ }
      throw new Error(detail);
    }
    return res.blob();
  },

  searchUrl: (url: string) =>
    request<UrlAnalysisResult>("/analysis/search", { method: "POST", body: JSON.stringify({ url }) }),

  getJob: (jobId: string) =>
    request<{ job_id: string; status: string; final_risk_score: number | null; risk_level: string | null }>(
      `/analysis/jobs/${jobId}`
    ),

  adminListReports: () => request<Report[]>("/admin/reports"),
  adminUpdateReportStatus: (id: string, status: string) =>
    request<Report>(`/admin/reports/${id}`, { method: "PATCH", body: JSON.stringify({ status }) }),
  adminBlockUser: (userId: string, reason: string) =>
    request<void>(`/admin/users/${userId}/block`, { method: "POST", body: JSON.stringify({ reason }) }),

  getStats: () => request<PlatformStats>("/stats"),
};
