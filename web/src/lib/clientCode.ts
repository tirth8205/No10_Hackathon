// The client's link token doubles as a short code they can type on the start screen
// (app/store.py: eight characters from an alphabet without 0, O, 1, I or L).

/** "k7qm-4xpr " -> "K7QM4XPR". */
export function normaliseClientCode(typed: string): string {
  return typed.toUpperCase().replace(/[^A-Z0-9]/g, "");
}

/** "K7QM4XPR" -> "K7QM-4XPR", easier to read out. Older, longer tokens are shown as they are. */
export function formatClientCode(token: string): string {
  return /^[A-Z0-9]{8}$/.test(token) ? `${token.slice(0, 4)}-${token.slice(4)}` : token;
}
