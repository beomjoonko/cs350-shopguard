/**
 * FT-01 – FT-23: Frontend pure-logic test suite.
 *
 * Covers the framework-free units in src/lib that previously had zero tests:
 *   - lib/auth.ts            (token storage, JWT role decode, auth-change events)
 *   - lib/recentSearches.ts  (localStorage-backed recent search list)
 *   - lib/reportLabels.ts    (status / fraud / risk label maps)
 *   - lib/api.ts             (HTTP client: auth header, 401/204/error handling)
 *
 * Maps 1:1 to docs/frontend_test_cases.csv (FT-01..FT-23).
 * Page-component tests (FT-24..FT-27) live in test_fe_pages.test.tsx because
 * they jest.mock("@/lib/api"), which would otherwise shadow the real api here.
 *
 * Run: cd frontend && npm test -- test_fe_lib
 */
import {
  getToken,
  setToken,
  clearToken,
  notifyAuthChange,
  getLoggedInSnapshot,
  getRoleSnapshot,
  subscribeAuth,
  AUTH_CHANGE_EVENT,
} from "@/lib/auth";
import { getRecentSearches, addRecentSearch } from "@/lib/recentSearches";
import { statusBadge, FRAUD_LABEL, RISK_BADGE } from "@/lib/reportLabels";
import { withScheme, isAnalyzableUrl } from "@/lib/url";

beforeEach(() => {
  localStorage.clear();
  jest.restoreAllMocks();
});

// ════════════════════════════════════════════════════════════════════════════
// lib/auth.ts — token storage & JWT role decode
// ════════════════════════════════════════════════════════════════════════════
describe("auth token storage", () => {
  // FT-01
  it("getToken returns null when unset", () => {
    expect(getToken()).toBeNull();
  });

  // FT-02
  it("setToken stores and getToken retrieves", () => {
    setToken("abc");
    expect(getToken()).toBe("abc");
  });

  // FT-03
  it("clearToken removes the token", () => {
    setToken("abc");
    clearToken();
    expect(getToken()).toBeNull();
  });

  // FT-04
  it("setToken fires the auth-change event", () => {
    const cb = jest.fn();
    window.addEventListener(AUTH_CHANGE_EVENT, cb);
    setToken("abc");
    expect(cb).toHaveBeenCalledTimes(1);
    window.removeEventListener(AUTH_CHANGE_EVENT, cb);
  });

  // FT-05
  it("getLoggedInSnapshot reflects token presence", () => {
    expect(getLoggedInSnapshot()).toBe(false);
    setToken("abc");
    expect(getLoggedInSnapshot()).toBe(true);
  });

  // FT-06
  it("getRoleSnapshot decodes the role claim from a JWT", () => {
    const payload = btoa(JSON.stringify({ sub: "u1", role: "ADMIN" }));
    setToken(`header.${payload}.sig`);
    expect(getRoleSnapshot()).toBe("ADMIN");
  });

  // FT-07
  it("getRoleSnapshot returns null for a malformed token", () => {
    setToken("not-a-jwt");
    expect(getRoleSnapshot()).toBeNull();
  });

  // FT-08
  it("subscribeAuth invokes the callback on change and stops after unsubscribe", () => {
    const cb = jest.fn();
    const unsubscribe = subscribeAuth(cb);
    notifyAuthChange();
    expect(cb).toHaveBeenCalledTimes(1);
    unsubscribe();
    notifyAuthChange();
    expect(cb).toHaveBeenCalledTimes(1); // no further calls
  });
});

// ════════════════════════════════════════════════════════════════════════════
// lib/recentSearches.ts
// ════════════════════════════════════════════════════════════════════════════
describe("recent searches", () => {
  // FT-09
  it("returns [] when nothing is stored", () => {
    expect(getRecentSearches()).toEqual([]);
  });

  // FT-10
  it("adds a search to the front of the list", () => {
    const next = addRecentSearch("https://a.com");
    expect(next[0]).toBe("https://a.com");
    expect(getRecentSearches()).toContain("https://a.com");
  });

  // FT-11
  it("de-duplicates and moves the repeat to the front", () => {
    addRecentSearch("https://a.com");
    addRecentSearch("https://b.com");
    const next = addRecentSearch("https://a.com");
    expect(next).toEqual(["https://a.com", "https://b.com"]);
  });

  // FT-12
  it("caps the list at 5 items", () => {
    for (const u of ["1", "2", "3", "4", "5", "6"]) {
      addRecentSearch(`https://${u}.com`);
    }
    const list = getRecentSearches();
    expect(list).toHaveLength(5);
    expect(list).not.toContain("https://1.com"); // oldest evicted
  });

  // FT-13
  it("ignores blank / whitespace-only input", () => {
    addRecentSearch("https://a.com");
    addRecentSearch("   ");
    expect(getRecentSearches()).toEqual(["https://a.com"]);
  });

  // FT-14
  it("tolerates corrupt JSON in storage", () => {
    localStorage.setItem("shopguard.recentSearches", "{not valid json");
    expect(getRecentSearches()).toEqual([]);
  });
});

// ════════════════════════════════════════════════════════════════════════════
// lib/reportLabels.ts
// ════════════════════════════════════════════════════════════════════════════
describe("report labels", () => {
  // FT-15
  it("statusBadge maps a known status", () => {
    expect(statusBadge("ACTIVE").label).toBe("Approved");
  });

  // FT-16
  it("statusBadge falls back for an unknown status, echoing the raw value", () => {
    const badge = statusBadge("WEIRD" as never);
    expect(badge.label).toBe("WEIRD");
    expect(badge.bg).toBe("bg-slate-100");
  });

  // FT-17
  it("FRAUD_LABEL covers all six fraud types", () => {
    const keys = [
      "NON_DELIVERY",
      "FALSE_ADVERTISING",
      "REFUSAL_OF_REFUND",
      "DEFECTIVE_PRODUCTS",
      "PERSONAL_DATA_LEAKAGE",
      "OTHERS",
    ];
    for (const k of keys) {
      expect(typeof FRAUD_LABEL[k]).toBe("string");
      expect(FRAUD_LABEL[k].length).toBeGreaterThan(0);
    }
  });

  // FT-18
  it("RISK_BADGE covers all four risk levels", () => {
    for (const level of ["SAFE", "WARNING", "DANGER", "CRITICAL"] as const) {
      expect(RISK_BADGE[level].label.length).toBeGreaterThan(0);
    }
  });
});

// ════════════════════════════════════════════════════════════════════════════
// lib/url.ts — search input scheme normalization
// ════════════════════════════════════════════════════════════════════════════
describe("withScheme", () => {
  // FT-28
  it("prepends https:// to a bare domain", () => {
    expect(withScheme("coupang.com/vp/products/123")).toBe(
      "https://coupang.com/vp/products/123"
    );
  });

  // FT-29
  it("leaves an already-schemed URL unchanged (http/https/other)", () => {
    expect(withScheme("https://a.com")).toBe("https://a.com");
    expect(withScheme("http://a.com")).toBe("http://a.com");
    expect(withScheme("  https://a.com  ")).toBe("https://a.com"); // trims
    expect(withScheme("")).toBe("");
  });

  // FT-32 — accepts analyzable links (valid host, labels ≤ 63 chars)
  it("isAnalyzableUrl accepts a normal link (with or without scheme)", () => {
    expect(isAnalyzableUrl("https://www.coupang.com/vp/products/123")).toBe(true);
    expect(isAnalyzableUrl("coupang.com")).toBe(true);
  });

  // FT-33 — rejects un-analyzable links (label > 63, whitespace, unparseable)
  it("isAnalyzableUrl rejects bad links: long label, internal whitespace, unparseable", () => {
    expect(isAnalyzableUrl(`https://${"a".repeat(70)}.com`)).toBe(false);
    expect(isAnalyzableUrl("cou pang.com")).toBe(false);      // space in host
    expect(isAnalyzableUrl("https://google .com")).toBe(false);
    expect(isAnalyzableUrl("")).toBe(false);
    expect(isAnalyzableUrl("https://")).toBe(false);
    // leading/trailing whitespace is fine (trimmed)
    expect(isAnalyzableUrl("  coupang.com  ")).toBe(true);
  });
});

// ════════════════════════════════════════════════════════════════════════════
// lib/api.ts — HTTP client behaviour (global.fetch mocked)
// ════════════════════════════════════════════════════════════════════════════
describe("api client", () => {
  function mockFetch(status: number, body: unknown) {
    const res = {
      ok: status < 400,
      status,
      statusText: "",
      json: async () => body,
    };
    const fn = jest.fn().mockResolvedValue(res);
    global.fetch = fn as unknown as typeof fetch;
    return fn;
  }

  // FT-19
  it("attaches the Authorization header when a token is present", async () => {
    setToken("tok123");
    const fetchMock = mockFetch(200, { id: "1", email: "a@b.com" });
    const { api } = await import("@/lib/api");
    await api.me();

    const [, init] = fetchMock.mock.calls[0];
    const headers = new Headers((init as RequestInit).headers);
    expect(headers.get("Authorization")).toBe("Bearer tok123");
  });

  // FT-20
  it("clears the token and throws Unauthorized on 401", async () => {
    setToken("tok123");
    mockFetch(401, {});
    const { api } = await import("@/lib/api");
    await expect(api.me()).rejects.toThrow("Unauthorized");
    expect(getToken()).toBeNull();
  });

  // FT-21
  it("returns undefined on 204 No Content", async () => {
    setToken("tok123");
    mockFetch(204, undefined);
    const { api } = await import("@/lib/api");
    await expect(api.changePassword("old12345", "new12345")).resolves.toBeUndefined();
  });

  // FT-22
  it("throws the backend detail message on a non-ok response", async () => {
    mockFetch(400, { detail: "Legal consent is required" });
    const { api } = await import("@/lib/api");
    await expect(api.searchUrl("https://x.com")).rejects.toThrow(
      "Legal consent is required"
    );
  });

  // FT-30 — 422 validation errors arrive as an object array; render them readably
  it("flattens a 422 validation-error array into a readable message (no [object Object])", async () => {
    mockFetch(422, {
      detail: [
        { type: "url_parsing", loc: ["body", "url"], msg: "Input should be a valid URL, relative URL without a base" },
      ],
    });
    const { api } = await import("@/lib/api");
    await expect(api.searchUrl("coupang.com/x")).rejects.toThrow(
      "Input should be a valid URL, relative URL without a base"
    );
  });

  // FT-23
  it("login POSTs to /auth/login with a JSON body", async () => {
    const fetchMock = mockFetch(200, { access_token: "t", token_type: "bearer" });
    const { api } = await import("@/lib/api");
    await api.login("a@b.com", "password1");

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toMatch(/\/auth\/login$/);
    expect((init as RequestInit).method).toBe("POST");
    expect(JSON.parse((init as RequestInit).body as string)).toEqual({
      email: "a@b.com",
      password: "password1",
    });
  });
});
