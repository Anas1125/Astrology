import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Account, getAccount, login as apiLogin, register as apiRegister } from './api';

type AuthState = {
  account: Account | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthState | null>(null);
const TOKEN_KEY = 'astroai_access_token';

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [account, setAccount] = useState<Account | null>(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setAccount(null);
  }, []);

  const acceptToken = useCallback(async (accessToken: string) => {
    sessionStorage.setItem(TOKEN_KEY, accessToken);
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
      const saved = sessionStorage.getItem(TOKEN_KEY);
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

  const login = useCallback(async (email: string, password: string) => {
    const response = await apiLogin(email, password);
    await acceptToken(response.access_token);
  }, [acceptToken]);

  const register = useCallback(async (email: string, password: string) => {
    const response = await apiRegister(email, password);
    await acceptToken(response.access_token);
  }, [acceptToken]);

  const logout = useCallback(() => clearSession(), [clearSession]);
  const value = useMemo(() => ({ account, token, loading, login, register, logout }), [account, token, loading, login, register, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
