// Idle logout.
//
// The open dashboard polls the API on its own every 30–60 s and refreshes the
// access token on 401, so the server cannot tell a person at the screen from
// an abandoned tab. The time of the last pointer/key/touch/scroll is stamped in
// localStorage instead: every tab shares it (activity in one keeps all alive)
// and it survives closing the browser, so reopening later still ends the
// session.

export const IDLE_TIMEOUT_MS = 30 * 60 * 1000;
export const IDLE_WARNING_MS = 60 * 1000;
export const LAST_ACTIVITY_KEY = 'last_activity_at';

const SESSION_KEYS = ['access_token', 'refresh_token', 'user'];

function lastActivityAt(storage) {
  const value = Number(storage.getItem(LAST_ACTIVITY_KEY));
  return value > 0 ? value : null;
}

// Skips the write while the stamp is younger than minGapMs (mousemove fires
// dozens of times a second).
export function recordActivity(storage, now, minGapMs = 0) {
  const last = lastActivityAt(storage);
  if (last === null || now - last >= minGapMs) {
    storage.setItem(LAST_ACTIVITY_KEY, String(now));
  }
}

// secondsLeft is set only during the warning before the timeout.
export function idleStatus(storage, now, timeoutMs = IDLE_TIMEOUT_MS, warningMs = IDLE_WARNING_MS) {
  const last = lastActivityAt(storage);
  if (last === null) return { expired: false, secondsLeft: null };
  const remaining = last + timeoutMs - now;
  if (remaining <= 0) return { expired: true, secondsLeft: 0 };
  return { expired: false, secondsLeft: remaining <= warningMs ? Math.ceil(remaining / 1000) : null };
}

// For page load: clears a session left idle past the timeout (tab closed and
// reopened later) and returns true when it did.
export function expireIdleSession(storage, now, timeoutMs = IDLE_TIMEOUT_MS) {
  if (!storage.getItem('access_token')) return false;
  if (lastActivityAt(storage) === null) {
    // Logged in before idle tracking existed: start its clock now.
    recordActivity(storage, now);
    return false;
  }
  if (!idleStatus(storage, now, timeoutMs).expired) return false;
  SESSION_KEYS.forEach((key) => storage.removeItem(key));
  return true;
}
