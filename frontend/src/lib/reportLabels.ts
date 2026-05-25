import type { ReportStatus, RiskLevel } from "@/types";

export const FRAUD_LABEL: Record<string, string> = {
  NON_DELIVERY: "Non-delivery",
  FALSE_ADVERTISING: "False Advertising",
  REFUSAL_OF_REFUND: "Refund Denial",
  DEFECTIVE_PRODUCTS: "Defective Products",
  PERSONAL_DATA_LEAKAGE: "Data Leakage",
  OTHERS: "Others",
};

export const STATUS_BADGE: Record<string, { label: string; bg: string; text: string }> = {
  PENDING: { label: "Pending", bg: "bg-amber-100", text: "text-amber-800" },
  SUBMITTED: { label: "Submitted", bg: "bg-blue-100", text: "text-blue-800" },
  ACTIVE: { label: "Approved", bg: "bg-green-100", text: "text-green-800" },
  UNDER_REVIEW: { label: "Under Review", bg: "bg-purple-100", text: "text-purple-800" },
  VERIFIED: { label: "Verified", bg: "bg-green-100", text: "text-green-800" },
  BLINDED_DELETED: { label: "Removed", bg: "bg-slate-100", text: "text-slate-600" },
  HIDDEN: { label: "Hidden", bg: "bg-slate-100", text: "text-slate-600" },
  DRAFT: { label: "Draft", bg: "bg-slate-100", text: "text-slate-500" },
};

export const RISK_BADGE: Record<RiskLevel, { label: string; bg: string; text: string }> = {
  SAFE: { label: "Safe", bg: "bg-emerald-100", text: "text-emerald-800" },
  WARNING: { label: "Warning", bg: "bg-amber-100", text: "text-amber-800" },
  DANGER: { label: "Danger", bg: "bg-red-100", text: "text-red-800" },
  CRITICAL: { label: "Critical", bg: "bg-red-200", text: "text-red-900" },
};

export function statusBadge(status: ReportStatus) {
  return STATUS_BADGE[status] ?? { label: status, bg: "bg-slate-100", text: "text-slate-600" };
}
