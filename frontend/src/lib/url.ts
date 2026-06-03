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

/**
 * Whether a pasted link can actually be analyzed. Mirrors the backend's
 * hostname check (is_hostname_encodable): the URL must parse and every DNS
 * label must be IDNA-encodable, i.e. ≤ 63 bytes. The browser's URL parser
 * already converts an IDN host to punycode, so a label that overflows 63
 * bytes is exactly what the backend would reject with a 422. Validating here
 * lets the search page show an inline message without navigating away.
 */
export function isAnalyzableUrl(input: string): boolean {
  const trimmed = input.trim();
  if (!trimmed) return false;
  // Internal whitespace can never be part of a valid hostname (the backend
  // rejects it with "invalid domain character"); reject it up front so it never
  // navigates. Note the URL parser silently strips tabs/newlines, which would
  // otherwise let a mistyped host through — this guard covers that too.
  if (/\s/.test(trimmed)) return false;
  let host: string;
  try {
    host = new URL(withScheme(trimmed)).hostname; // browser applies IDNA → punycode
  } catch {
    return false;
  }
  if (!host) return false;
  return host.split(".").every((label) => label.length > 0 && label.length <= 63);
}
