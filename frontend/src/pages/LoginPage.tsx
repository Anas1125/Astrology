import { useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Brand from '../components/Brand';
import { useAuth } from '../auth/AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const destination = (location.state as { from?: string } | null)?.from ?? '/app';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setSubmitting(true);
    try { await login(email.trim(), password); navigate(destination, { replace: true }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to log in. Please try again.'); }
    finally { setSubmitting(false); }
  }

  return <AuthLayout eyebrow="WELCOME BACK" title="Your sky is waiting." subtitle="Log in to continue to your personal astrology space."><form className="auth-form" onSubmit={handleSubmit}>
    <label htmlFor="login-email">Email address</label><div className="auth-input"><Mail size={17}/><input id="login-email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"/></div>
    <label htmlFor="login-password">Password</label><div className="auth-input"><LockKeyhole size={17}/><input id="login-password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} placeholder="Your password"/><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>
    {error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={submitting}>{submitting ? 'Logging in…' : 'Log in'} <ArrowRight size={16}/></button>
  </form><p className="auth-switch">New to AstroAI? <Link to="/register">Create an account</Link></p></AuthLayout>;
}

export function AuthLayout({ eyebrow, title, subtitle, children }: { eyebrow: string; title: string; subtitle: string; children: ReactNode }) {
  return <div className="auth-page"><header className="auth-header"><Link to="/" aria-label="Back to AstroAI home"><ArrowLeft size={17}/><span>Home</span></Link><Brand/></header><main className="auth-card"><div className="auth-symbol"><LockKeyhole size={19}/></div><div className="eyebrow gold-text">{eyebrow}</div><h1>{title}</h1><p className="auth-subtitle">{subtitle}</p>{children}<div className="auth-privacy">Your account details stay private and secure.</div></main></div>;
}
