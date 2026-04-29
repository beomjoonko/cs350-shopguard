import { getToken, clearToken } from "./auth";
import type { Report, UrlAnalysisResult, User, FraudType } from "@/types";

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
  register: (email: string, password: string) =>
    request<User>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/users/me"),
  myReports: () => request<Report[]>("/users/me/reports"),
  changePassword: (currentPassword: string, newPassword: string) =>
    request<void>("/users/me/password", {
      method: "POST",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
    }),

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
};
