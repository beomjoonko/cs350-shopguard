"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Props = {
  reportId: string;
  className?: string;
};

export function ReportEvidenceImage({ reportId, className }: Props) {
  const [src, setSrc] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let objectUrl: string | null = null;
    api
      .fetchReportEvidence(reportId)
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setSrc(objectUrl);
      })
      .catch((e) => setError(String(e)));

    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [reportId]);

  if (error) {
    return <p className="text-sm text-red-600">{error}</p>;
  }
  if (!src) {
    return <div className={`h-40 animate-pulse rounded-xl bg-slate-100 ${className ?? ""}`} />;
  }
  return (
    <img
      src={src}
      alt="Report evidence"
      className={`max-h-80 w-full rounded-xl border border-slate-200 object-contain ${className ?? ""}`}
    />
  );
}
