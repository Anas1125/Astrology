import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';

export default function ProtectedRoute() {
  const { account, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="auth-loading" role="status">Restoring your secure session…</div>;
  return account ? <Outlet /> : <Navigate to="/login" replace state={{ from: location.pathname }} />;
}
