/**
 * FT-24 – FT-27: Frontend page-component tests (known-bug documentation).
 *
 * Consolidates the former admin_filter.test.tsx + search_hardcoded.test.tsx.
 * Kept separate from test_fe_lib.test.tsx because these jest.mock("@/lib/api"),
 * which would shadow the real api module used by the lib tests.
 *
 *   FT-24 / FT-25  BUG-2: admin status filter is missing "SUBMITTED"
 *                  → it.failing (passes while the bug exists; flip to it once fixed)
 *   FT-26          BUG-4: hardcoded "82%" AI confidence in the search card
 *   FT-27          BUG-1: unauthenticated search shows an error but does NOT redirect
 *
 * Run: cd frontend && npm test -- test_fe_pages
 */
import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "fs";
import { resolve } from "path";

// ── Shared mocks (hoisted) ──────────────────────────────────────────────────
jest.mock("next/navigation", () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn() }),
  useSearchParams: () => ({
    get: (key: string) => (key === "url" ? "https://www.example.com" : null),
  }),
  usePathname: () => "/",
}));

jest.mock("@/lib/api", () => ({
  api: {
    adminListReports: jest.fn().mockResolvedValue([]),
    searchUrl: jest.fn(),
    getJob: jest.fn(),
  },
}));

jest.mock("@/lib/recentSearches", () => ({
  addRecentSearch: jest.fn(),
  getRecentSearches: jest.fn().mockReturnValue([]),
}));

jest.mock("@/hooks/useLoggedIn", () => ({ useLoggedIn: () => true }));

import AdminPage from "@/app/admin/page";
import SearchPage from "@/app/search/page";
import { api } from "@/lib/api";

// ════════════════════════════════════════════════════════════════════════════
// FT-24 / FT-25 — Admin status filter (BUG-2)
// ════════════════════════════════════════════════════════════════════════════
describe("Admin status filter (BUG-2)", () => {
  function optionValues(): string[] {
    render(<AdminPage />);
    const select = screen.getByRole("combobox");
    return Array.from(select.querySelectorAll("option")).map((o) => o.value);
  }

  // FT-24 — bug present: dropdown lacks SUBMITTED → it.failing stays green until fixed
  it.failing('includes "SUBMITTED" in the status dropdown', () => {
    expect(optionValues()).toContain("SUBMITTED");
  });

  // FT-25 — bug present: not all 8 SRS statuses are offered
  it.failing("offers ALL + every SRS-defined report status", () => {
    const values = optionValues();
    for (const status of [
      "ALL",
      "SUBMITTED",
      "ACTIVE",
      "PENDING",
      "HIDDEN",
      "UNDER_REVIEW",
      "VERIFIED",
      "BLINDED_DELETED",
    ]) {
      expect(values).toContain(status);
    }
  });
});

// ════════════════════════════════════════════════════════════════════════════
// FT-26 — Hardcoded AI confidence literal removed (BUG-4 fixed)
// ════════════════════════════════════════════════════════════════════════════
describe("Search card hardcoded confidence (BUG-4)", () => {
  // FT-26 — the fake "AI Confidence: 82%" stat was removed; guard against regressions
  it("search page no longer shows the hardcoded 82% confidence", () => {
    const src = readFileSync(resolve(__dirname, "../app/search/page.tsx"), "utf-8");
    expect(src).not.toMatch(/82%/);
    expect(src).not.toMatch(/AI Confidence/);
  });
});

// ════════════════════════════════════════════════════════════════════════════
// FT-27 — Unauthenticated search shows error without redirect (BUG-1)
// ════════════════════════════════════════════════════════════════════════════
describe("Unauthenticated search (BUG-1)", () => {
  // FT-27
  it("renders the API error message instead of redirecting to /login", async () => {
    (api.searchUrl as jest.Mock).mockRejectedValueOnce(new Error("Unauthorized"));
    render(<SearchPage />);

    await waitFor(() => {
      expect(screen.getByText(/Unauthorized/i)).toBeInTheDocument();
    });
    // BUG-1: there SHOULD be a redirect to /login here, but there isn't.
    // Once fixed, assert router.push("/login") and drop the error expectation.
  });
});
