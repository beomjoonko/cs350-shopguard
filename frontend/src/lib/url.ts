/** URL input helpers for the search flow. */

/**
 * Prepend `https://` when the input has no scheme, so a pasted bare domain
 * (e.g. "coupang.com/x") is accepted by the backend's HttpUrl validation
 * instead of failing with a 422 "relative URL without a base" error.
 */
export function withScheme(url: string): string {
  const trimmed = url.trim();
  if (!trimmed) return trimmed;
  // Already has a scheme (http://, https://, ftp://, ...) — leave it untouched.
  if (/^[a-zA-Z][a-zA-Z0-9+.-]*:\/\//.test(trimmed)) return trimmed;
  return `https://${trimmed}`;
}
