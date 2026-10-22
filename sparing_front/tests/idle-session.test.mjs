import assert from 'node:assert/strict';
import test from 'node:test';
import {
  IDLE_TIMEOUT_MS,
  LAST_ACTIVITY_KEY,
  expireIdleSession,
  idleStatus,
  recordActivity,
} from '../resources/js/Utils/idleSession.js';

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => (values.has(key) ? values.get(key) : null),
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

const MIN = 60 * 1000;
const T0 = Date.UTC(2026, 9, 22, 8, 0, 0);

function loggedIn(lastActivity) {
  const initial = { access_token: 'a', refresh_token: 'r', user: '{"role":"admin"}' };
  if (lastActivity !== undefined) initial[LAST_ACTIVITY_KEY] = String(lastActivity);
  return memoryStorage(initial);
}

test('the timeout is the 30 minutes the footer promises', () => {
  assert.equal(IDLE_TIMEOUT_MS, 30 * MIN);
});

test('recent activity neither warns nor expires', () => {
  assert.deepEqual(idleStatus(loggedIn(T0), T0 + 10 * MIN), { expired: false, secondsLeft: null });
});

test('the last minute before the timeout counts down in whole seconds', () => {
  assert.deepEqual(idleStatus(loggedIn(T0), T0 + 29 * MIN + 30_500), { expired: false, secondsLeft: 30 });
});

test('30 minutes without activity expires the session', () => {
  assert.equal(idleStatus(loggedIn(T0), T0 + 30 * MIN).expired, true);
});

test('polling is not activity: only recordActivity moves the stamp', () => {
  const storage = loggedIn(T0);
  recordActivity(storage, T0 + 20 * MIN);

  assert.equal(idleStatus(storage, T0 + 45 * MIN).expired, false);
  assert.equal(idleStatus(storage, T0 + 50 * MIN).expired, true);
});

test('activity is written at most once per gap so mousemove stays cheap', () => {
  const storage = loggedIn(T0);

  recordActivity(storage, T0 + 2_000, 5_000);
  assert.equal(storage.getItem(LAST_ACTIVITY_KEY), String(T0));

  recordActivity(storage, T0 + 5_000, 5_000);
  assert.equal(storage.getItem(LAST_ACTIVITY_KEY), String(T0 + 5_000));
});

test('reopening the app after the timeout clears the stored session', () => {
  const storage = loggedIn(T0);

  assert.equal(expireIdleSession(storage, T0 + 2 * 60 * MIN), true);
  for (const key of ['access_token', 'refresh_token', 'user']) {
    assert.equal(storage.getItem(key), null, `${key} must be cleared`);
  }
});

test('reopening within the timeout keeps the session', () => {
  const storage = loggedIn(T0);

  assert.equal(expireIdleSession(storage, T0 + 5 * MIN), false);
  assert.equal(storage.getItem('access_token'), 'a');
});

test('a session from before idle tracking starts its idle clock instead of ending', () => {
  const storage = loggedIn(undefined);

  assert.equal(expireIdleSession(storage, T0), false);
  assert.equal(storage.getItem('access_token'), 'a');
  assert.equal(storage.getItem(LAST_ACTIVITY_KEY), String(T0));
});

test('without a session there is nothing to expire', () => {
  const storage = memoryStorage({ [LAST_ACTIVITY_KEY]: String(T0) });

  assert.equal(expireIdleSession(storage, T0 + 2 * 60 * MIN), false);
});
