import { useState } from 'react';
import type { FormEvent, ReactNode } from 'react';
import { ArrowLeft, ArrowRight, Eye, EyeOff, LockKeyhole, Mail } from 'lucide-react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Brand from '../components/Brand';
import { useAuth } from '../auth/AuthContext';
import { useAstroLanguage } from '../auth/language';

export default function LoginPage() {
  const { login } = useAuth();
  const [language] = useAstroLanguage();
  const navigate = useNavigate();
  const location = useLocation();
  const destination = (location.state as { from?: string } | null)?.from ?? '/app';
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(''); setSubmitting(true);
    try { await login(email.trim(), password, rememberMe); navigate(destination, { replace: true }); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to log in. Please try again.'); }
    finally { setSubmitting(false); }
  }

  return <AuthLayout eyebrow="WELCOME BACK" title="Your sky is waiting." subtitle="Log in to continue to your personal astrology space."><form className="auth-form" onSubmit={handleSubmit}>
    <label htmlFor="login-email">Email address</label><div className="auth-input"><Mail size={17}/><input id="login-email" type="email" autoComplete="email" required maxLength={320} value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com"/></div>
    <div className="auth-label-row"><label htmlFor="login-password">Password</label><Link to="/forgot-password">{language === 'ta' ? 'கடவுச்சொல் மறந்துவிட்டீர்களா?' : 'Forgot password?'}</Link></div><div className="auth-input"><LockKeyhole size={17}/><input id="login-password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" required value={password} onChange={e => setPassword(e.target.value)} placeholder="Your password"/><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></div>
    <label className="remember-me"><input type="checkbox" checked={rememberMe} onChange={e => setRememberMe(e.target.checked)} /><span>{language === 'ta' ? 'என்னை நினைவில் கொள்ளவும்' : 'Remember me'}</span></label>
    {error && <p className="auth-error" role="alert">{error}</p>}<button className="auth-submit" type="submit" disabled={submitting}>{submitting ? 'Logging in…' : 'Log in'} <ArrowRight size={16}/></button>
  </form><p className="auth-switch">New to AstroAI? <Link to="/register">Create an account</Link></p></AuthLayout>;
}

export function AuthLayout({ eyebrow, title, subtitle, children }: { eyebrow: string; title: string; subtitle: string; children: ReactNode }) {
  const [language, setLanguage] = useAstroLanguage();
  const home = language === 'ta' ? 'முகப்பு' : 'Home';
  const privacy = language === 'ta' ? 'உங்கள் கணக்கு விவரங்கள் தனிப்பட்டும் பாதுகாப்பாகவும் இருக்கும்.' : 'Your account details stay private and secure.';
  return <div className="auth-page"><header className="auth-header"><Link to="/" aria-label={language === 'ta' ? 'AstroAI முகப்புக்குத் திரும்பு' : 'Back to AstroAI home'}><ArrowLeft size={17}/><span>{home}</span></Link><Brand/><button className="auth-language" onClick={() => setLanguage(language === 'en' ? 'ta' : 'en')} aria-label={language === 'en' ? 'தமிழுக்கு மாற்று' : 'Switch to English'}>{language === 'en' ? 'தமிழ்' : 'EN'}</button></header><main className="auth-card"><div className="auth-symbol"><LockKeyhole size={19}/></div><div className="eyebrow gold-text">{eyebrow}</div><h1>{title}</h1><p className="auth-subtitle">{subtitle}</p>{children}<div className="auth-privacy">{privacy}</div></main></div>;
}
