// Access-token refresh shared by every API call on the page.
//
// The dashboard fires several requests at once; when the access token expires
// they all get 401 together. Refreshing once per 401 sent the same refresh
// token several times — the server rotates it on the first call, so the rest
// failed and the user was logged out. One refresh is kept in flight and every
// caller awaits it. Another tab may also rotate the token first; its stored
// tokens are then reused instead of failing.

export function refreshRequestBody(refreshToken) {
  return { refresh_token: refreshToken };
}

export function createTokenRefresher({ storage, postRefresh }) {
  let inFlight = null;

  async function run() {
    const startToken = storage.getItem('refresh_token');
    if (!startToken) throw new Error('no_refresh_token');
    try {
      const data = await postRefresh(startToken);
      storage.setItem('access_token', data.access_token);
      storage.setItem('refresh_token', data.refresh_token);
      return data.access_token;
    } catch (error) {
      const current = storage.getItem('refresh_token');
      if (current && current !== startToken && storage.getItem('access_token')) {
        return storage.getItem('access_token');
      }
      throw error;
    }
  }

  return function refreshAccessToken() {
    if (!inFlight) inFlight = run().finally(() => { inFlight = null; });
    return inFlight;
  };
}
