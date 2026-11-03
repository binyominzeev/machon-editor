(() => {
  const config = window.MACHON_CONFIG || { enabled: false };
  const tokenKey = 'machon.accessToken';
  const refreshTokenKey = 'machon.refreshToken';
  const userNameKey = 'machon.userName';
  const userIdKey = 'machon.userId';
  const verifierKey = 'machon.pkceVerifier';
  const returnPathKey = 'machon.returnPath';
  const shellReloadKey = 'machon.shellReload';
  const cookieName = 'machon_at';
  const isLoginShell = document.body.hasAttribute('data-login');
  // Olvasó módban kapott oldal: ha közben van érvényes token, újratöltjük szerkeszthetőként.
  const isReadonlyPage = document.body.hasAttribute('data-readonly');
  let accessToken = localStorage.getItem(tokenKey);
  let refreshToken = localStorage.getItem(refreshTokenKey);
  let userName = localStorage.getItem(userNameKey) || '';
  let userId = localStorage.getItem(userIdKey) || decodeJwtPayload(accessToken).sub || '';
  let refreshTimer = null;
  let refreshing = null;

  function decodeJwtPayload(token) {
    try {
      const normalized = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
      return JSON.parse(atob(normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')));
    } catch {
      return {};
    }
  }

  function base64Url(bytes) {
    let binary = '';
    bytes.forEach(byte => { binary += String.fromCharCode(byte); });
    return btoa(binary).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
  }

  async function createCodeChallenge(verifier) {
    const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
    return base64Url(new Uint8Array(digest));
  }

  function createVerifier() {
    const bytes = new Uint8Array(32);
    crypto.getRandomValues(bytes);
    return base64Url(bytes);
  }

  function redirectUri() {
    return `${window.location.origin}/`;
  }

  // Az oldal-navigációt (HTML) a szerver ebből a sütiből azonosítja; az API-hívások Authorization-fejlécet használnak.
  function syncCookie(exp) {
    if (!accessToken) {
      document.cookie = `${cookieName}=; path=/; max-age=0; SameSite=Lax`;
      return;
    }
    const maxAge = exp ? Math.max(Math.floor(exp - Date.now() / 1000), 0) : 3600;
    const secure = window.location.protocol === 'https:' ? '; Secure' : '';
    document.cookie = `${cookieName}=${accessToken}; path=/; max-age=${maxAge}; SameSite=Lax${secure}`;
  }

  function applyTokens(tokens) {
    accessToken = tokens.access_token;
    if (tokens.refresh_token) refreshToken = tokens.refresh_token;
    const claims = decodeJwtPayload(tokens.id_token || accessToken);
    const accessClaims = decodeJwtPayload(accessToken);
    userName = claims.name || claims.preferred_username || claims.email || 'felhasználó';
    userId = claims.sub || accessClaims.sub || '';
    localStorage.setItem(tokenKey, accessToken);
    localStorage.setItem(userNameKey, userName);
    if (userId) localStorage.setItem(userIdKey, userId);
    if (refreshToken) localStorage.setItem(refreshTokenKey, refreshToken);
    syncCookie(accessClaims.exp);
    scheduleRefresh(accessClaims.exp);
  }

  function scheduleRefresh(exp) {
    if (refreshTimer) clearTimeout(refreshTimer);
    if (!exp || !refreshToken) return;
    // Lejárat előtt 60 mp-cel frissítünk.
    const delay = Math.max(exp * 1000 - Date.now() - 60000, 5000);
    refreshTimer = setTimeout(() => { refreshAccessToken().catch(() => {}); }, delay);
  }

  function refreshAccessToken() {
    if (!refreshToken) return Promise.reject(new Error('No refresh token available'));
    if (!refreshing) {
      refreshing = (async () => {
        const response = await fetch('/api/auth/refresh', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: new URLSearchParams({ refresh_token: refreshToken })
        });
        const text = await response.text();
        if (!response.ok) throw new Error(`Refresh failed (${response.status}): ${text}`);
        applyTokens(JSON.parse(text));
        document.dispatchEvent(new CustomEvent('machon-auth-updated'));
        return accessToken;
      })().finally(() => { refreshing = null; });
    }
    return refreshing;
  }

  async function login() {
    if (!config.oidcClientId) throw new Error('OIDC client ID is not configured');
    const issuer = config.oidcIssuer.replace(/\/$/, '');
    const response = await fetch(`${issuer}/.well-known/openid-configuration`);
    if (!response.ok) throw new Error('OIDC discovery failed');
    const metadata = await response.json();
    const verifier = createVerifier();
    sessionStorage.setItem(verifierKey, verifier);
    sessionStorage.setItem(returnPathKey, `${window.location.pathname}${window.location.search}`);
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: config.oidcClientId,
      redirect_uri: redirectUri(),
      scope: 'openid profile email offline_access',
      state: verifier,
      code_challenge: await createCodeChallenge(verifier),
      code_challenge_method: 'S256'
    });
    window.location.assign(`${metadata.authorization_endpoint}?${params}`);
  }

  // Visszatérés a Pocket ID-ból: code -> token csere a saját backendünkön át.
  async function handleCallback() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('error')) {
      throw new Error(`OIDC authorization failed: ${params.get('error')}${params.get('error_description') ? ` (${params.get('error_description')})` : ''}`);
    }
    const code = params.get('code');
    if (!code) return false;
    const verifier = sessionStorage.getItem(verifierKey);
    if (!verifier || params.get('state') !== verifier) throw new Error('Invalid OIDC state');
    const response = await fetch('/api/auth/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ code, code_verifier: verifier, redirect_uri: redirectUri() })
    });
    const text = await response.text();
    if (!response.ok) throw new Error(`OIDC token exchange failed (${response.status}): ${text || 'empty response'}`);
    const tokens = JSON.parse(text);
    if (!tokens.access_token) throw new Error('OIDC token exchange returned no access token');
    applyTokens(tokens);
    sessionStorage.removeItem(verifierKey);
    const returnPath = sessionStorage.getItem(returnPathKey) || '/';
    sessionStorage.removeItem(returnPathKey);
    window.history.replaceState(null, '', returnPath);
    return true;
  }

  function logout(reload = true) {
    accessToken = null;
    refreshToken = null;
    userName = '';
    userId = '';
    if (refreshTimer) clearTimeout(refreshTimer);
    localStorage.removeItem(tokenKey);
    localStorage.removeItem(refreshTokenKey);
    localStorage.removeItem(userNameKey);
    localStorage.removeItem(userIdKey);
    syncCookie();
    document.dispatchEvent(new CustomEvent('machon-auth-updated'));
    if (reload) window.location.reload();
  }

  // Pontosan egyszeri refresh-then-retry, utána kijelentkeztetés (nincs végtelen ciklus).
  async function authFetch(path, options = {}, retried = false) {
    if (!config.enabled) return fetch(path, options);
    await ready;
    const send = () => fetch(path, {
      ...options,
      headers: { ...(options.headers || {}), Authorization: `Bearer ${accessToken || ''}` }
    });
    const response = await send();
    if (response.status !== 401) return response;
    if (!retried && refreshToken) {
      try {
        await refreshAccessToken();
        return authFetch(path, options, true);
      } catch { /* a kijelentkeztetés lent történik */ }
    }
    logout();
    return response;
  }

  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible' || !accessToken) return;
    const exp = decodeJwtPayload(accessToken).exp;
    if (exp && exp * 1000 - Date.now() < 60000) {
      refreshAccessToken().catch(error => {
        if (navigator.onLine && !(error instanceof TypeError)) logout(false);
      });
    }
  });

  function showError(message) {
    const status = document.getElementById('auth-status');
    if (status) status.textContent = `Bejelentkezési hiba: ${message}`;
    const button = document.getElementById('login-button');
    if (button && isLoginShell) button.hidden = false;
  }

  function updateControls() {
    const status = document.getElementById('auth-status');
    const button = document.getElementById('login-button');
    const bar = document.getElementById('auth-controls');
    if (bar) bar.hidden = !config.enabled;
    if (isLoginShell) {
      if (button) { button.hidden = false; button.onclick = () => login().catch(e => showError(e.message)); }
      return;
    }
    if (status) status.textContent = accessToken ? userName : 'Csak olvasható';
    if (button) {
      button.textContent = accessToken ? 'Kilépés' : 'Belépés';
      button.onclick = () => accessToken ? logout() : login().catch(e => showError(e.message));
    }
  }

  async function initialize() {
    if (!config.enabled) return;
    try {
      await handleCallback();
      if (accessToken) {
        const exp = decodeJwtPayload(accessToken).exp;
        if (!exp || exp * 1000 - Date.now() < 60000) {
          if (refreshToken) {
            await refreshAccessToken().catch(error => {
              if (navigator.onLine && !(error instanceof TypeError)) logout(false);
            });
          }
          else logout(false);
        } else {
          syncCookie(exp);
          scheduleRefresh(exp);
        }
      }
    } catch (error) {
      updateControls();
      showError(error.message);
      return;
    }
    if ((isLoginShell || isReadonlyPage) && accessToken) {
      // A szerver még login/olvasó oldalt adott; a süti beállítva, újratöltés. Hibás konfigurációnál nem pörgünk végtelen ciklusban.
      const last = Number(sessionStorage.getItem(shellReloadKey) || 0);
      if (Date.now() - last > 15000) {
        sessionStorage.setItem(shellReloadKey, String(Date.now()));
        window.location.replace(window.location.pathname + window.location.search);
        return;
      }
      showError('a szerver nem fogadta el a tokent');
      return;
    }
    updateControls();
  }

  const ready = initialize();

  window.MachonAuth = {
    fetch: authFetch,
    login: () => login().catch(e => showError(e.message)),
    logout,
    ready,
    isAuthenticated: () => Boolean(accessToken),
    getUserName: () => userName,
    getUserId: () => userId || 'anonymous'
  };

  document.addEventListener('DOMContentLoaded', updateControls);
  document.addEventListener('machon-auth-updated', updateControls);
})();
