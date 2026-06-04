/** SRS §4.3 REQ-6 — keep in sync with backend/app/utils/password_policy.py */
const HAS_DIGIT = /\d/;
const HAS_SPECIAL = /[^A-Za-z0-9]/;

export function isPasswordComplex(password: string): boolean {
  return (
    password.length >= 8 &&
    HAS_DIGIT.test(password) &&
    HAS_SPECIAL.test(password)
  );
}

export const PASSWORD_COMPLEXITY_HINT =
  "At least 8 characters, including a number and a special character.";

export function passwordComplexityError(password: string): string | null {
  if (isPasswordComplex(password)) return null;
  const parts: string[] = [];
  if (password.length < 8) parts.push("at least 8 characters");
  if (!HAS_DIGIT.test(password)) parts.push("a number");
  if (!HAS_SPECIAL.test(password)) parts.push("a special character");
  return `Password must include ${parts.join(", ")}.`;
}
