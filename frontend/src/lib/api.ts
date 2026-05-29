import { getToken, clearToken } from "./auth";
import type { Report, UrlAnalysisResult, User, FraudType, PlatformStats } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");

  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(`${BASE_URL}${path}`, { ...init, headers });

  if (res.status === 401) {
    clearToken();
    throw new Error("Unauthorized");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch { /* noop */ }
    throw new Error(detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  /**
   * Register a new account.
   * Calls the FastAPI backend which:
   *   1. Checks the blacklist (server-side)
   *   2. Creates the Supabase Auth user via Admin API
   *   3. Provisions the local users row
   */
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  me: () => request<User>("/users/me"),
  myReports: () => request<Report[]>("/users/me/reports"),

  /**
   * Upload an evidence image to Supabase Storage.
   * Returns the public URL of the uploaded file.
   * The caller stores this URL in evidenceImageUrl before createReport().
   */
  uploadEvidence: async (file: File): Promise<{ url: string }> => {
    const token = getToken();
    const headers = new Headers();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    // Do NOT set Content-Type — let the browser set multipart/form-data boundary
    const body = new FormData();
    body.append("file", file);
    const res = await fetch(`${BASE_URL}/reports/upload-evidence`, {
      method: "POST",
      headers,
      body,
    });
    if (res.status === 401) {
      clearToken();
      throw new Error("Unauthorized");
    }
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const b = await res.json();
        detail = b.detail ?? detail;
      } catch { /* noop */ }
      throw new Error(detail);
    }
    return res.json() as Promise<{ url: string }>;
  },

  createReport: (data: {
    url: string;
    fraud_type: FraudType;
    description: string;
    evidence_image_url?: string;
    legal_consent: boolean;
  }) => request<Report>("/reports", { method: "POST", body: JSON.stringify(data) }),

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
