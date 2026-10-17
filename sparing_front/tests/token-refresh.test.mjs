import assert from 'node:assert/strict';
import test from 'node:test';
import { createTokenRefresher, refreshRequestBody } from '../resources/js/Utils/tokenRefresh.js';

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial));
  return {
    getItem: (key) => (values.has(key) ? values.get(key) : null),
    setItem: (key, value) => values.set(key, String(value)),
    removeItem: (key) => values.delete(key),
  };
}

test('concurrent 401s share a single refresh request', async () => {
  const storage = memoryStorage({ access_token: 'old-a', refresh_token: 'old-r' });
  let calls = 0;
  const refresh = createTokenRefresher({
    storage,
    postRefresh: async (token) => {
      calls += 1;
      assert.equal(token, 'old-r');
      await new Promise((resolve) => setTimeout(resolve, 5));
      return { access_token: 'new-a', refresh_token: 'new-r' };
    },
  });

  const tokens = await Promise.all([refresh(), refresh(), refresh()]);

  assert.equal(calls, 1);
  assert.deepEqual(tokens, ['new-a', 'new-a', 'new-a']);
  assert.equal(storage.getItem('refresh_token'), 'new-r');
});

test('a token already rotated by another tab is reused instead of failing', async () => {
  const storage = memoryStorage({ access_token: 'old-a', refresh_token: 'old-r' });
  const refresh = createTokenRefresher({
    storage,
    postRefresh: async () => {
      // The other tab won the race and stored fresh tokens meanwhile.
      storage.setItem('access_token', 'tab2-a');
      storage.setItem('refresh_token', 'tab2-r');
      throw Object.assign(new Error('401'), { response: { status: 401 } });
    },
  });

  assert.equal(await refresh(), 'tab2-a');
});

test('a genuinely expired session still fails', async () => {
  const storage = memoryStorage({ refresh_token: 'dead-r' });
  const refresh = createTokenRefresher({
    storage,
    postRefresh: async () => { throw new Error('401'); },
  });

  await assert.rejects(refresh());
});

test('a later 401 after a finished refresh starts a new refresh', async () => {
  const storage = memoryStorage({ refresh_token: 'r1' });
  let calls = 0;
  const refresh = createTokenRefresher({
    storage,
    postRefresh: async () => { calls += 1; return { access_token: `a${calls}`, refresh_token: `r${calls + 1}` }; },
  });

  await refresh();
  await refresh();

  assert.equal(calls, 2);
});

test('the refresh token travels in the JSON body, not the URL', () => {
  assert.deepEqual(refreshRequestBody('abc'), { refresh_token: 'abc' });
});
