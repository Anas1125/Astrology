import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Account, getAccount, login as apiLogin, register as apiRegister, COOKIE_AUTH, COOKIE_SESSION, loginSession, registerSession, logoutSession } from './api';

type AuthState = {
  account: Account | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = 'astroai_access_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => COOKIE_AUTH ? null : (localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY)));
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    localStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setAccount(null);
  }, []);

  const acceptToken = useCallback(async (accessToken: string, rememberMe = false) => {
    if (rememberMe) {
      localStorage.setItem(TOKEN_KEY, accessToken);
      sessionStorage.removeItem(TOKEN_KEY);
    } else {
      sessionStorage.setItem(TOKEN_KEY, accessToken);
      localStorage.removeItem(TOKEN_KEY);
    }
    setToken(accessToken);
    try {
      const actualAccount = await getAccount(accessToken);
      setAccount(actualAccount);
    } catch (error) {
      clearSession();
      throw error;
    }
  }, [clearSession]);

  useEffect(() => {
    let cancelled = false;
    const restore = async () => {
      if (COOKIE_AUTH) {
        localStorage.removeItem(TOKEN_KEY);
        sessionStorage.removeItem(TOKEN_KEY);
      }
      const saved = COOKIE_AUTH ? COOKIE_SESSION : (localStorage.getItem(TOKEN_KEY) ?? sessionStorage.getItem(TOKEN_KEY));
      if (!saved) {
        setLoading(false);
        return;
      }
      try {
        const actualAccount = await getAccount(saved);
        if (!cancelled) {
          setToken(saved);
          setAccount(actualAccount);
        }
      } catch {
        if (!cancelled) clearSession();
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void restore();
    return () => { cancelled = true; };
  }, [clearSession]);

  useEffect(() => {
    const onUnauthorized = () => clearSession();
    window.addEventListener('astroai:unauthorized', onUnauthorized);
    return () => window.removeEventListener('astroai:unauthorized', onUnauthorized);
  }, [clearSession]);

  const login = useCallback(async (email: string, password: string, rememberMe = false) => {
    if (COOKIE_AUTH) {
      const actualAccount = await loginSession(email, password, rememberMe);
      clearSession();
      setToken(COOKIE_SESSION);
      setAccount(actualAccount);
      return;
    }
    const response = await apiLogin(email, password, rememberMe);
    await acceptToken(response.access_token, rememberMe);
  }, [acceptToken, clearSession]);

  const register = useCallback(async (email: string, password: string) => {
    if (COOKIE_AUTH) {
      const actualAccount = await registerSession(email, password);
      clearSession();
      setToken(COOKIE_SESSION);
      setAccount(actualAccount);
      return;
    }
    const response = await apiRegister(email, password);
    await acceptToken(response.access_token);
  }, [acceptToken, clearSession]);

  const logout = useCallback(async () => {
    if (COOKIE_AUTH) await logoutSession();
    clearSession();
  }, [clearSession]);
  const value = useMemo(() => ({ account, token, loading, login, register, logout }), [account, token, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
