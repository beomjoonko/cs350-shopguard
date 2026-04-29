export type RiskLevel = "SAFE" | "WARNING" | "DANGER" | "CRITICAL";

export type FraudType =
  | "NON_DELIVERY"
  | "FALSE_ADVERTISING"
  | "REFUSAL_OF_REFUND"
  | "DEFECTIVE_PRODUCTS"
  | "PERSONAL_DATA_LEAKAGE"
  | "OTHERS";

export type ReportStatus =
  | "DRAFT" | "SUBMITTED" | "ACTIVE" | "UNDER_REVIEW"
  | "VERIFIED" | "BLINDED_DELETED" | "PENDING" | "HIDDEN";

export type UserRole = "USER" | "ADMIN";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  status: "ACTIVE" | "LOCKED" | "SUSPENDED";
  created_at: string;
}

export interface Report {
  id: string;
  url_id: string;
  fraud_type: FraudType;
  description: string;
  evidence_image_url: string | null;
  status: ReportStatus;
  created_at: string;
}

export interface UrlAnalysisResult {
  url: string;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  report_count: number;
  last_analyzed_at: string | null;
  job_id: string | null;
  cached: boolean;
}
