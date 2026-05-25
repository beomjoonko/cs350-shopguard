const STORAGE_KEY = "shopguard.recentSearches";
const MAX_ITEMS = 5;

export function getRecentSearches(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.filter((v) => typeof v === "string") : [];
  } catch {
    return [];
  }
}

export function addRecentSearch(url: string): string[] {
  const trimmed = url.trim();
  if (!trimmed || typeof window === "undefined") return getRecentSearches();

  const next = [trimmed, ...getRecentSearches().filter((u) => u !== trimmed)].slice(
    0,
    MAX_ITEMS
  );
  localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
  return next;
}

